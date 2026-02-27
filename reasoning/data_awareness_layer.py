"""
DATA AWARENESS LAYER
====================

CORE PRINCIPLE: "Do I have this data?" check BEFORE answering.

This layer ensures:
1. System knows what data fields exist vs what's missing
2. Answers are scoped to available data
3. "I don't know" responses when data is unavailable
4. No over-analysis or hallucination

FIXES:
- "Did alerts increase after last patch?" → No patch data available
- "What is the current apply lag in minutes?" → No lag metrics in CSV
- "How alerts from yesterday only" → Date filtering capability
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Set
from enum import Enum
from datetime import datetime, timedelta
import re


class DataField(Enum):
    """Available data fields in the OEM alert dataset."""
    # AVAILABLE FIELDS (from CSV)
    TARGET_NAME = "target_name"
    SEVERITY = "severity"
    MESSAGE = "message"
    ISSUE_TYPE = "issue_type"
    TIMESTAMP = "timestamp"
    ALERT_STATE = "alert_state"
    
    # UNAVAILABLE FIELDS (not in CSV)
    PATCH_TIMESTAMP = "patch_timestamp"
    APPLY_LAG_MINUTES = "apply_lag_minutes"
    TRANSPORT_LAG_MINUTES = "transport_lag_minutes"
    BASELINE_THRESHOLD = "baseline_threshold"
    HISTORICAL_AVERAGE = "historical_average"


@dataclass
class DataAvailabilityResult:
    """Result of data availability check."""
    has_data: bool
    available_fields: List[str]
    missing_fields: List[str]
    confidence_impact: str  # HIGH, MEDIUM, LOW
    safe_answer_prefix: Optional[str] = None


class DataAwarenessEngine:
    """
    Checks what data is available before answering.
    
    CRITICAL: Prevents over-analysis and hallucination.
    """
    
    # Fields that EXIST in our CSV data
    AVAILABLE_FIELDS = {
        "target_name", "target", "severity", "alert_state",
        "message", "msg_text", "issue_type", "timestamp",
        "creation_date", "last_updated"
    }
    
    # Fields that DO NOT EXIST - prevent hallucination
    UNAVAILABLE_FIELDS = {
        "patch_timestamp": "Patch timing data not available in OEM alerts",
        "apply_lag_minutes": "Exact apply lag metric not available (only alert-based inference)",
        "transport_lag_minutes": "Exact transport lag metric not available",
        "baseline_threshold": "Historical baseline thresholds not configured",
        "cpu_usage": "CPU metrics not in alert data",
        "memory_usage": "Memory metrics not in alert data",
        "disk_space": "Disk space metrics not in alert data",
        "session_count": "Session count not in alert data",
    }
    
    # Keywords that request unavailable data
    UNAVAILABLE_KEYWORDS = {
        "after patch": "patch_timestamp",
        "after last patch": "patch_timestamp",
        "before patch": "patch_timestamp",
        "patch timing": "patch_timestamp",
        "apply lag in minutes": "apply_lag_minutes",
        "current lag": "apply_lag_minutes",
        "lag in minutes": "apply_lag_minutes",
        "transport lag": "transport_lag_minutes",
        "cpu usage": "cpu_usage",
        "memory usage": "memory_usage",
        "disk space": "disk_space",
        "active sessions": "session_count",
    }
    
    def check_data_availability(self, question: str, alerts: List[Dict]) -> DataAvailabilityResult:
        """
        Check if we have the data needed to answer this question.
        
        Returns:
            DataAvailabilityResult with availability status
        """
        q_lower = question.lower()
        missing_fields = []
        
        # Check for keywords requesting unavailable data
        for keyword, field in self.UNAVAILABLE_KEYWORDS.items():
            if keyword in q_lower:
                if field not in missing_fields:
                    missing_fields.append(field)
        
        if missing_fields:
            explanations = [self.UNAVAILABLE_FIELDS.get(f, f"'{f}' not available") for f in missing_fields]
            return DataAvailabilityResult(
                has_data=False,
                available_fields=list(self.AVAILABLE_FIELDS),
                missing_fields=missing_fields,
                confidence_impact="LOW",
                safe_answer_prefix=f"⚠️ **Limited Data:** {'; '.join(explanations)}."
            )
        
        # Check for temporal queries
        if self._is_temporal_query(q_lower):
            has_timestamps = self._check_timestamp_availability(alerts)
            if not has_timestamps:
                return DataAvailabilityResult(
                    has_data=False,
                    available_fields=list(self.AVAILABLE_FIELDS),
                    missing_fields=["parsed_timestamps"],
                    confidence_impact="MEDIUM",
                    safe_answer_prefix="⚠️ **Note:** Alert timestamps may not support precise time filtering."
                )
        
        return DataAvailabilityResult(
            has_data=True,
            available_fields=list(self.AVAILABLE_FIELDS),
            missing_fields=[],
            confidence_impact="HIGH",
            safe_answer_prefix=None
        )
    
    def _is_temporal_query(self, q_lower: str) -> bool:
        """Check if query asks about time-based filtering."""
        temporal_keywords = [
            "yesterday", "today", "last hour", "last week",
            "this week", "this month", "before", "after",
            "increased", "decreased", "trend", "over time"
        ]
        return any(kw in q_lower for kw in temporal_keywords)
    
    def _check_timestamp_availability(self, alerts: List[Dict]) -> bool:
        """Check if alerts have parseable timestamps."""
        if not alerts:
            return False
        
        sample = alerts[0]
        timestamp_fields = ["timestamp", "creation_date", "last_updated"]
        
        for field in timestamp_fields:
            if field in sample and sample[field]:
                return True
        return False
    
    def get_safe_response_for_missing_data(self, question: str, missing_field: str) -> str:
        """Generate a safe response when data is unavailable."""
        responses = {
            "patch_timestamp": (
                "Cannot determine — patch timing data not available in OEM alerts. "
                "To analyze pre/post-patch behavior, patch dates would need to be provided separately.\n\n"
                "**What I can tell you:** Alert patterns and counts from available data."
            ),
            "apply_lag_minutes": (
                "Exact apply lag in minutes is not available — OEM alerts show lag-related issues "
                "but not precise lag metrics.\n\n"
                "**What I can infer:** "
                "Data Guard alerts exist, but for exact lag values, check `V$DATAGUARD_STATS` directly."
            ),
            "transport_lag_minutes": (
                "Transport lag metrics not available in alert data.\n\n"
                "**Recommendation:** Query `V$DATAGUARD_STATS` for exact transport lag."
            ),
            "baseline_threshold": (
                "Historical baseline thresholds not configured.\n\n"
                "**What I can tell you:** Current alert volume vs. general patterns observed."
            ),
        }
        return responses.get(missing_field, f"Data for '{missing_field}' is not available.")


class TemporalIntelligence:
    """
    Handle time-based queries: yesterday, today, trends, etc.
    
    FIXES: "How alerts from yesterday only"
    """
    
    def filter_by_time(self, alerts: List[Dict], time_filter: str) -> tuple:
        """
        Filter alerts by time period.
        
        Returns:
            (filtered_alerts, filter_description, success)
        """
        if not alerts:
            return [], "No alerts available", False
        
        # Try to parse timestamps
        parsed_alerts = self._parse_timestamps(alerts)
        if not parsed_alerts:
            return alerts, "Timestamp parsing not available", False
        
        now = datetime.now()
        time_filter_lower = time_filter.lower()
        
        if "yesterday" in time_filter_lower:
            yesterday = now - timedelta(days=1)
            start = yesterday.replace(hour=0, minute=0, second=0)
            end = yesterday.replace(hour=23, minute=59, second=59)
            filtered = [a for a in parsed_alerts if start <= a.get("_parsed_time", now) <= end]
            return filtered, f"Alerts from yesterday ({yesterday.strftime('%Y-%m-%d')})", True
        
        elif "today" in time_filter_lower:
            start = now.replace(hour=0, minute=0, second=0)
            filtered = [a for a in parsed_alerts if a.get("_parsed_time", now) >= start]
            return filtered, f"Alerts from today ({now.strftime('%Y-%m-%d')})", True
        
        elif "last hour" in time_filter_lower:
            cutoff = now - timedelta(hours=1)
            filtered = [a for a in parsed_alerts if a.get("_parsed_time", now) >= cutoff]
            return filtered, "Alerts from the last hour", True
        
        elif "last 24 hours" in time_filter_lower:
            cutoff = now - timedelta(hours=24)
            filtered = [a for a in parsed_alerts if a.get("_parsed_time", now) >= cutoff]
            return filtered, "Alerts from the last 24 hours", True
        
        elif "this week" in time_filter_lower:
            start = now - timedelta(days=now.weekday())
            start = start.replace(hour=0, minute=0, second=0)
            filtered = [a for a in parsed_alerts if a.get("_parsed_time", now) >= start]
            return filtered, "Alerts from this week", True
        
        return alerts, "No time filter applied", False
    
    def _parse_timestamps(self, alerts: List[Dict]) -> List[Dict]:
        """Try to parse timestamps from alerts."""
        parsed = []
        for alert in alerts:
            ts = alert.get("timestamp") or alert.get("creation_date") or alert.get("last_updated")
            if ts:
                parsed_time = self._try_parse_timestamp(ts)
                if parsed_time:
                    alert_copy = alert.copy()
                    alert_copy["_parsed_time"] = parsed_time
                    parsed.append(alert_copy)
                else:
                    parsed.append(alert)
            else:
                parsed.append(alert)
        return parsed
    
    def _try_parse_timestamp(self, ts: str) -> Optional[datetime]:
        """Try various timestamp formats."""
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%d-%b-%Y %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%m/%d/%Y %H:%M:%S",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(str(ts), fmt)
            except:
                continue
        return None


class BaselineComparison:
    """
    Compare current alert volume against baselines.
    
    FIXES: "Is this alert volume normal for MIDEVSTB?"
    """
    
    # Default baselines (can be overridden by config)
    DEFAULT_BASELINES = {
        "critical_per_day_normal": 50,
        "critical_per_day_warning": 200,
        "critical_per_day_severe": 1000,
        "warning_per_day_normal": 100,
        "warning_per_day_warning": 500,
        "total_per_db_normal": 200,
        "total_per_db_warning": 1000,
        "total_per_db_severe": 10000,
    }
    
    def assess_volume_normality(self, db_name: str, alert_count: int, 
                                 severity: str = None, period: str = "snapshot") -> Dict:
        """
        Assess if alert volume is normal for a database.
        
        Returns:
            Dict with normality assessment
        """
        # Determine threshold based on severity
        if severity and severity.upper() == "CRITICAL":
            normal_threshold = self.DEFAULT_BASELINES["critical_per_day_normal"]
            warning_threshold = self.DEFAULT_BASELINES["critical_per_day_warning"]
            severe_threshold = self.DEFAULT_BASELINES["critical_per_day_severe"]
        elif severity and severity.upper() == "WARNING":
            normal_threshold = self.DEFAULT_BASELINES["warning_per_day_normal"]
            warning_threshold = self.DEFAULT_BASELINES["warning_per_day_warning"]
            severe_threshold = warning_threshold * 2
        else:
            normal_threshold = self.DEFAULT_BASELINES["total_per_db_normal"]
            warning_threshold = self.DEFAULT_BASELINES["total_per_db_warning"]
            severe_threshold = self.DEFAULT_BASELINES["total_per_db_severe"]
        
        if alert_count <= normal_threshold:
            status = "NORMAL"
            explanation = f"Alert count ({alert_count:,}) is within normal range (< {normal_threshold:,})."
        elif alert_count <= warning_threshold:
            status = "ELEVATED"
            explanation = f"Alert count ({alert_count:,}) is elevated. Normal is < {normal_threshold:,}."
        elif alert_count <= severe_threshold:
            status = "HIGH"
            explanation = f"Alert count ({alert_count:,}) is significantly high. Normal is < {normal_threshold:,}."
        else:
            status = "CRITICAL"
            explanation = f"Alert count ({alert_count:,}) is **{alert_count // normal_threshold}x higher** than normal baseline ({normal_threshold:,})."
        
        return {
            "status": status,
            "is_normal": status == "NORMAL",
            "alert_count": alert_count,
            "normal_threshold": normal_threshold,
            "warning_threshold": warning_threshold,
            "explanation": explanation,
            "severity_context": severity,
            "recommendation": self._get_recommendation(status, alert_count, db_name)
        }
    
    def _get_recommendation(self, status: str, count: int, db_name: str) -> str:
        """Get recommendation based on status."""
        if status == "NORMAL":
            return "No action required."
        elif status == "ELEVATED":
            return f"Monitor {db_name} for further increases."
        elif status == "HIGH":
            return f"Investigate root cause for {db_name}. Review alert patterns."
        else:
            return f"**Immediate attention required** for {db_name}. This is significantly above normal."


class RelationshipGraph:
    """
    Understand Primary ↔ Standby database relationships.
    
    FIXES: "Are these related to MIDEVSTB?" - explain MIDEVSTBN is standby of MIDEVSTB
    """
    
    # Known relationships (can be extended from metadata)
    KNOWN_RELATIONSHIPS = {
        # Primary → Standby mappings
        "MIDEVSTB": ["MIDEVSTBN"],
        "MIDEVSTBN": [],  # This IS a standby
    }
    
    # Patterns to detect standby databases
    STANDBY_PATTERNS = [
        r"(.+)N$",      # MIDEVSTB → MIDEVSTBN (N suffix)
        r"(.+)_STB$",   # PRIMARY → PRIMARY_STB
        r"(.+)_DR$",    # PRIMARY → PRIMARY_DR
        r"(.+)_STBY$",  # PRIMARY → PRIMARY_STBY
    ]
    
    def get_relationship(self, db1: str, db2: str = None) -> Dict:
        """
        Get relationship information for database(s).
        
        Returns:
            Dict with relationship details
        """
        db1_upper = db1.upper()
        
        result = {
            "database": db1_upper,
            "is_standby": self._is_standby(db1_upper),
            "is_primary": not self._is_standby(db1_upper),
            "related_databases": [],
            "relationship_explanation": None
        }
        
        # Check known relationships
        if db1_upper in self.KNOWN_RELATIONSHIPS:
            standbys = self.KNOWN_RELATIONSHIPS[db1_upper]
            if standbys:
                result["related_databases"] = standbys
                result["relationship_explanation"] = (
                    f"**{db1_upper}** is the PRIMARY database. "
                    f"Its standby database(s): {', '.join(standbys)}."
                )
        
        # Check if db1 is a standby of something
        primary = self._get_primary_for_standby(db1_upper)
        if primary:
            result["is_standby"] = True
            result["is_primary"] = False
            result["primary_database"] = primary
            result["relationship_explanation"] = (
                f"**{db1_upper}** is the STANDBY database of **{primary}**. "
                f"Issues on {db1_upper} may indicate problems propagating from primary."
            )
        
        # If db2 provided, explain their relationship
        if db2:
            db2_upper = db2.upper()
            result["related_to"] = db2_upper
            
            # Check if they're related
            if self._are_related(db1_upper, db2_upper):
                if self._is_standby(db1_upper):
                    result["relationship_explanation"] = (
                        f"**Yes, related.** {db1_upper} is the standby of {db2_upper}. "
                        f"Primary instability on {db2_upper} can propagate to standby alerts."
                    )
                else:
                    result["relationship_explanation"] = (
                        f"**Yes, related.** {db2_upper} is the standby of {db1_upper}. "
                        f"Standby issues on {db2_upper} may indicate primary problems on {db1_upper}."
                    )
        
        return result
    
    def _is_standby(self, db_name: str) -> bool:
        """Check if database name indicates it's a standby."""
        for pattern in self.STANDBY_PATTERNS:
            if re.match(pattern, db_name):
                return True
        # Also check if it's in known standbys
        for primary, standbys in self.KNOWN_RELATIONSHIPS.items():
            if db_name in standbys:
                return True
        return False
    
    def _get_primary_for_standby(self, standby_name: str) -> Optional[str]:
        """Get primary database name for a standby."""
        # Check known relationships first
        for primary, standbys in self.KNOWN_RELATIONSHIPS.items():
            if standby_name in standbys:
                return primary
        
        # Try pattern matching
        for pattern in self.STANDBY_PATTERNS:
            match = re.match(pattern, standby_name)
            if match:
                potential_primary = match.group(1)
                # Verify this primary exists in our known databases
                if potential_primary in self.KNOWN_RELATIONSHIPS:
                    return potential_primary
                # Return anyway as a guess
                return potential_primary
        return None
    
    def _are_related(self, db1: str, db2: str) -> bool:
        """Check if two databases are related (primary-standby pair)."""
        # Direct relationship
        if db1 in self.KNOWN_RELATIONSHIPS.get(db2, []):
            return True
        if db2 in self.KNOWN_RELATIONSHIPS.get(db1, []):
            return True
        
        # Pattern-based detection
        if db1 + "N" == db2 or db2 + "N" == db1:
            return True
        if db1 + "_STB" == db2 or db2 + "_STB" == db1:
            return True
        if db1 + "_DR" == db2 or db2 + "_DR" == db1:
            return True
        
        return False
    
    def explain_standby_alert_propagation(self, primary: str, standby: str, 
                                           primary_count: int, standby_count: int) -> str:
        """Explain how alerts propagate from primary to standby."""
        if primary_count > standby_count:
            return (
                f"**{primary}** (primary) has {primary_count:,} alerts, "
                f"**{standby}** (standby) has {standby_count:,}. "
                f"Primary issues are likely causing standby-side Data Guard alerts."
            )
        else:
            return (
                f"**{standby}** (standby) has {standby_count:,} alerts, "
                f"more than primary **{primary}** ({primary_count:,}). "
                f"This suggests standby-specific issues (apply lag, network, etc.)."
            )


