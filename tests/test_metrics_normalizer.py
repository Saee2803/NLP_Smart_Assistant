from metrics_engine.metrics_loader import OEMMetricsLoader
from metrics_engine.metrics_normalizer import MetricsNormalizer

loader = OEMMetricsLoader("data/oem_metrics_25.csv")
raw = loader.load_metrics()

normalizer = MetricsNormalizer()
events = normalizer.normalize(raw)

print("Normalized events:", len(events))
print(events[:5])

