import csv
import os
from datetime import datetime
from data_engine.target_normalizer import TargetNormalizer


def parse_metric_time(value):
    if not value:
        return None

    if isinstance(value, str):
        value = value.replace("T", " ").split("+")[0]

    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except Exception:
            pass

    return None


class MetricStore:
    """
    Loads, merges and normalizes all OEM metrics CSVs
    """

    def __init__(self, metrics_dir="data/metrics"):
        self.metrics_dir = metrics_dir
        self.metrics = self._load_all()

    def _load_all(self):
        all_metrics = []

        if not os.path.isdir(self.metrics_dir):
            return all_metrics

        for file in os.listdir(self.metrics_dir):
            if not file.endswith(".csv"):
                continue

            path = os.path.join(self.metrics_dir, file)
            all_metrics.extend(self._load_file(path))

        return all_metrics

    def _load_file(self, csv_path):
        metrics = []

        # Python 3.6 safe CSV open
        with open(csv_path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)

            for r in reader:
                if not r:
                    continue

                # -------- VALUE --------
                val = r.get("value")
                if val in ("", None):
                    continue

                try:
                    val = float(val)
                except Exception:
                    continue

                # -------- TIME (FIXED) --------
                ts = (
                    r.get("timestamp")
                    or r.get("time")
                    or r.get("metric_time")
                )
                parsed_time = parse_metric_time(ts)
                if parsed_time is None:
                    continue  # skip bad timestamps

                # -------- TARGET (NORMALIZED) --------
                raw_target = r.get("target_name")
                # CRITICAL: Normalize target at load time
                normalized_target = TargetNormalizer.normalize(raw_target)
                
                # Skip metrics with invalid targets (listener noise, etc)
                if normalized_target is None:
                    continue

                metrics.append({
                    "time": parsed_time,
                    "target": normalized_target,
                    "target_type": r.get("target_type"),
                    "metric": r.get("metric_name"),
                    "key": r.get("metric_column"),
                    "value": val
                })

        return metrics

    def all(self):
        return self.metrics
