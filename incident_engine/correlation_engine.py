from datetime import timedelta
from collections import Counter, defaultdict
from data_engine.target_normalizer import TargetNormalizer


class CorrelationEngine:
    """
    ADVANCED OEM CORRELATION ENGINE

    Capabilities:
    - Root Cause Analysis (RCA)
    - Risk Assessment
    - Ranked Probable Causes
    - Predictive Outage Probability
    """

    def __init__(self, alerts, metrics, incidents=None):
        self.alerts = alerts or []
        self.metrics = metrics or []
        self.incidents = incidents or []

    # =====================================================
    # MAIN RCA (single alert)
    # =====================================================
    def analyze(self, alert):
        alert_time = alert.get("time") or alert.get("start_time")
        target = alert.get("target")

        if not alert_time or not target:
            return self._default_result(alert, "Missing alert timestamp or target")

        window_start = alert_time - timedelta(minutes=15)
        window_end = alert_time + timedelta(minutes=5)

        related_metrics = [
            m for m in self.metrics
            if m.get("time")
            and window_start <= m["time"] <= window_end
            and self._same_target(target, m)
        ]

        abnormal_metrics = self._detect_abnormal_metrics(related_metrics)
        repeated = self._is_repeated_alert(alert)

        if abnormal_metrics:
            root_cause = self._derive_root_cause(abnormal_metrics)
            risky = True
            recommendation = self._recommend(root_cause)

        elif repeated:
            root_cause = "Repeated critical alerts without clear metric spike"
            risky = True
            recommendation = (
                "Investigate database logs, OS logs, and recurring failure patterns"
            )

        else:
            root_cause = "No abnormal metrics detected near incident time"
            risky = False
            recommendation = "Continue monitoring and review OEM logs"

        return {
            "alert": alert,
            "root_cause": root_cause,
            "risky": risky,
            "current_status": self._current_status(target),
            "recommendation": recommendation
        }

    # =====================================================
    # 🔥 RANKED ROOT CAUSES (CONFIDENCE BASED)
    # =====================================================
    def rank_causes(self):
        scores = defaultdict(float)

        for a in self.alerts:
            msg = (a.get("message") or "").lower()
            sev = a.get("severity", "")

            if "ora-" in msg:
                scores["Oracle internal error"] += 1.0
            if "reboot" in msg:
                scores["Unexpected server reboot"] += 0.8
            if sev == "CRITICAL":
                scores["Repeated critical alerts"] += 0.5

        for m in self.metrics:
            name = (m.get("metric") or "").lower()
            value = m.get("value", 0)

            if "cpu" in name and value > 85:
                scores["CPU saturation"] += 1.0
            if "memory" in name and value > 80:
                scores["Memory pressure"] += 1.0
            if ("disk" in name or "storage" in name) and value > 90:
                scores["Storage exhaustion"] += 1.0

        if not scores:
            return []

        total = sum(scores.values())

        ranked = [
            {
                "cause": cause,
                "confidence": round((score / total) * 100, 1)
            }
            for cause, score in scores.items()
        ]

        ranked.sort(key=lambda x: x["confidence"], reverse=True)
        return ranked

    # =====================================================
    # OUTAGE PROBABILITY (PREDICTIVE)
    # Enhanced with incident patterns, time gaps, and severity
    # =====================================================
    def outage_probability(self, target, incidents=None):
        """
        Predicts failure probability (0-100) based on:
        1. Critical alert frequency (weight: 25%)
        2. Incident frequency (weight: 25%)
        3. Shrinking time gaps between incidents (weight: 25%)
        4. Severity progression (weight: 25%)
        
        Args:
            target: Database/target name
            incidents: Optional list of incidents (if not provided, uses self.incidents)
        
        Returns:
            {
                "probability": 0-100,
                "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
                "reasons": ["explanation", ...],
                "score_breakdown": {"critical_alerts": X, "incident_frequency": X, ...}
            }
        """
        if incidents is None:
            incidents = self.incidents
        
        score = 0
        reasons = []
        breakdown = {}
        
        # ===== 1. CRITICAL ALERT FREQUENCY (0-25 points) =====
        criticals = [
            a for a in self.alerts
            if a.get("target") == target and a.get("severity") == "CRITICAL"
        ]
        
        critical_count = len(criticals)
        critical_score = min(25, critical_count * 2.5)  # 10+ criticals = 25 points
        score += critical_score
        breakdown["critical_alerts"] = int(critical_score)
        
        if critical_count >= 50:
            reasons.append("CRITICAL: {} critical alerts detected".format(critical_count))
        elif critical_count >= 20:
            reasons.append("HIGH: {} critical alerts indicate repeated failures".format(critical_count))
        elif critical_count >= 5:
            reasons.append("MEDIUM: {} critical alerts suggest instability".format(critical_count))
        
        # ===== 2. INCIDENT FREQUENCY (0-25 points) =====
        if incidents:
            target_incidents = [
                i for i in incidents if i.get("target") == target
            ]
            incident_count = len(target_incidents)
            # Scale: 10 incidents = 10 pts, 50 incidents = 20 pts, 100+ = 25 pts
            incident_score = min(25, incident_count * 0.25)
            score += incident_score
            breakdown["incident_frequency"] = int(incident_score)
            
            if incident_count >= 100:
                reasons.append("CRITICAL: {} separate incidents in system".format(incident_count))
            elif incident_count >= 50:
                reasons.append("HIGH: {} incidents indicate recurring issues".format(incident_count))
            elif incident_count >= 20:
                reasons.append("MEDIUM: {} incidents show pattern of failures".format(incident_count))
            elif incident_count >= 5:
                reasons.append("MEDIUM: {} incidents detected".format(incident_count))
            
            # ===== 3. TIME GAP ANALYSIS (0-25 points) =====
            # Shrinking time gaps = higher probability of imminent failure
            if len(target_incidents) >= 3:
                time_gaps = self._calculate_time_gaps(target_incidents)
                gap_score = self._score_time_gaps(time_gaps)
                score += gap_score
                breakdown["time_gaps"] = int(gap_score)
                
                if gap_score >= 20:
                    reasons.append("CRITICAL: Incidents accelerating (gaps shrinking)")
                elif gap_score >= 15:
                    reasons.append("HIGH: Time between incidents decreasing")
                elif gap_score >= 10:
                    reasons.append("MEDIUM: Unstable incident pattern detected")
        else:
            breakdown["incident_frequency"] = 0
            breakdown["time_gaps"] = 0
        
        # ===== 4. SEVERITY PROGRESSION (0-25 points) =====
        # Are failures getting worse over time?
        severity_score = self._score_severity_progression(criticals)
        score += severity_score
        breakdown["severity_progression"] = int(severity_score)
        
        if severity_score >= 20:
            reasons.append("CRITICAL: Severity escalating over time")
        elif severity_score >= 10:
            reasons.append("MEDIUM: Alert severity increasing")
        
        # ===== NORMALIZE AND CLASSIFY =====
        probability = min(int(score), 100)
        
        risk_level = (
            "CRITICAL" if probability >= 80 else
            "HIGH" if probability >= 60 else
            "MEDIUM" if probability >= 40 else
            "LOW"
        )
        
        # Add final assessment
        if probability >= 80:
            reasons.append("FINAL: Imminent failure risk - immediate action required")
        elif probability >= 60:
            reasons.append("FINAL: Significant outage risk - escalate to DBA team")
        elif probability >= 40:
            reasons.append("FINAL: Moderate risk - monitor closely and plan maintenance")
        else:
            reasons.append("FINAL: Low risk - continue standard monitoring")
        
        return {
            "target": target,
            "probability": probability,
            "risk_level": risk_level,
            "reasons": reasons,
            "score_breakdown": breakdown
        }
    
    # ===== TIME GAP ANALYSIS HELPERS =====
    def _calculate_time_gaps(self, incidents):
        """
        Calculate time gaps between consecutive incidents.
        Returns list of gap durations in minutes.
        """
        if len(incidents) < 2:
            return []
        
        # Sort by first_seen
        sorted_inc = sorted(incidents, key=lambda i: i.get("first_seen") or i.get("time"))
        gaps = []
        
        for i in range(1, len(sorted_inc)):
            prev_time = sorted_inc[i-1].get("last_seen") or sorted_inc[i-1].get("time")
            curr_time = sorted_inc[i].get("first_seen") or sorted_inc[i].get("time")
            
            if prev_time and curr_time:
                gap_seconds = (curr_time - prev_time).total_seconds()
                gap_minutes = gap_seconds / 60.0
                gaps.append(gap_minutes)
        
        return gaps
    
    def _score_time_gaps(self, gaps):
        """
        Score based on gap trends.
        Shrinking gaps = higher score (worse situation)
        """
        if len(gaps) < 2:
            return 0
        
        score = 0
        
        # Measure: are gaps shrinking?
        early_gaps = gaps[:len(gaps)//2]
        late_gaps = gaps[len(gaps)//2:]
        
        avg_early = sum(early_gaps) / len(early_gaps) if early_gaps else float('inf')
        avg_late = sum(late_gaps) / len(late_gaps) if late_gaps else float('inf')
        
        if avg_early > 0:
            reduction_ratio = (avg_early - avg_late) / avg_early
            
            if reduction_ratio >= 0.70:  # Gaps shrinking by 70%+
                score += 25
            elif reduction_ratio >= 0.50:  # Gaps shrinking by 50%+
                score += 20
            elif reduction_ratio >= 0.30:  # Gaps shrinking by 30%+
                score += 15
            elif reduction_ratio >= 0.10:  # Any significant shrinking
                score += 10
        
        # Measure: are gaps very small now?
        if len(late_gaps) > 0:
            min_gap = min(late_gaps)
            if min_gap < 60:  # < 1 hour between incidents
                score += 5
        
        return min(score, 25)
    
    def _score_severity_progression(self, alerts):
        """
        Score based on whether alert severity is escalating.
        """
        if len(alerts) < 3:
            return 0
        
        # Split alerts chronologically
        sorted_alerts = sorted(alerts, key=lambda a: a.get("time") or a.get("start_time"))
        early_alerts = sorted_alerts[:len(sorted_alerts)//2]
        late_alerts = sorted_alerts[len(sorted_alerts)//2:]
        
        # Severity ranking
        severity_rank = {"INFO": 1, "WARNING": 2, "CRITICAL": 3}
        
        early_avg = sum(
            severity_rank.get(a.get("severity"), 1) for a in early_alerts
        ) / len(early_alerts) if early_alerts else 0
        
        late_avg = sum(
            severity_rank.get(a.get("severity"), 1) for a in late_alerts
        ) / len(late_alerts) if late_alerts else 0
        
        # Higher score if severity is increasing
        if late_avg > early_avg * 1.3:
            return 20
        elif late_avg > early_avg * 1.15:
            return 15
        elif late_avg > early_avg:
            return 10
        
        return 0

    # =====================================================
    # HELPERS
    # =====================================================
    def _same_target(self, target, metric):
        # CRITICAL FIX: Use centralized TargetNormalizer instead of string contains
        return TargetNormalizer.equals(target, metric.get("target"))

    def _detect_abnormal_metrics(self, metrics):
        abnormal = []

        for m in metrics:
            name = (m.get("metric") or "").lower()
            value = m.get("value", 0)

            if "cpu" in name and value > 85:
                abnormal.append(("CPU", value))
            elif "memory" in name and value > 80:
                abnormal.append(("MEMORY", value))
            elif ("disk" in name or "storage" in name) and value > 90:
                abnormal.append(("STORAGE", value))

        return abnormal

    def _derive_root_cause(self, abnormal_metrics):
        categories = [c[0] for c in abnormal_metrics]
        most_common = Counter(categories).most_common(1)[0][0]

        mapping = {
            "CPU": "CPU utilization reached critical levels",
            "MEMORY": "Memory utilization was abnormally high",
            "STORAGE": "Storage or tablespace pressure detected"
        }

        return mapping.get(most_common, "Abnormal system metrics detected")

    def _recommend(self, cause):
        cause = cause.lower()

        if "cpu" in cause:
            return "Identify CPU-intensive jobs and reschedule heavy workloads"
        if "memory" in cause:
            return "Tune memory parameters and monitor for memory leaks"
        if "storage" in cause:
            return "Clean up data and add storage capacity"

        return "Perform detailed log analysis and monitor the system closely"

    def _is_metric_abnormal(self, metric):
        name = (metric.get("metric") or "").lower()
        value = metric.get("value", 0)

        return (
            ("cpu" in name and value > 85) or
            ("memory" in name and value > 80) or
            (("disk" in name or "storage" in name) and value > 90)
        )

    def _is_repeated_alert(self, alert):
        target = alert.get("target")
        severity = alert.get("severity")

        similar = [
            a for a in self.alerts
            if a.get("target") == target and a.get("severity") == severity
        ]

        return len(similar) >= 3

    def _current_status(self, target):
        recent = [a for a in self.alerts if a.get("target") == target]

        if not recent:
            return "UNKNOWN"

        if any(a.get("severity") == "CRITICAL" for a in recent[-3:]):
            return "UNSTABLE"

        return "STABLE"

    def _default_result(self, alert, reason):
        return {
            "alert": alert,
            "root_cause": reason,
            "risky": False,
            "current_status": "UNKNOWN",
            "recommendation": "Review OEM data"
        }

