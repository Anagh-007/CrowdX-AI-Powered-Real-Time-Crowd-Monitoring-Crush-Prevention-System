import cv2
import numpy as np

def generate_heatmap(frame, objects):

    heatmap = np.zeros((frame.shape[0], frame.shape[1]), dtype=np.float32)

    for (_, x, y, w, h) in objects:
        cx = x + w//2
        cy = y + h//2

        cv2.circle(heatmap, (cx, cy), 50, 1, -1)

    heatmap = cv2.GaussianBlur(heatmap, (51,51), 0)

    heatmap = np.uint8(255 * heatmap / np.max(heatmap + 1e-5))
    heatmap = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)

    return cv2.addWeighted(frame, 0.6, heatmap, 0.4, 0)