# incident_engine/rca_summary_builder.py

from collections import Counter
from datetime import datetime


class RCASummaryBuilder:
    """
    Builds a human-readable RCA summary
    from correlated incident data.
    """

    def build(self, incident, correlation_result):
        incident_time = incident.get("start_time")

        what = (
            f"A critical incident occurred at "
            f"{incident_time.strftime('%H:%M')}."
        )

        why = correlation_result.get(
            "root_cause",
            "Cause could not be determined"
        )

        risky = "YES" if incident.get("severity") == "CRITICAL" else "NO"

        current_status = correlation_result.get(
            "current_status", "UNKNOWN"
        )

        recommendation = correlation_result.get(
            "recommendation",
            "Review OEM logs and metrics"
        )

        return {
            "INCIDENT_TIME": incident_time,
            "WHAT_HAPPENED": what,
            "WHY_HAPPENED": why,
            "RISKY": risky,
            "CURRENT_STATUS": current_status,
            "RECOMMENDATION": recommendation
        }


    # ------------------------------------------------
    # ROOT CAUSE DETECTION
    # ------------------------------------------------
    def _detect_root_cause(self, before_events):
        if not before_events:
            return {
                "category": "UNKNOWN",
                "severity": "UNKNOWN",
                "explanation": "No abnormal metrics were detected before the incident."
            }

        counts = Counter()
        severities = {}

        for e in before_events:
            cat = e.get("category")
            sev = e.get("severity", "INFO")

            if not cat:
                continue

            counts[cat] += 1
            severities[cat] = sev

        # pick highest priority category
        primary = max(
            counts.keys(),
            key=lambda c: self.SEVERITY_PRIORITY.get(c, 0)
        )

        return {
            "category": primary,
            "severity": severities.get(primary, "INFO"),
            "explanation": (
                f"{primary} related issues were observed before the incident, "
                f"indicating system instability."
            )
        }

    # ------------------------------------------------
    # RECOVERY DETECTION
    # ------------------------------------------------
    def _detect_recovery(self, after_events):
        for e in after_events:
            if (
                e.get("category") == "AVAILABILITY"
                and e.get("severity") == "INFO"
            ):
                return "NORMAL"

        return "UNSTABLE"

    # ------------------------------------------------
    # RECOMMENDATION ENGINE
    # ------------------------------------------------
    def _recommend(self, category):
        if category == "CPU":
            return (
                "Identify CPU-intensive jobs, reschedule batch workloads "
                "during night hours, and configure proactive CPU alerts."
            )
        if category == "MEMORY":
            return (
                "Review JVM/PGA memory usage and tune memory configuration."
            )
        if category == "STORAGE":
            return (
                "Monitor tablespace usage and clean up unnecessary data."
            )
        if category == "AVAILABILITY":
            return (
                "Investigate network and service availability issues "
                "and improve failover mechanisms."
            )

        return "Review OEM logs and system metrics."