class StateBasedExplainer:
    """
    Explain WHY alerts are repeating based on database state.
    
    FIXES: "Why are MIDEVSTB warnings repeated?"
    """
    
    # Known states that cause repeated alerts
    STATE_EXPLANATIONS = {
        "MOUNTED": (
            "Database is in **MOUNTED** state (not OPEN). "
            "OEM continuously raises alerts until the database is opened. "
            "This is expected behavior — not a bug."
        ),
        "UNKNOWN": (
            "Database status is **UNKNOWN** — OEM cannot connect. "
            "Repeated alerts indicate persistent connectivity issue. "
            "Check listener, network, or if database is down."
        ),
        "RESTRICTED": (
            "Database is in **RESTRICTED** mode. "
            "OEM raises warnings until normal mode is restored."
        ),
        "RECOVERY": (
            "Database is in **RECOVERY** mode. "
            "OEM alerts will repeat until recovery completes."
        ),
    }
    
    def explain_repeated_alerts(self, alerts: List[Dict], db_name: str = None) -> Dict:
        """
        Explain why alerts are repeating.
        
        Returns:
            Dict with explanation and recommendation
        """
        if not alerts:
            return {"explanation": "No alerts to analyze", "state": None}
        
        # Look for state information in alert messages
        states_found = set()
        for alert in alerts[:100]:  # Sample first 100
            msg = (alert.get("message") or alert.get("msg_text") or "").upper()
            for state, explanation in self.STATE_EXPLANATIONS.items():
                if state in msg:
                    states_found.add(state)
        
        if not states_found:
            # Try to infer from alert patterns
            return self._infer_repetition_cause(alerts, db_name)
        
        # Build explanation
        explanations = [self.STATE_EXPLANATIONS[s] for s in states_found]
        primary_state = list(states_found)[0]
        
        return {
            "states_detected": list(states_found),
            "primary_state": primary_state,
            "explanation": explanations[0],
            "additional_states": explanations[1:] if len(explanations) > 1 else [],
            "recommendation": self._get_state_recommendation(primary_state, db_name)
        }
    
    def _infer_repetition_cause(self, alerts: List[Dict], db_name: str) -> Dict:
        """Infer cause when state not explicitly mentioned."""
        # Check for common patterns
        messages = [a.get("message") or a.get("msg_text") or "" for a in alerts[:50]]
        
        # Count unique messages
        unique_msgs = set(messages)
        
        if len(unique_msgs) <= 3:
            # Very few unique messages = same issue repeating
            sample_msg = list(unique_msgs)[0] if unique_msgs else ""
            return {
                "explanation": (
                    f"Alerts are repeating because the **underlying condition persists**. "
                    f"OEM re-raises the same alert until the issue is resolved. "
                    f"Primary alert type: {sample_msg[:100]}..."
                ),
                "unique_alert_types": len(unique_msgs),
                "recommendation": (
                    f"Resolve the root cause for {db_name or 'this database'}. "
                    f"Alerts will stop once the condition clears."
                )
            }
        else:
            return {
                "explanation": (
                    f"Multiple distinct alert types ({len(unique_msgs)}) are being raised. "
                    f"This indicates several issues, not just one repeating."
                ),
                "unique_alert_types": len(unique_msgs),
                "recommendation": "Review top alert types and address each root cause."
            }
    
    def _get_state_recommendation(self, state: str, db_name: str) -> str:
        """Get recommendation for a specific state."""
        db = db_name or "the database"
        recommendations = {
            "MOUNTED": f"If {db} should be open, run `ALTER DATABASE OPEN`. If intentionally mounted, suppress alerts.",
            "UNKNOWN": f"Check: 1) Is {db} running? 2) Listener status 3) Network connectivity 4) OEM agent health",
            "RESTRICTED": f"If {db} should be in normal mode, run `ALTER SYSTEM DISABLE RESTRICTED SESSION`",
            "RECOVERY": f"Wait for recovery to complete or check recovery progress with `V$RECOVERY_PROGRESS`",
        }
        return recommendations.get(state, f"Investigate and resolve the condition on {db}.")


# Singleton instances
DATA_AWARENESS = DataAwarenessEngine()
TEMPORAL_INTELLIGENCE = TemporalIntelligence()
BASELINE_COMPARISON = BaselineComparison()
RELATIONSHIP_GRAPH = RelationshipGraph()
STATE_EXPLAINER = StateBasedExplainer()
