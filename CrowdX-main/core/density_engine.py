import config.settings as settings

def compute_density(objects):
    zone_counts = {}

    zone_w = settings.FRAME_WIDTH // settings.COLS
    zone_h = settings.FRAME_HEIGHT // settings.ROWS

    for (track_id, x, y, w, h) in objects:

        cx = x + w // 2
        cy = y + h // 2

        col = cx // zone_w
        row = cy // zone_h

        zone = (int(row), int(col))

        zone_counts[zone] = zone_counts.get(zone, 0) + 1

    return zone_counts