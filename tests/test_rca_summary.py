from incident_engine.rca_summary_builder import RCASummaryBuilder
from incident_engine.incident_timeline import IncidentTimelineBuilder
from oem_ingestion.xml_parser import OEMXMLParser
from metrics_engine.metrics_loader import OEMMetricsLoader
from metrics_engine.metrics_normalizer import MetricsNormalizer


# Load incidents
parser = OEMXMLParser("oem_ingestion/xml_samples/oem_sample_1.xml")
xml_events = parser.flatten_events()

# Load metrics
loader = OEMMetricsLoader("data/oem_metrics_25.csv")
raw = loader.load_metrics()
metrics = MetricsNormalizer().normalize(raw)

# Pick one CRITICAL incident
incident = next(e for e in xml_events if e["severity"] == "CRITICAL")

timeline = IncidentTimelineBuilder(
    incidents=xml_events,
    metrics=metrics
).build_timeline(incident)

rca = RCASummaryBuilder().build(timeline)

print("\n===== RCA SUMMARY =====")
for k, v in rca.items():
    print(f"{k.upper()} : {v}")

