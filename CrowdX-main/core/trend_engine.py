import time


class TrendEngine:
    """
    Tracks crowd count over time and predicts whether a crush is imminent.
    """

    def __init__(self, window=10):
        """
        window : int — number of seconds of history to keep for trend calc
        """
        self.window      = window          # seconds
        self.history     = []              # list of (timestamp, total_people)
        self.zone_history = []             # list of (timestamp, zone_counts dict)

    # ------------------------------------------------------------------
    def update(self, total_people, zone_counts):
        """Call once per frame with the latest headcount and per-zone counts."""
        now = time.time()
        self.history.append((now, total_people))
        self.zone_history.append((now, dict(zone_counts)))

        # Prune old entries outside the window
        cutoff = now - self.window
        self.history      = [(t, c) for t, c in self.history      if t >= cutoff]
        self.zone_history = [(t, z) for t, z in self.zone_history if t >= cutoff]

    # ------------------------------------------------------------------
    def get_summary(self):
        """
        Returns a dict with:
            trend_label      : str   — STABLE / GROWING / SURGING / DECLINING
            growth_rate      : float — people added per second (can be negative)
            predicted_count  : int   — estimated count 10 seconds from now
            predicted_crash  : bool  — True if surge detected
        """
        if len(self.history) < 2:
            return {
                "trend_label"     : "STABLE",
                "growth_rate"     : 0.0,
                "predicted_count" : self.history[-1][1] if self.history else 0,
                "predicted_crash" : False,
            }

        t0, c0 = self.history[0]
        t1, c1 = self.history[-1]
        elapsed = t1 - t0

        if elapsed == 0:
            growth_rate = 0.0
        else:
            growth_rate = (c1 - c0) / elapsed   # people per second

        predicted_count = max(0, int(c1 + growth_rate * 10))  # 10-sec lookahead

        if growth_rate > 1.5:
            trend_label = "SURGING"
        elif growth_rate > 0.3:
            trend_label = "GROWING"
        elif growth_rate < -0.3:
            trend_label = "DECLINING"
        else:
            trend_label = "STABLE"

        predicted_crash = trend_label == "SURGING"

        return {
            "trend_label"     : trend_label,
            "growth_rate"     : round(growth_rate, 2),
            "predicted_count" : predicted_count,
            "predicted_crash" : predicted_crash,
        }

    # ------------------------------------------------------------------
    def time_to_danger(self, threshold):
        """
        Estimate seconds until total count hits `threshold`.
        Returns 0 if already there, or '?' if growth rate is <= 0.
        """
        if len(self.history) < 2:
            return "?"

        _, current = self.history[-1]
        summary    = self.get_summary()
        rate       = summary["growth_rate"]

        if current >= threshold:
            return 0

        if rate <= 0:
            return "?"

        seconds = (threshold - current) / rate
        return max(0, int(seconds))