"""
CrowdX — server.py
HOW TO RUN:
  1. pip install pymongo
  2. python server.py
  3. Open Chrome/Edge → http://localhost:5000
  NEVER open dashboard.html as a file — it won't work
"""

from flask import Flask, Response, render_template, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import cv2, numpy as np, threading, time
from datetime import datetime, timezone

# ── MongoDB ──
try:
    from pymongo import MongoClient, DESCENDING
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

    MONGO_URI = "mongodb://localhost:27017/"   # ← change if using Atlas: "mongodb+srv://user:pass@cluster.mongodb.net/"
    DB_NAME   = "crowdx"

    _mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    _mongo_client.admin.command("ping")        # test connection
    _db            = _mongo_client[DB_NAME]
    alerts_col     = _db["alerts"]             # overcrowd / surge alerts
    snapshots_col  = _db["snapshots"]          # periodic crowd snapshots

    # indexes for fast queries
    alerts_col.create_index([("timestamp", DESCENDING)])
    alerts_col.create_index([("camera", 1)])
    snapshots_col.create_index([("timestamp", DESCENDING)])

    MONGO_OK = True
    print("[MongoDB] ✅ Connected to", MONGO_URI)

except Exception as _me:
    MONGO_OK = False
    alerts_col = snapshots_col = None
    print(f"[MongoDB] ⚠️  Not connected ({_me}). Running without DB.")


def db_save_alert(alert_type, camera, count, zones, growth_rate, location_url):
    """Save an overcrowd / surge alert document."""
    if not MONGO_OK:
        return
    try:
        doc = {
            "timestamp":    datetime.now(timezone.utc),
            "type":         alert_type,          # "OVERCROWD" | "SURGE"
            "camera":       camera,              # "cam1" | "cam2"
            "people_count": count,
            "unsafe_zones": zones,
            "growth_rate":  round(growth_rate, 3),
            "location_url": location_url,
            "resolved":     False,
        }
        alerts_col.insert_one(doc)
    except Exception as e:
        print(f"[MongoDB] alert save error: {e}")


def db_resolve_alerts(camera):
    """Mark all unresolved alerts for a camera as resolved."""
    if not MONGO_OK:
        return
    try:
        alerts_col.update_many(
            {"camera": camera, "resolved": False},
            {"$set": {"resolved": True, "resolved_at": datetime.now(timezone.utc)}}
        )
    except Exception as e:
        print(f"[MongoDB] resolve error: {e}")


def db_save_snapshot(camera, count, trend_label, growth_rate, overcrowd, unsafe_zones):
    """Save a periodic crowd-state snapshot every N seconds."""
    if not MONGO_OK:
        return
    try:
        doc = {
            "timestamp":    datetime.now(timezone.utc),
            "camera":       camera,
            "people_count": count,
            "trend":        trend_label,
            "growth_rate":  round(growth_rate, 3),
            "overcrowd":    overcrowd,
            "unsafe_zones": unsafe_zones,
        }
        snapshots_col.insert_one(doc)
    except Exception as e:
        print(f"[MongoDB] snapshot save error: {e}")


# ── App imports ──
from core.detector       import detect_people
from core.tracker        import track_people
from core.density_engine import compute_density
from core.risk_engine    import compute_risk
from core.trend_engine   import TrendEngine
from utils.heatmap       import generate_heatmap
from utils.visualizer    import draw
from utils.sound_alert   import play_alert
from utils.location      import get_location
from alerts.alert_manager import send_alert

app = Flask(__name__)
app.config['SECRET_KEY'] = 'crowdx-2024'
CORS(app, origins="*")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ── Latest JPEG bytes for each camera ──
frames = {"cam1": None, "cam2": None}
flocks = {"cam1": threading.Lock(), "cam2": threading.Lock()}

# ── Shared dashboard state ──
state = {
    "cam1": {"total":0,"overcrowd":False,"zones":{},"overcrowd_zones":[],
             "trend":{"trend_label":"STABLE","growth_rate":0.0,"predicted_count":0,"predicted_crash":False},
             "best_zone":None,"safe_zones":[]},
    "cam2": {"total":0,"overcrowd":False,"zones":{},"overcrowd_zones":[],
             "trend":{"trend_label":"STABLE","growth_rate":0.0,"predicted_count":0,"predicted_crash":False},
             "best_zone":None,"safe_zones":[]},
    "global_status":"SAFE",
    "message_for_crowd":{"status":"SAFE","headline":"Zone Safe","body":"Monitoring...","action":"All clear","color":"green"},
}
slock        = threading.Lock()
alert_active = {"cam1": False, "cam2": False}   # per-camera alert flags
CONF_TH      = 0.3
SIM_MODE     = True
SIM_TH       = 3
trend1, trend2 = TrendEngine(), TrendEngine()

# snapshot every 10 seconds per camera
_last_snapshot = {"cam1": 0.0, "cam2": 0.0}
SNAPSHOT_INTERVAL = 10


