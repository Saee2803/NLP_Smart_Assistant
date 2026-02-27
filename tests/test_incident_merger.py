from metrics_engine.metrics_loader import OEMMetricsLoader
from metrics_engine.metrics_normalizer import MetricsNormalizer
from incident_engine.metric_incident_builder import MetricIncidentBuilder
from incident_engine.incident_merger import IncidentMerger

# Metrics → incidents
loader = OEMMetricsLoader("data/oem_metrics_25.csv")
raw = loader.load_metrics()

normalizer = MetricsNormalizer()
signals = normalizer.normalize(raw)

builder = MetricIncidentBuilder()
metric_incidents = builder.build(signals)

# Merge (only metrics for now)
merger = IncidentMerger()
all_incidents = merger.merge(metric_incidents)

print("Total unified incidents:", len(all_incidents))
print(all_incidents[:3])

