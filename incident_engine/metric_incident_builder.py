from typing import List, Dict


class MetricIncidentBuilder:
    """
    Converts normalized metric signals
    into incident-style alert records.
    """

    def build(self, events: List[Dict]) -> List[Dict]:
        incidents = []

        for e in events:
            target = e.get("target", "")
            category = e.get("category")
            severity = e.get("severity")
            value = e.get("value")

            # Try to extract DB name from target
            db = self._extract_db(target)

            message = f"{category} metric observed with value {value}"

            incidents.append({
                "database": db,
                "category": category,
                "severity": severity,
                "message": message,
                "time": e.get("time"),
                "source": "METRIC"
            })

        return incidents

    def _extract_db(self, target: str):
        """
        Best-effort DB name extraction
        """
        if not target:
            return "UNKNOWN"

        if "mitestdb" in target.lower():
            return "mitestdb"

        return "UNKNOWN"