def blank_jpg(msg="No Signal"):
    f = np.zeros((480,640,3), dtype=np.uint8)
    cv2.putText(f, msg,            (150,230), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (70,70,70), 2)
    cv2.putText(f, "Check camera",(190,270), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (50,50,50), 1)
    _, buf = cv2.imencode('.jpg', f)
    return buf.tobytes()


def to_jpg(frame):
    _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return buf.tobytes()


def maps_link():
    try:
        r = get_location()
        if r and len(r)>=2 and r[0]:
            return f"https://www.google.com/maps?q={r[0]},{r[1]}"
    except:
        pass
    return "Location unavailable"


def crowd_msg(cam):
    t, n, sz = cam["trend"]["trend_label"], cam["total"], cam.get("safe_zones",[])
    if cam["overcrowd"] or t == "SURGING":
        return {"status":"DANGER","headline":"OVERCROWDED","body":f"{n} people. HIGH crush risk.",
                "action":f"Move to Zone {sz[0]}" if sz else "Go to nearest exit","color":"red"}
    if t == "GROWING":
        return {"status":"WARNING","headline":"Crowd Growing","body":f"{n} people. Move away.",
                "action":"Find open space","color":"orange"}
    return {"status":"SAFE","headline":"Zone Safe","body":f"{n} people. All clear.","action":"Continue","color":"green"}


# ── Camera processing thread ──
def camera_thread(source, key, trend_eng):
    print(f"[{key}] Opening {source}")
    cap = cv2.VideoCapture(source)
    if key == 'cam1':
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
    print(f"[{key}] Opened: {cap.isOpened()}")

    fails = 0
    count, overcrowd, overcrowd_zones = 0, False, []
    trend_data = {"trend_label":"STABLE","growth_rate":0.0,"predicted_count":0,"predicted_crash":False}

    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            fails += 1
            if fails % 50 == 0:
                print(f"[{key}] {fails} read failures, reconnecting...")
                cap.release(); time.sleep(1)
                cap = cv2.VideoCapture(source)
            with flocks[key]: frames[key] = blank_jpg(f"{key.upper()} — No Signal")
            time.sleep(0.05)
            continue
        fails = 0

        try:
            raw      = detect_people(frame)
            det      = [d for d in raw if d[-1] >= CONF_TH]
            trk      = track_people(frame, det)
            den      = compute_density(trk)
            risk_map, count, overcrowd, overcrowd_zones = compute_risk(den)

            zc = {z: den.get(z,0) for z in overcrowd_zones} if overcrowd_zones else den
            trend_eng.update(count, zc)
            trend_data = trend_eng.get_summary()

            if SIM_MODE and count >= SIM_TH:
                overcrowd, overcrowd_zones = True, list(den.keys())
                trend_data["trend_label"]     = "SURGING"
                trend_data["predicted_crash"] = True

            zones_info, safe_zones = {}, []
            for z,(zn,risk) in risk_map.items():
                zones_info[str(z)] = {"count":zn,"risk":risk,"status":"danger" if z in overcrowd_zones else "safe"}
                if z not in overcrowd_zones: safe_zones.append(z)
            best = min(safe_zones, key=lambda z: risk_map[z][0]) if safe_zones else None

            frame = generate_heatmap(frame, trk)
            frame = draw(frame, trk, risk_map, count, overcrowd, overcrowd_zones, trend_data)

            with slock:
                state[key].update({
                    "total":count,"overcrowd":overcrowd,"zones":zones_info,
                    "overcrowd_zones":[str(z) for z in overcrowd_zones],
                    "trend":trend_data,
                    "best_zone":str(best) if best else None,
                    "safe_zones":[str(z) for z in safe_zones]
                })
                state["message_for_crowd"] = crowd_msg(state[key])
                if overcrowd or trend_data.get("predicted_crash"): state["global_status"] = "DANGER"
                elif trend_data["trend_label"] == "GROWING":        state["global_status"] = "WARNING"
                else:                                                state["global_status"] = "SAFE"

            # emit to dashboard
            try:
                with slock: socketio.emit('crowd_update', state)
            except: pass

            # ── periodic snapshot to MongoDB ──
            now = time.time()
            if now - _last_snapshot[key] >= SNAPSHOT_INTERVAL:
                _last_snapshot[key] = now
                threading.Thread(
                    target=db_save_snapshot,
                    args=(key, count, trend_data["trend_label"],
                          trend_data["growth_rate"], overcrowd,
                          [str(z) for z in overcrowd_zones]),
                    daemon=True
                ).start()

        except Exception as e:
            print(f"[{key}] Processing error: {e}")

        # store frame
        try:
            with flocks[key]: frames[key] = to_jpg(frame)
        except: pass

        # ── Alerts + MongoDB save ──
        try:
            loc = maps_link()

            if trend_data.get("predicted_crash") and not alert_active[key]:
                send_alert(f"⚠️ SURGE WARNING\nCount:{count}\nRate:+{trend_data['growth_rate']:.2f}/s\n{loc}")
                play_alert()
                alert_active[key] = True
                threading.Thread(
                    target=db_save_alert,
                    args=("SURGE", key, count,
                          [str(z) for z in overcrowd_zones],
                          trend_data["growth_rate"], loc),
                    daemon=True
                ).start()

            elif overcrowd and not alert_active[key]:
                send_alert(f"🚨 OVERCROWD\nCount:{count}\nZones:{','.join([str(z) for z in overcrowd_zones])}\n{loc}")
                play_alert()
                alert_active[key] = True
                threading.Thread(
                    target=db_save_alert,
                    args=("OVERCROWD", key, count,
                          [str(z) for z in overcrowd_zones],
                          trend_data["growth_rate"], loc),
                    daemon=True
                ).start()

            if count < SIM_TH and not trend_data.get("predicted_crash"):
                if alert_active[key]:
                    alert_active[key] = False
                    threading.Thread(target=db_resolve_alerts, args=(key,), daemon=True).start()

        except: pass


