from datetime import datetime
from fastapi import APIRouter
from collections import Counter

from data_engine.global_cache import GLOBAL_DATA, SYSTEM_READY, INIT_STATUS
from data_engine.target_normalizer import TargetNormalizer
from incident_engine.metric_alert_validator import MetricAlertValidator
from incident_engine.risk_analyzer import RiskAnalyzer

dashboard_router = APIRouter()


# =====================================================
# SYSTEM STATUS (NEW - PRODUCTION WIRING)
# =====================================================
@dashboard_router.get("/system-status")
def system_status():
    """Check if system is ready to serve data."""
    return {
        "ready": SYSTEM_READY.get("ready", False),
        "status": "READY" if SYSTEM_READY.get("ready", False) else "INITIALIZING",
        "init_status": INIT_STATUS
    }


# =====================================================
# DEBUG: CHECK GLOBAL_DATA STATUS
# =====================================================
@dashboard_router.get("/debug")
def debug_global_data():
    return {
        "system_ready": SYSTEM_READY.get("ready", False),
        "alerts_count": len(GLOBAL_DATA.get("alerts", [])),
        "incidents_count": len(GLOBAL_DATA.get("incidents", [])),
        "metrics_count": len(GLOBAL_DATA.get("metrics", [])),
        "validated_alerts_count": len(GLOBAL_DATA.get("validated_alerts", [])),
        "risk_trends_count": len(GLOBAL_DATA.get("risk_trends", []))
    }


