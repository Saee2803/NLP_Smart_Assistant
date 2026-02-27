from typing import List, Dict


class MetricsNormalizer:
    """
    Converts raw OEM metrics into
    normalized health signals.
    """

    def normalize(self, events: List[Dict]) -> List[Dict]:
        normalized = []

        for e in events:
            metric = (e.get("metric") or "").lower()
            key = (e.get("key") or "").lower()
            value = e.get("value")

            category = None
            severity = "INFO"

            # ---- CPU ----
            if "cpu" in metric:
                category = "CPU"
                if isinstance(value, float) and value > 80:
                    severity = "CRITICAL"

            # ---- MEMORY ----
            elif "heap" in metric or "memory" in metric:
                category = "MEMORY"
                if isinstance(value, float) and value > 75:
                    severity = "WARNING"

            # ---- STORAGE ----
            elif "pctused" in key or "tablespace" in metric:
                category = "STORAGE"
                if isinstance(value, float) and value > 85:
                    severity = "CRITICAL"

            # ---- AVAILABILITY ----
            elif "status" in key:
                category = "AVAILABILITY"
                if value != 1:
                    severity = "CRITICAL"

            if not category:
                continue

            normalized.append({
                "time": e["time"],
                "target": e["target"],
                "category": category,
                "severity": severity,
                "metric": e["metric"],
                "value": value
            })

        return normalized

