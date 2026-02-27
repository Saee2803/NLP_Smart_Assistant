import csv
from datetime import datetime
from typing import List, Dict, Any


class OEMMetricsLoader:
    """
    Loads and cleans OEM metrics CSV data.
    Converts raw CSV rows into structured metric events.
    """

    def __init__(self, csv_path: str):
        self.csv_path = csv_path

    def _parse_time(self, ts: str):
        """
        OEM timestamps may include timezone (+05:30)
        Python 3.6 does NOT support it.
        So we strip timezone safely.
        """
        if not ts:
            return None

        # Remove timezone if present
        if "+" in ts:
            ts = ts.split("+")[0]

        try:
            return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%f")
        except Exception:
            return None

    def load_metrics(self) -> List[Dict[str, Any]]:
        events = []

        with open(self.csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                event_time = self._parse_time(row.get("timestamp"))
                if not event_time:
                    continue

                raw_value = row.get("value")

                try:
                    value = float(raw_value)
                except (TypeError, ValueError):
                    value = raw_value

                event = {
                    "time": event_time,
                    "target": row.get("target_name"),
                    "target_type": row.get("target_type"),
                    "metric": row.get("metric_name"),
                    "key": row.get("metric_column"),
                    "value": value,
                }

                events.append(event)

        return events

