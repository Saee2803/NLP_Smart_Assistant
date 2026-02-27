from collections import defaultdict
from datetime import datetime


class RootCauseRanker:
    """
    Ranks multiple possible root causes
    based on frequency, recency and severity
    """

    def rank(self, alerts):
        cause_scores = defaultdict(float)

        now = datetime.utcnow()

        for a in alerts:
            msg = (a.get("message") or "").lower()
            sev = a.get("severity", "INFO")
            t = a.get("time")

            if not t:
                continue

            # -------------------------------
            # Identify cause category
            # -------------------------------
            cause = self._classify(msg)

            # -------------------------------
            # Weight calculation
            # -------------------------------
            severity_weight = {
                "CRITICAL": 3.0,
                "WARNING": 1.5,
                "INFO": 1.0
            }.get(sev, 1.0)

            recency_minutes = max((now - t).total_seconds() / 60, 1)
            recency_weight = 1 / recency_minutes

            score = severity_weight + recency_weight
            cause_scores[cause] += score

        # normalize
        total = sum(cause_scores.values()) or 1

        ranked = []
        for cause, score in sorted(
            cause_scores.items(),
            key=lambda x: x[1],
            reverse=True
        ):
            ranked.append({
                "cause": cause,
                "confidence": round((score / total) * 100, 1)
            })

        return ranked

    def _classify(self, msg: str) -> str:
        if "ora-" in msg or "internal error" in msg:
            return "Oracle internal error"
        if "disk" in msg or "i/o" in msg or "storage" in msg:
            return "Storage I/O bottleneck"
        if "cpu" in msg:
            return "CPU contention"
        if "memory" in msg or "pga" in msg:
            return "Memory pressure"
        if "listener" in msg or "tns" in msg:
            return "Listener / connectivity issue"
        if "reboot" in msg or "restart" in msg:
            return "Server reboot / crash"
        return "Unknown systemic issue"

