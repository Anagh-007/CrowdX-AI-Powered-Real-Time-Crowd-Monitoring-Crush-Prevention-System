from flask import Flask, Response
import cv2
from core.detector import detect_people
from core.tracker import track_people
from core.density_engine import compute_density
from core.risk_engine import compute_risk
from utils.visualizer import draw

app = Flask(__name__)

cap = cv2.VideoCapture(0)

def generate_frames():
    while True:
        success, frame = cap.read()
        if not success:
            break

        detections = detect_people(frame)
        tracked = track_people(frame, detections)
        density = compute_density(tracked)
        risk_map, total_people, overcrowd, zones = compute_risk(density)

        frame = draw(frame, tracked, risk_map, total_people, overcrowd, zones)

        _, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')


@app.route('/video')
def video():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/')
def home():
    return "Crowd System Running"


if __name__ == "__main__":
    app.run(debug=True)