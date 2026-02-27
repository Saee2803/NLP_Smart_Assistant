from controllers.alerts_controller import load_oem_data
from metrics_engine.metrics_loader import OEMMetricsLoader
from metrics_engine.metrics_normalizer import MetricsNormalizer
from incident_engine.night_incident_report import NightIncidentReportGenerator


# Load incidents from OEM XML / alerts
incidents, _ = load_oem_data()

# Load metrics
loader = OEMMetricsLoader("data/oem_metrics_25.csv")
raw_metrics = loader.load_metrics()

normalizer = MetricsNormalizer()
metrics = normalizer.normalize(raw_metrics)

# Generate night report
generator = NightIncidentReportGenerator(incidents, metrics)
report = generator.generate(start_hour=0, end_hour=6)

print("\n===== NIGHT INCIDENT REPORT (12 AM – 6 AM) =====\n")

if not report:
    print("No night incidents detected.")
else:
    for r in report:
        print(f"🕒 Time        : {r['incident_time']}")
        print(f"🗄️  Database    : {r['database']}")
        print(f"❗ What        : {r['what_happened']}")
        print(f"🔍 Why         : {r['why_happened']}")
        print(f"⚠️  Risky      : {r['risky']}")
        print(f"✅ Status      : {r['current_status']}")
        print(f"💡 Recommendation:")
        print(f"   - {r['recommendation']}")
        print("-" * 60)

