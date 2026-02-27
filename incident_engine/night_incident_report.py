from datetime import datetime, time
from incident_engine.correlation_engine import CorrelationEngine
from incident_engine.rca_summary_builder import RCASummaryBuilder


class NightIncidentReportGenerator:
    """
    Generates automatic night-time incident reports
    (e.g. 12 AM – 6 AM)
    """

    def __init__(self, incidents, metrics):
        self.incidents = incidents
        self.metrics = metrics
        self.correlation_engine = CorrelationEngine(incidents, metrics)
        self.rca_builder = RCASummaryBuilder()

    def generate(self, start_hour=0, end_hour=6):
        report = []

        for inc in self.incidents:
            inc_time = inc.get("start_time") or inc.get("time")
            if not inc_time:
                continue

            # Check night window
            if not self._is_night_time(inc_time, start_hour, end_hour):
                continue

            # RCA
            correlation = self.correlation_engine.analyze_incident(inc)
            rca = self.rca_builder.build(inc, correlation)

            report.append({
                "incident_time": inc_time,
                "database": inc.get("database"),
                "what_happened": rca["WHAT_HAPPENED"],
                "why_happened": rca["WHY_HAPPENED"],
                "risky": rca["RISKY"],
                "current_status": rca["CURRENT_STATUS"],
                "recommendation": rca["RECOMMENDATION"]
            })

        return report

    def _is_night_time(self, dt, start_hour, end_hour):
        t = dt.time()
        return time(start_hour, 0) <= t <= time(end_hour, 0)

