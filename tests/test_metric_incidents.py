from metrics_engine.metrics_loader import OEMMetricsLoader
from metrics_engine.metrics_normalizer import MetricsNormalizer
from incident_engine.metric_incident_builder import MetricIncidentBuilder

loader = OEMMetricsLoader("data/oem_metrics_25.csv")
raw = loader.load_metrics()

normalizer = MetricsNormalizer()
signals = normalizer.normalize(raw)

builder = MetricIncidentBuilder()
incidents = builder.build(signals)

print("Metric incidents:", len(incidents))
print(incidents[:5])

