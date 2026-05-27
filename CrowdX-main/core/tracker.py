def track_people(frame, detections):
    objects = []

    for i, (x, y, w, h) in enumerate(detections):
        objects.append((i, x, y, w, h))

    return objects