# =====================================================
# DEBUG: FORCE RELOAD DATA
# =====================================================
@dashboard_router.get("/force-reload")
def force_reload():
    from data_engine.data_fetcher import DataFetcher
    from incident_engine.risk_trend_analyzer import RiskTrendAnalyzer
    from incident_engine.failure_predictor import FailurePredictor
    from incident_engine.correlation_engine import CorrelationEngine
    from learning.pattern_engine import PatternEngine
    from storage.database import Database
    from data_engine.global_cache import set_system_ready
    from data_engine.target_normalizer import TargetNormalizer
    global _validation_cache, _validation_cache_timestamp
    
    try:
        # Mark system as not ready during reload
        set_system_ready(False)
        INIT_STATUS["alerts_loaded"] = False
        INIT_STATUS["metrics_loaded"] = False
        INIT_STATUS["incidents_built"] = False
        INIT_STATUS["validations_computed"] = False
        INIT_STATUS["risk_trends_computed"] = False
        INIT_STATUS["patterns_computed"] = False
        INIT_STATUS["predictions_computed"] = False
        INIT_STATUS["rca_computed"] = False
        
        # Clear validation cache
        _validation_cache = None
        _validation_cache_timestamp = None
        
        fetcher = DataFetcher()
        data = fetcher.fetch({})
        
        alerts = data.get("alerts", [])
        metrics = data.get("metrics", [])
        incidents = data.get("incidents", [])
        
        INIT_STATUS["alerts_loaded"] = True
        INIT_STATUS["metrics_loaded"] = True
        INIT_STATUS["incidents_built"] = True
        INIT_STATUS["validations_computed"] = True  # Will compute on-demand
        
        trend_analyzer: RiskTrendAnalyzer = RiskTrendAnalyzer(alerts, incidents)
        risk_trends = trend_analyzer.build_trends()
        INIT_STATUS["risk_trends_computed"] = True
        
        # Recompute patterns
        patterns = []
        try:
            db = Database()
            targets = set()
            for alert in alerts:
                if alert and alert.get("target"):
                    normalized = TargetNormalizer.normalize(alert.get("target"))
                    if normalized:
                        targets.add(normalized)
            
            pattern_engine: PatternEngine = PatternEngine(db, min_confidence=0.60, lookback_days=60)
            for target in sorted(targets):
                try:
                    day_patterns = pattern_engine.detect_day_of_week_patterns(target)
                    patterns.extend(day_patterns)
                    hour_patterns = pattern_engine.detect_hour_of_day_patterns(target)
                    patterns.extend(hour_patterns)
                except Exception:
                    pass
            db.close()
            INIT_STATUS["patterns_computed"] = True
        except Exception:
            pass
        
        # Recompute predictions
        predictions = []
        try:
            predictor: FailurePredictor = FailurePredictor(alerts, incidents, risk_trends)
            targets = set()
            for alert in alerts:
                if alert and alert.get("target"):
                    normalized = TargetNormalizer.normalize(alert.get("target"))
                    if normalized:
                        targets.add(normalized)
            
            for target in sorted(targets):
                try:
                    prediction = predictor.predict(target)
                    if prediction.get("failure_probability", 0) >= 15:
                        predictions.append(prediction)
                except Exception:
                    pass
            
            predictions.sort(key=lambda p: p.get("failure_probability", 0), reverse=True)
            INIT_STATUS["predictions_computed"] = True
        except Exception:
            pass
        
        # Recompute RCA summaries
        rca_summaries = []
        try:
            critical_incidents = [
                i for i in incidents
                if i and i.get("severity") == "CRITICAL"
            ]
            critical_incidents.sort(
                key=lambda x: x.get("last_seen") or x.get("first_seen"),
                reverse=True
            )
            recent_criticals = critical_incidents[:10]
            
            for incident in recent_criticals:
                try:
                    target = incident.get("target")
                    if not target:
                        continue
                    
                    related_alerts = [
                        a for a in alerts
                        if a and TargetNormalizer.equals(a.get("target"), target)
                    ]
                    
                    if related_alerts:
                        latest_alert = sorted(
                            related_alerts, 
                            key=lambda x: x.get("time"),
                            reverse=True
                        )[0]
                        
                        engine: CorrelationEngine = CorrelationEngine(alerts, metrics, incidents)
                        rca = engine.analyze(latest_alert)
                        
                        rca_summaries.append({
                            "incident": incident,
                            "rca": rca
                        })
                except Exception:
                    pass
            
            INIT_STATUS["rca_computed"] = True
        except Exception:
            pass
        
        GLOBAL_DATA.clear()
        GLOBAL_DATA.update({
            "alerts": alerts,
            "metrics": metrics,
            "incidents": incidents,
            "validated_alerts": [],  # Empty, computed on-demand
            "risk_trends": risk_trends,
            "patterns": patterns,
            "predictions": predictions,
            "rca_summaries": rca_summaries
        })
        
        # Mark system as ready after successful reload
        set_system_ready(True)
        
        return {
            "success": True,
            "alerts_count": len(alerts),
            "incidents_count": len(incidents),
            "metrics_count": len(metrics),
            "validated_count": "computed on-demand",
            "trends_count": len(risk_trends),
            "patterns_count": len(patterns),
            "predictions_count": len(predictions),
            "rca_count": len(rca_summaries)
        }
    except Exception as e:
        import traceback
        set_system_ready(False)
        INIT_STATUS["error"] = str(e)
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


# =====================================================
# INTERNAL: NORMALIZE DB TARGET
# =====================================================
def normalize_db(target):
    # Use centralized TargetNormalizer
    return TargetNormalizer.normalize(target)


