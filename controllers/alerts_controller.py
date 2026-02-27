from fastapi import APIRouter
from data_engine.global_cache import GLOBAL_DATA, SYSTEM_READY
from incident_engine.alert_type_classifier import classify_alert_type

alerts_router = APIRouter(
    tags=["Alerts API"]
)


@alerts_router.get("/")
def get_alerts(limit=200):
    """
    Returns latest normalized alerts with display_alert_type.
    Python 3.6 compatible: explicit loop instead of list comprehension.
    """
    # Check if system is initialized
    if not SYSTEM_READY.get("ready", False):
        return []
    
    if not isinstance(limit, int) or limit <= 0:
        limit = 200

    alerts = GLOBAL_DATA.get("alerts", [])

    if not alerts:
        return []

    # Build result (Python 3.6 safe - no list comprehension with dict access)
    result = []
    
    for a in alerts[:limit]:
        if a is None or not isinstance(a, dict):
            continue
        
        # Get display_alert_type (derive if not present)
        display_alert_type = a.get("display_alert_type")
        if not display_alert_type:
            display_alert_type = classify_alert_type(
                a.get("issue_type"),
                a.get("message")
            )
        
        alert_obj = {
            "time": a.get("time"),
            "target": a.get("target"),
            "severity": a.get("severity"),
            "message": a.get("message"),
            "metric": a.get("metric"),
            "issue_type": a.get("issue_type"),
            "display_alert_type": display_alert_type
        }
        
        result.append(alert_obj)

    return result

