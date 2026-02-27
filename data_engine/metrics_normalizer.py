from datetime import datetime


class MetricsNormalizer:

    def normalize(self, rows):
        normalized = []

        for r in rows:
            try:
                metric = {
                    "time": self._parse_time(r),
                    "target": (r.get("target_name") or "").upper(),
                    "metric": (r.get("metric_name") or "").strip(),
                    "value": self._parse_float(r.get("metric_value")),
                    "unit": r.get("metric_unit"),
                }

                if metric["time"] and metric["target"] and metric["metric"]:
                    normalized.append(metric)

            except Exception:
                continue

        # remove duplicates (time + target + metric)
        seen = set()
        unique = []
        for m in normalized:
            key = (m["time"], m["target"], m["metric"])
            if key not in seen:
                seen.add(key)
                unique.append(m)

        # sort by time
        unique.sort(key=lambda x: x["time"])

        print("🧹 Normalized metrics rows: {0}".format(len(unique)))
        return unique

    def _parse_time(self, r):
        """
        Python 3.6 safe ISO timestamp parsing
        """
        for k in ["collection_time", "metric_time", "time"]:
            val = r.get(k)
            if not val:
                continue

            if isinstance(val, str):
                val = val.replace("T", " ").split("+")[0]

            for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
                try:
                    return datetime.strptime(val, fmt)
                except Exception:
                    pass

        return None

    def _parse_float(self, v):
        try:
            return float(v)
        except Exception:
            return None