# =====================================================
# SUMMARY (PRODUCTION WIRING - CHECK SYSTEM READY)
# =====================================================
@dashboard_router.get("/summary")
def summary():
    # Check if system is initialized
    if not SYSTEM_READY.get("ready", False):
        return {
            "status": "INITIALIZING",
            "message": "System is loading data. Please wait...",
            "total_alerts": 0,
            "critical_alerts": 0,
            "total_databases": 0,
            "most_problematic_db": "N/A",
            "overall_health": "SYSTEM INITIALIZING",
            "confidence": {
                "confidence_score": 0,
                "confidence_level": "N/A"
            }
        }
    
    alerts = GLOBAL_DATA.get("alerts", [])
    incidents = GLOBAL_DATA.get("incidents", [])

    # Collect unique logical databases
    dbs = set()
    for a in alerts:
        db = normalize_db(a.get("target") if a else None)
        if db:
            dbs.add(db)

    analyzer: RiskAnalyzer[list] = RiskAnalyzer(incidents)

    risks = []
    for db in dbs:
        try:
            r = analyzer.analyze_target(db)
            if r:
                risks.append(r)
        except Exception:
            pass

    worst = max(risks, key=lambda r: r.get("risk_score", 0), default=None)
    worst_score = worst.get("risk_score", 0) if worst else 0

    critical_alerts: int = sum(
        1 for a in alerts if a and a.get("severity") == "CRITICAL"
    )

    # Confidence calculation (REALISTIC)
    if worst_score >= 10000:
        confidence_score = 20
    elif worst_score >= 5000:
        confidence_score = 40
    elif worst_score > 0:
        confidence_score = 70
    else:
        confidence_score = 85

    confidence_level: str = (
        "LOW" if confidence_score < 40 else
        "MEDIUM" if confidence_score < 70 else
        "HIGH"
    )

    overall_health: str = (
        "Critical" if confidence_level == "LOW" else
        "Degraded" if confidence_level == "MEDIUM" else
        "Healthy"
    )

    return {
        "total_alerts": len(alerts),
        "critical_alerts": critical_alerts,
        "total_databases": len(dbs),
        "most_problematic_db": worst.get("target") if worst else "N/A",
        "overall_health": overall_health,
        "confidence": {
            "confidence_score": confidence_score,
            "confidence_level": confidence_level
        }
    }


# =====================================================
# DATABASE LIST (PRODUCTION WIRING - CHECK SYSTEM READY)
# =====================================================
@dashboard_router.get("/databases")
def databases():
    # Check if system is initialized
    if not SYSTEM_READY.get("ready", False):
        return []
    
    alerts = GLOBAL_DATA.get("alerts", [])
    incidents = GLOBAL_DATA.get("incidents", [])

    dbs = set()
    for a in alerts:
        db = normalize_db(a.get("target") if a else None)
        if db:
            dbs.add(db)

    analyzer: RiskAnalyzer[list] = RiskAnalyzer(incidents)
    result = []

    for db in sorted(dbs):
        try:
            risk = analyzer.analyze_target(db)
            risk_score = risk.get("risk_score", 0)
        except Exception:
            risk_score = 0

        critical_count: int = sum(
            1 for a in alerts
            if a and normalize_db(a.get("target")) == db and a.get("severity") == "CRITICAL"
        )

        issues = [
            i.get("issue_type")
            for i in incidents
            if i and normalize_db(i.get("target")) == db and i.get("issue_type")
        ]

        top_issue = Counter(issues).most_common(1)[0][0] if issues else "N/A"

        result.append({
            "database": db,
            "status": "UNSTABLE" if critical_count > 0 else "STABLE",
            "critical_alerts": critical_count,
            "top_issue": top_issue
        })

    return result


# =====================================================
# HISTORY (INCIDENTS – PRODUCTION WIRING)
# =====================================================
@dashboard_router.get("/incidents")
def incidents():
    # Check if system is initialized
    if not SYSTEM_READY.get("ready", False):
        return []
    
    inc = GLOBAL_DATA.get("incidents", [])
    return inc[:500] if inc else []


# =====================================================
# ALERT ↔ METRIC VALIDATION (ON-DEMAND WITH CACHING)
# =====================================================
_validation_cache = None
_validation_cache_timestamp = None

