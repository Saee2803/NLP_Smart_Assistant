from fastapi import APIRouter
from data_engine.global_cache import GLOBAL_DATA, SYSTEM_READY
from incident_engine.correlation_engine import CorrelationEngine

rca_router = APIRouter(
    tags=["RCA"]
)

@rca_router.get("/latest")
def latest_rca():
    """
    Returns RCA for the latest critical incident.
    PRODUCTION FIX: Uses GLOBAL_DATA as single source of truth.
    """
    # Check if system is initialized
    if not SYSTEM_READY.get("ready", False):
        return {"message": "System initializing"}
    
    # Get data from GLOBAL_DATA
    incidents = GLOBAL_DATA.get("incidents", [])
    alerts = GLOBAL_DATA.get("alerts", [])
    metrics = GLOBAL_DATA.get("metrics", [])
    
    if not incidents:
        return {"message": "No incidents detected"}

    # Filter critical incidents
    criticals = [
        i for i in incidents
        if i and i.get("severity") == "CRITICAL"
    ]

    if not criticals:
        return {"message": "No critical incidents detected"}

    # Get latest critical incident
    latest_incident = sorted(
        criticals,
        key=lambda x: x.get("last_seen") or x.get("first_seen"),
        reverse=True
    )[0]

    # Perform RCA using CorrelationEngine
    try:
        engine = CorrelationEngine(alerts, metrics, incidents)
        
        # Find related alert for this incident
        target = latest_incident.get("target")
        related_alerts = [
            a for a in alerts
            if a and a.get("target") == target
        ]
        
        if related_alerts:
            latest_alert = sorted(related_alerts, key=lambda x: x.get("time"), reverse=True)[0]
            rca = engine.analyze(latest_alert)
            
            return {
                "incident": latest_incident.get("issue_type"),
                "target": target,
                "time": str(latest_incident.get("last_seen")),
                "root_cause": rca.get("root_cause"),
                "current_status": rca.get("current_status"),
                "recommendation": rca.get("recommendation"),
                "risky": rca.get("risky", False)
            }
        else:
            return {
                "incident": latest_incident.get("issue_type"),
                "target": target,
                "message": "Incident detected but no related alerts found"
            }
    
    except Exception as e:
        return {
            "message": "RCA analysis failed",
            "error": str(e)
        }

