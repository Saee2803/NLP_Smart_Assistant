from datetime import datetime
from metrics_engine.metrics_loader import OEMMetricsLoader
from metrics_engine.metrics_normalizer import MetricsNormalizer
from incident_engine.metric_incident_builder import MetricIncidentBuilder
from incident_engine.incident_timeline import IncidentTimelineBuilder

# ------------------------------------------------
# 🔴 SYNTHETIC INCIDENT (TIME-ALIGNED WITH METRICS)
# ------------------------------------------------
incident = {
    "database": "mitestdb",
    "category": "CPU",
    "severity": "CRITICAL",
    "message": "Server reboot detected",
    "start_time": datetime(2025, 12, 25, 14, 47, 0)
}

# ------------------------------------------------
# Load metrics (CSV)
# ------------------------------------------------
loader = OEMMetricsLoader("data/oem_metrics_25.csv")
raw_metrics = loader.load_metrics()

normalizer = MetricsNormalizer()
metrics = normalizer.normalize(raw_metrics)

# ------------------------------------------------
# Build timeline
# ------------------------------------------------
timeline_builder = IncidentTimelineBuilder(
    incidents=[incident],   # 👈 ONLY THIS INCIDENT
    metrics=metrics
)

timeline = timeline_builder.build_timeline(incident)

# ------------------------------------------------
# Output
# ------------------------------------------------
print("\n===== INCIDENT TIMELINE =====")
print("Incident Time:", timeline["incident_time"])
print("Incident:", timeline["incident"])

print("\n--- BEFORE INCIDENT ---")
for e in timeline["before"][-5:]:
    print(e)

print("\n--- AFTER INCIDENT ---")
for e in timeline["after"][:5]:
    print(e)

