from config.settings import OVERCROWD_THRESHOLD, ALERT_THRESHOLD


def compute_risk(density):

    risk_map        = {}
    total_people    = 0
    overcrowd_zones = []

    for zone, count in density.items():
        total_people += count

        if count >= OVERCROWD_THRESHOLD:
            risk = "HIGH"
            overcrowd_zones.append(zone)
        else:
            risk = "LOW"

        risk_map[zone] = (count, risk)

    # Global overcrowd flag uses total headcount vs ALERT_THRESHOLD
    overcrowd = total_people >= ALERT_THRESHOLD

    return risk_map, total_people, overcrowd, overcrowd_zones