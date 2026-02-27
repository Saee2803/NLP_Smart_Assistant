from datetime import datetime, timedelta
from data_engine.target_normalizer import TargetNormalizer


class FailurePredictor:
    """
    Predicts probability of near-future failures
    based on alerts, incidents, and risk trends.

    NO ML – fully explainable & interview-safe.
    """

    def __init__(self, alerts, incidents, risk_trends):
        self.alerts = alerts or []
        self.incidents = incidents or []
        self.risk_trends = risk_trends or []

    # =====================================================
    # 🔮 MAIN PREDICTION API
    # =====================================================
    def predict(self, target):
        score = 0
        reasons = []

        now = datetime.utcnow()
        recent_window = now - timedelta(hours=24)

        # -------------------------------------------------
        # 1️⃣ Recent CRITICAL alerts
        # -------------------------------------------------
        recent_criticals = [
            a for a in self.alerts
            if TargetNormalizer.equals(a.get("target"), target)
            and a.get("severity") == "CRITICAL"
            and a.get("time")
            and a["time"] >= recent_window
        ]

        if len(recent_criticals) >= 3:
            score += 30
            reasons.append("Multiple critical alerts in last 24 hours")

        if len(recent_criticals) >= 6:
            score += 15
            reasons.append("High frequency of critical alerts")

        # -------------------------------------------------
        # 2️⃣ Incident repetition
        # -------------------------------------------------
        related_incidents = [
            i for i in self.incidents
            if TargetNormalizer.equals(i.get("target"), target)
        ]

        if len(related_incidents) >= 3:
            score += 20
            reasons.append("Repeated incidents detected")

        # -------------------------------------------------
        # 3️⃣ Risk trend (Phase-2 output)
        # -------------------------------------------------
        trend_info = None
        for t in self.risk_trends:
            if TargetNormalizer.equals(t.get("target"), target):
                trend_info = t
                break

        if trend_info:
            if trend_info.get("trend") == "INCREASING":
                score += 25
                reasons.append("Risk trend is increasing")

            if trend_info.get("risk_score", 0) >= 70:
                score += 20
                reasons.append("High overall risk score")

        # -------------------------------------------------
        # 4️⃣ No recovery signals
        # -------------------------------------------------
        recent_alerts = [
            a for a in self.alerts
            if TargetNormalizer.equals(a.get("target"), target)
        ][-5:]

        if recent_alerts and not any(a.get("severity") == "CLEAR" for a in recent_alerts):
            score += 10
            reasons.append("No recovery alerts observed")

        # -------------------------------------------------
        # FINAL NORMALIZATION
        # -------------------------------------------------
        probability = min(score, 100)

        return {
            "target": target,
            "failure_probability": probability,
            "window": self._window(probability),
            "confidence": self._confidence(probability),
            "reasons": reasons or ["Insufficient data for prediction"]
        }

    # =====================================================
    # HELPERS
    # =====================================================
    def _confidence(self, probability):
        if probability >= 70:
            return "HIGH"
        if probability >= 40:
            return "MEDIUM"
        return "LOW"

    def _window(self, probability):
        if probability >= 70:
            return "next 24 hours"
        if probability >= 40:
            return "next 48 hours"
        return "no immediate risk"

