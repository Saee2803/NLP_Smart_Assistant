from fastapi import APIRouter
from data_engine.global_cache import GLOBAL_DATA, SYSTEM_READY
from incident_engine.risk_analyzer import RiskAnalyzer

confidence_router = APIRouter(
    tags=["Confidence API"]
)


@confidence_router.get("/")
def confidence():
    """
    Returns overall system confidence based on incident risk.
    Python 3.6 compatible: explicit loops and safe division.
    """
    # Check if system is initialized
    if not SYSTEM_READY.get("ready", False):
        return {
            "confidence_score": 0,
            "confidence_level": "INITIALIZING",
            "reason": "System is loading data"
        }
    
    incidents = GLOBAL_DATA.get("incidents", [])

    if not incidents:
        return {
            "confidence_score": 100,
            "confidence_level": "HIGH",
            "reason": "No incidents detected"
        }

    analyzer = RiskAnalyzer(incidents)

    # Compute average risk (Python 3.6 safe - explicit loop)
    scores = []
    
    for i in incidents:
        if i is None or not isinstance(i, dict):
            continue
        
        target = i.get("target")
        if not target:
            continue
        
        try:
            risk = analyzer.analyze_target(target)
            if risk:
                risk_score = risk.get("risk_score", 0)
                if risk_score is not None:
                    scores.append(risk_score)
        except Exception:
            pass

    if not scores:
        return {
            "confidence_score": 100,
            "confidence_level": "HIGH",
            "reason": "No risk patterns detected"
        }

    # Calculate average (safe division)
    total = sum(scores)
    count = len(scores)
    
    if count == 0:
        avg_risk = 0
    else:
        avg_risk = total / float(count)

    confidence = max(100 - avg_risk, 25)

    # Determine confidence level
    if confidence >= 70:
        level = "HIGH"
    elif confidence >= 40:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        "confidence_score": round(confidence, 2),
        "confidence_level": level,
        "reason": "Calculated from historical incident risk"
    }

