from metrics_engine.metrics_loader import OEMMetricsLoader
from metrics_engine.metrics_normalizer import MetricsNormalizer
from incident_engine.metric_incident_builder import MetricIncidentBuilder
from incident_engine.incident_merger import IncidentMerger
from incident_engine.incident_analyzer import IncidentAnalyzer

# Load metrics
loader = OEMMetricsLoader("data/oem_metrics_25.csv")
raw = loader.load_metrics()

# Normalize
normalizer = MetricsNormalizer()
signals = normalizer.normalize(raw)

# Build metric incidents
builder = MetricIncidentBuilder()
metric_incidents = builder.build(signals)

# Merge (only metrics for now)
merger = IncidentMerger()
all_incidents = merger.merge(metric_incidents)

# Analyze
analyzer = IncidentAnalyzer(all_incidents)

print("\nFrequent issues:")
print(analyzer.frequent_issues())

print("\nHealth:")
print(analyzer.downtime_patterns())

print("\nConfidence:")
print(analyzer.confidence_score())