# ── MJPEG stream generator ──
def mjpeg(key):
    fb = blank_jpg(f"{key.upper()} Starting...")
    while True:
        with flocks[key]:
            data = frames[key] or fb
        yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + data + b'\r\n'
        time.sleep(0.033)


# ── Flask routes ──
@app.route('/stream/cam1')
def stream1(): return Response(mjpeg('cam1'), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/stream/cam2')
def stream2(): return Response(mjpeg('cam2'), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index(): return render_template('dashboard.html')

@app.route('/crowd')
def crowd(): return render_template('crowd.html')

@app.route('/api/state')
def api_state():
    with slock: return jsonify(state)

@app.route('/api/crowd-status')
def api_crowd():
    with slock:
        return jsonify({
            "status":  state["global_status"],
            "message": state["message_for_crowd"],
            "cam1":    {"total":state["cam1"]["total"],"trend":state["cam1"]["trend"]["trend_label"],"best_zone":state["cam1"]["best_zone"]},
            "cam2":    {"total":state["cam2"]["total"],"trend":state["cam2"]["trend"]["trend_label"],"best_zone":state["cam2"]["best_zone"]}
        })

# ── MongoDB API routes ──
@app.route('/api/alerts')
def api_alerts():
    """Return last 50 alerts from MongoDB."""
    if not MONGO_OK:
        return jsonify({"error": "MongoDB not connected"}), 503
    try:
        docs = list(alerts_col.find({}, {"_id":0}).sort("timestamp", DESCENDING).limit(50))
        for d in docs:
            d["timestamp"] = d["timestamp"].isoformat()
            if "resolved_at" in d:
                d["resolved_at"] = d["resolved_at"].isoformat()
        return jsonify(docs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/alerts/unresolved')
def api_alerts_unresolved():
    """Return all currently active (unresolved) alerts."""
    if not MONGO_OK:
        return jsonify({"error": "MongoDB not connected"}), 503
    try:
        docs = list(alerts_col.find({"resolved": False}, {"_id":0}).sort("timestamp", DESCENDING))
        for d in docs:
            d["timestamp"] = d["timestamp"].isoformat()
        return jsonify(docs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/snapshots')
def api_snapshots():
    """Return last 100 crowd snapshots from MongoDB."""
    if not MONGO_OK:
        return jsonify({"error": "MongoDB not connected"}), 503
    try:
        docs = list(snapshots_col.find({}, {"_id":0}).sort("timestamp", DESCENDING).limit(100))
        for d in docs:
            d["timestamp"] = d["timestamp"].isoformat()
        return jsonify(docs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/db-status')
def api_db_status():
    """Check MongoDB connection status."""
    return jsonify({"mongodb_connected": MONGO_OK, "db": DB_NAME if MONGO_OK else None})

@socketio.on('connect')
def on_connect():
    with slock: emit('crowd_update', state)


if __name__ == '__main__':
    frames['cam1'] = blank_jpg("CAM1 Starting...")
    frames['cam2'] = blank_jpg("CAM2 Starting...")

    t1 = threading.Thread(target=camera_thread, args=(0,                               'cam1', trend1), daemon=True)
    t2 = threading.Thread(target=camera_thread, args=("http://10.50.49.87:8080/video", 'cam2', trend2), daemon=True)
    t1.start()
    t2.start()

    print("\n" + "="*55)
    print("  CrowdX is running!")
    print("="*55)
    print("  ✅  Dashboard:       http://localhost:5000")
    print("  ✅  Crowd page:      http://localhost:5000/crowd")
    print("  ✅  Cam1 stream:     http://localhost:5000/stream/cam1")
    print("  ✅  Cam2 stream:     http://localhost:5000/stream/cam2")
    print()
    print("  ✅  MongoDB APIs:")
    print("      /api/alerts             ← last 50 alerts")
    print("      /api/alerts/unresolved  ← active alerts")
    print("      /api/snapshots          ← crowd history")
    print("      /api/db-status          ← connection check")
    print()
    if MONGO_OK:
        print(f"  ✅  MongoDB: connected  → db='{DB_NAME}'")
    else:
        print("  ⚠️   MongoDB: NOT connected (running without DB)")
    print()
    print("  ❌  DO NOT open dashboard.html as a file!")
    print("  ❌  DO NOT use VS Code Live Server!")
    print("="*55 + "\n")

    socketio.run(app, host='0.0.0.0', port=5000, debug=False, use_reloader=False)