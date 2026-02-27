# incident_engine/incident_timeline.py

from datetime import timedelta
from typing import List, Dict


class IncidentTimelineBuilder:
    """
    Builds before / during / after timeline
    around a critical incident.
    """

    def __init__(self, incidents: List[Dict], metrics: List[Dict]):
        self.incidents = incidents
        self.metrics = metrics

    def build_timeline(
        self,
        incident: Dict,
        window_minutes: int = 30
    ) -> Dict:
        """
        Builds timeline around an incident.

        Returns:
        {
            incident_time,
            before: [],
            during: {},
            after: []
        }
        """

        incident_time = (
            incident.get("start_time")
            or incident.get("time")
        )

        if not incident_time:
            raise ValueError("Incident has no timestamp")

        start = incident_time - timedelta(minutes=window_minutes)
        end = incident_time + timedelta(minutes=window_minutes)

        before = []
        after = []

        for m in self.metrics:
            m_time = m.get("time")
            if not m_time:
                continue

            entry = {
                "time": m_time,
                "category": m.get("category"),
                "metric": m.get("metric"),
                "value": m.get("value"),
                "severity": m.get("severity"),
            }

            if start <= m_time < incident_time:
                before.append(entry)

            elif incident_time < m_time <= end:
                after.append(entry)

        before.sort(key=lambda x: x["time"])
        after.sort(key=lambda x: x["time"])

        return {
            "incident_time": incident_time,
            "incident": {
                "database": incident.get("database"),
                "category": incident.get("category"),
                "severity": incident.get("severity"),
                "message": incident.get("message"),
            },
            "before": before,
            "after": after,
        }