@dashboard_router.get("/alert-validation")
def alert_validation():
    """
    On-demand validation computation with caching.
    Enterprise approach: Don't block startup, compute when needed.
    """
    global _validation_cache, _validation_cache_timestamp
    
    # Check if system is initialized
    if not SYSTEM_READY.get("ready", False):
        return []
    
    # Return cached results if available
    if _validation_cache is not None:
        return _validation_cache[:100]
    
    # Compute validation on first request
    print("[*] Computing alert validation on-demand...")
    from incident_engine.metric_alert_validator import MetricAlertValidator
    from datetime import datetime
    
    alerts = GLOBAL_DATA.get("alerts", [])
    metrics = GLOBAL_DATA.get("metrics", [])
    
    if not alerts or not metrics:
        return []
    
    try:
        validator: MetricAlertValidator = MetricAlertValidator(alerts, metrics)
        _validation_cache = validator.validate()
        _validation_cache_timestamp = datetime.now()
        
        # Update GLOBAL_DATA for consistency
        GLOBAL_DATA["validated_alerts"] = _validation_cache
        
        print("[OK] Validation computed: {0} alerts validated".format(len(_validation_cache)))
        return _validation_cache[:100]
    except Exception as e:
        print("[ERROR] Validation computation failed: {0}".format(str(e)))
        import traceback
        traceback.print_exc()
        return []


# =====================================================
# RISK TREND (PRODUCTION WIRING)
# =====================================================
@dashboard_router.get("/risk-trend")
def risk_trend():
    # Check if system is initialized
    if not SYSTEM_READY.get("ready", False):
        return []
    
    return GLOBAL_DATA.get("risk_trends", [])


# =====================================================
# LEARNED PATTERNS (NEW - PRODUCTION INTELLIGENCE)
# =====================================================
@dashboard_router.get("/patterns")
def patterns():
    """
    Returns learned patterns from historical data:
    - Day-of-week patterns
    - Hour-of-day patterns
    - Alert combinations
    """
    # Check if system is initialized
    if not SYSTEM_READY.get("ready", False):
        return []
    
    return GLOBAL_DATA.get("patterns", [])


# =====================================================
# FAILURE PREDICTIONS (NEW - PROACTIVE ALERTS)
# =====================================================
@dashboard_router.get("/predictions")
def predictions():
    """
    Returns failure predictions for at-risk databases.
    Proactively identifies systems requiring attention.
    """
    # Check if system is initialized
    if not SYSTEM_READY.get("ready", False):
        return []
    
    return GLOBAL_DATA.get("predictions", [])


# =====================================================
# RCA SUMMARIES (NEW - ROOT CAUSE VISIBILITY)
# =====================================================
@dashboard_router.get("/rca-summary")
def rca_summary():
    """
    Returns RCA analyses for recent critical incidents.
    Shows metric evidence and explainable root causes.
    Includes display_alert_type for DBA-grade display.
    """
    # Check if system is initialized
    if not SYSTEM_READY.get("ready", False):
        return []
    
    summaries = GLOBAL_DATA.get("rca_summaries", [])
    
    # Format for dashboard display
    result = []
    for summary in summaries[:20]:  # Limit to 20 most recent
        incident = summary.get("incident", {})
        rca = summary.get("rca", {})
        
        # Get display_alert_type from incident (already computed)
        display_alert_type = incident.get("display_alert_type")
        if not display_alert_type:
            display_alert_type = incident.get("issue_type", "Unknown")
        
        result.append({
            "target": incident.get("target"),
            "issue_type": incident.get("issue_type"),
            "display_alert_type": display_alert_type,
            "severity": incident.get("severity"),
            "time": str(incident.get("last_seen") or incident.get("first_seen")),
            "root_cause": rca.get("root_cause"),
            "risky": rca.get("risky", False),
            "recommendation": rca.get("recommendation"),
            "current_status": rca.get("current_status")
        })
    
    return result


