"""
==========================================================================
PHASE 5: PREDICTIVE INTELLIGENCE ENGINE
==========================================================================

Transforms the DBA Intelligence System from:
    "This is what is happening"
into:
    "This is likely to happen next and how serious it could become"

You are an Autonomous Enterprise DBA Intelligence System with:
- Historical awareness
- Trend detection  
- Adaptive learning
- Risk projection

You behave like: Principal DBA + SRE + Incident Postmortem Reviewer + Capacity Analyst

📌 ABSOLUTE DATA RULES (NON-NEGOTIABLE):
  - Use ONLY current CSV alert data
  - Use historical snapshots (if available)
  - NEVER guess timelines
  - NEVER predict exact failures
  - Predictions are RISK-BASED, not deterministic

==========================================================================
"""

from typing import Dict, List, Any, Optional, Tuple
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import re
import json
import os


# ============================================================
# PHASE 5 LAYER 1: TREND DETECTION ENGINE
# ============================================================
class TrendDetectionEngine:
    """
    Analyzes alert trends over time.
    
    Compares: Current volume vs Previous snapshots
    Detects: Increasing / Stable / Decreasing patterns
    
    Trend Categories:
      🟢 Improving
      🟡 Stable  
      🔴 Deteriorating
    """
    
    # Thresholds for trend classification
    SIGNIFICANT_CHANGE_THRESHOLD = 0.15  # 15% change is significant
    MAJOR_CHANGE_THRESHOLD = 0.30  # 30% change is major
    
    def __init__(self, history_path: str = None):
        """Initialize with optional history storage path."""
        self.history_path = history_path or "data/alert_history.json"
        self.history_snapshots: List[Dict] = []
        self._load_history()
    
    def _load_history(self):
        """Load historical snapshots from storage."""
        try:
            if os.path.exists(self.history_path):
                with open(self.history_path, 'r') as f:
                    self.history_snapshots = json.load(f)
        except Exception:
            self.history_snapshots = []
    
    def _save_history(self):
        """Save historical snapshots to storage."""
        try:
            os.makedirs(os.path.dirname(self.history_path), exist_ok=True)
            with open(self.history_path, 'w') as f:
                json.dump(self.history_snapshots[-100:], f)  # Keep last 100 snapshots
        except Exception:
            pass
    
    def capture_snapshot(self, alerts: List[Dict], timestamp: datetime = None):
        """
        Capture a point-in-time snapshot of alert state.
        Call this periodically to build history.
        """
        timestamp = timestamp or datetime.now()
        
        # Calculate current state metrics
        severity_counts = Counter()
        database_counts = Counter()
        category_counts = Counter()
        
        for alert in alerts:
            severity = str(alert.get("severity", "UNKNOWN")).upper()
            database = str(alert.get("target_name") or alert.get("target") or "UNKNOWN").upper()
            category = str(alert.get("category", "GENERAL")).upper()
            
            severity_counts[severity] += 1
            database_counts[database] += 1
            category_counts[category] += 1
        
        snapshot = {
            "timestamp": timestamp.isoformat(),
            "total_alerts": len(alerts),
            "critical_count": severity_counts.get("CRITICAL", 0),
            "warning_count": severity_counts.get("WARNING", 0),
            "top_databases": dict(database_counts.most_common(10)),
            "top_categories": dict(category_counts.most_common(10))
        }
        
        self.history_snapshots.append(snapshot)
        self._save_history()
        
        return snapshot
    
    def analyze_trend(self, current_alerts: List[Dict]) -> Dict[str, Any]:
        """
        Analyze trend by comparing current state to historical snapshots.
        
        Returns comprehensive trend analysis with confidence levels.
        """
        # Current state
        current_critical = sum(1 for a in current_alerts 
                              if str(a.get("severity", "")).upper() == "CRITICAL")
        current_warning = sum(1 for a in current_alerts 
                             if str(a.get("severity", "")).upper() == "WARNING")
        current_total = len(current_alerts)
        
        # Check if we have historical data
        if len(self.history_snapshots) < 2:
            return {
                "trend_available": False,
                "message": "Trend analysis unavailable due to insufficient historical data.",
                "current_state": {
                    "total": current_total,
                    "critical": current_critical,
                    "warning": current_warning
                },
                "confidence": "N/A"
            }
        
        # Calculate historical averages
        recent_snapshots = self.history_snapshots[-10:]  # Last 10 snapshots
        
        avg_total = sum(s.get("total_alerts", 0) for s in recent_snapshots) / len(recent_snapshots)
        avg_critical = sum(s.get("critical_count", 0) for s in recent_snapshots) / len(recent_snapshots)
        avg_warning = sum(s.get("warning_count", 0) for s in recent_snapshots) / len(recent_snapshots)
        
        # Calculate percent changes
        def pct_change(current, avg):
            if avg == 0:
                return 0 if current == 0 else 1.0
            return (current - avg) / avg
        
        total_change = pct_change(current_total, avg_total)
        critical_change = pct_change(current_critical, avg_critical)
        warning_change = pct_change(current_warning, avg_warning)
        
        # Classify trends
        def classify_trend(change):
            if change < -self.SIGNIFICANT_CHANGE_THRESHOLD:
                return "improving"
            elif change > self.MAJOR_CHANGE_THRESHOLD:
                return "deteriorating"
            elif change > self.SIGNIFICANT_CHANGE_THRESHOLD:
                return "worsening"
            else:
                return "stable"
        
        overall_trend = classify_trend(critical_change)  # Critical is most important
        
        # Determine confidence based on history depth
        if len(self.history_snapshots) >= 20:
            confidence = "High"
        elif len(self.history_snapshots) >= 10:
            confidence = "Medium"
        else:
            confidence = "Low"
        
        return {
            "trend_available": True,
            "overall_trend": overall_trend,
            "overall_indicator": self._get_trend_indicator(overall_trend),
            "critical_trend": {
                "direction": classify_trend(critical_change),
                "change_pct": round(critical_change * 100, 1),
                "current": current_critical,
                "historical_avg": round(avg_critical, 0)
            },
            "warning_trend": {
                "direction": classify_trend(warning_change),
                "change_pct": round(warning_change * 100, 1),
                "current": current_warning,
                "historical_avg": round(avg_warning, 0)
            },
            "total_trend": {
                "direction": classify_trend(total_change),
                "change_pct": round(total_change * 100, 1),
                "current": current_total,
                "historical_avg": round(avg_total, 0)
            },
            "confidence": confidence,
            "history_depth": len(self.history_snapshots)
        }
    
    def _get_trend_indicator(self, trend: str) -> str:
        """Get visual indicator for trend."""
        return {
            "improving": "🟢 Improving",
            "stable": "🟡 Stable",
            "worsening": "🟠 Worsening",
            "deteriorating": "🔴 Deteriorating"
        }.get(trend, "⚪ Unknown")


