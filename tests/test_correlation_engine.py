from datetime import datetime
from incident_engine.correlation_engine import CorrelationEngine


# ---- Dummy incident (like OEM XML alert) ----
incident = {
    "start_time": datetime(2025, 12, 25, 2, 0, 0),
    "database": "mitestdb",
    "category": "CPU",
    "severity": "CRITICAL",
    "message": "Server reboot detected"
}

# ---- Dummy metric spike ----
metrics = [
    {
        "time": datetime(2025, 12, 25, 1, 58, 0),
        "category": "CPU",
        "severity": "CRITICAL",
        "value": 100.0
    }
]

engine = CorrelationEngine([incident], metrics)

result = engine.analyze_incident(incident)

print("Root cause:", result["root_cause"])
print("Current status:", result["current_status"])
print("Recommendation:", result["recommendation"])

