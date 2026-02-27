import csv
import os
from datetime import datetime
from data_engine.target_normalizer import TargetNormalizer
from incident_engine.alert_type_classifier import classify_alert_type


def parse_alert_time(value):
    if not value:
        return None

    value = value.replace("T", " ").split("+")[0]

    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except Exception:
            pass

    return None


class AlertStore:
    def __init__(self, alerts_dir="data/alerts"):
        self.alerts_dir = alerts_dir
        self.alerts = self._load_all()

    def _load_all(self):
        all_alerts = []

        if not os.path.isdir(self.alerts_dir):
            return all_alerts

        for file in os.listdir(self.alerts_dir):
            if not file.endswith(".csv"):
                continue

            path = os.path.join(self.alerts_dir, file)
            all_alerts.extend(self._load_file(path))

        return all_alerts

    def _load_file(self, csv_path):
        alerts = []

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for r in reader:
                raw_target = r.get("target_name")
                # CRITICAL: Normalize target at load time
                normalized_target = TargetNormalizer.normalize(raw_target)
                
                # Skip alerts with invalid targets (listener noise, etc)
                if normalized_target is None:
                    continue
                
                # Get message and classify alert type
                message = r.get("message")
                issue_type = "INTERNAL_ERROR" if "internal error" in (message or "").lower() else "OTHER"
                display_alert_type = classify_alert_type(issue_type, message)
                
                alerts.append({
                    "time": parse_alert_time(r.get("timestamp")),
                    "target": normalized_target,
                    "target_type": r.get("target_type"),
                    "severity": r.get("severity"),
                    "metric": r.get("metric_name"),
                    "message": message,
                    "issue_type": issue_type,
                    "display_alert_type": display_alert_type
                })

        return alerts

    def all(self):
        return self.alerts

