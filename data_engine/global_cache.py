# data_engine/global_cache.py

"""
Global in-memory data cache.
Loaded once at startup and shared across:
- Dashboard
- Chatbot
- Risk / Trend analyzers

PRODUCTION WIRING:
- SYSTEM_READY flag indicates whether initial data load is complete
- Controllers must check this flag before serving data

PRODUCTION FIX (v2.2):
- Added safe data access functions
- Added data freshness tracking
- Prevents stale/partial data access
"""

from datetime import datetime

GLOBAL_DATA = {
    "alerts": [],
    "metrics": [],
    "incidents": [],
    "validated_alerts": [],
    "risk_trends": [],
    "patterns": [],           # NEW: Day/hour/combination patterns from PatternEngine
    "predictions": [],        # NEW: Failure predictions from FailurePredictor
    "rca_summaries": []       # NEW: RCA analyses for dashboard
}

# System readiness flag (mutable container to allow modification)
_SYSTEM_STATE = {
    "ready": False,
    "load_timestamp": None,   # When data was loaded
    "load_complete": False    # True only when ALL data is loaded
}

# Initialization status
INIT_STATUS = {
    "alerts_loaded": False,
    "metrics_loaded": False,
    "incidents_built": False,
    "validations_computed": False,
    "risk_trends_computed": False,
    "patterns_computed": False,      # NEW: Pattern learning status
    "predictions_computed": False,   # NEW: Failure predictions status
    "rca_computed": False,           # NEW: RCA summaries status
    "error": None
}


def set_system_ready(ready=True):
    """Set system ready status."""
    _SYSTEM_STATE["ready"] = ready
    if ready:
        _SYSTEM_STATE["load_timestamp"] = datetime.now().isoformat()
        _SYSTEM_STATE["load_complete"] = True


def is_system_ready():
    """Check if system is ready."""
    return _SYSTEM_STATE["ready"]


def get_alerts_safe():
    """
    PRODUCTION FIX: Safely get alerts with readiness check.
    Returns empty list if system is not ready.
    """
    if not _SYSTEM_STATE["ready"]:
        return []
    return GLOBAL_DATA.get("alerts", [])


def get_data_timestamp():
    """Get the timestamp when data was loaded."""
    return _SYSTEM_STATE.get("load_timestamp")


def is_data_fresh(max_age_seconds=3600):
    """
    Check if data is fresh (loaded within max_age_seconds).
    Default: 1 hour.
    """
    timestamp = _SYSTEM_STATE.get("load_timestamp")
    if not timestamp:
        return False
    try:
        load_time = datetime.fromisoformat(timestamp)
        age = (datetime.now() - load_time).total_seconds()
        return age < max_age_seconds
    except:
        return False


# Backward compatibility
SYSTEM_READY = _SYSTEM_STATE