# ============================================================
# PHASE 5 LAYER 2: INCIDENT TRAJECTORY PREDICTION
# ============================================================
class IncidentTrajectoryPredictor:
    """
    For P1/P2 incidents, estimates likely trajectory:
    - Self-resolve
    - Persist
    - Escalate
    
    Uses ONLY: Alert frequency, Persistence, Past patterns
    NEVER claims certainty - uses confidence labels.
    """
    
    def __init__(self):
        self.incident_history: Dict[str, List[Dict]] = {}
    
    def predict_trajectory(
        self, 
        incident_signature: str,
        current_count: int,
        first_seen: datetime,
        last_seen: datetime,
        priority: str,
        pattern: str,
        historical_data: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Predict likely trajectory for an incident.
        
        Returns trajectory prediction with confidence level.
        """
        # Calculate incident characteristics
        duration = (last_seen - first_seen).total_seconds() if first_seen and last_seen else 0
        duration_hours = duration / 3600 if duration > 0 else 0
        
        # Calculate alert rate
        alert_rate = current_count / max(duration_hours, 0.1)  # alerts per hour
        
        # Default prediction factors
        escalation_score = 0
        resolution_score = 0
        persistence_score = 0
        
        # Factor 1: Pattern-based scoring
        if pattern == "escalating":
            escalation_score += 3
        elif pattern == "persistent":
            persistence_score += 3
        elif pattern == "transient":
            resolution_score += 2
        elif pattern == "continuous":
            persistence_score += 2
        
        # Factor 2: Priority-based scoring
        if priority == "P1":
            escalation_score += 2
            persistence_score += 1
        elif priority == "P2":
            persistence_score += 2
        else:
            resolution_score += 1
        
        # Factor 3: Volume-based scoring
        if current_count > 10000:
            escalation_score += 2
        elif current_count > 1000:
            persistence_score += 1
        elif current_count < 10:
            resolution_score += 2
        
        # Factor 4: Rate-based scoring
        if alert_rate > 100:  # > 100 alerts/hour
            escalation_score += 2
        elif alert_rate > 10:
            persistence_score += 1
        elif alert_rate < 1:
            resolution_score += 1
        
        # Factor 5: Duration-based scoring
        if duration_hours > 48:
            persistence_score += 2
        elif duration_hours > 24:
            persistence_score += 1
        elif duration_hours < 1:
            resolution_score += 1
        
        # Determine trajectory
        max_score = max(escalation_score, resolution_score, persistence_score)
        
        if escalation_score == max_score and escalation_score > persistence_score:
            trajectory = "escalate"
            trajectory_label = "Likely to ESCALATE"
            trajectory_indicator = "🔴"
        elif resolution_score == max_score and resolution_score > persistence_score:
            trajectory = "resolve"
            trajectory_label = "Likely to self-resolve"
            trajectory_indicator = "🟢"
        else:
            trajectory = "persist"
            trajectory_label = "Likely to PERSIST"
            trajectory_indicator = "🟡"
        
        # Calculate confidence
        score_spread = max_score - min(escalation_score, resolution_score, persistence_score)
        if score_spread >= 4:
            confidence = "High"
        elif score_spread >= 2:
            confidence = "Medium"
        else:
            confidence = "Low"
        
        return {
            "trajectory": trajectory,
            "trajectory_label": trajectory_label,
            "trajectory_indicator": trajectory_indicator,
            "confidence": confidence,
            "confidence_indicator": self._get_confidence_indicator(confidence),
            "factors": {
                "escalation_score": escalation_score,
                "resolution_score": resolution_score,
                "persistence_score": persistence_score,
                "alert_rate_per_hour": round(alert_rate, 1),
                "duration_hours": round(duration_hours, 1)
            },
            "reasoning": self._generate_reasoning(trajectory, pattern, priority, alert_rate, duration_hours)
        }
    
    def _get_confidence_indicator(self, confidence: str) -> str:
        """Get confidence indicator."""
        return {
            "High": "●●●",
            "Medium": "●●○",
            "Low": "●○○"
        }.get(confidence, "○○○")
    
    def _generate_reasoning(
        self, 
        trajectory: str, 
        pattern: str, 
        priority: str,
        alert_rate: float,
        duration_hours: float
    ) -> str:
        """Generate human-readable reasoning for prediction."""
        reasons = []
        
        if trajectory == "escalate":
            if pattern == "escalating":
                reasons.append("alert pattern shows escalating frequency")
            if alert_rate > 50:
                reasons.append(f"high alert rate ({alert_rate:.0f}/hour)")
            if priority == "P1":
                reasons.append("incident is already P1 priority")
            return "Based on " + ", ".join(reasons) + ", this incident is likely to worsen."
        
        elif trajectory == "resolve":
            if pattern == "transient":
                reasons.append("pattern suggests transient behavior")
            if alert_rate < 5:
                reasons.append("low alert frequency")
            if duration_hours < 2:
                reasons.append("short duration")
            return "Based on " + ", ".join(reasons) + ", this may self-resolve."
        
        else:  # persist
            if pattern in ["persistent", "continuous"]:
                reasons.append("pattern shows ongoing persistence")
            if duration_hours > 24:
                reasons.append(f"already persisted for {duration_hours:.0f} hours")
            return "Based on " + ", ".join(reasons) + ", this will likely continue without intervention."


# ============================================================
# PHASE 5 LAYER 3: EARLY WARNING SIGNAL DETECTION
# ============================================================
class EarlyWarningDetector:
    """
    Detects pre-incident signals:
    - Rising WARNING before CRITICAL
    - Repeated standby warnings
    - Escalating frequency bursts
    
    Explicitly calls these out as "Early Warning Indicators"
    """
    
    def __init__(self):
        self.warning_patterns = [
            ("warning_to_critical", "Rising WARNING counts often precede CRITICAL escalation"),
            ("standby_warnings", "Repeated standby warnings may indicate impending replication issues"),
            ("frequency_burst", "Alert frequency bursts often precede major incidents"),
            ("archiver_warnings", "Archiver warnings can lead to database hangs"),
            ("space_warnings", "Storage warnings may escalate to datafile issues"),
        ]
    
    def detect_early_warnings(
        self, 
        alerts: List[Dict],
        incidents: List[Any] = None,
        trend_data: Dict = None
    ) -> List[Dict]:
        """
        Scan for early warning signals in current alert data.
        
        Returns list of detected early warning indicators.
        """
        warnings = []
        
        # Signal 1: Warning to Critical ratio analysis
        critical_count = sum(1 for a in alerts 
                            if str(a.get("severity", "")).upper() == "CRITICAL")
        warning_count = sum(1 for a in alerts 
                           if str(a.get("severity", "")).upper() == "WARNING")
        
        if warning_count > 0 and trend_data:
            warning_trend = trend_data.get("warning_trend", {})
            if warning_trend.get("direction") == "worsening":
                warnings.append({
                    "signal_type": "warning_escalation",
                    "severity": "MEDIUM",
                    "indicator": "⚠️",
                    "message": "Warning alerts are trending upward",
                    "detail": f"Warning count increased by {warning_trend.get('change_pct', 0)}% from historical average",
                    "implication": "Rising warnings often precede critical incidents"
                })
        
        # Signal 2: Standby/Data Guard warnings
        standby_alerts = [a for a in alerts 
                         if "standby" in str(a.get("message", "")).lower() or
                         "data guard" in str(a.get("message", "")).lower() or
                         "dataguard" in str(a.get("message", "")).lower()]
        
        standby_warnings = [a for a in standby_alerts 
                          if str(a.get("severity", "")).upper() == "WARNING"]
        
        if len(standby_warnings) > 5:
            warnings.append({
                "signal_type": "standby_health",
                "severity": "HIGH",
                "indicator": "🔶",
                "message": f"Multiple standby warnings detected ({len(standby_warnings)})",
                "detail": "Standby database health may be degrading",
                "implication": "This pattern historically leads to standby disconnects or apply lag"
            })
        
        # Signal 3: Archiver warnings
        archiver_alerts = [a for a in alerts 
                         if "archiver" in str(a.get("message", "")).lower() or
                         "archive" in str(a.get("message", "")).lower() or
                         "ORA-00255" in str(a.get("message", "")) or
                         "ORA-16038" in str(a.get("message", ""))]
        
        if len(archiver_alerts) > 3:
            warnings.append({
                "signal_type": "archiver_health",
                "severity": "HIGH",
                "indicator": "🔶",
                "message": f"Archiver-related alerts detected ({len(archiver_alerts)})",
                "detail": "Archive log destination may be filling or inaccessible",
                "implication": "Archiver issues can lead to database hangs"
            })
        
        # Signal 4: Frequency burst detection
        # Analyze alert timestamps for sudden bursts
        burst_detected = self._detect_frequency_burst(alerts)
        if burst_detected:
            warnings.append({
                "signal_type": "frequency_burst",
                "severity": "MEDIUM",
                "indicator": "⚡",
                "message": "Alert frequency burst detected",
                "detail": burst_detected.get("detail", "Sudden increase in alert rate"),
                "implication": "Similar alert bursts have previously escalated to P1 incidents"
            })
        
        # Signal 5: ORA-600/7445 detection (internal errors)
        internal_errors = [a for a in alerts 
                         if "ORA-600" in str(a.get("message", "")) or
                         "ORA-7445" in str(a.get("message", ""))]
        
        if len(internal_errors) > 0:
            warnings.append({
                "signal_type": "internal_error",
                "severity": "CRITICAL",
                "indicator": "🔴",
                "message": f"Oracle internal errors detected ({len(internal_errors)})",
                "detail": "ORA-600/ORA-7445 errors indicate Oracle kernel issues",
                "implication": "These require immediate investigation and may indicate instance instability"
            })
        
        return warnings
    
    def _detect_frequency_burst(self, alerts: List[Dict]) -> Optional[Dict]:
        """Detect sudden frequency bursts in alert data."""
        if len(alerts) < 100:
            return None
        
        # Parse timestamps and group by hour
        hourly_counts = Counter()
        
        for alert in alerts:
            ts = alert.get("alert_time") or alert.get("time") or alert.get("timestamp")
            if ts:
                try:
                    if isinstance(ts, datetime):
                        dt = ts
                    else:
                        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                    hour_key = dt.strftime("%Y-%m-%d %H:00")
                    hourly_counts[hour_key] += 1
                except:
                    pass
        
        if len(hourly_counts) < 3:
            return None
        
        # Check for burst (hour with 3x average count)
        avg_count = sum(hourly_counts.values()) / len(hourly_counts)
        max_count = max(hourly_counts.values())
        max_hour = max(hourly_counts, key=hourly_counts.get)
        
        if max_count > avg_count * 3:
            return {
                "detected": True,
                "detail": f"Peak hour ({max_hour}) had {max_count} alerts vs average of {avg_count:.0f}"
            }
        
        return None
    
    def format_early_warnings(self, warnings: List[Dict]) -> str:
        """Format early warnings for display."""
        if not warnings:
            return "No early warning signals detected at this time."
        
        parts = ["### 🚦 Early Warning Signals", ""]
        
        for w in warnings:
            indicator = w.get("indicator", "⚠️")
            severity = w.get("severity", "MEDIUM")
            message = w.get("message", "")
            detail = w.get("detail", "")
            implication = w.get("implication", "")
            
            parts.append(f"{indicator} **{message}** ({severity})")
            if detail:
                parts.append(f"   - {detail}")
            if implication:
                parts.append(f"   - *{implication}*")
            parts.append("")
        
        return "\n".join(parts)


# ============================================================
# PHASE 5 LAYER 4: DBA BEHAVIOR LEARNING
# ============================================================
class DBABehaviorLearner:
    """
    Observes DBA interaction patterns to build operational intelligence:
    - Which alerts DBA asks about repeatedly
    - Which incidents are ignored
    - Which databases get most focus
    
    Builds soft learning signals (NOT personalization).
    """
    
    def __init__(self, learning_path: str = None):
        self.learning_path = learning_path or "data/dba_learning.json"
        self.query_history: List[Dict] = []
        self.database_focus: Counter = Counter()
        self.alert_type_focus: Counter = Counter()
        self.ignored_patterns: List[str] = []
        self._load_learning()
    
    def _load_learning(self):
        """Load learning data from storage."""
        try:
            if os.path.exists(self.learning_path):
                with open(self.learning_path, 'r') as f:
                    data = json.load(f)
                    self.query_history = data.get("query_history", [])
                    self.database_focus = Counter(data.get("database_focus", {}))
                    self.alert_type_focus = Counter(data.get("alert_type_focus", {}))
        except Exception:
            pass
    
    def _save_learning(self):
        """Save learning data to storage."""
        try:
            os.makedirs(os.path.dirname(self.learning_path), exist_ok=True)
            data = {
                "query_history": self.query_history[-500:],  # Keep last 500
                "database_focus": dict(self.database_focus.most_common(50)),
                "alert_type_focus": dict(self.alert_type_focus.most_common(50))
            }
            with open(self.learning_path, 'w') as f:
                json.dump(data, f)
        except Exception:
            pass
    
    def record_query(
        self, 
        question: str,
        database: str = None,
        severity: str = None,
        category: str = None,
        intent: str = None
    ):
        """Record a DBA query for learning."""
        self.query_history.append({
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "database": database,
            "severity": severity,
            "category": category,
            "intent": intent
        })
        
        # Update focus counters
        if database:
            self.database_focus[database.upper()] += 1
        if category:
            self.alert_type_focus[category.upper()] += 1
        
        self._save_learning()
    
    def get_operational_insights(self) -> Dict[str, Any]:
        """
        Get operational insights from DBA behavior patterns.
        
        Returns insights about operationally sensitive areas.
        """
        insights = {
            "has_learning": len(self.query_history) > 10,
            "query_count": len(self.query_history),
            "sensitive_databases": [],
            "high_concern_alerts": [],
            "focus_patterns": []
        }
        
        if len(self.query_history) < 10:
            insights["message"] = "Insufficient interaction history for pattern learning"
            return insights
        
        # Identify sensitive databases (most queried)
        top_databases = self.database_focus.most_common(5)
        for db, count in top_databases:
            if count >= 3:  # At least 3 queries
                insights["sensitive_databases"].append({
                    "database": db,
                    "query_count": count,
                    "significance": "This database is operationally sensitive (frequently queried)"
                })
        
        # Identify high-concern alert types
        top_alerts = self.alert_type_focus.most_common(5)
        for alert_type, count in top_alerts:
            if count >= 3:
                insights["high_concern_alerts"].append({
                    "alert_type": alert_type,
                    "query_count": count,
                    "significance": "This alert type is high DBA concern"
                })
        
        # Analyze recent focus patterns
        recent_queries = self.query_history[-20:]
        recent_dbs = Counter(q.get("database", "").upper() for q in recent_queries if q.get("database"))
        
        if recent_dbs:
            most_recent = recent_dbs.most_common(1)[0]
            if most_recent[1] >= 3:
                insights["focus_patterns"].append(
                    f"Recent focus on {most_recent[0]} ({most_recent[1]} queries in last 20 interactions)"
                )
        
        return insights
    
    def get_context_enhancement(self, database: str = None, category: str = None) -> Optional[str]:
        """Get context enhancement based on learned patterns."""
        enhancements = []
        
        if database:
            db_upper = database.upper()
            if self.database_focus.get(db_upper, 0) >= 5:
                enhancements.append(f"*Note: {db_upper} has been a focus of recent operational attention.*")
        
        if category:
            cat_upper = category.upper()
            if self.alert_type_focus.get(cat_upper, 0) >= 3:
                enhancements.append(f"*This alert type ({cat_upper}) has been of high DBA concern.*")
        
        return " ".join(enhancements) if enhancements else None


# ============================================================
# PHASE 5 LAYER 5: PROACTIVE DBA GUIDANCE
# ============================================================
class ProactiveDBAGuidance:
    """
    Provides proactive guidance based on patterns:
    - Preventive awareness (NOT fixes)
    - Pattern-based warnings
    - Historical context
    
    NO commands, NO remediation steps, ONLY guidance & awareness.
    """
    
    def __init__(self):
        # Known pattern implications
        self.pattern_implications = {
            "standby_gap": "This pattern historically leads to standby disconnects or significant apply lag",
            "archiver_stuck": "Archiver issues typically escalate to database hangs within hours if unresolved",
            "space_warning": "Storage warnings often precede datafile extend failures",
            "memory_pressure": "Memory pressure patterns can lead to instance instability",
            "redo_issues": "Redo log issues may cause log switch waits and performance degradation",
            "network_issues": "TNS errors often indicate broader network or listener problems"
        }
    
    def generate_proactive_guidance(
        self,
        incidents: List[Any],
        early_warnings: List[Dict],
        trend_data: Dict,
        trajectory_predictions: List[Dict]
    ) -> str:
        """
        Generate proactive DBA guidance based on all intelligence layers.
        
        Returns formatted guidance (max 3 bullets).
        """
        guidance_items = []
        
        # Guidance from trajectory predictions
        escalating = [p for p in trajectory_predictions 
                     if p.get("trajectory") == "escalate"]
        if escalating:
            guidance_items.append(
                f"**Monitor closely:** {len(escalating)} incident(s) show escalation trajectory — "
                "consider preemptive investigation before further degradation"
            )
        
        # Guidance from early warnings
        critical_warnings = [w for w in early_warnings 
                            if w.get("severity") == "CRITICAL"]
        if critical_warnings:
            warning = critical_warnings[0]
            guidance_items.append(
                f"**Early warning detected:** {warning.get('message', 'Unknown')} — "
                f"{warning.get('implication', 'requires attention')}"
            )
        
        # Guidance from trends
        if trend_data.get("trend_available"):
            if trend_data.get("overall_trend") == "deteriorating":
                guidance_items.append(
                    "**Environment deteriorating:** Overall trend shows worsening conditions — "
                    "this may warrant escalation to incident management"
                )
            elif trend_data.get("critical_trend", {}).get("direction") == "worsening":
                change_pct = trend_data.get("critical_trend", {}).get("change_pct", 0)
                guidance_items.append(
                    f"**Critical alerts rising:** {change_pct}% above historical average — "
                    "monitor for further escalation"
                )
        
        # Limit to 3 items
        guidance_items = guidance_items[:3]
        
        if not guidance_items:
            return ""
        
        parts = ["### 🧭 Proactive DBA Considerations", ""]
        for i, item in enumerate(guidance_items, 1):
            parts.append(f"{i}. {item}")
        parts.append("")
        parts.append("*These are awareness signals only. Actual action depends on operational assessment.*")
        
        return "\n".join(parts)
    
    def get_pattern_implication(self, pattern_type: str) -> Optional[str]:
        """Get implication for a known pattern."""
        return self.pattern_implications.get(pattern_type)


# ============================================================
# PHASE 5 MASTER: PREDICTIVE INTELLIGENCE ENGINE
# ============================================================
class PredictiveIntelligenceEngine:
    """
    Master orchestrator for Phase 5 Predictive Intelligence.
    
    Combines all 5 layers:
    1. Trend Detection
    2. Trajectory Prediction
    3. Early Warning Detection
    4. DBA Behavior Learning
    5. Proactive Guidance
    
    Transforms system from "what is happening" to "what will happen next".
    """
    
    def __init__(self):
        self.trend_engine = TrendDetectionEngine()
        self.trajectory_predictor = IncidentTrajectoryPredictor()
        self.early_warning_detector = EarlyWarningDetector()
        self.behavior_learner = DBABehaviorLearner()
        self.proactive_guidance = ProactiveDBAGuidance()
    
    def analyze_with_prediction(
        self,
        alerts: List[Dict],
        incidents: List[Any] = None,
        question: str = None,
        intent: Dict = None
    ) -> Dict[str, Any]:
        """
        Perform full predictive intelligence analysis.
        
        Returns comprehensive analysis with predictions.
        """
        # Record DBA query for learning
        if question:
            database = (intent or {}).get("database")
            severity = (intent or {}).get("severity")
            category = (intent or {}).get("category")
            self.behavior_learner.record_query(
                question=question,
                database=database,
                severity=severity,
                category=category,
                intent=(intent or {}).get("intent")
            )
        
        # Layer 1: Trend Analysis
        trend_data = self.trend_engine.analyze_trend(alerts)
        
        # Layer 2: Trajectory Predictions (for incidents)
        trajectory_predictions = []
        if incidents:
            for incident in incidents[:5]:  # Top 5 incidents only
                if hasattr(incident, 'signature'):
                    pred = self.trajectory_predictor.predict_trajectory(
                        incident_signature=incident.signature,
                        current_count=incident.alert_count,
                        first_seen=incident.first_seen,
                        last_seen=incident.last_seen,
                        priority=incident.priority,
                        pattern=incident.pattern
                    )
                    pred["incident_signature"] = incident.signature
                    pred["incident_database"] = incident.database
                    trajectory_predictions.append(pred)
        
        # Layer 3: Early Warning Detection
        early_warnings = self.early_warning_detector.detect_early_warnings(
            alerts=alerts,
            incidents=incidents,
            trend_data=trend_data
        )
        
        # Layer 4: Get behavioral insights
        behavioral_insights = self.behavior_learner.get_operational_insights()
        
        # Layer 5: Generate proactive guidance
        proactive_guidance = self.proactive_guidance.generate_proactive_guidance(
            incidents=incidents or [],
            early_warnings=early_warnings,
            trend_data=trend_data,
            trajectory_predictions=trajectory_predictions
        )
        
        return {
            "trend_analysis": trend_data,
            "trajectory_predictions": trajectory_predictions,
            "early_warnings": early_warnings,
            "behavioral_insights": behavioral_insights,
            "proactive_guidance": proactive_guidance
        }
    
    def format_predictive_response(
        self,
        base_response: str,
        prediction_data: Dict[str, Any]
    ) -> str:
        """
        Enhance a base response with predictive intelligence.
        
        Returns complete response with all Phase 5 intelligence layers.
        """
        parts = [base_response, ""]
        
        # Add Trend & Risk Outlook
        trend_data = prediction_data.get("trend_analysis", {})
        parts.append(self._format_trend_outlook(trend_data))
        
        # Add Incident Risk Projection
        trajectories = prediction_data.get("trajectory_predictions", [])
        if trajectories:
            parts.append(self._format_risk_projection(trajectories))
        
        # Add Early Warning Signals
        early_warnings = prediction_data.get("early_warnings", [])
        parts.append(self.early_warning_detector.format_early_warnings(early_warnings))
        
        # Add DBA Meaning
        parts.append(self._format_dba_meaning(trend_data, trajectories, early_warnings))
        
        # Add Proactive Guidance
        proactive = prediction_data.get("proactive_guidance", "")
        if proactive:
            parts.append(proactive)
        
        return "\n".join(parts)
    
    def _format_trend_outlook(self, trend_data: Dict) -> str:
        """Format trend outlook section."""
        parts = ["### 📈 Trend & Risk Outlook", ""]
        
        if not trend_data.get("trend_available"):
            parts.append(f"*{trend_data.get('message', 'Trend analysis unavailable')}*")
            return "\n".join(parts)
        
        overall = trend_data.get("overall_indicator", "Unknown")
        confidence = trend_data.get("confidence", "Unknown")
        
        parts.append(f"| Metric | Current | Historical Avg | Trend |")
        parts.append(f"|--------|---------|----------------|-------|")
        
        # Critical trend
        ct = trend_data.get("critical_trend", {})
        if ct:
            parts.append(f"| **Critical Alerts** | {ct.get('current', 0):,} | "
                        f"{int(ct.get('historical_avg', 0)):,} | "
                        f"{ct.get('direction', 'unknown').title()} ({ct.get('change_pct', 0):+.1f}%) |")
        
        # Warning trend
        wt = trend_data.get("warning_trend", {})
        if wt:
            parts.append(f"| **Warning Alerts** | {wt.get('current', 0):,} | "
                        f"{int(wt.get('historical_avg', 0)):,} | "
                        f"{wt.get('direction', 'unknown').title()} ({wt.get('change_pct', 0):+.1f}%) |")
        
        parts.append("")
        parts.append(f"**Overall Environment Trend:** {overall}")
        parts.append(f"**Trend Confidence:** {confidence} (based on {trend_data.get('history_depth', 0)} historical snapshots)")
        parts.append("")
        
        return "\n".join(parts)
    
    def _format_risk_projection(self, trajectories: List[Dict]) -> str:
        """Format incident risk projection section."""
        parts = ["### 🔮 Incident Risk Projection", ""]
        
        for traj in trajectories[:3]:  # Top 3 only
            signature = traj.get("incident_signature", "Unknown")
            database = traj.get("incident_database", "Unknown")
            indicator = traj.get("trajectory_indicator", "⚪")
            label = traj.get("trajectory_label", "Unknown")
            confidence = traj.get("confidence", "Unknown")
            conf_ind = traj.get("confidence_indicator", "○○○")
            reasoning = traj.get("reasoning", "")
            
            parts.append(f"**{signature}** ({database})")
            parts.append(f"- Current State: Active")
            parts.append(f"- Trajectory: {indicator} {label}")
            parts.append(f"- Confidence: {confidence} {conf_ind}")
            if reasoning:
                parts.append(f"- *{reasoning}*")
            parts.append("")
        
        return "\n".join(parts)
    
    def _format_dba_meaning(
        self, 
        trend_data: Dict, 
        trajectories: List[Dict],
        early_warnings: List[Dict]
    ) -> str:
        """Format 'What This Means for the DBA' section."""
        parts = ["### 🧠 What This Means for the DBA", ""]
        
        # Assess urgency
        escalating_count = len([t for t in trajectories if t.get("trajectory") == "escalate"])
        critical_warnings = len([w for w in early_warnings if w.get("severity") == "CRITICAL"])
        trend_bad = trend_data.get("overall_trend") in ["deteriorating", "worsening"]
        
        if escalating_count > 0 or critical_warnings > 0:
            parts.append("⚠️ **Should DBA be alert?** YES — active escalation signals detected.")
        elif trend_bad:
            parts.append("⚡ **Should DBA be alert?** MONITOR CLOSELY — conditions are worsening.")
        else:
            parts.append("✅ **Should DBA be alert?** Routine monitoring is sufficient for now.")
        
        parts.append("")
        
        # Situation assessment
        if trend_data.get("overall_trend") == "deteriorating":
            parts.append("📉 **Situation:** WORSENING — alert volumes are trending upward significantly.")
        elif trend_data.get("overall_trend") == "improving":
            parts.append("📈 **Situation:** IMPROVING — alert volumes are trending downward.")
        else:
            parts.append("📊 **Situation:** STABLE — no significant trend detected.")
        
        parts.append("")
        
        # Escalation likelihood
        if escalating_count > 1:
            parts.append(f"🚨 **Escalation Likely:** {escalating_count} incidents show escalation trajectory. "
                        "Consider proactive incident bridge preparation.")
        elif escalating_count == 1:
            parts.append("⚠️ **Escalation Possible:** One incident shows escalation trajectory. Monitor closely.")
        else:
            parts.append("✅ **Escalation Unlikely:** No incidents currently show escalation trajectory.")
        
        parts.append("")
        
        return "\n".join(parts)
    
    def capture_state_snapshot(self, alerts: List[Dict]):
        """Capture current state for trend analysis."""
        return self.trend_engine.capture_snapshot(alerts)


# Singleton instance
PREDICTIVE_INTELLIGENCE = PredictiveIntelligenceEngine()
