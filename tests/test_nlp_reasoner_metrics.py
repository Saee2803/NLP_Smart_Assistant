from nlp_engine.nlp_reasoner import NLPReasoner
from incident_engine.incident_analyzer import IncidentAnalyzer
from incident_engine.incident_merger import IncidentMerger
from metrics_engine.metrics_loader import OEMMetricsLoader
from metrics_engine.metrics_normalizer import MetricsNormalizer
from incident_engine.metric_incident_builder import MetricIncidentBuilder

# Load metrics
loader = OEMMetricsLoader("data/oem_metrics_25.csv")
raw = loader.load_metrics()

# Normalize
normalizer = MetricsNormalizer()
signals = normalizer.normalize(raw)

# Build incidents
builder = MetricIncidentBuilder()
metric_incidents = builder.build(signals)

# Merge
merger = IncidentMerger()
incidents = merger.merge(metric_incidents)

# NLP Reasoner
reasoner = NLPReasoner(incidents)

print(reasoner.answer("Why mitestdb is unstable?"))
print(reasoner.answer("What is health of mitestdb?"))
print(reasoner.answer("Which issue is frequent in mitestdb?"))

