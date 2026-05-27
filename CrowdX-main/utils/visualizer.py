import cv2
import config.settings as settings


def draw(frame, objects, risk_map, total_people, overcrowd, overcrowd_zones, trend_data=None):
    """
    Draw all overlays on the frame.

    Parameters
    ----------
    frame           : numpy array — current video frame
    objects         : list of (track_id, x, y, w, h)
    risk_map        : dict  { (row,col): (count, risk) }
    total_people    : int
    overcrowd       : bool  — global overcrowd flag
    overcrowd_zones : list  of (row,col) tuples
    trend_data      : dict  — keys: trend_label, growth_rate,
                                     predicted_count, predicted_crash
                      Pass None (or omit) to skip the trend panel.
    """

    if trend_data is None:
        trend_data = {}

    # =========================
    # Grid size
    # =========================
    zone_w = settings.FRAME_WIDTH  // settings.COLS
    zone_h = settings.FRAME_HEIGHT // settings.ROWS

    # =========================
    # Find BEST SAFE ZONE
    # =========================
    safe_zones = [
        (zone, count, risk)
        for zone, (count, risk) in risk_map.items()
        if zone not in overcrowd_zones
    ]

    best_zone = min(safe_zones, key=lambda x: x[1])[0] if safe_zones else None

    # =========================
    # Draw bounding boxes
    # =========================
    for (track_id, x, y, w, h) in objects:
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(frame, f"ID:{track_id}", (x, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # =========================
    # Draw grid lines
    # =========================
    for i in range(1, settings.COLS):
        cv2.line(frame,
                 (i * zone_w, 0),
                 (i * zone_w, settings.FRAME_HEIGHT),
                 (255, 0, 0), 2)

    for j in range(1, settings.ROWS):
        cv2.line(frame,
                 (0, j * zone_h),
                 (settings.FRAME_WIDTH, j * zone_h),
                 (255, 0, 0), 2)

    # =========================
    # Draw zone labels
    # =========================
    for zone, (count, risk) in risk_map.items():
        row, col = zone
        x = col * zone_w + 10
        y = row * zone_h + 30

        if best_zone and zone == best_zone:
            text  = f"BEST ({zone})"
            color = (255, 165, 0)   # Orange — stands out from grid blue
        elif zone in overcrowd_zones:
            text  = f"UNSAFE ({zone})"
            color = (0, 0, 255)     # Red
        else:
            text  = f"SAFE ({zone})"
            color = (0, 255, 0)     # Green

        cv2.putText(frame, text, (x, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    # =========================
    # Top panel — dark overlay
    # =========================
    panel_h = 110 if trend_data else 90
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (settings.FRAME_WIDTH, panel_h), (0, 0, 0), -1)
    frame = cv2.addWeighted(overlay, 0.45, frame, 0.55, 0)

    # People count
    cv2.putText(frame, f"People: {total_people}", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    # Global crowd status
    if overcrowd:
        cv2.putText(frame, "OVERCROWDED", (300, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
    else:
        cv2.putText(frame, "SAFE", (300, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)

    # Trend info row (only when trend_data is present)
    if trend_data:
        trend_label     = trend_data.get("trend_label", "")
        growth_rate     = trend_data.get("growth_rate", 0.0)
        predicted_count = trend_data.get("predicted_count", total_people)
        predicted_crash = trend_data.get("predicted_crash", False)

        trend_color = (0, 0, 255) if predicted_crash else (0, 255, 255)
        trend_text  = (
            f"Trend: {trend_label}  |  "
            f"+{growth_rate:.2f}/s  |  "
            f"~{predicted_count} in 10s"
        )
        cv2.putText(frame, trend_text, (20, 75),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, trend_color, 2)

        if predicted_crash:
            cv2.putText(frame, "CRASH PREDICTED", (20, 100),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    # =========================
    # Highlight overcrowded zones
    # =========================
    for zone in overcrowd_zones:
        row, col = zone
        x1, y1 = col * zone_w,          row * zone_h
        x2, y2 = x1  + zone_w,          y1  + zone_h

        overlay = frame.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 0, 255), -1)
        frame = cv2.addWeighted(overlay, 0.2, frame, 0.8, 0)

    # =========================
    # Highlight BEST zone
    # =========================
    if best_zone:
        row, col = best_zone
        x1, y1 = col * zone_w,          row * zone_h
        x2, y2 = x1  + zone_w,          y1  + zone_h

        overlay = frame.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (255, 165, 0), -1)
        frame = cv2.addWeighted(overlay, 0.25, frame, 0.75, 0)

        # Arrow from top-center of the frame down to best zone centre
        cx = col * zone_w + zone_w // 2
        cy = row * zone_h + zone_h // 2

        cv2.arrowedLine(frame,
                        (settings.FRAME_WIDTH // 2, panel_h + 10),
                        (cx, cy),
                        (255, 165, 0), 4, tipLength=0.03)
    else:
        cv2.putText(frame, "NO SAFE ZONE", (300, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    return frame