import csv
import glob


class MetricsLoader:
    def __init__(self, metrics_dir="data/metrics"):
        self.metrics_dir = metrics_dir

    def load_all(self):
        rows = []

        files = glob.glob(self.metrics_dir + "/*.csv")
        for path in files:
            try:
                # Python 3.6 safe CSV open
                with open(path, encoding="utf-8", newline="") as f:
                    reader = csv.DictReader(f)
                    for r in reader:
                        if r:
                            rows.append(r)
            except Exception:
                # Skip bad files without crashing entire pipeline
                continue

        print("📥 Raw metrics rows loaded: {0}".format(len(rows)))
        return rows
