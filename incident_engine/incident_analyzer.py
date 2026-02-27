# incident_engine/incident_analyzer.py

from data_engine.target_normalizer import TargetNormalizer


class RiskAnalyzer:
    def __init__(self, incidents):
        self.incidents = incidents or []

    def analyze_target(self, target):
        if not target:
            return {
                "risk": "LOW",
                "risk_score": 0,
                "incident_count": 0
            }

        normalized_target = TargetNormalizer.normalize(target)
        if not normalized_target:
            return {
                "risk": "LOW",
                "risk_score": 0,
                "incident_count": 0
            }

        relevant = [
            i for i in self.incidents
            if TargetNormalizer.equals(i.get("target"), normalized_target)
        ]

        if not relevant:
            return {
                "risk": "LOW",
                "risk_score": 0,
                "incident_count": 0
            }

        score = 0

        for i in relevant:
            count = i.get("count", 1)  # 🔥 SAFE DEFAULT
            severity = i.get("severity", "INFO")

            if severity == "CRITICAL":
                score += count * 10
            elif severity == "WARNING":
                score += count * 4
            else:
                score += count

        risk = (
            "HIGH" if score >= 50 else
            "MEDIUM" if score >= 20 else
            "LOW"
        )

        return {
            "risk": risk,
            "risk_score": score,
            "incident_count": len(relevant)
        }