# =====================================================
# OEM DASHBOARD SUMMARY (COMPREHENSIVE)
# =====================================================
@dashboard_router.get("/oem-summary")
def oem_summary():
    """
    Comprehensive OEM dashboard data.
    Returns all data needed for the new OEM dashboard UI.
    """
    if not SYSTEM_READY.get("ready", False):
        return {
            "status": "INITIALIZING",
            "total_databases": 0,
            "total_alerts": 0,
            "critical_count": 0,
            "top_databases": [],
            "top_issues": [],
            "recent_alerts": [],
            "time_patterns": [],
            "insights": []
        }
    
    alerts = GLOBAL_DATA.get("alerts", [])
    incidents = GLOBAL_DATA.get("incidents", [])
    
    # Count by database
    db_counts = Counter()
    for a in alerts:
        if a:
            db = normalize_db(a.get("target"))
            if db:
                db_counts[db] += 1
    
    # Count by issue type
    issue_counts = Counter()
    for a in alerts:
        if a:
            issue = a.get("issue_type") or a.get("alert_type") or "UNKNOWN"
            issue_counts[issue] += 1
    
    # Count by severity
    severity_counts = Counter()
    for a in alerts:
        if a:
            severity = (a.get("severity") or "INFO").upper()
            severity_counts[severity] += 1
    
    # Time patterns (hour of day)
    hour_counts = Counter()
    for a in alerts:
        if a:
            time_str = a.get("time") or a.get("first_seen") or ""
            if time_str:
                try:
                    from datetime import datetime
                    if isinstance(time_str, str):
                        # Try multiple formats
                        for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"]:
                            try:
                                dt: datetime = datetime.strptime(time_str[:19], fmt[:len(time_str)])
                                hour_counts[dt.hour] += 1
                                break
                            except Exception:
                                pass
                except Exception:
                    pass
    
    # Top databases
    top_databases = [
        {"name": db, "alert_count": count}
        for db, count in db_counts.most_common(10)
    ]
    
    # Top issues
    top_issues = [
        {"type": issue, "count": count}
        for issue, count in issue_counts.most_common(10)
    ]
    
    # Recent alerts (from incidents or alerts) with display_alert_type
    recent_alerts = []
    for a in alerts[:30]:
        if a:
            # Get display_alert_type (derive if not present)
            display_alert_type = a.get("display_alert_type")
            if not display_alert_type:
                from incident_engine.alert_type_classifier import classify_alert_type
                display_alert_type = classify_alert_type(
                    a.get("issue_type"),
                    a.get("message")
                )
            
            recent_alerts.append({
                "target": normalize_db(a.get("target")) or "Unknown",
                "issue_type": a.get("issue_type") or a.get("alert_type") or "Alert",
                "display_alert_type": display_alert_type,
                "severity": a.get("severity") or "INFO",
                "time": a.get("time") or a.get("first_seen"),
                "message": a.get("message") or a.get("description") or ""
            })
    
    # Time patterns (top 5 hours)
    time_patterns = [
        {"hour": hour, "count": count}
        for hour, count in hour_counts.most_common(5)
    ]
    
    # Generate insights
    insights = []
    if top_databases:
        insights.append(f"{top_databases[0]['name']} is the most problematic database with {top_databases[0]['alert_count']:,} alerts in the historical data.")
    if top_issues:
        insights.append(f"{top_issues[0]['type']} is the most frequent issue type, occurring {top_issues[0]['count']:,} times.")
    if time_patterns:
        peak_hour = time_patterns[0]['hour']
        insights.append(f"Alert activity peaks at {peak_hour}:00 hours, consider investigating scheduled jobs or maintenance windows.")
    if severity_counts.get("CRITICAL", 0) > 100:
        insights.append(f"High volume of critical alerts ({severity_counts['CRITICAL']:,}) detected - immediate attention recommended.")
    
    return {
        "status": "READY",
        "total_databases": len(db_counts),
        "total_alerts": len(alerts),
        "critical_count": severity_counts.get("CRITICAL", 0),
        "warning_count": severity_counts.get("WARNING", 0),
        "top_databases": top_databases,
        "top_issues": top_issues,
        "recent_alerts": recent_alerts,
        "time_patterns": time_patterns,
        "insights": insights
    }

