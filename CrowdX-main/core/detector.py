from ultralytics import YOLO

model = YOLO("yolov8n.pt")

def detect_people(frame):
    results = model(frame)[0]

    detections = []

    for r in results.boxes.data.tolist():
        x1, y1, x2, y2, score, cls = r

        if int(cls) == 0:  # person class
            detections.append([int(x1), int(y1), int(x2-x1), int(y2-y1)])

    return detections