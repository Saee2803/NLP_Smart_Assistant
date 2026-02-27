from data_engine.target_normalizer import TargetNormalizer


class RiskAnalyzer:
    """
    Calculates risk per database/target using incidents
    Python 3.6 compatible - no f-strings, explicit type handling
    """

    def __init__(self, incidents):
        """
        Initialize with incidents.
        Python 3.6 safe: explicit None checks.
        """
        self.incidents = []
        
        if incidents is None:
            pass
        elif isinstance(incidents, list):
            self.incidents = incidents
        else:
            self.incidents = []

    def analyze_target(self, target):
        """
        Analyze risk for a specific target.
        Python 3.6 safe: no f-strings, .format() instead.
        """
        total = 0
        matched = []

        if not self.incidents:
            return {
                "target": target,
                "risk_level": "LOW",
                "risk_score": 0,
                "summary": "LOW RISK (0 incidents)",
                "incident_count": 0,
                "incidents": []
            }

        for i in self.incidents:
            if i is None:
                continue
            
            # Get target with safe None check
            incident_target = i.get("target")
            if incident_target is None:
                incident_target = ""
            
            # CRITICAL FIX: Use TargetNormalizer for consistent comparison
            if TargetNormalizer.equals(incident_target, target):
                count = i.get("count")
                
                # Safe type checking for count
                if count is None:
                    count = 1
                elif not isinstance(count, int):
                    try:
                        count = int(count)
                    except (ValueError, TypeError):
                        count = 1

                total += count
                matched.append(i)

        # ---------------------------
        # Risk level classification
        # ---------------------------
        if total >= 10:
            level = "HIGH"
        elif total >= 3:
            level = "MEDIUM"
        else:
            level = "LOW"

        # ---------------------------
        # Normalized score (0–100)
        # ---------------------------
        risk_score = min(total * 10, 100)

        # Build summary using .format() (Python 3.6 safe)
        summary = "{0} RISK ({1} incidents)".format(level, total)

        return {
            "target": target,
            "risk_level": level,
            "risk_score": risk_score,
            "summary": summary,
            "incident_count": total,
            "incidents": matched
        }

