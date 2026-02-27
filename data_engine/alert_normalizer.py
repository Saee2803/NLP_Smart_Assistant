import csv
from data_engine.alert_normalizer import AlertNormalizer

class AlertStore:
    def __init__(self, csv_path="data/oem_alerts_raw.csv"):
        self.csv_path = csv_path
        self.normalizer = AlertNormalizer()
        self.alerts = self._load()

    def _load(self):
        alerts = {}
        total = 0

        with open(self.csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                total += 1
                alert = self.normalizer.normalize(row)
                if not alert:
                    continue

                # 🔥 DEDUP KEY
                key = (
                    alert["target"],
                    alert["time"],
                    alert["message"]
                )

                if key not in alerts:
                    alerts[key] = alert

        print(f"✅ Alerts loaded: {len(alerts)} (from {total} raw rows)")
        return list(alerts.values())

    def all(self):
        return self.alerts

