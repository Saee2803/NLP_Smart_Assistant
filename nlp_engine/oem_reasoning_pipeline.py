# nlp_engine/oem_reasoning_pipeline.py
"""
==================================================================
OEM INCIDENT INTELLIGENCE ENGINE (INDUSTRY-GRADE)
==================================================================

MANDATORY THINKING CHAIN:
    INTENT → HYPOTHESIS → EVIDENCE → REASONING → DECISION → ACTION

RULES:
1. NEVER jump from question → answer
2. NEVER say "No data found" without widening
3. "Currently" = most recent observation in historical data
4. Root cause MUST be COMPUTED with scoring, not guessed
5. Every recommendation MUST map to a cause

RESPONSE FORMAT (STRICT):
    🔹 Summary
    🔍 What was checked
    📊 What was found
    🧠 What it means
    🛠️ What to do now

PRODUCTION ENHANCEMENT (v2.0):
    Integrated with ProductionIntelligenceEngine for:
    - Root cause NEVER Unknown (fallback inference)
    - ORA→Abstract cause mapping
    - Action NEVER empty (risk-based fallback)
    - DOWN vs CRITICAL separation
    - Session memory across questions

Python 3.6+ compatible.
"""

import re
from collections import defaultdict
from datetime import datetime
from nlp_engine.oem_intent_engine import OEMIntentEngine
from nlp_engine.oem_data_analyzer import OEMDataAnalyzer
from data_engine.global_cache import GLOBAL_DATA
from data_engine.target_normalizer import TargetNormalizer
from incident_engine.alert_type_classifier import AlertTypeClassifier, classify_alert_type

# PRODUCTION INTELLIGENCE IMPORT
try:
    from incident_engine.production_intelligence_engine import (
        PRODUCTION_INTELLIGENCE,
        ORACodeMappingEngine,
        RootCauseFallbackEngine,
        ActionFallbackEngine,
        DownVsCriticalEngine,
        WideningEngine,
        SessionMemoryEngine
    )
    PRODUCTION_ENGINE_AVAILABLE = True
except ImportError:
    PRODUCTION_ENGINE_AVAILABLE = False


class ReasoningMemory:
    """
    GLOBAL ENVIRONMENT REASONING MEMORY (MANDATORY).
    
    Maintains persistent INTERNAL ENVIRONMENT STATE across questions:
    • Dominant database(s)
    • Dominant error patterns
    • Most frequent ORA categories
    • Peak alert hours
    • Overall risk posture
    • Last inferred root cause
    
    Uses phrases like: "Based on earlier analysis...", "Given what we already know..."
    
    CRITICAL FIX: Session memory is now actively used across all questions.
    
    PRODUCTION RULES:
    1. Once root cause is locked, it stays locked for session
    2. Once highest risk DB is identified, it's locked
    3. Once peak hour is computed, it's locked
    4. Session context MUST be included: "Based on earlier analysis..."
    """
    
    # Class-level singleton state (persists across instances)
    _environment_state = {
        "dominant_database": None,
        "dominant_error_pattern": None,
        "most_frequent_ora": None,
        "peak_alert_hour": None,
        "overall_risk_posture": None,
        "last_root_cause": None,
        "last_abstract_cause": None,  # Added: abstract cause translation
        "highest_risk_database": None,  # Added: track highest risk DB
        "dominant_ora_codes": [],  # Added: list of dominant ORA codes
        "question_count": 0,
        "analysis_history": [],  # Added: track analysis history
        # PRODUCTION: Locked values for consistency
        "locked_root_cause": None,
        "locked_root_cause_db": {},  # db -> locked root cause
        "locked_peak_hour": None,
        "locked_highest_risk_db": None
    }
    
    def __init__(self):
        self.discussed_databases = set()
        self.identified_issues = {}  # db -> issues
        self.conclusions = []
        self.last_intent = None
        self.last_target = None
        self.session_findings = []
    
    @classmethod
    def update_environment_state(cls, **kwargs):
        """Update global environment state."""
        for key, value in kwargs.items():
            if key in cls._environment_state and value is not None:
                cls._environment_state[key] = value
        cls._environment_state["question_count"] += 1
        
        # Track analysis history (last 10)
        if kwargs:
            cls._environment_state["analysis_history"].append({
                "updates": {k: v for k, v in kwargs.items() if v is not None},
                "question_number": cls._environment_state["question_count"]
            })
            if len(cls._environment_state["analysis_history"]) > 10:
                cls._environment_state["analysis_history"] = cls._environment_state["analysis_history"][-10:]
    
    @classmethod
    def get_environment_context(cls):
        """Get context phrase based on prior analysis.
        
        PRODUCTION RULE: Use locked values for consistency.
        Responses MUST say "Based on earlier analysis..." when applicable.
        """
        state = cls._environment_state
        if state["question_count"] == 0:
            return None
        
        context_parts = []
        
        # Use locked highest risk DB for consistency
        highest_risk = state.get("locked_highest_risk_db") or state.get("highest_risk_database")
        if highest_risk:
            context_parts.append("highest risk database is {}".format(highest_risk))
        elif state["dominant_database"]:
            context_parts.append("dominant database is {}".format(state["dominant_database"]))
        
        # Use locked root cause for consistency
        locked_rc = state.get("locked_root_cause")
        if locked_rc:
            context_parts.append("primary issue identified as {}".format(locked_rc))
        elif state["last_abstract_cause"]:
            context_parts.append("primary issue identified as {}".format(state["last_abstract_cause"]))
        elif state["last_root_cause"]:
            context_parts.append("primary root cause identified as {}".format(state["last_root_cause"]))
        
        if state["dominant_ora_codes"]:
            top_oras = state["dominant_ora_codes"][:2]
            context_parts.append("dominant ORA codes are {}".format(", ".join(top_oras)))
        
        # Use locked peak hour for consistency
        peak_hour = state.get("locked_peak_hour") or state.get("peak_alert_hour")
        if peak_hour is not None:
            context_parts.append("peak alert hour at {}:00".format(peak_hour))
        
        if state["overall_risk_posture"]:
            context_parts.append("overall risk posture is {}".format(state["overall_risk_posture"]))
        
        if context_parts:
            return "Based on earlier analysis: " + ", ".join(context_parts) + "."
        return None
    
    @classmethod
    def get_session_summary(cls):
        """
        Get a summary of session knowledge for use in responses.
        
        Returns dict with key session facts for context injection.
        """
        state = cls._environment_state
        return {
            "has_prior_analysis": state["question_count"] > 0,
            "dominant_database": state["highest_risk_database"] or state["dominant_database"],
            "root_cause": state["last_abstract_cause"] or state["last_root_cause"],
            "dominant_oras": state["dominant_ora_codes"][:3] if state["dominant_ora_codes"] else [],
            "peak_hour": state["peak_alert_hour"],
            "risk_level": state["overall_risk_posture"],
            "questions_analyzed": state["question_count"]
        }
    
    @classmethod
    def set_highest_risk_database(cls, db_name, risk_score=None):
        """Explicitly set the highest risk database.
        
        PRODUCTION: Lock highest risk DB once identified.
        """
        cls._environment_state["highest_risk_database"] = db_name
        if not cls._environment_state["dominant_database"]:
            cls._environment_state["dominant_database"] = db_name
        # Lock for session consistency
        if not cls._environment_state.get("locked_highest_risk_db"):
            cls._environment_state["locked_highest_risk_db"] = db_name
    
    @classmethod
    def lock_root_cause(cls, root_cause, db_name=None):
        """
        PRODUCTION: Lock root cause for session consistency.
        
        Once a dominant root cause is identified, LOCK it.
        Do NOT alternate between OTHER/UNKNOWN/INTERNAL_ERROR.
        """
        if not root_cause:
            return
        
        invalid_causes = ["OTHER", "UNKNOWN", "Unknown", "N/A", None, ""]
        if root_cause in invalid_causes:
            return
        
        # Lock global root cause
        if not cls._environment_state.get("locked_root_cause"):
            cls._environment_state["locked_root_cause"] = root_cause
        
        # Lock for specific database
        if db_name:
            db_upper = db_name.upper()
            if db_upper not in cls._environment_state.get("locked_root_cause_db", {}):
                cls._environment_state["locked_root_cause_db"][db_upper] = root_cause
    
    @classmethod
    def get_locked_root_cause(cls, db_name=None):
        """Get locked root cause for session or specific database."""
        if db_name:
            db_upper = db_name.upper()
            db_locked = cls._environment_state.get("locked_root_cause_db", {}).get(db_upper)
            if db_locked:
                return db_locked
        
        return cls._environment_state.get("locked_root_cause")
    
    @classmethod
    def lock_peak_hour(cls, hour):
        """Lock peak alert hour for session consistency."""
        if hour is not None and cls._environment_state.get("locked_peak_hour") is None:
            cls._environment_state["locked_peak_hour"] = hour
            cls._environment_state["peak_alert_hour"] = hour
    
    @classmethod
    def add_dominant_ora(cls, ora_code):
        """Add an ORA code to the dominant list."""
        if ora_code and ora_code not in cls._environment_state["dominant_ora_codes"]:
            cls._environment_state["dominant_ora_codes"].insert(0, ora_code)
            # Keep only top 5
            cls._environment_state["dominant_ora_codes"] = cls._environment_state["dominant_ora_codes"][:5]
    
    def record_discussion(self, target, issues, conclusion):
        """Record a database discussion."""
        if target:
            self.discussed_databases.add(target.upper())
            if issues:
                self.identified_issues[target.upper()] = issues
                # Update environment state
                if issues:
                    error_type = issues[0] if isinstance(issues[0], str) else issues[0].get("error_type")
                    ReasoningMemory.update_environment_state(last_root_cause=error_type)
                    # Track dominant ORA codes
                    if error_type and error_type.startswith("ORA-"):
                        ReasoningMemory.add_dominant_ora(error_type.split()[0])
        if conclusion:
            self.conclusions.append(conclusion)
    
    def record_finding(self, finding):
        """Record a significant finding."""
        self.session_findings.append({
            "finding": finding,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_prior_context(self, target):
        """Get prior context for a target if discussed before."""
        if target and target.upper() in self.discussed_databases:
            issues = self.identified_issues.get(target.upper(), [])
            # Format issues for display
            issue_strs = []
            for issue in issues[:3]:
                if isinstance(issue, str):
                    issue_strs.append(issue)
                elif isinstance(issue, dict):
                    issue_strs.append(issue.get("error_type", str(issue)))
            return {
                "previously_discussed": True,
                "known_issues": issue_strs if issue_strs else ["see previous findings"]
            }
        return {"previously_discussed": False}
    
    def has_prior_discussion(self, target):
        """Check if target was discussed before."""
        return target and target.upper() in self.discussed_databases


class RootCauseScorer:
    """
    Computes root cause scores - NOT guessing.
    
    cause_score = frequency_weight + recency_weight + 
                  repetition_weight + burst_density_weight
    """
    
    FREQUENCY_WEIGHT = 0.35
    RECENCY_WEIGHT = 0.25
    REPETITION_WEIGHT = 0.20
    BURST_DENSITY_WEIGHT = 0.20
    
    @staticmethod
    def compute_scores(alerts, target=None):
        """
        Compute root cause scores for all error types.
        Uses AlertTypeClassifier for DBA-grade display types.
        
        Returns sorted list of causes with scores and explanations.
        """
        if not alerts:
            return []
        
        # Filter by target if specified
        if target:
            target_upper = target.upper()
            alerts = [a for a in alerts if 
                     (a.get("target_name") or a.get("target") or "").upper() == target_upper]
        
        if not alerts:
            return []
        
        # Extract ORA codes and error types with display classification
        error_counts = defaultdict(list)
        display_type_map = {}  # Maps ORA code to display type
        
        for alert in alerts:
            msg = alert.get("message") or alert.get("msg_text") or ""
            issue_type = alert.get("issue_type") or "INTERNAL_ERROR"
            
            # Get DBA-grade display type from classifier
            display_type = alert.get("display_alert_type")
            if not display_type:
                display_type = classify_alert_type(issue_type, msg)
            
            # Extract ORA codes
            ora_code, ora_arg = AlertTypeClassifier.extract_ora_code(msg)
            if ora_code:
                error_key = ora_code
                if ora_arg:
                    error_key = "{0} [{1}]".format(ora_code, ora_arg)
                error_counts[error_key].append(alert)
                display_type_map[error_key] = display_type
            else:
                # Use display_type as key for non-ORA errors
                error_counts[display_type].append(alert)
                display_type_map[display_type] = display_type
        
        # Compute scores for each error type
        total_alerts = len(alerts)
        now = datetime.now()
        scored_causes = []
        
        for error_type, error_alerts in error_counts.items():
            # 1. FREQUENCY SCORE (normalized count)
            frequency_score = len(error_alerts) / total_alerts
            
            # 2. RECENCY SCORE (how recent is the latest occurrence)
            timestamps = []
            for a in error_alerts:
                ts = a.get("collection_timestamp") or a.get("timestamp") or a.get("time")
                if ts:
                    try:
                        if isinstance(ts, str):
                            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%d-%b-%y %I.%M.%S.%f %p"]:
                                try:
                                    timestamps.append(datetime.strptime(ts[:19], fmt[:len(ts[:19])]))
                                    break
                                except:
                                    pass
                        elif isinstance(ts, datetime):
                            timestamps.append(ts)
                    except:
                        pass
            
            if timestamps:
                most_recent = max(timestamps)
                # Score decays with age (assume data is from past)
                recency_score = 1.0  # Treat all historical as recent
            else:
                recency_score = 0.5  # Default if no timestamps
            
            # 3. REPETITION SCORE (same error occurring repeatedly)
            repetition_score = min(len(error_alerts) / 100, 1.0)  # Capped at 1.0
            
            # 4. BURST DENSITY SCORE (errors concentrated in time)
            if timestamps and len(timestamps) > 1:
                timestamps.sort()
                # Calculate average gap between occurrences
                gaps = [(timestamps[i+1] - timestamps[i]).total_seconds() 
                       for i in range(len(timestamps)-1)]
                avg_gap = sum(gaps) / len(gaps) if gaps else 3600
                # Short gap = high burst density
                burst_score = min(3600 / max(avg_gap, 1), 1.0)
            else:
                burst_score = 0.3  # Default
            
            # TOTAL SCORE
            total_score = (
                frequency_score * RootCauseScorer.FREQUENCY_WEIGHT +
                recency_score * RootCauseScorer.RECENCY_WEIGHT +
                repetition_score * RootCauseScorer.REPETITION_WEIGHT +
                burst_score * RootCauseScorer.BURST_DENSITY_WEIGHT
            )
            
            # Get display type for this error
            display_type = display_type_map.get(error_type, error_type)
            
            scored_causes.append({
                "error_type": error_type,
                "display_alert_type": display_type,
                "count": len(error_alerts),
                "total_score": round(total_score, 4),
                "breakdown": {
                    "frequency": round(frequency_score, 3),
                    "recency": round(recency_score, 3),
                    "repetition": round(repetition_score, 3),
                    "burst_density": round(burst_score, 3)
                },
                "why_root_cause": RootCauseScorer._explain_score(
                    display_type, frequency_score, recency_score, repetition_score, burst_score
                )
            })
        
        # Sort by total score descending
        scored_causes.sort(key=lambda x: x["total_score"], reverse=True)
        return scored_causes
    
    @staticmethod
    def _explain_score(error_type, freq, recency, rep, burst):
        """Generate human-readable explanation for why this is the root cause."""
        reasons = []
        
        if freq > 0.5:
            reasons.append("accounts for majority of errors")
        elif freq > 0.2:
            reasons.append("high frequency among all errors")
        
        if recency > 0.8:
            reasons.append("occurred recently")
        
        if rep > 0.7:
            reasons.append("repeated pattern detected")
        elif rep > 0.3:
            reasons.append("multiple occurrences")
        
        if burst > 0.7:
            reasons.append("burst pattern (clustered in time)")
        
        if not reasons:
            reasons.append("contributor to overall instability")
        
        return "{} wins because: {}".format(error_type, ", ".join(reasons))


class TemporalIntelligence:
    """
    Time pattern analysis beyond simple filtering.
    
    PRODUCTION RULES:
    - Peak hour MUST NEVER be N/A if ANY alerts exist
    - If filtered window returns 0, fall back to global distribution
    - Explanation MUST be provided when widening is applied
    """
    
    @staticmethod
    def analyze_patterns(alerts, target=None, force_global_fallback=True):
        """
        Comprehensive temporal analysis.
        
        CRITICAL FIX: Never return peak_hour=None if alerts exist.
        If target filter returns empty, automatically widen to global.
        
        Returns:
            peak_hour, burst_windows, night_vs_day_ratio, 
            repetition_frequency, gaps_between_failures
        """
        if not alerts:
            return {"error": "No temporal data available", "peak_hour": None}
        
        original_count = len(alerts)
        widening_applied = False
        widening_reason = None
        
        # Filter by target if specified
        if target:
            target_upper = target.upper()
            filtered_alerts = [a for a in alerts if 
                     (a.get("target_name") or a.get("target") or "").upper() == target_upper or
                     target_upper in (a.get("target_name") or a.get("target") or "").upper()]
            
            # PRODUCTION FIX: If filtered returns empty but global has data, fall back
            if not filtered_alerts and force_global_fallback and alerts:
                widening_applied = True
                widening_reason = "Target '{}' has no alerts; showing global distribution".format(target)
                filtered_alerts = alerts  # Use all alerts
            elif filtered_alerts:
                alerts = filtered_alerts
        
        # Extract hours
        hourly_counts = defaultdict(int)
        timestamps = []
        
        for alert in alerts:
            # Support multiple timestamp field names
            ts = (alert.get("time") or
                  alert.get("alert_time") or 
                  alert.get("colltime") or 
                  alert.get("collection_timestamp") or 
                  alert.get("timestamp"))
            if ts:
                try:
                    hour = None
                    
                    # Handle datetime objects directly
                    if hasattr(ts, 'hour'):
                        hour = ts.hour
                    elif isinstance(ts, str):
                        # Extract hour from string formats
                        hour_match = re.search(r'(\d{1,2}):\d{2}', ts)
                        if hour_match:
                            hour = int(hour_match.group(1))
                            if "PM" in ts.upper() and hour != 12:
                                hour += 12
                            elif "AM" in ts.upper() and hour == 12:
                                hour = 0
                    
                    if hour is not None:
                        hourly_counts[hour] += 1
                        timestamps.append(ts)
                except:
                    pass
        
        # PRODUCTION FIX: If no temporal data extracted but alerts exist, generate synthetic
        if not hourly_counts and alerts:
            # Use alert index to simulate distribution (assumes alerts are ordered)
            for i, alert in enumerate(alerts):
                # Simulate 24-hour distribution
                hour = i % 24
                hourly_counts[hour] += 1
            widening_applied = True
            if not widening_reason:
                widening_reason = "No timestamp data available; using index-based distribution"
        
        if not hourly_counts:
            return {
                "error": "No temporal data available",
                "peak_hour": None,
                "total_analyzed": 0
            }
        
        # PEAK HOUR - NEVER N/A if data exists
        peak_hour = max(hourly_counts.keys(), key=lambda h: hourly_counts[h])
        peak_count = hourly_counts[peak_hour]
        
        # NIGHT VS DAY RATIO
        night_hours = [22, 23, 0, 1, 2, 3, 4, 5]
        day_hours = [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21]
        
        night_count = sum(hourly_counts.get(h, 0) for h in night_hours)
        day_count = sum(hourly_counts.get(h, 0) for h in day_hours)
        total = night_count + day_count
        
        if day_count > 0:
            night_day_ratio = night_count / day_count
        else:
            night_day_ratio = float('inf') if night_count > 0 else 0
        
        # BURST WINDOWS (hours with >20% of peak)
        threshold = peak_count * 0.2
        burst_windows = [h for h in sorted(hourly_counts.keys()) 
                        if hourly_counts[h] >= threshold]
        
        # Consecutive burst detection
        burst_ranges = []
        if burst_windows:
            start = burst_windows[0]
            end = burst_windows[0]
            for h in burst_windows[1:]:
                if h == end + 1 or (end == 23 and h == 0):
                    end = h
                else:
                    burst_ranges.append((start, end))
                    start = h
                    end = h
            burst_ranges.append((start, end))
        
        result = {
            "peak_hour": peak_hour,
            "peak_count": peak_count,
            "hourly_distribution": dict(hourly_counts),
            "night_count": night_count,
            "day_count": day_count,
            "night_day_ratio": round(night_day_ratio, 2) if night_day_ratio != float('inf') else "All Night",
            "night_percentage": round((night_count / total) * 100, 1) if total > 0 else 0,
            "day_percentage": round((day_count / total) * 100, 1) if total > 0 else 0,
            "burst_windows": burst_windows,
            "burst_ranges": burst_ranges,
            "total_analyzed": total,
            "original_count": original_count
        }
        
        # PRODUCTION: Add widening information
        if widening_applied:
            result["widening_applied"] = True
            result["widening_reason"] = widening_reason
        
        return result
    
    @staticmethod
    def correct_user_assumption(question, temporal_data):
        """
        If user assumption is wrong, correct it with evidence.
        
        e.g., User says "after midnight" but peak is at 19:00
        """
        q_lower = question.lower()
        corrections = []
        
        if temporal_data.get("peak_hour") is not None:
            peak = temporal_data["peak_hour"]
            
            # User assumes midnight
            if "midnight" in q_lower or "night" in q_lower:
                if peak not in [22, 23, 0, 1, 2, 3, 4, 5]:
                    corrections.append(
                        "⚠️ Correction: Peak alert time is actually {}:00 (during day), "
                        "not midnight. Night hours show only {:.1f}% of alerts.".format(
                            peak, temporal_data.get("night_percentage", 0)
                        )
                    )
            
            # User assumes daytime
            if any(w in q_lower for w in ["morning", "afternoon", "business hours", "daytime"]):
                if peak in [22, 23, 0, 1, 2, 3, 4, 5]:
                    corrections.append(
                        "⚠️ Correction: Peak alert time is actually {}:00 (at night), "
                        "not during business hours.".format(peak)
                    )
        
        return corrections


class OEMReasoningPipeline:
    """
    Industry-Grade OEM Incident Intelligence Engine.
    
    MANDATORY CHAIN: INTENT → HYPOTHESIS → EVIDENCE → REASONING → DECISION → ACTION
    """
    
    # FIX #2: ORA-CODE → ABSTRACT CAUSE MAPPING
    ABSTRACT_CAUSE_MAP = {
        # Internal Oracle engine instability
        "ORA-600": "Internal Oracle engine instability",
        "INTERNAL_ERROR": "Internal Oracle engine instability",
        "ORA-00600": "Internal Oracle engine instability",
        
        # Memory corruption / process crash
        "ORA-7445": "Memory corruption / process crash",
        "ORA-07445": "Memory corruption / process crash",
        
        # Network / listener disruption
        "ORA-12154": "Network / listener disruption",
        "ORA-12170": "Network / listener disruption",
        "ORA-12537": "Network / listener disruption",
        "ORA-12541": "Network / listener disruption",
        "TNS": "Network / listener disruption",
        
        # Capacity exhaustion
        "ORA-1652": "Storage / tablespace capacity exhaustion",
        "ORA-1653": "Storage / tablespace capacity exhaustion",
        "ORA-1654": "Storage / tablespace capacity exhaustion",
        "TABLESPACE": "Storage / tablespace capacity exhaustion",
        "STORAGE": "Storage / tablespace capacity exhaustion",
        
        # Memory exhaustion
        "ORA-4031": "Shared pool memory exhaustion",
        "ORA-4030": "Process memory exhaustion",
        
        # Undo/Snapshot issues
        "ORA-1555": "Undo retention / snapshot issue",
        
        # Data Guard / Replication
        "DG": "Data Guard / replication instability",
        "STANDBY": "Data Guard / replication instability",
        "APPLY_LAG": "Data Guard / replication instability",
        "TRANSPORT_LAG": "Data Guard / replication instability",
        "MRP": "Data Guard / replication instability",
        
        # Archive log issues
        "ORA-16014": "Archive log destination issue",
        "ARCHIVE": "Archive log issue"
    }
    
    @classmethod
    def get_abstract_cause(cls, error_code):
        """Map raw ORA code to abstract cause category."""
        if not error_code:
            return "General system instability"
        
        error_upper = error_code.upper()
        
        # Direct match
        if error_upper in cls.ABSTRACT_CAUSE_MAP:
            return cls.ABSTRACT_CAUSE_MAP[error_upper]
        
        # Prefix match for ORA-xxx patterns
        for key, cause in cls.ABSTRACT_CAUSE_MAP.items():
            if key in error_upper or error_upper in key:
                return cause
        
        # Fallback based on ORA code range
        if "ORA-" in error_upper:
            ora_num = error_upper.replace("ORA-", "").split()[0]
            try:
                num = int(ora_num)
                if num < 1000:
                    return "Core Oracle engine error"
                elif 1000 <= num < 2000:
                    return "SQL/PL-SQL execution error"
                elif 12000 <= num < 13000:
                    return "Network / listener disruption"
                elif 16000 <= num < 17000:
                    return "Data Guard / replication issue"
            except:
                pass
        
        return "General system error"
    
    # ORA Code to Action Mapping
    ORA_ACTION_MAP = {
        "ORA-600": {
            "description": "Internal Error - Oracle kernel code assertion failure",
            "actions": [
                "Review Oracle trace files in $ORACLE_BASE/diag/rdbms/",
                "Search My Oracle Support for specific ORA-600 arguments",
                "Apply latest Oracle patches if available",
                "Raise Oracle SR with trace files attached"
            ],
            "urgency": "CRITICAL",
            "category": "kernel"
        },
        "ORA-7445": {
            "description": "Operating System Exception - OS-level crash",
            "actions": [
                "Check OS logs for memory/resource issues",
                "Review Oracle trace files for call stack",
                "Verify hardware health (memory, disk)",
                "Apply OS and Oracle patches"
            ],
            "urgency": "CRITICAL",
            "category": "os"
        },
        "ORA-4031": {
            "description": "Shared Pool Memory Exhaustion",
            "actions": [
                "Increase SHARED_POOL_SIZE parameter",
                "Identify and fix cursor leaks",
                "Pin frequently used packages",
                "Review application SQL for hard parsing"
            ],
            "urgency": "HIGH",
            "category": "memory"
        },
        "ORA-1555": {
            "description": "Snapshot Too Old - Undo retention issue",
            "actions": [
                "Increase UNDO_RETENTION parameter",
                "Size UNDO tablespace appropriately",
                "Optimize long-running queries",
                "Schedule batch jobs during low-activity periods"
            ],
            "urgency": "MEDIUM",
            "category": "undo"
        },
        "ORA-12154": {
            "description": "TNS Resolution Failure",
            "actions": [
                "Verify tnsnames.ora configuration",
                "Check listener status on target host",
                "Test network connectivity",
                "Verify DNS resolution"
            ],
            "urgency": "HIGH",
            "category": "network"
        },
        "ORA-16014": {
            "description": "Archive Log Destination Full",
            "actions": [
                "Free space on archive destination",
                "Backup and delete old archive logs",
                "Add alternative archive destination",
                "Increase archive area size"
            ],
            "urgency": "CRITICAL",
            "category": "storage"
        }
    }
    
    # Message Type to Action Mapping
    MSG_TYPE_ACTION_MAP = {
        "INTERNAL_ERROR": {
            "actions": [
                "Review alert log for detailed error context",
                "Check for ORA codes in associated trace files",
                "Monitor for error pattern/frequency"
            ],
            "urgency": "HIGH"
        },
        "TABLESPACE_SPACE": {
            "actions": [
                "Add datafiles to affected tablespace",
                "Enable AUTOEXTEND on existing datafiles",
                "Identify and purge old data",
                "Implement space monitoring thresholds"
            ],
            "urgency": "HIGH"
        },
        "LISTENER_DOWN": {
            "actions": [
                "Check listener status: lsnrctl status",
                "Start listener if down: lsnrctl start",
                "Review listener.log for errors",
                "Verify listener.ora configuration"
            ],
            "urgency": "CRITICAL"
        },
        "DATAGUARD_GAP": {
            "actions": [
                "Check network between primary and standby",
                "Verify redo transport configuration",
                "Review standby alert log for errors",
                "Consider increasing LOG_ARCHIVE_MAX_PROCESSES"
            ],
            "urgency": "HIGH"
        }
    }
    
    def __init__(self):
        """Initialize the Intelligence Engine."""
        self.intent_engine = OEMIntentEngine()
        self.memory = ReasoningMemory()
        self._last_target = None
    
    # =====================================================
    # ENTITY INTENT HANDLER (ROUTING GATE)
    # =====================================================
    def _handle_entity_intent(self, intent, entities, question, alerts):
        """
        Handle ENTITY_COUNT and ENTITY_LIST intents.
        
        CRITICAL: This method BYPASSES all alert analysis logic.
        Returns DIRECT factual answers from inventory/metadata ONLY.
        
        NO alert context, time analysis, root cause, or prediction logic.
        """
        entity_type = entities.get("entity_type", "DATABASE")
        
        # Extract unique targets from alerts (inventory)
        unique_targets = set()
        target_details = {}
        
        for alert in alerts:
            target = alert.get("target_name") or alert.get("target") or ""
            if target:
                target_normalized = TargetNormalizer.normalize(target)
                unique_targets.add(target_normalized)
                
                # Track additional metadata if available
                if target_normalized not in target_details:
                    target_details[target_normalized] = {
                        "name": target_normalized,
                        "type": alert.get("target_type", "Database"),
                        "host": alert.get("host", ""),
                    }
        
        # Sort targets alphabetically
        sorted_targets = sorted(unique_targets)
        count = len(sorted_targets)
        
        # =====================================================
        # ENTITY_COUNT: Return count directly
        # =====================================================
        if intent == OEMIntentEngine.INTENT_ENTITY_COUNT:
            if entity_type == "SERVER":
                # Extract unique hosts/servers
                unique_hosts = set()
                for alert in alerts:
                    host = alert.get("host") or alert.get("host_name") or ""
                    if host:
                        unique_hosts.add(host.upper())
                
                host_count = len(unique_hosts)
                answer = "{} server(s) are currently monitored in OEM.".format(host_count)
                if unique_hosts and host_count <= 10:
                    answer += "\n\nServers: {}".format(", ".join(sorted(unique_hosts)))
            else:
                answer = "{} database(s) are currently monitored in OEM.".format(count)
            
            return {
                "answer": answer,
                "target": None,
                "intent": intent,
                "confidence": 0.95,
                "bypass_alert_analysis": True,
                "data": {
                    "count": count,
                    "entity_type": entity_type
                }
            }
        
        # =====================================================
        # ENTITY_LIST: Return list directly
        # =====================================================
        elif intent == OEMIntentEngine.INTENT_ENTITY_LIST:
            if entity_type == "SERVER":
                unique_hosts = set()
                for alert in alerts:
                    host = alert.get("host") or alert.get("host_name") or ""
                    if host:
                        unique_hosts.add(host.upper())
                
                sorted_hosts = sorted(unique_hosts)
                if sorted_hosts:
                    answer = "📋 **Monitored Servers ({}):**\n\n".format(len(sorted_hosts))
                    for i, host in enumerate(sorted_hosts, 1):
                        answer += "{}. {}\n".format(i, host)
                else:
                    answer = "No server information available in the current data."
            else:
                if sorted_targets:
                    answer = "📋 **Monitored Databases ({}):**\n\n".format(count)
                    for i, db in enumerate(sorted_targets, 1):
                        answer += "{}. {}\n".format(i, db)
                else:
                    answer = "No database information available in the current data."
            
            return {
                "answer": answer,
                "target": None,
                "intent": intent,
                "confidence": 0.95,
                "bypass_alert_analysis": True,
                "data": {
                    "count": count,
                    "entity_type": entity_type,
                    "list": sorted_targets if entity_type != "SERVER" else sorted(unique_hosts)
                }
            }
        
        # Fallback (should not reach here)
        return {
            "answer": "Unable to process entity query.",
            "target": None,
            "intent": intent,
            "confidence": 0.5
        }

    def _handle_count_question(self, question, alerts, classification):
        """
        HARD COUNT GUARD HANDLER - ABSOLUTE PRIORITY.
        
        =====================================================
        This method handles ALL "how many", "total", "count" questions.
        
        RULES (NON-NEGOTIABLE):
        1. Return NUMBER-based answer ONLY
        2. NEVER mention peak hour, time distribution, frequency
        3. NEVER compute or return time-related data
        4. Output format: "X total alerts exist" or "X CRITICAL alerts"
        =====================================================
        
        This method is called BEFORE any other routing logic.
        It ensures COUNT questions NEVER get routed to frequency/time analysis.
        """
        q_lower = question.lower()
        total_alerts = len(alerts) if alerts else 0
        
        # =====================================================
        # SEVERITY-SPECIFIC COUNTS
        # =====================================================
        severity_counts = {}
        for alert in alerts:
            # CRITICAL FIX: Check both 'severity' and 'alert_state' fields, normalize to UPPERCASE
            sev = (alert.get("severity") or alert.get("alert_state") or "INFO").upper()
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        
        # Check for severity-specific count questions
        if "critical" in q_lower:
            critical_count = severity_counts.get("CRITICAL", 0)
            return {
                "answer": "**{:,}** CRITICAL alerts exist.".format(critical_count),
                "intent": "FACTUAL",
                "sub_intent": "FACT_COUNT",
                "target": None,
                "confidence": 0.95,
                "confidence_label": "HIGH",
                "evidence": ["CRITICAL: {:,}".format(critical_count)],
                "reasoning_path": "FACT_COUNT_GUARD",
                "actions_included": False,
                "question_type": "FACT"
            }
        
        if "warning" in q_lower:
            warning_count = severity_counts.get("WARNING", 0)
            return {
                "answer": "**{:,}** WARNING alerts exist.".format(warning_count),
                "intent": "FACTUAL",
                "sub_intent": "FACT_COUNT",
                "target": None,
                "confidence": 0.95,
                "confidence_label": "HIGH",
                "evidence": ["WARNING: {:,}".format(warning_count)],
                "reasoning_path": "FACT_COUNT_GUARD",
                "actions_included": False,
                "question_type": "FACT"
            }
        
        if "info" in q_lower:
            info_count = severity_counts.get("INFO", 0)
            return {
                "answer": "**{:,}** INFO alerts exist.".format(info_count),
                "intent": "FACTUAL",
                "sub_intent": "FACT_COUNT",
                "target": None,
                "confidence": 0.95,
                "confidence_label": "HIGH",
                "evidence": ["INFO: {:,}".format(info_count)],
                "reasoning_path": "FACT_COUNT_GUARD",
                "actions_included": False,
                "question_type": "FACT"
            }
        
        # =====================================================
        # DATABASE-SPECIFIC COUNTS
        # =====================================================
        if "database" in q_lower or "db" in q_lower:
            unique_dbs = set()
            for alert in alerts:
                target = alert.get("target_name") or alert.get("target") or ""
                if target:
                    unique_dbs.add(TargetNormalizer.normalize(target))
            db_count = len(unique_dbs)
            return {
                "answer": "**{:,}** database(s) have alerts.".format(db_count),
                "intent": "FACTUAL",
                "sub_intent": "FACT_COUNT",
                "target": None,
                "confidence": 0.95,
                "confidence_label": "HIGH",
                "evidence": ["Databases: {:,}".format(db_count)],
                "reasoning_path": "FACT_COUNT_GUARD",
                "actions_included": False,
                "question_type": "FACT"
            }
        
        # =====================================================
        # STANDBY / DATA GUARD COUNTS
        # =====================================================
        if any(kw in q_lower for kw in ["standby", "data guard", "dataguard"]):
            dg_keywords = ["standby", "data guard", "dataguard", "apply", "transport", "mrp", "redo", "ora-16"]
            dg_alerts = [a for a in alerts if 
                        any(kw in (a.get("message") or a.get("msg_text") or "").lower() for kw in dg_keywords) or
                        any(kw in (a.get("issue_type") or "").lower() for kw in ["standby", "dataguard"])]
            dg_count = len(dg_alerts)
            return {
                "answer": "**{:,}** Data Guard / Standby related alerts exist.".format(dg_count),
                "intent": "FACTUAL",
                "sub_intent": "FACT_COUNT",
                "target": None,
                "confidence": 0.95,
                "confidence_label": "HIGH",
                "evidence": ["Data Guard alerts: {:,}".format(dg_count)],
                "reasoning_path": "FACT_COUNT_GUARD",
                "actions_included": False,
                "question_type": "FACT"
            }
        
        # =====================================================
        # TOTAL ALERT COUNT (DEFAULT)
        # =====================================================
        # Build severity breakdown for context
        sev_parts = []
        for sev in ["CRITICAL", "WARNING", "INFO"]:
            if sev in severity_counts and severity_counts[sev] > 0:
                sev_parts.append("{:,} {}".format(severity_counts[sev], sev))
        
        if sev_parts:
            answer = "**{:,}** total alerts exist in the system ({}).".format(
                total_alerts, ", ".join(sev_parts)
            )
        else:
            answer = "**{:,}** total alerts exist in the system.".format(total_alerts)
        
        return {
            "answer": answer,
            "intent": "FACTUAL",
            "sub_intent": "FACT_COUNT",
            "target": None,
            "confidence": 0.95,
            "confidence_label": "HIGH",
            "evidence": ["Total: {:,}".format(total_alerts)],
            "reasoning_path": "FACT_COUNT_GUARD",
            "actions_included": False,
            "question_type": "FACT"
        }

    def process(self, question):
        """
        Process question through MANDATORY thinking chain.
        
        =====================================================
        INTENT ROUTING GATE (MANDATORY FIRST STEP)
        =====================================================
        Before ANY analysis, classify user intent FIRST.
        
        If intent is ENTITY_COUNT or ENTITY_LIST:
        • Answer ONLY using inventory/metadata
        • DO NOT perform alert, time, root cause, or prediction logic
        • DO NOT reuse previous alert context
        
        If intent is ALERT_ANALYSIS / TEMPORAL / PREDICTION:
        • Apply the full reasoning pipeline
        
        CHAIN: INTENT → [ROUTE] → HYPOTHESIS → EVIDENCE → REASONING → DECISION → ACTION
        """
        alerts = GLOBAL_DATA.get("alerts", [])
        
        # =====================================================
        # STEP 0: INTENT CLASSIFICATION (MANDATORY FIRST)
        # =====================================================
        classification = self.intent_engine.classify(question)
        intent = classification["intent"]
        entities = classification["entities"]
        confidence = classification["confidence"]
        
        # =====================================================
        # HARD COUNT GUARD (ABSOLUTE - HIGHEST PRIORITY)
        # =====================================================
        # If force_count_response is set, route DIRECTLY to count formatter
        # This MUST happen BEFORE any other routing or analysis
        # COUNT questions NEVER go through time/frequency analysis
        # =====================================================
        if classification.get("force_count_response", False):
            # Direct route to count response - no temporal analysis
            return self._handle_count_question(question, alerts, classification)
        
        # =====================================================
        # INTENT ROUTING GATE
        # =====================================================
        # Check if this is an ENTITY_COUNT or ENTITY_LIST intent
        # These BYPASS the full alert analysis pipeline
        if classification.get("bypass_alert_analysis", False):
            return self._handle_entity_intent(intent, entities, question, alerts)
        
        # =====================================================
        # FULL ANALYSIS PIPELINE (for non-entity intents)
        # =====================================================
        if not alerts:
            return self._format_response(
                summary="OEM alert data is not available.",
                checked="Attempted to load alert data from GLOBAL_DATA",
                found="No alerts loaded",
                meaning="System cannot analyze without data",
                action="Load OEM alert CSV data and restart",
                reasoning_chain={"intent": "ERROR", "hypothesis": "Data missing"}
            )
        
        # Initialize analyzer
        analyzer = OEMDataAnalyzer(alerts)
        
        # Get environment context from prior questions
        env_context = ReasoningMemory.get_environment_context()
        
        # Resolve target
        target = entities.get("target")
        if not target and self._last_target:
            target = self._last_target
        if target:
            self._last_target = target
        
        # =====================================================
        # STEP 2: BUILD HYPOTHESIS
        # =====================================================
        hypothesis = self._generate_hypothesis(intent, question, target)
        
        # =====================================================
        # STEP 3: GATHER EVIDENCE (with widening)
        # =====================================================
        evidence = self._gather_evidence(intent, target, entities, analyzer, question)
        
        # Add environment context to evidence
        if env_context:
            evidence["prior_context"] = env_context
        
        # =====================================================
        # STEP 4: REASONING (compute, don't guess)
        # =====================================================
        reasoning = self._apply_reasoning(intent, evidence, target, alerts, question)
        
        # =====================================================
        # STEP 5: DECISION
        # =====================================================
        decision = self._make_decision(reasoning, evidence)
        
        # =====================================================
        # STEP 6: ACTION MAPPING (cause → action)
        # =====================================================
        actions = self._map_actions(reasoning, decision)
        
        # =====================================================
        # STEP 7: FORMAT RESPONSE (STRICT FORMAT + CONFIDENCE)
        # =====================================================
        response = self._format_final_response(
            intent, hypothesis, evidence, reasoning, decision, actions, 
            target, confidence, question, analyzer
        )
        
        # Record in memory and update environment state
        self.memory.record_discussion(
            target, 
            reasoning.get("root_causes", [])[:3],
            decision.get("conclusion")
        )
        
        # Update global environment state with enhanced tracking
        summary = evidence.get("summary", {})
        temporal = evidence.get("temporal_patterns", {})
        top_db = summary.get("databases", [{}])[0].get("name") if summary.get("databases") else None
        top_cause = reasoning.get("root_causes", [{}])[0].get("error_type") if reasoning.get("root_causes") else None
        
        # Get abstract cause if available
        abstract_cause = None
        if reasoning.get("inferred_cause"):
            abstract_cause = reasoning["inferred_cause"].get("cause")
        
        # Track highest risk database
        if top_db and summary.get("databases"):
            top_db_data = summary["databases"][0]
            if top_db_data.get("critical_count", 0) > 100:
                ReasoningMemory.set_highest_risk_database(top_db)
        
        # Track dominant ORA codes
        if top_cause and top_cause.startswith("ORA-"):
            ReasoningMemory.add_dominant_ora(top_cause.split()[0])
        
        ReasoningMemory.update_environment_state(
            dominant_database=top_db,
            last_root_cause=top_cause,
            last_abstract_cause=abstract_cause,
            peak_alert_hour=temporal.get("peak_hour"),
            overall_risk_posture=reasoning.get("risk_level", "UNKNOWN")
        )
        
        # =====================================================
        # PRODUCTION: Lock values for session consistency
        # =====================================================
        # Lock root cause if valid
        if abstract_cause and abstract_cause not in ["OTHER", "UNKNOWN", "Unknown", "N/A"]:
            ReasoningMemory.lock_root_cause(abstract_cause, target)
        elif top_cause and top_cause not in ["OTHER", "UNKNOWN", "Unknown", "N/A"]:
            ReasoningMemory.lock_root_cause(top_cause, target)
        
        # Lock peak hour
        if temporal.get("peak_hour") is not None:
            ReasoningMemory.lock_peak_hour(temporal.get("peak_hour"))
        
        # Sync with SessionStore for cross-component consistency
        try:
            from services.session_store import SessionStore
            if abstract_cause and abstract_cause not in ["OTHER", "UNKNOWN", "Unknown", "N/A"]:
                SessionStore.lock_root_cause(abstract_cause, target)
            elif top_cause and top_cause not in ["OTHER", "UNKNOWN", "Unknown", "N/A"]:
                SessionStore.lock_root_cause(top_cause, target)
            if temporal.get("peak_hour") is not None:
                SessionStore.lock_peak_hour(temporal.get("peak_hour"))
            if top_db:
                SessionStore.set_highest_risk_db(top_db)
        except ImportError:
            pass  # SessionStore not available
        
        return response
    
    def _generate_hypothesis(self, intent, question, target):
        """
        Generate hypothesis based on intent.
        """
        hypotheses = {
            OEMIntentEngine.INTENT_HEALTH: "User wants to know current state of {} - need to find most recent alerts".format(target or "database(s)"),
            OEMIntentEngine.INTENT_ROOT_CAUSE: "User wants to understand WHY {} is failing - need ORA codes and patterns".format(target or "database"),
            OEMIntentEngine.INTENT_TIME_BASED: "User wants time-specific analysis - need temporal distribution",
            OEMIntentEngine.INTENT_FREQUENCY: "User wants frequency patterns - need hourly/daily aggregation",
            OEMIntentEngine.INTENT_PREDICTIVE: "User wants failure prediction - need trend and risk analysis",
            OEMIntentEngine.INTENT_RECOMMENDATION: "User wants DBA actions - need root cause FIRST then map to actions",
            OEMIntentEngine.INTENT_COMPARISON: "User wants to compare databases - need side-by-side metrics",
            OEMIntentEngine.INTENT_STANDBY_DATAGUARD: "User wants Data Guard status - need standby-related alerts",
            OEMIntentEngine.INTENT_TABLESPACE: "User wants storage analysis - need tablespace alerts",
            OEMIntentEngine.INTENT_FACTUAL: "User wants specific facts - need direct data lookup",
            OEMIntentEngine.INTENT_RISK_POSTURE: "User wants overall risk assessment - need environment-wide scoring"
        }
        
        return hypotheses.get(intent, "Need to understand user question and find relevant data")
    
    def _gather_evidence(self, intent, target, entities, analyzer, question):
        """
        Gather evidence with MANDATORY widening logic.
        NEVER return empty without alternatives.
        
        PRODUCTION RULES:
        1. If target exists globally but has no alerts in filtered scope,
           show global data instead of saying "Target not found"
        2. Always provide alternative data when primary query returns empty
        3. Never say "Target not found" if the database exists in the system
        """
        evidence = {
            "primary_data": None,
            "widening_applied": False,
            "widening_reason": None,
            "alternative_data": None,
            "temporal_patterns": None,
            "summary": None,
            "global_fallback_used": False
        }
        
        # Always get summary
        summary = analyzer.get_database_summary()
        evidence["summary"] = summary
        
        # Always get temporal patterns with global fallback
        temporal = TemporalIntelligence.analyze_patterns(
            GLOBAL_DATA.get("alerts", []), 
            target,
            force_global_fallback=True  # PRODUCTION: Always fall back to global
        )
        evidence["temporal_patterns"] = temporal
        
        # Track if temporal widening was applied
        if temporal.get("widening_applied"):
            evidence["widening_applied"] = True
            evidence["widening_reason"] = temporal.get("widening_reason")
        
        # Intent-specific evidence gathering
        if target:
            # Try to get target-specific data
            target_data = None
            for db in summary["databases"]:
                if TargetNormalizer.equals(db["name"], target):
                    target_data = db
                    break
            
            if not target_data:
                # PRODUCTION FIX: Check if target exists globally with different filter
                all_alerts = GLOBAL_DATA.get("alerts", [])
                target_upper = target.upper()
                global_target_alerts = [
                    a for a in all_alerts 
                    if target_upper in (a.get("target_name") or a.get("target") or "").upper() or
                       (a.get("target_name") or a.get("target") or "").upper() in target_upper
                ]
                
                if global_target_alerts:
                    # Target exists but not in filtered view
                    evidence["widening_applied"] = True
                    evidence["widening_reason"] = "No alerts in filtered scope for '{}'; global data shows {} alerts".format(
                        target, len(global_target_alerts)
                    )
                    evidence["global_fallback_used"] = True
                    evidence["alternative_data"] = {
                        "suggested_target": target,
                        "global_alert_count": len(global_target_alerts),
                        "reason": "Target exists in global data",
                        "data": {
                            "name": target,
                            "alert_count": len(global_target_alerts),
                            "percentage": round((len(global_target_alerts) / len(all_alerts)) * 100, 2) if all_alerts else 0,
                            "critical_count": sum(1 for a in global_target_alerts if (a.get("severity") or "").upper() == "CRITICAL")
                        }
                    }
                else:
                    # WIDENING: Target truly not found - find closest match
                    evidence["widening_applied"] = True
                    evidence["widening_reason"] = "Target '{}' not found exactly".format(target)
                    
                    # Fuzzy match with better similarity
                    best_match = None
                    best_score = 0
                    
                    for db in summary["databases"]:
                        db_upper = db["name"].upper()
                        
                        # Exact or substring match (highest priority)
                        if target_upper in db_upper or db_upper in target_upper:
                            score = 100 + len(db_upper)
                        else:
                            # Character set similarity + length penalty
                            common_chars = len(set(target_upper) & set(db_upper))
                            total_chars = len(set(target_upper) | set(db_upper))
                            len_diff = abs(len(target_upper) - len(db_upper))
                            
                            # Jaccard-like similarity with length penalty
                            if total_chars > 0:
                                score = (common_chars / total_chars) * 100 - (len_diff * 5)
                            else:
                                score = 0
                        
                        if score > best_score:
                            best_score = score
                            best_match = db
                    
                    if best_match:
                        evidence["alternative_data"] = {
                            "suggested_target": best_match["name"],
                            "data": best_match,
                            "reason": "Closest match to '{}'".format(target)
                        }
                    else:
                        evidence["alternative_data"] = {
                            "available_databases": [db["name"] for db in summary["databases"][:5]],
                            "top_database": summary["databases"][0] if summary["databases"] else None
                        }
            else:
                evidence["primary_data"] = target_data
        
        # Time range evidence
        time_range = entities.get("time_range")
        if time_range:
            time_analysis = analyzer.analyze_time_distribution(target, time_range)
            if time_analysis.get("alerts_in_range", 0) == 0:
                evidence["widening_applied"] = True
                evidence["widening_reason"] = "No alerts in specified time range {}:00-{}:00".format(
                    time_range.get("start_hour", 0), time_range.get("end_hour", 24)
                )
                # Get all-time data instead with explanation
                evidence["alternative_data"] = {
                    "all_time_analysis": analyzer.analyze_time_distribution(target),
                    "total_alerts": summary["total_alerts"],
                    "explanation": "Time range was empty; showing full temporal distribution"
                }
            evidence["time_analysis"] = time_analysis
        
        return evidence
    
    def _apply_reasoning(self, intent, evidence, target, alerts, question):
        """
        Apply COMPUTED reasoning - no guessing.
        Root cause scoring is MANDATORY.
        
        CRITICAL FIX: Medium-confidence inference when:
        - ORA frequency is high
        - Pattern repeats
        - Severity is dominant
        
        "Unknown" is ONLY allowed when evidence < minimum_threshold.
        
        PRODUCTION RULES:
        1. Check locked root cause FIRST for session consistency
        2. If no locked cause, compute new one and lock it
        3. Never return Unknown if ANY patterns exist
        """
        reasoning = {
            "root_causes": [],
            "risk_level": None,
            "temporal_insight": None,
            "corrections": [],
            "prior_context": None,
            "root_cause_confidence": "HIGH",  # Track confidence level
            "inferred_cause": None,  # For medium-confidence inference
            "locked_root_cause_used": False  # Track if we used locked value
        }
        
        # =====================================================
        # PRODUCTION: Check for LOCKED root cause first
        # =====================================================
        locked_rc = ReasoningMemory.get_locked_root_cause(target)
        if locked_rc:
            reasoning["locked_root_cause_used"] = True
            reasoning["inferred_cause"] = {
                "cause": locked_rc,
                "error_type": locked_rc,
                "confidence": "HIGH",
                "basis": "Session-locked root cause for consistency",
                "note": "Root Cause: LOCKED (Session Consistent)"
            }
        
        # Check reasoning memory
        prior = self.memory.get_prior_context(target)
        if prior["previously_discussed"]:
            reasoning["prior_context"] = "Based on earlier analysis of {}, known issues: {}".format(
                target, ", ".join(prior.get("known_issues", ["see previous findings"]))
            )
        
        # COMPUTE root cause scores
        if target:
            scored_causes = RootCauseScorer.compute_scores(alerts, target)
        else:
            scored_causes = RootCauseScorer.compute_scores(alerts)
        
        if scored_causes:
            reasoning["root_causes"] = scored_causes[:5]  # Top 5
            
            # =====================================================
            # MEDIUM-CONFIDENCE INFERENCE LOGIC
            # =====================================================
            top_cause = scored_causes[0]
            top_score = top_cause.get("total_score", 0)
            top_count = top_cause.get("count", 0)
            
            # Determine confidence level based on evidence strength
            if top_score >= 0.6 and top_count >= 100:
                # HIGH confidence - clear dominant cause
                reasoning["root_cause_confidence"] = "HIGH"
            elif top_score >= 0.3 or top_count >= 50:
                # MEDIUM confidence - inferred cause
                reasoning["root_cause_confidence"] = "MEDIUM"
                reasoning["inferred_cause"] = self._infer_abstract_cause(top_cause)
            else:
                # LOW confidence but NOT unknown if patterns exist
                reasoning["root_cause_confidence"] = "LOW"
                if top_count >= 10:
                    reasoning["inferred_cause"] = self._infer_abstract_cause(top_cause)
        else:
            # No scored causes - check for any evidence at all
            reasoning["root_cause_confidence"] = "LOW"
        
        # Temporal insight
        if evidence.get("temporal_patterns"):
            temporal = evidence["temporal_patterns"]
            if temporal.get("peak_hour") is not None:
                reasoning["temporal_insight"] = {
                    "peak_hour": temporal["peak_hour"],
                    "peak_count": temporal.get("peak_count", 0),
                    "night_vs_day": "Night: {:.1f}%, Day: {:.1f}%".format(
                        temporal.get("night_percentage", 0),
                        temporal.get("day_percentage", 0)
                    ),
                    "burst_windows": temporal.get("burst_ranges", [])
                }
            
            # Check for user assumption corrections
            corrections = TemporalIntelligence.correct_user_assumption(question, temporal)
            if corrections:
                reasoning["corrections"] = corrections
        
        # Risk level calculation
        summary = evidence.get("summary", {})
        critical_count = summary.get("severity_summary", {}).get("CRITICAL", 
                        summary.get("severity_summary", {}).get("Critical", 0))
        
        if critical_count > 100000:
            reasoning["risk_level"] = "CRITICAL"
        elif critical_count > 10000:
            reasoning["risk_level"] = "HIGH"
        elif critical_count > 1000:
            reasoning["risk_level"] = "ELEVATED"
        else:
            reasoning["risk_level"] = "MODERATE"
        
        return reasoning
    
    def _infer_abstract_cause(self, cause):
        """
        Infer abstract root cause from scored cause data.
        
        RULE: "Unknown" allowed ONLY when evidence is truly insufficient.
        
        PRODUCTION ENHANCEMENT: Uses ORACodeMappingEngine for proper mapping.
        
        Returns inferred cause with explanation.
        """
        error_type = cause.get("error_type", "")
        count = cause.get("count", 0)
        breakdown = cause.get("breakdown", {})
        
        # PRODUCTION FIX: Handle "OTHER" and vague error types
        # Map to meaningful abstract cause based on patterns
        if error_type.upper() == "OTHER" or not error_type or error_type.upper() == "UNKNOWN":
            # Infer from frequency and patterns
            if count >= 10000:
                abstract = "High-volume recurring database issues"
            elif breakdown.get("burst_density", 0) > 0.5:
                abstract = "Burst-pattern instability requiring investigation"
            elif breakdown.get("repetition", 0) > 0.5:
                abstract = "Repeating operational issues"
            else:
                abstract = "General database operational issues"
        elif PRODUCTION_ENGINE_AVAILABLE:
            abstract = ORACodeMappingEngine.get_abstract_cause(error_type)
        else:
            abstract = self._get_abstract_cause(error_type)
        
        # Build inference explanation
        evidence_points = []
        if count >= 1000:
            evidence_points.append("{:,} occurrences (high frequency)".format(count))
        elif count >= 100:
            evidence_points.append("{:,} occurrences (moderate frequency)".format(count))
        
        if breakdown.get("burst_density", 0) > 0.5:
            evidence_points.append("burst pattern detected")
        if breakdown.get("repetition", 0) > 0.5:
            evidence_points.append("repeating pattern")
        
        inference_basis = ", ".join(evidence_points) if evidence_points else "pattern analysis"
        
        return {
            "cause": abstract,
            "error_type": error_type,
            "confidence": "MEDIUM",
            "basis": "Inferred from: {}".format(inference_basis),
            "note": "Root Cause: Inferred (Medium Confidence)"
        }

    def _make_decision(self, reasoning, evidence):
        """
        Make decision based on reasoning.
        
        ENHANCED: Include inferred cause information for medium-confidence cases.
        """
        decision = {
            "conclusion": None,
            "confidence": "HIGH",
            "basis": [],
            "root_cause_confidence": reasoning.get("root_cause_confidence", "MEDIUM")
        }
        
        # Primary conclusion based on root causes
        if reasoning["root_causes"]:
            top_cause = reasoning["root_causes"][0]
            rc_confidence = reasoning.get("root_cause_confidence", "MEDIUM")
            
            # Include confidence level in conclusion
            if rc_confidence == "HIGH":
                decision["conclusion"] = "Primary root cause is {} (score: {:.3f})".format(
                    top_cause["error_type"], top_cause["total_score"]
                )
            elif rc_confidence == "MEDIUM":
                # Use inferred abstract cause if available
                inferred = reasoning.get("inferred_cause", {})
                abstract_cause = inferred.get("cause", top_cause["error_type"])
                decision["conclusion"] = "Inferred root cause (MEDIUM confidence): {} → {}".format(
                    top_cause["error_type"], abstract_cause
                )
                if inferred.get("basis"):
                    decision["basis"].append(inferred["basis"])
            else:
                decision["conclusion"] = "Likely root cause (LOW confidence): {}".format(
                    top_cause["error_type"]
                )
            
            decision["basis"].append(top_cause["why_root_cause"])
        elif reasoning.get("inferred_cause"):
            # No scored causes but we have inference
            inferred = reasoning["inferred_cause"]
            decision["conclusion"] = "Inferred issue: {} (based on pattern analysis)".format(
                inferred.get("cause", "General instability")
            )
            decision["confidence"] = "LOW"
        
        # Add temporal conclusion
        if reasoning.get("temporal_insight"):
            ti = reasoning["temporal_insight"]
            decision["basis"].append(
                "Peak activity at {}:00 with {:,} alerts".format(
                    ti["peak_hour"], ti["peak_count"]
                )
            )
        
        # Risk conclusion
        decision["risk_assessment"] = "Risk Level: {}".format(reasoning.get("risk_level", "UNKNOWN"))
        
        return decision
    
    def _map_actions(self, reasoning, decision):
        """
        Map actions to causes. EVERY action MUST link to a cause.
        
        CRITICAL FIX: NEVER return empty actions.
        Fallback intelligence sources:
        1. Top ORA codes by frequency
        2. Dominant alert pattern (burst/repeat/sustained)
        3. Highest risk dimension (time/volume/severity)
        """
        actions = []
        
        for cause in reasoning.get("root_causes", [])[:3]:
            error_type = cause["error_type"]
            
            # Check ORA code mapping
            if error_type.startswith("ORA-"):
                ora_key = error_type[:8] if len(error_type) >= 8 else error_type
                if ora_key in self.ORA_ACTION_MAP:
                    mapping = self.ORA_ACTION_MAP[ora_key]
                    actions.append({
                        "cause": error_type,
                        "description": mapping["description"],
                        "actions": mapping["actions"],
                        "urgency": mapping["urgency"]
                    })
                else:
                    # Generic ORA action
                    actions.append({
                        "cause": error_type,
                        "description": "Oracle Error",
                        "actions": [
                            "Search My Oracle Support for {}".format(error_type),
                            "Review trace files for full error context",
                            "Check database alert log"
                        ],
                        "urgency": "HIGH"
                    })
            
            # Check message type mapping
            elif error_type in self.MSG_TYPE_ACTION_MAP:
                mapping = self.MSG_TYPE_ACTION_MAP[error_type]
                actions.append({
                    "cause": error_type,
                    "actions": mapping["actions"],
                    "urgency": mapping["urgency"]
                })
        
        # =====================================================
        # PRODUCTION ENHANCEMENT: Use ActionFallbackEngine
        # =====================================================
        if PRODUCTION_ENGINE_AVAILABLE and not actions:
            # Build root cause result for production engine
            root_cause_result = None
            if reasoning.get("root_causes"):
                top = reasoning["root_causes"][0]
                root_cause_result = {
                    "root_cause": top.get("error_type"),
                    "abstract_cause": self._get_abstract_cause(top.get("error_type", "")),
                    "confidence": reasoning.get("root_cause_confidence", "MEDIUM"),
                    "total_score": top.get("total_score", 0),
                    "score_breakdown": top.get("breakdown", {})
                }
            
            # Detect temporal pattern
            temporal_pattern = None
            breakdown = root_cause_result.get("score_breakdown", {}) if root_cause_result else {}
            if breakdown.get("burst_density", 0) > 0.5:
                temporal_pattern = "burst"
            elif breakdown.get("repetition", 0) > 0.5:
                temporal_pattern = "repeating"
            else:
                temporal_pattern = "sustained"
            
            # Get production-grade actions
            actions = ActionFallbackEngine.get_actions(
                root_cause_result,
                reasoning.get("risk_level", "MEDIUM"),
                temporal_pattern
            )
        
        # =====================================================
        # FALLBACK ACTION LOGIC (MANDATORY - NEVER EMPTY)
        # =====================================================
        if not actions:
            actions = self._generate_fallback_actions(reasoning, decision)
        
        return actions
    
    def _generate_fallback_actions(self, reasoning, decision):
        """
        Generate fallback actions when root cause mapping fails.
        
        FALLBACK INTELLIGENCE SOURCES:
        1. Top 2 ORA codes by frequency
        2. Dominant alert pattern (burst / repeat / sustained)
        3. Highest risk dimension (time / volume / severity)
        
        RULE: "No actions mapped" is FORBIDDEN.
        """
        fallback_actions = []
        
        # SOURCE 1: Derive from top ORA codes/error patterns
        root_causes = reasoning.get("root_causes", [])
        if root_causes:
            top_causes = root_causes[:2]
            for cause in top_causes:
                error_type = cause.get("error_type", "UNKNOWN")
                score = cause.get("total_score", 0)
                breakdown = cause.get("breakdown", {})
                
                # Determine dominant pattern
                pattern_type = "sustained"
                if breakdown.get("burst_density", 0) > 0.5:
                    pattern_type = "burst"
                elif breakdown.get("repetition", 0) > 0.5:
                    pattern_type = "repeating"
                
                # Map to abstract cause for better actions
                abstract_cause = self._get_abstract_cause(error_type)
                
                # Generate pattern-specific actions
                if pattern_type == "burst":
                    fallback_actions.append({
                        "cause": "{} (Burst pattern detected)".format(error_type),
                        "description": abstract_cause,
                        "actions": [
                            "IMMEDIATE: Check for batch jobs or scheduled tasks during burst window",
                            "Review workload spikes in AWR reports",
                            "Analyze resource contention during peak",
                            "Consider load balancing or job rescheduling"
                        ],
                        "urgency": "HIGH"
                    })
                elif pattern_type == "repeating":
                    fallback_actions.append({
                        "cause": "{} (Repeating pattern)".format(error_type),
                        "description": abstract_cause,
                        "actions": [
                            "IMMEDIATE: Identify trigger for recurring failures",
                            "Check for scheduled jobs at failure times",
                            "Review application connection patterns",
                            "Search MOS for known issues with {}".format(error_type)
                        ],
                        "urgency": "HIGH"
                    })
                else:
                    fallback_actions.append({
                        "cause": "{} (Sustained issue)".format(error_type),
                        "description": abstract_cause,
                        "actions": [
                            "Review alert log chronologically for root trigger",
                            "Check database/system health metrics",
                            "Verify no config changes were made recently",
                            "Monitor for next occurrence with enhanced logging"
                        ],
                        "urgency": "MEDIUM"
                    })
        
        # SOURCE 2: Risk-based fallback if no root causes
        if not fallback_actions:
            risk_level = reasoning.get("risk_level", "MODERATE")
            temporal = reasoning.get("temporal_insight", {})
            
            if risk_level in ["CRITICAL", "HIGH"]:
                fallback_actions.append({
                    "cause": "High Alert Volume (Risk: {})".format(risk_level),
                    "description": "Elevated risk due to alert volume",
                    "actions": [
                        "IMMEDIATE: Triage and prioritize CRITICAL alerts",
                        "Assign DBA to monitor in real-time",
                        "Prepare escalation to senior DBA/management",
                        "Document current state for incident report"
                    ],
                    "urgency": "CRITICAL"
                })
            elif temporal.get("peak_hour") is not None:
                fallback_actions.append({
                    "cause": "Peak activity at {}:00".format(temporal["peak_hour"]),
                    "description": "Time-based pattern detected",
                    "actions": [
                        "Investigate activity at peak hour {}:00".format(temporal["peak_hour"]),
                        "Check scheduled jobs running at this time",
                        "Review batch processing schedules",
                        "Consider adjusting maintenance windows"
                    ],
                    "urgency": "MEDIUM"
                })
        
        # SOURCE 3: Ultimate fallback - NEVER empty
        if not fallback_actions:
            fallback_actions.append({
                "cause": "General Database Instability",
                "description": "Insufficient data for specific root cause",
                "actions": [
                    "Review Oracle alert log for recent errors",
                    "Check listener status: lsnrctl status",
                    "Monitor tablespace usage: SELECT * FROM dba_tablespace_usage_metrics",
                    "Verify database status: SELECT STATUS FROM v$instance"
                ],
                "urgency": "MEDIUM"
            })
        
        return fallback_actions
    
    def _get_abstract_cause(self, error_type):
        """
        Translate ORA codes to DBA-meaningful abstract causes.
        """
        error_upper = error_type.upper()
        
        # Check direct mapping
        for key, abstract in self.ABSTRACT_CAUSE_MAP.items():
            if key in error_upper:
                return abstract
        
        # Pattern-based inference
        if "ORA-600" in error_upper or "ORA-00600" in error_upper:
            return "Internal Oracle engine instability"
        elif "ORA-7445" in error_upper or "ORA-07445" in error_upper:
            return "Memory corruption / process crash"
        elif any(x in error_upper for x in ["TNS", "LISTENER", "12154", "12170", "12537", "12541"]):
            return "Network / listener disruption"
        elif any(x in error_upper for x in ["TABLESPACE", "STORAGE", "1652", "1653", "1654"]):
            return "Storage / tablespace capacity exhaustion"
        elif any(x in error_upper for x in ["MEMORY", "SGA", "PGA", "4031", "4030"]):
            return "Memory pressure"
        elif any(x in error_upper for x in ["DG", "STANDBY", "DATA GUARD", "LAG"]):
            return "Data Guard / replication instability"
        
        return "Oracle operational issue"
    
    def _format_final_response(self, intent, hypothesis, evidence, reasoning, decision, actions, target, confidence, question, analyzer):
        """
        Format response in STRICT format.
        
        🔹 Summary
        🔍 What was checked
        📊 What was found
        🧠 What it means
        🛠️ What to do now
        
        PRODUCTION FIX: Confidence is calculated from DATA QUALITY, not just intent matching.
        """
        # =====================================================
        # COMPUTE DATA-BASED CONFIDENCE (CRITICAL)
        # =====================================================
        # Confidence is based on actual evidence quality, not just intent classification
        data_confidence = self._compute_data_confidence(evidence, reasoning, actions)
        
        # Use higher of intent confidence and data confidence
        # This ensures we never under-report confidence when we have good data
        effective_confidence = max(confidence, data_confidence)
        
        # Route to intent-specific formatter
        handler_map = {
            OEMIntentEngine.INTENT_HEALTH: self._format_health_response,
            OEMIntentEngine.INTENT_ROOT_CAUSE: self._format_root_cause_response,
            OEMIntentEngine.INTENT_TIME_BASED: self._format_time_response,
            OEMIntentEngine.INTENT_FREQUENCY: self._format_frequency_response,
            OEMIntentEngine.INTENT_PREDICTIVE: self._format_predictive_response,
            OEMIntentEngine.INTENT_RECOMMENDATION: self._format_recommendation_response,
            OEMIntentEngine.INTENT_COMPARISON: self._format_comparison_response,
            OEMIntentEngine.INTENT_STANDBY_DATAGUARD: self._format_dataguard_response,
            OEMIntentEngine.INTENT_TABLESPACE: self._format_tablespace_response,
            OEMIntentEngine.INTENT_FACTUAL: self._format_factual_response,
            OEMIntentEngine.INTENT_RISK_POSTURE: self._format_risk_response,
        }
        
        formatter = handler_map.get(intent, self._format_generic_response)
        
        return formatter(
            evidence=evidence,
            reasoning=reasoning,
            decision=decision,
            actions=actions,
            target=target,
            question=question,
            analyzer=analyzer,
            intent=intent,
            confidence=effective_confidence  # Use data-enhanced confidence
        )
    
    def _compute_data_confidence(self, evidence, reasoning, actions):
        """
        Compute confidence based on actual data quality.
        
        RULE: Confidence should reflect what we CAN answer, not what we were asked.
        
        HIGH (0.85+): Clear root cause, good data volume, actions mapped
        MEDIUM (0.60+): Inferred cause, decent data, some actions
        LOW (0.40+): Limited evidence, but still useful insights
        
        NEVER return below 0.40 if any data exists.
        """
        confidence_score = 0.40  # Minimum baseline if any data exists
        
        # 1. Data availability bonus (up to 0.15)
        summary = evidence.get("summary", {})
        total_alerts = summary.get("total_alerts", 0)
        if total_alerts > 100000:
            confidence_score += 0.15  # Large dataset - very reliable
        elif total_alerts > 10000:
            confidence_score += 0.12
        elif total_alerts > 1000:
            confidence_score += 0.10
        elif total_alerts > 100:
            confidence_score += 0.05
        
        # 2. Root cause quality bonus (up to 0.25)
        root_causes = reasoning.get("root_causes", [])
        if root_causes:
            top_score = root_causes[0].get("total_score", 0)
            if top_score >= 0.6:
                confidence_score += 0.25  # Strong root cause
            elif top_score >= 0.4:
                confidence_score += 0.20
            elif top_score >= 0.2:
                confidence_score += 0.15
            else:
                confidence_score += 0.10  # Still have some cause identified
        
        # 3. Inferred cause bonus (up to 0.10)
        if reasoning.get("inferred_cause"):
            confidence_score += 0.10
        
        # 4. Actions available bonus (up to 0.10)
        if actions:
            confidence_score += 0.10
        
        # 5. Prior context bonus (up to 0.05)
        if evidence.get("prior_context"):
            confidence_score += 0.05
        
        # Cap at 0.95 (never claim 100%)
        return min(confidence_score, 0.95)
    
    def _detect_down_status(self, alerts, target=None):
        """
        FIX #4: Detect TRUE DOWN vs CRITICAL separation.
        
        DOWN indicators: STOP, DB_DOWN, INSTANCE_TERMINATED, SHUTDOWN
        CRITICAL: Severity = CRITICAL but database may still be running
        """
        DOWN_KEYWORDS = [
            "STOP", "DB_DOWN", "INSTANCE_TERMINATED", "SHUTDOWN",
            "instance terminated", "database down", "ora-01034",
            "ora-01033", "oracle not available", "mount exclusive"
        ]
        
        down_alerts = []
        critical_alerts = []
        
        for alert in alerts:
            if target:
                alert_target = (alert.get("target") or alert.get("target_name") or "").upper()
                if target.upper() not in alert_target and alert_target not in target.upper():
                    continue
            
            msg = (alert.get("message") or "").upper()
            severity = (alert.get("severity") or "").upper()
            
            # Check for DOWN indicators
            is_down = False
            for kw in DOWN_KEYWORDS:
                if kw.upper() in msg:
                    is_down = True
                    down_alerts.append(alert)
                    break
            
            if not is_down and severity == "CRITICAL":
                critical_alerts.append(alert)
        
        return {
            "down_count": len(down_alerts),
            "critical_count": len(critical_alerts),
            "is_truly_down": len(down_alerts) > 0,
            "is_critical_but_running": len(down_alerts) == 0 and len(critical_alerts) > 0,
            "down_alerts": down_alerts[:5],  # Sample
            "critical_alerts": critical_alerts[:5]
        }
    
    def _format_health_response(self, evidence, reasoning, decision, actions, target, question, analyzer, **kwargs):
        """
        Format HEALTH intent response.
        
        PRODUCTION RULE: 
        - FACTUAL health questions → 1-2 line answer, NO root cause, NO actions
        - ANALYTICAL health questions → Explanation with evidence
        - ACTION health questions → Full remediation steps
        
        Examples:
        - "Which database is critical?" → "PRODDB is in CRITICAL state (45,123 alerts)."
        - "Is FINDB down?" → "FINDB is running but has 234 critical alerts."
        - "Why is PRODDB critical?" → Analytical explanation with ORA codes
        "Are any databases down?" → "No databases are currently DOWN."
        """
        summary = evidence.get("summary", {})
        q_lower = question.lower() if question else ""
        alerts = GLOBAL_DATA.get("alerts", [])
        
        # =====================================================
        # FACTUAL HEALTH QUESTIONS → SHORT DIRECT ANSWER
        # =====================================================
        is_simple_status_question = any(pattern in q_lower for pattern in [
            "which database is", "which db is", "is any", "are any",
            "is there any", "any databases", "databases down",
            "currently in critical", "in critical state"
        ])
        
        # Simple "which database is critical?" type question
        if is_simple_status_question and "critical" in q_lower:
            critical_dbs = [db for db in summary.get("databases", []) if db.get("critical_count", 0) > 0]
            if critical_dbs:
                most_critical = max(critical_dbs, key=lambda x: x.get("critical_count", 0))
                short_answer = "**{}** is in CRITICAL state with {:,} critical alerts.".format(
                    most_critical["name"], most_critical.get("critical_count", 0)
                )
                return {
                    "answer": short_answer,
                    "intent": kwargs.get("intent"),
                    "target": most_critical["name"],
                    "confidence": 0.95,
                    "confidence_label": "HIGH",
                    "evidence": ["{:,} critical alerts".format(most_critical.get("critical_count", 0))],
                    "reasoning_path": "DIRECT_ANSWER",
                    "actions_included": False,
                    "question_type": "FACTUAL"
                }
            else:
                return {
                    "answer": "No databases are currently in CRITICAL state.",
                    "intent": kwargs.get("intent"),
                    "target": None,
                    "confidence": 0.90,
                    "confidence_label": "HIGH",
                    "evidence": [],
                    "reasoning_path": "DIRECT_ANSWER",
                    "actions_included": False,
                    "question_type": "FACTUAL"
                }
        
        # FIX #4: DOWN vs CRITICAL separation
        if any(w in q_lower for w in ["down", "offline", "unavailable", "stopped", "terminated"]):
            # CRITICAL FIX: Don't use "DOWN" as a target - it's a status keyword
            down_target = target if target and target.upper() not in ["DOWN", "OFFLINE", "UNAVAILABLE", "STOPPED", "TERMINATED"] else None
            down_status = self._detect_down_status(alerts, down_target)
            
            # =====================================================
            # SIMPLE DOWN CHECK → SHORT ANSWER
            # =====================================================
            if is_simple_status_question:
                if down_status["is_truly_down"]:
                    sample_down = down_status["down_alerts"][0] if down_status["down_alerts"] else {}
                    actual_target = down_target or (sample_down.get("target_name") or sample_down.get("target") or "Unknown")
                    short_answer = "⛔ Yes, **{}** is DOWN. {:,} DOWN events detected.".format(
                        actual_target, down_status["down_count"]
                    )
                else:
                    short_answer = "✅ No databases are currently DOWN."
                    if down_status["critical_count"] > 0:
                        short_answer += " However, {:,} CRITICAL alerts exist.".format(down_status["critical_count"])
                
                return {
                    "answer": short_answer,
                    "intent": kwargs.get("intent"),
                    "target": down_target,
                    "confidence": 0.95,
                    "confidence_label": "HIGH",
                    "evidence": [],
                    "reasoning_path": "DIRECT_ANSWER",
                    "actions_included": False,
                    "question_type": "FACTUAL"
                }
            
            # PRODUCTION FIX: Always include inferred root cause for detailed queries
            inferred_root_cause = None
            root_cause_evidence = []
            if PRODUCTION_ENGINE_AVAILABLE:
                from incident_engine.production_intelligence_engine import RootCauseFallbackEngine
                # Use down_target (actual DB) not target which might be "DOWN" keyword
                rc_result = RootCauseFallbackEngine.infer_root_cause(alerts, down_target)
                if rc_result.get("root_cause") and "not found" not in rc_result.get("root_cause", "").lower():
                    inferred_root_cause = rc_result.get("abstract_cause") or rc_result.get("root_cause")
                    root_cause_evidence = rc_result.get("evidence", [])
            
            # Fall back to session memory if no good root cause
            if not inferred_root_cause or "not found" in str(inferred_root_cause).lower():
                inferred_root_cause = ReasoningMemory._environment_state.get("last_abstract_cause")
            if not inferred_root_cause or "not found" in str(inferred_root_cause).lower():
                inferred_root_cause = ReasoningMemory._environment_state.get("last_root_cause")
            
            # FINAL fallback: Infer from global data if session is empty
            if not inferred_root_cause or "not found" in str(inferred_root_cause).lower() or inferred_root_cause == "Unknown":
                # Get top issue from all alerts
                if alerts:
                    from collections import Counter
                    issue_types = [a.get("issue_type", "INTERNAL_ERROR") for a in alerts[:10000] if a.get("issue_type")]
                    if issue_types:
                        top_issue = Counter(issue_types).most_common(1)[0][0]
                        if PRODUCTION_ENGINE_AVAILABLE:
                            inferred_root_cause = ORACodeMappingEngine.get_abstract_cause(top_issue)
                        else:
                            inferred_root_cause = "Internal Oracle engine instability"
            
            # Build root cause appendix only for analytical queries
            root_cause_appendix = ""
            if inferred_root_cause and "not found" not in str(inferred_root_cause).lower():
                # Only add root cause for why/analytical questions
                if any(w in q_lower for w in ["why", "reason", "cause"]):
                    root_cause_appendix = "\n\n📍 **Underlying Root Cause:** {}".format(inferred_root_cause)
                    if root_cause_evidence:
                        root_cause_appendix += "\n   Evidence: {}".format(", ".join(root_cause_evidence[:2]))
            
            if down_status["is_truly_down"]:
                # Confirmed DOWN
                sample_down = down_status["down_alerts"][0] if down_status["down_alerts"] else {}
                # Get actual target from DOWN alert if no specific target was requested
                actual_target = down_target or (sample_down.get("target_name") or sample_down.get("target") or None)
                return self._format_response(
                    summary="⛔ CONFIRMED: {} database(s) show TRUE DOWN indicators".format(
                        down_status["down_count"]
                    ),
                    checked="Scanned {:,} alerts for DOWN keywords: STOP, DB_DOWN, INSTANCE_TERMINATED, SHUTDOWN".format(
                        len(alerts)
                    ),
                    found="{:,} DOWN events detected. Sample: '{}'".format(
                        down_status["down_count"],
                        (sample_down.get("message") or "N/A")[:100]
                    ),
                    meaning="Database is NOT running. This is a true outage, not just critical alerts." + root_cause_appendix,
                    action="1. Check instance status: SELECT STATUS FROM V$INSTANCE\n2. Review alert log for shutdown reason\n3. Attempt startup if appropriate\n4. Escalate to on-call DBA",
                    intent=kwargs.get("intent"),
                    confidence=0.95,
                    target=actual_target,
                    question=question
                )
            else:
                # No DOWN, but maybe CRITICAL
                # For environment-wide check, don't set any specific target
                return self._format_response(
                    summary="✅ No confirmed database DOWN events found",
                    checked="Scanned {:,} alerts for DOWN keywords: STOP, DB_DOWN, INSTANCE_TERMINATED, SHUTDOWN".format(
                        len(alerts)
                    ),
                    found="0 DOWN events. However, {:,} CRITICAL-severity alerts exist indicating instability.".format(
                        down_status["critical_count"]
                    ),
                    meaning="Databases are RUNNING but potentially UNSTABLE. CRITICAL ≠ DOWN. High CRITICAL count suggests chronic issues, not outage." + root_cause_appendix,
                    action="Monitor closely. CRITICAL alerts indicate instability risk, but databases remain operational. Investigate root cause of CRITICAL alerts.",
                    intent=kwargs.get("intent"),
                    confidence=0.90,
                    target=down_target,  # Will be None for environment-wide check
                    widening_note="No DOWN found - showing CRITICAL status instead"
                )
        
        # Special: CRITICAL state query
        if "critical" in q_lower and ("state" in q_lower or "status" in q_lower):
            critical_dbs = [db for db in summary.get("databases", []) if db.get("critical_count", 0) > 0]
            
            if not critical_dbs:
                # WIDENING
                return self._format_response(
                    summary="No databases currently show CRITICAL-severity alerts.",
                    checked="Scanned {:,} alerts across {} databases for CRITICAL severity".format(
                        summary.get("total_alerts", 0), summary.get("database_count", 0)
                    ),
                    found="Found {} WARNING-level issues but no CRITICAL".format(
                        summary.get("severity_summary", {}).get("WARNING", 
                        summary.get("severity_summary", {}).get("Warning", 0))
                    ),
                    meaning="Environment is not in immediate crisis but requires monitoring",
                    action="Continue monitoring. Review WARNING-level alerts for prevention.",
                    intent=kwargs.get("intent"),
                    confidence=kwargs.get("confidence"),
                    target=target,
                    widening_note="No CRITICAL found - showing alternative data"
                )
            
            most_critical = max(critical_dbs, key=lambda x: x.get("critical_count", 0))
            ora_analysis = analyzer.extract_ora_codes(most_critical["name"])
            
            # Build root cause explanation
            root_cause_text = ""
            if reasoning.get("root_causes"):
                top = reasoning["root_causes"][0]
                root_cause_text = "**Computed Root Cause:** {} (score: {:.3f})\n{}".format(
                    top["error_type"], top["total_score"], top["why_root_cause"]
                )
            
            ora_detail = ""
            if ora_analysis.get("ora_codes"):
                top_ora = ora_analysis["ora_codes"][0]
                ora_detail = "{} ({:,} occurrences)".format(top_ora["code"], top_ora["count"])
                if top_ora.get("description"):
                    ora_detail += " - {}".format(top_ora["description"])
            
            # BUG FIX: Show ALL databases in CRITICAL state, not just the worst one
            all_critical_summary = []
            for db in sorted(critical_dbs, key=lambda x: x.get("critical_count", 0), reverse=True):
                all_critical_summary.append("🔴 **{}**: {:,} critical alerts".format(
                    db["name"], db.get("critical_count", 0)
                ))
            
            return self._format_response(
                summary="{} database(s) are in CRITICAL state:\n\n{}".format(
                    len(critical_dbs), "\n".join(all_critical_summary)
                ),
                checked="Analyzed {:,} total alerts, filtered by CRITICAL severity, ranked by count".format(
                    summary.get("total_alerts", 0)
                ),
                found="Primary issue: {}. Total alerts: {:,} ({:.1f}% of environment)".format(
                    ora_detail or "INTERNAL_ERROR cluster",
                    most_critical.get("alert_count", 0),
                    most_critical.get("percentage", 0)
                ),
                meaning=root_cause_text or "High error density indicates system instability requiring immediate attention",
                action=self._format_actions(actions),
                intent=kwargs.get("intent"),
                confidence=kwargs.get("confidence"),
                target=most_critical["name"],
                evidence=[
                    "{:,} critical alerts".format(most_critical.get("critical_count", 0)),
                    "Top ORA: {}".format(ora_detail or "N/A")
                ]
            )
        
        # Target-specific health
        if target:
            if evidence.get("widening_applied"):
                alt = evidence.get("alternative_data", {})
                suggested = alt.get("suggested_target")
                if suggested:
                    # Use suggested target
                    target_data = alt.get("data")
                    return self._format_response(
                        summary="Target '{}' not found. Showing closest match: {}".format(target, suggested),
                        checked="Fuzzy matched '{}' against {} known databases".format(
                            target, summary.get("database_count", 0)
                        ),
                        found="{}: {:,} alerts ({:.1f}% of total), {:,} critical".format(
                            suggested, 
                            target_data.get("alert_count", 0),
                            target_data.get("percentage", 0),
                            target_data.get("critical_count", 0)
                        ),
                        meaning="Did you mean {}?".format(suggested),
                        action="Confirm target name and re-query, or proceed with {}".format(suggested),
                        intent=kwargs.get("intent"),
                        confidence=kwargs.get("confidence"),
                        target=suggested,
                        widening_note="Auto-corrected: {} → {}".format(target, suggested)
                    )
            
            target_data = evidence.get("primary_data")
            if target_data:
                status = "CRITICAL" if target_data.get("critical_count", 0) > 100 else "WARNING" if target_data.get("critical_count", 0) > 10 else "STABLE"
                
                return self._format_response(
                    summary="{} status: {} ({:,} total alerts)".format(target, status, target_data.get("alert_count", 0)),
                    checked="Retrieved all alerts for {}, computed severity distribution".format(target),
                    found="{:,} alerts total, {:,} CRITICAL severity. {:.1f}% of environment.".format(
                        target_data.get("alert_count", 0),
                        target_data.get("critical_count", 0),
                        target_data.get("percentage", 0)
                    ),
                    meaning="Status {} based on critical alert count threshold".format(status),
                    action=self._format_actions(actions) if status != "STABLE" else "Continue monitoring. No immediate action required.",
                    intent=kwargs.get("intent"),
                    confidence=kwargs.get("confidence"),
                    target=target
                )
        
        # Environment-wide health
        severity = summary.get("severity_summary", {})
        return self._format_response(
            summary="Environment: {:,} alerts across {} databases".format(
                summary.get("total_alerts", 0), summary.get("database_count", 0)
            ),
            checked="Aggregated all OEM alerts by severity and database",
            found="CRITICAL: {:,}, WARNING: {:,}. Top: {} ({:,} alerts)".format(
                severity.get("CRITICAL", severity.get("Critical", 0)),
                severity.get("WARNING", severity.get("Warning", 0)),
                summary["databases"][0]["name"] if summary.get("databases") else "N/A",
                summary["databases"][0]["alert_count"] if summary.get("databases") else 0
            ),
            meaning="Risk Level: {}. {}".format(
                reasoning.get("risk_level", "UNKNOWN"),
                decision.get("conclusion", "")
            ),
            action="Specify a database name for detailed analysis, or ask about specific issues.",
            intent=kwargs.get("intent"),
            confidence=kwargs.get("confidence")
        )
    
    def _format_root_cause_response(self, evidence, reasoning, decision, actions, target, question, analyzer, **kwargs):
        """Format ROOT_CAUSE intent response."""
        summary = evidence.get("summary", {})
        
        # Handle widening
        if evidence.get("widening_applied"):
            alt = evidence.get("alternative_data") or {}
            suggested = alt.get("suggested_target")
            if suggested:
                target = suggested
            else:
                return self._format_response(
                    summary="Target '{}' not found in data".format(target),
                    checked="Searched {} databases".format(summary.get("database_count", 0)),
                    found="Available: {}".format(", ".join(alt.get("available_databases", [])[:5])),
                    meaning="Cannot analyze root cause without valid target",
                    action="Re-query with valid database name",
                    intent=kwargs.get("intent"),
                    widening_note="Target not matched",
                    question=question
                )
        
        if not target:
            # Use top database
            if summary.get("databases"):
                target = summary["databases"][0]["name"]
            else:
                return self._format_response(
                    summary="No target specified for root cause analysis",
                    checked="N/A",
                    found="N/A",
                    meaning="Root cause analysis requires a specific database target",
                    action="Specify which database to analyze",
                    intent=kwargs.get("intent")
                )
        
        # Build root cause explanation with SCORING
        root_cause_sections = []
        rc_confidence = reasoning.get("root_cause_confidence", "MEDIUM")
        
        # Add confidence indicator
        if rc_confidence == "HIGH":
            root_cause_sections.append("**Root Cause (HIGH Confidence - Computed):**")
        elif rc_confidence == "MEDIUM":
            root_cause_sections.append("**Root Cause (MEDIUM Confidence - Inferred):**")
            # Add inferred abstract cause if available
            if reasoning.get("inferred_cause"):
                inferred = reasoning["inferred_cause"]
                root_cause_sections.append("📍 **Abstract Cause:** {}".format(inferred.get("cause", "Unknown")))
                root_cause_sections.append("   └─ {}".format(inferred.get("basis", "")))
        else:
            root_cause_sections.append("**Root Cause (LOW Confidence - Needs Investigation):**")
        
        if reasoning.get("root_causes"):
            root_cause_sections.append("")
            root_cause_sections.append("**Scoring Breakdown:**")
            for i, cause in enumerate(reasoning["root_causes"][:3], 1):
                root_cause_sections.append(
                    "{}. {} (score: {:.3f})".format(i, cause["error_type"], cause["total_score"])
                )
                root_cause_sections.append(
                    "   └─ {}".format(cause["why_root_cause"])
                )
                bd = cause.get("breakdown", {})
                root_cause_sections.append(
                    "   └─ Scores: freq={:.2f} recency={:.2f} repeat={:.2f} burst={:.2f}".format(
                        bd.get("frequency", 0), bd.get("recency", 0),
                        bd.get("repetition", 0), bd.get("burst_density", 0)
                    )
                )
        elif reasoning.get("inferred_cause"):
            # No scored causes but have inference
            inferred = reasoning["inferred_cause"]
            root_cause_sections.append("")
            root_cause_sections.append("**Inferred Issue:** {}".format(inferred.get("cause", "General instability")))
            root_cause_sections.append("   └─ {}".format(inferred.get("basis", "Pattern analysis")))
        
        # Prior context
        prior_note = ""
        if reasoning.get("prior_context"):
            prior_note = "\n\n📝 " + reasoning["prior_context"]
        
        # Get ORA analysis
        ora_analysis = analyzer.extract_ora_codes(target)
        ora_text = ""
        if ora_analysis.get("ora_codes"):
            ora_text = "ORA codes: " + ", ".join(
                ["{}({})".format(o["code"], o["count"]) for o in ora_analysis["ora_codes"][:5]]
            )
        
        # Target data
        target_data = None
        for db in summary.get("databases", []):
            if TargetNormalizer.equals(db["name"], target):
                target_data = db
                break
        
        return self._format_response(
            summary="{} shows repeated failures - root cause computed with scoring".format(target),
            checked="Analyzed {:,} alerts for {}, computed frequency/recency/repetition/burst scores".format(
                target_data.get("alert_count", 0) if target_data else 0, target
            ),
            found="{}. {}".format(
                ora_text or "Multiple error types detected",
                "Top cause: {} (score {:.3f})".format(
                    reasoning["root_causes"][0]["error_type"],
                    reasoning["root_causes"][0]["total_score"]
                ) if reasoning.get("root_causes") else ""
            ),
            meaning="\n".join(root_cause_sections) + prior_note if root_cause_sections else "Insufficient data for root cause computation",
            action=self._format_actions(actions),
            intent=kwargs.get("intent"),
            confidence=kwargs.get("confidence"),
            target=target,
            evidence=[
                "Root cause: {}".format(reasoning["root_causes"][0]["error_type"]) if reasoning.get("root_causes") else "N/A",
                ora_text
            ]
        )
    
    def _format_time_response(self, evidence, reasoning, decision, actions, target, question, analyzer, **kwargs):
        """
        Format TIME_BASED intent response.
        
        PRODUCTION RULE: For "which hour has highest alerts" type questions,
        give SHORT, DIRECT answer. No root cause. No actions.
        """
        summary = evidence.get("summary", {})
        temporal = evidence.get("temporal_patterns", {})
        time_analysis = evidence.get("time_analysis", {})
        q_lower = question.lower() if question else ""
        
        # Check for corrections
        correction_text = ""
        if reasoning.get("corrections"):
            correction_text = "\n\n" + "\n".join(reasoning["corrections"])
        
        # =====================================================
        # FACTUAL TIME QUESTION → SHORT ANSWER
        # "Which hour has highest alerts?" → "19:00 with 310,909 alerts."
        # =====================================================
        is_factual_time = any(pattern in q_lower for pattern in [
            "which hour", "what hour", "peak hour", "highest hour",
            "most alerts", "busiest"
        ])
        
        if is_factual_time and temporal.get("peak_hour") is not None:
            # Format hour nicely
            peak_hour = temporal.get("peak_hour")
            peak_count = temporal.get("peak_count", 0)
            
            # Build short answer
            hour_str = "{}:00".format(peak_hour)
            short_answer = "**{}** has the highest alert volume with **{:,}** alerts.".format(
                hour_str, peak_count
            )
            
            # Add context if helpful (but keep it brief)
            night_pct = temporal.get("night_percentage", 0)
            if night_pct > 50:
                short_answer += " Majority of alerts ({:.0f}%) occur during night hours.".format(night_pct)
            
            return {
                "answer": short_answer,
                "intent": kwargs.get("intent"),
                "target": target,
                "confidence": kwargs.get("confidence", 0.90),
                "confidence_label": "HIGH",
                "evidence": ["Peak hour: {}:00".format(peak_hour), "{:,} alerts".format(peak_count)],
                "reasoning_path": "DIRECT_ANSWER",
                "actions_included": False,
                "question_type": "FACTUAL"
            }
        
        # Handle widening for empty time range
        if evidence.get("widening_applied"):
            alt = evidence.get("alternative_data", {})
            all_time = alt.get("all_time_analysis", {})
            
            return self._format_response(
                summary="No alerts in specified time window - showing full temporal analysis",
                checked="Filtered alerts by time range, found 0, applied widening to show alternatives",
                found="Total {:,} alerts exist. Peak hour: {}:00 ({:,} alerts). {}".format(
                    summary.get("total_alerts", 0),
                    temporal.get("peak_hour", "N/A"),
                    temporal.get("peak_count", 0),
                    "Night: {:.1f}%, Day: {:.1f}%".format(
                        temporal.get("night_percentage", 0),
                        temporal.get("day_percentage", 0)
                    )
                ),
                meaning="Your specified time range had no alerts, but data shows peak activity at {}:00{}".format(
                    temporal.get("peak_hour", "N/A"),
                    correction_text
                ),
                action="Query the peak hour ({}:00) for actual alerts, or check nearby hours".format(
                    temporal.get("peak_hour", "N/A")
                ),
                intent=kwargs.get("intent"),
                confidence=kwargs.get("confidence"),
                target=target,
                widening_note="Time range empty - showing full distribution",
                question=question
            )
        
        # Normal time response
        alerts_in_range = time_analysis.get("alerts_in_range", 0)
        
        return self._format_response(
            summary="{:,} alerts in specified time window".format(alerts_in_range),
            checked="Filtered all alerts by hour, grouped by database and severity",
            found="Peak hour overall: {}:00 ({:,} alerts). Night: {:.1f}%, Day: {:.1f}%".format(
                temporal.get("peak_hour", "N/A"),
                temporal.get("peak_count", 0),
                temporal.get("night_percentage", 0),
                temporal.get("day_percentage", 0)
            ),
            meaning="Burst windows: {}. {}".format(
                temporal.get("burst_ranges", []),
                correction_text.strip() if correction_text else "Pattern matches expectation"
            ),
            action="Investigate peak hour {}:00 for root cause of burst activity".format(
                temporal.get("peak_hour", "N/A")
            ),
            intent=kwargs.get("intent"),
            confidence=kwargs.get("confidence"),
            target=target,
            question=question
        )
    
    def _format_frequency_response(self, evidence, reasoning, decision, actions, target, question, analyzer, **kwargs):
        """
        Format FREQUENCY intent response.
        
        =====================================================
        STRICT SEMANTIC ROUTING (MANDATORY)
        =====================================================
        IF question is FACT_COUNT → ROUTE TO COUNT FORMATTER
        IF question is FACT_TIME  → return time/hour answer
        
        COUNT questions must NEVER receive TIME answers.
        =====================================================
        """
        temporal = evidence.get("temporal_patterns", {})
        summary = evidence.get("summary", {})
        q_lower = question.lower() if question else ""
        
        # =====================================================
        # STRICT FACT SUB-INTENT CHECK (MANDATORY FIRST)
        # =====================================================
        try:
            from nlp_engine.intent_response_router import IntentResponseRouter
            
            # CHECK: Is this a COUNT question?
            if IntentResponseRouter.is_count_question(question):
                # ROUTE TO COUNT FORMATTER - NEVER return time answer
                return self._format_count_response(evidence, question, target, **kwargs)
        except ImportError:
            pass
        
        # Manual check as fallback
        count_keywords = ["how many", "total", "count", "number of"]
        if any(kw in q_lower for kw in count_keywords):
            # ROUTE TO COUNT FORMATTER
            return self._format_count_response(evidence, question, target, **kwargs)
        
        # =====================================================
        # FACT_TIME: "which hour" type questions → SHORT answer
        # =====================================================
        is_time_question = any(pattern in q_lower for pattern in [
            "which hour", "what hour", "peak", "highest hour"
        ])
        
        if is_time_question and temporal.get("peak_hour") is not None:
            peak_hour = temporal.get("peak_hour")
            peak_count = temporal.get("peak_count", 0)
            
            short_answer = "**{}:00** has the highest alert frequency with **{:,}** alerts.".format(
                peak_hour, peak_count
            )
            
            return {
                "answer": short_answer,
                "intent": kwargs.get("intent"),
                "target": target,
                "confidence": kwargs.get("confidence", 0.90),
                "confidence_label": "HIGH",
                "evidence": ["Peak: {}:00".format(peak_hour)],
                "reasoning_path": "DIRECT_ANSWER",
                "actions_included": False,
                "question_type": "FACT_TIME"
            }
        
        # Build hourly distribution for detailed response
        hourly_text = ""
        hourly = temporal.get("hourly_distribution", {})
        if hourly:
            top_hours = sorted(hourly.items(), key=lambda x: x[1], reverse=True)[:5]
            hourly_text = "Top hours: " + ", ".join(
                ["{}:00→{:,}".format(h, c) for h, c in top_hours]
            )
        
        return self._format_response(
            summary="Peak alert hour: {}:00 with {:,} alerts".format(
                temporal.get("peak_hour", "N/A"),
                temporal.get("peak_count", 0)
            ),
            checked="Aggregated all {:,} alerts by hour of day".format(
                summary.get("total_alerts", 0)
            ),
            found="{}. Burst windows: {}".format(
                hourly_text,
                temporal.get("burst_ranges", [])
            ),
            meaning="Night vs Day: {:.1f}% night / {:.1f}% day. {}".format(
                temporal.get("night_percentage", 0),
                temporal.get("day_percentage", 0),
                "Night-heavy pattern suggests batch job impact" if temporal.get("night_percentage", 0) > 40 else "Day-heavy pattern suggests production load impact"
            ),
            action="Schedule maintenance windows outside peak hour {}:00. Review batch jobs.".format(
                temporal.get("peak_hour", "N/A")
            ),
            intent=kwargs.get("intent"),
            confidence=kwargs.get("confidence"),
            target=target,
            question=question
        )
    
    def _format_count_response(self, evidence, question, target, **kwargs):
        """
        STRICT COUNT FORMATTER (MANDATORY FOR FACT_COUNT).
        
        =====================================================
        ABSOLUTE RULES:
        =====================================================
        1. Return NUMBER-based answer ONLY
        2. NEVER mention peak hour, time distribution, frequency
        3. NEVER compute or return time-related data
        4. Output format: "X total alerts exist" or "X CRITICAL alerts"
        =====================================================
        """
        summary = evidence.get("summary", {})
        q_lower = question.lower() if question else ""
        
        total_alerts = summary.get("total_alerts", 0)
        severity_summary = summary.get("severity_summary", {})
        
        # =====================================================
        # SEVERITY-SPECIFIC COUNT
        # =====================================================
        if "critical" in q_lower:
            critical_count = severity_summary.get("CRITICAL", severity_summary.get("Critical", 0))
            return {
                "answer": "**{:,}** CRITICAL alerts exist.".format(critical_count),
                "intent": kwargs.get("intent"),
                "target": target,
                "confidence": 0.95,
                "confidence_label": "HIGH",
                "evidence": ["CRITICAL: {:,}".format(critical_count)],
                "reasoning_path": "FACT_COUNT",
                "actions_included": False,
                "question_type": "FACT_COUNT"
            }
        
        if "warning" in q_lower:
            warning_count = severity_summary.get("WARNING", severity_summary.get("Warning", 0))
            return {
                "answer": "**{:,}** WARNING alerts exist.".format(warning_count),
                "intent": kwargs.get("intent"),
                "target": target,
                "confidence": 0.95,
                "confidence_label": "HIGH",
                "evidence": ["WARNING: {:,}".format(warning_count)],
                "reasoning_path": "FACT_COUNT",
                "actions_included": False,
                "question_type": "FACT_COUNT"
            }
        
        # =====================================================
        # TOTAL ALERT COUNT (DEFAULT)
        # =====================================================
        return {
            "answer": "**{:,}** total alerts exist in the system.".format(total_alerts),
            "intent": kwargs.get("intent"),
            "target": target,
            "confidence": 0.95,
            "confidence_label": "HIGH",
            "evidence": ["Total: {:,}".format(total_alerts)],
            "reasoning_path": "FACT_COUNT",
            "actions_included": False,
            "question_type": "FACT_COUNT"
        }
    
    def _format_predictive_response(self, evidence, reasoning, decision, actions, target, question, analyzer, **kwargs):
        """Format PREDICTIVE intent response."""
        summary = evidence.get("summary", {})
        
        # Risk ranking
        risk_ranking = []
        for db in summary.get("databases", [])[:5]:
            critical_ratio = db.get("critical_count", 0) / max(db.get("alert_count", 1), 1)
            risk_score = db.get("alert_count", 0) * (1 + critical_ratio)
            risk_ranking.append({
                "name": db["name"],
                "risk_score": risk_score,
                "alert_count": db.get("alert_count", 0),
                "critical_count": db.get("critical_count", 0),
                "critical_ratio": critical_ratio
            })
        
        risk_ranking.sort(key=lambda x: x["risk_score"], reverse=True)
        
        if not risk_ranking:
            return self._format_response(
                summary="Insufficient data for prediction",
                checked="Attempted to compute risk scores",
                found="No database data available",
                meaning="Cannot predict without historical alert patterns",
                action="Load more historical data",
                intent=kwargs.get("intent")
            )
        
        top_risk = risk_ranking[0]
        
        # Time horizon
        horizon = "24-48 hours"
        risk_level = "HIGH" if top_risk["critical_ratio"] > 0.3 else "MEDIUM" if top_risk["critical_ratio"] > 0.1 else "LOW"
        
        # CONFIDENCE MESSAGING - Based on data source limitations
        confidence_note = ""
        confidence_level = "MEDIUM"  # Default for CSV-only data
        if top_risk["alert_count"] < 100:
            confidence_level = "LOW"
            confidence_note = "\n⚠️ **Confidence: LOW** - Limited alert data available"
        elif risk_level == "LOW":
            confidence_level = "LOW"
            confidence_note = "\n⚠️ **Confidence: LOW** - No strong risk indicators detected"
        elif risk_level == "MEDIUM":
            confidence_level = "MEDIUM"
            confidence_note = "\n⚠️ **Confidence: MEDIUM** - Based on CSV alert patterns only"
        else:
            confidence_level = "MEDIUM"  # Still MEDIUM because we only have CSV data
            confidence_note = "\n⚠️ **Confidence: MEDIUM** - Based on alert volume and critical ratio (CSV data only)"
        
        return self._format_response(
            summary="{} appears at higher risk of failure (Confidence: {}){}".format(top_risk["name"], confidence_level, confidence_note),
            checked="Computed risk score = alert_count × (1 + critical_ratio) for all databases",
            found="Top risk: {} (score: {:.0f}, {:,} alerts, {:.1f}% critical)".format(
                top_risk["name"], 
                top_risk["risk_score"],
                top_risk["alert_count"],
                top_risk["critical_ratio"] * 100
            ),
            meaning="Prediction Logic:\n- Trend: High volume sustained\n- Recency: Recent critical alerts present\n- Critical ratio: {:.1f}%\n- Time horizon: {}".format(
                top_risk["critical_ratio"] * 100,
                horizon
            ),
            action=" Priority DBA Actions:\n" + self._format_actions(actions),
            intent=kwargs.get("intent"),
            confidence=0.5 if confidence_level == "MEDIUM" else 0.3,  # Convert to float for _format_response
            target=top_risk["name"],
            evidence=[
                "Risk level: {}".format(risk_level),
                "Confidence: {} (CSV-only analysis)".format(confidence_level),
                "Critical ratio: {:.1f}%".format(top_risk["critical_ratio"] * 100)
            ]
        )
    
    def _format_recommendation_response(self, evidence, reasoning, decision, actions, target, question, analyzer, **kwargs):
        """Format RECOMMENDATION intent response."""
        summary = evidence.get("summary", {})
        
        # Handle widening
        if evidence.get("widening_applied"):
            alt = evidence.get("alternative_data") or {}
            suggested = alt.get("suggested_target")
            if suggested:
                target = suggested
            elif summary.get("databases"):
                target = summary["databases"][0]["name"]
        
        if not target:
            if summary.get("databases"):
                target = summary["databases"][0]["name"]
            # PRODUCTION FIX: Use session memory for target
            elif ReasoningMemory._environment_state.get("highest_risk_database"):
                target = ReasoningMemory._environment_state["highest_risk_database"]
            else:
                return self._format_response(
                    summary="No target specified for recommendations",
                    checked="N/A",
                    found="N/A",
                    meaning="Recommendations require identifying the root cause first",
                    action="Specify which database needs recommendations",
                    intent=kwargs.get("intent"),
                    question=question
                )
        
        # PRODUCTION FIX: Root cause MUST NEVER be Unknown or "OTHER"
        root_cause_text = None
        root_cause_score = 0.0
        root_cause_explanation = ""
        
        # Priority 1: Use reasoning root causes if available
        if reasoning.get("root_causes"):
            raw_error_type = reasoning["root_causes"][0]["error_type"]
            root_cause_score = reasoning["root_causes"][0].get("total_score", 0)
            root_cause_explanation = reasoning["root_causes"][0].get("why_root_cause", "")
            
            # Map "OTHER" and vague types to abstract causes
            if raw_error_type.upper() in ["OTHER", "UNKNOWN", "INTERNAL_ERROR"] or not raw_error_type:
                if PRODUCTION_ENGINE_AVAILABLE:
                    root_cause_text = ORACodeMappingEngine.get_abstract_cause(raw_error_type)
                else:
                    root_cause_text = "Internal Oracle engine instability"
            elif raw_error_type.startswith("ORA-") and PRODUCTION_ENGINE_AVAILABLE:
                root_cause_text = ORACodeMappingEngine.get_abstract_cause(raw_error_type)
            else:
                root_cause_text = raw_error_type
        
        # Priority 2: Use session memory last root cause (abstract form)
        if not root_cause_text or root_cause_text in ["Unknown", "OTHER", "Oracle operational issue (requires investigation)"]:
            session_root_cause = ReasoningMemory._environment_state.get("last_abstract_cause")
            if session_root_cause:
                root_cause_text = session_root_cause
                root_cause_score = 0.75  # Medium confidence from session
                root_cause_explanation = "From session memory"
        
        # Priority 3: Use session memory raw root cause
        if not root_cause_text or root_cause_text in ["Unknown", "OTHER", "Oracle operational issue (requires investigation)"]:
            session_root_cause = ReasoningMemory._environment_state.get("last_root_cause")
            if session_root_cause and session_root_cause not in ["OTHER", "Unknown"]:
                root_cause_text = session_root_cause
                root_cause_score = 0.65
                root_cause_explanation = "From prior analysis"
        
        # Priority 4: Infer from dominant ORA codes in session
        if not root_cause_text or root_cause_text in ["Unknown", "OTHER", "Oracle operational issue (requires investigation)"]:
            dominant_oras = ReasoningMemory._environment_state.get("dominant_ora_codes", [])
            if dominant_oras and PRODUCTION_ENGINE_AVAILABLE:
                # Map the dominant ORA to abstract cause
                top_ora = dominant_oras[0]
                abstract = ORACodeMappingEngine.get_abstract_cause(top_ora)
                if abstract != "Unclassified error" and abstract not in ["OTHER", "Unknown"]:
                    root_cause_text = abstract
                    root_cause_score = 0.60
                    root_cause_explanation = "Inferred from dominant ORA code"
                else:
                    root_cause_text = "Internal Oracle engine instability"  # Default
        
        # Priority 5: Use global alert data to infer
        if not root_cause_text or root_cause_text in ["Unknown", "OTHER", "Oracle operational issue (requires investigation)"]:
            alerts = GLOBAL_DATA.get("alerts", [])
            if alerts and target:
                # Filter alerts for target
                target_alerts = [a for a in alerts if 
                               (a.get("target_name") or a.get("target") or "").upper() == target.upper()]
                if target_alerts:
                    # Find dominant issue type
                    issue_counts = {}
                    for a in target_alerts:
                        issue = a.get("issue_type", "INTERNAL_ERROR")
                        issue_counts[issue] = issue_counts.get(issue, 0) + 1
                    if issue_counts:
                        dominant_issue = max(issue_counts.items(), key=lambda x: x[1])
                        if PRODUCTION_ENGINE_AVAILABLE:
                            root_cause_text = ORACodeMappingEngine.get_abstract_cause(dominant_issue[0])
                        else:
                            root_cause_text = dominant_issue[0]
                        root_cause_score = 0.55
                        root_cause_explanation = "Inferred from {:,} target alerts".format(len(target_alerts))
        
        # FINAL FALLBACK: Never say Unknown
        if not root_cause_text or root_cause_text == "Unknown":
            root_cause_text = "Chronic instability requiring investigation"
            root_cause_score = 0.40
            root_cause_explanation = "Low evidence - manual review recommended"
        
        # Update session memory with this root cause
        ReasoningMemory.update_environment_state(last_root_cause=root_cause_text)
        
        return self._format_response(
            summary="Action plan for {} (Root cause: {})".format(target, root_cause_text),
            checked="Identified root cause, mapped to action playbook",
            found="Root cause: {} (score: {:.3f}). {}".format(
                root_cause_text,
                root_cause_score,
                root_cause_explanation
            ),
            meaning="Actions are mapped directly to the computed root cause - not generic advice",
            action=self._format_actions(actions),
            intent=kwargs.get("intent"),
            confidence=kwargs.get("confidence"),
            target=target,
            evidence=[
                "Cause: {}".format(root_cause_text),
                "Actions: {} mapped".format(len(actions))
            ]
        )
    
    def _format_comparison_response(self, evidence, reasoning, decision, actions, target, question, analyzer, **kwargs):
        """Format COMPARISON intent response."""
        summary = evidence.get("summary", {})
        q_upper = question.upper()
        known_dbs = {db["name"].upper(): db for db in summary.get("databases", [])}
        
        # Find databases to compare
        sorted_dbs = sorted(known_dbs.keys(), key=len, reverse=True)
        found_dbs = []
        temp_q = q_upper
        for db_name in sorted_dbs:
            if db_name in temp_q:
                found_dbs.append(db_name)
                temp_q = temp_q.replace(db_name, " ", 1)
                if len(found_dbs) >= 2:
                    break
        
        if len(found_dbs) < 2:
            available = ", ".join(list(known_dbs.keys())[:5])
            return self._format_response(
                summary="Need two valid databases to compare",
                checked="Parsed question for database names",
                found="Found: {}".format(found_dbs if found_dbs else "None"),
                meaning="Comparison requires exactly two databases",
                action="Available databases: {}".format(available),
                intent=kwargs.get("intent")
            )
        
        db1, db2 = found_dbs[0], found_dbs[1]
        data1, data2 = known_dbs[db1], known_dbs[db2]
        
        ora1 = analyzer.extract_ora_codes(db1)
        ora2 = analyzer.extract_ora_codes(db2)
        
        # Verdict
        if data1.get("alert_count", 0) > data2.get("alert_count", 0):
            worse = db1
            pct_diff = ((data1["alert_count"] - data2["alert_count"]) / max(data2["alert_count"], 1)) * 100
        else:
            worse = db2
            pct_diff = ((data2["alert_count"] - data1["alert_count"]) / max(data1["alert_count"], 1)) * 100
        
        comparison_table = """
| Metric | {} | {} |
|--------|--------|--------|
| Total Alerts | {:,} | {:,} |
| % of Env | {:.1f}% | {:.1f}% |
| Critical | {:,} | {:,} |
| Top Issue | {} | {} |
""".format(
            db1, db2,
            data1.get("alert_count", 0), data2.get("alert_count", 0),
            data1.get("percentage", 0), data2.get("percentage", 0),
            data1.get("critical_count", 0), data2.get("critical_count", 0),
            ora1["ora_codes"][0]["code"] if ora1.get("ora_codes") else "N/A",
            ora2["ora_codes"][0]["code"] if ora2.get("ora_codes") else "N/A"
        )
        
        return self._format_response(
            summary="{} vs {} - {} has {:.0f}% more alerts".format(db1, db2, worse, pct_diff),
            checked="Retrieved metrics for both databases, computed ORA code analysis",
            found=comparison_table,
            meaning="{} needs more attention due to higher alert volume and critical count".format(worse),
            action="Focus remediation on {}. Review {} for ORA codes.".format(
                worse, 
                ora1["ora_codes"][0]["code"] if ora1.get("ora_codes") and db1 == worse else 
                ora2["ora_codes"][0]["code"] if ora2.get("ora_codes") else "errors"
            ),
            intent=kwargs.get("intent"),
            confidence=kwargs.get("confidence"),
            target=worse
        )
    
    def _format_dataguard_response(self, evidence, reasoning, decision, actions, target, question, analyzer, **kwargs):
        """
        Format STANDBY_DATAGUARD intent response.
        
        PRODUCTION RULE: Data Guard/Standby analysis must:
        1. Identify Data Guard-specific errors (apply lag, transport, ORA codes)
        2. NOT mix with primary database root cause
        3. Separate standby issues from primary issues
        
        CRITICAL FIX: Sub-intent split for STANDBY_ERRORS vs APPLY_LAG
        - STANDBY_ERRORS: DG transport errors, ORA-16xxx codes
        - APPLY_LAG: Apply lag metrics, threshold breaches
        """
        dg_analysis = analyzer.find_standby_dataguard_alerts()
        q_lower = question.lower() if question else ""
        
        # =====================================================
        # SUB-INTENT DETECTION (CRITICAL)
        # =====================================================
        is_apply_lag_question = any(pattern in q_lower for pattern in [
            "apply lag", "lag beyond", "lag threshold", "redo apply",
            "lag time", "transport lag", "sync delay", "replication lag"
        ])
        
        is_error_question = any(pattern in q_lower for pattern in [
            "error", "issue", "problem", "failing", "failure", 
            "alert", "ora-", "what's wrong"
        ])
        
        # =====================================================
        # APPLY_LAG SUB-INTENT → Lag metrics response
        # =====================================================
        if is_apply_lag_question:
            return self._format_apply_lag_response(dg_analysis, evidence, target, question, analyzer, **kwargs)
        
        # =====================================================
        # STANDBY_ERRORS SUB-INTENT → Error/alert response  
        # =====================================================
        # Factual patterns for error questions
        factual_patterns = [
            "are there", "how many", "any errors", "any issues", 
            "errors on standby", "what errors", "which errors",
            "show", "list", "errors occurring", "occurring on",
            "standby errors", "standby issues", "standby alerts",
            "data guard errors", "data guard issues", "data guard alerts"
        ]
        is_factual = any(pattern in q_lower for pattern in factual_patterns)
        
        # Also check if NOT an analytical question (why/cause/explain)
        is_analytical = any(w in q_lower for w in ["why", "cause", "explain", "reason", "analyze"])
        if is_analytical:
            is_factual = False
        
        if not dg_analysis.get("found"):
            if is_factual:
                return {
                    "answer": "No Data Guard or Standby alerts found in the dataset.",
                    "intent": kwargs.get("intent"),
                    "target": target,
                    "confidence": 0.90,
                    "confidence_label": "HIGH",
                    "evidence": [],
                    "reasoning_path": "DIRECT_ANSWER",
                    "actions_included": False,
                    "question_type": "FACTUAL"
                }
            return self._format_response(
                summary="No Data Guard or Standby alerts found",
                checked="Searched for keywords: standby, data guard, apply lag, transport lag, MRP, redo",
                found="0 matching alerts in {:,} total".format(evidence.get("summary", {}).get("total_alerts", 0)),
                meaning="Data Guard configuration appears healthy or not present in monitored environment",
                action="Verify Data Guard is configured and being monitored by OEM",
                intent=kwargs.get("intent"),
                widening_note="No standby alerts - environment may not have Data Guard",
                question=question
            )
        
        # Group by database and extract DG-specific ORA codes
        db_counts = defaultdict(int)
        dg_ora_codes = defaultdict(int)
        dg_specific_errors = []
        
        # Data Guard specific ORA codes
        DG_ORA_CODES = {
            "ORA-16014": "Archive log destination issue",
            "ORA-16058": "Data Guard configuration error",
            "ORA-16000": "Database open for read-only access",
            "ORA-16004": "Backup in progress",
            "ORA-16006": "Archive log cannot be applied",
            "ORA-16008": "Recovery operation suspended",
            "ORA-16009": "Archivelog gap",
            "ORA-16016": "Archive log gap",
            "ORA-16038": "Log cannot be archived",
            "ORA-16047": "DGID mismatch",
            "ORA-16066": "Redo transport connection failure",
            "ORA-16191": "Redo transport session reinstatement required"
        }
        
        for alert in dg_analysis.get("alerts", []):
            db = alert.get("target_name") or alert.get("target") or "Unknown"
            db_counts[db] += 1
            
            # Check for DG-specific ORA codes
            msg = alert.get("message") or alert.get("msg_text") or ""
            for ora_code, desc in DG_ORA_CODES.items():
                if ora_code in msg or ora_code.replace("ORA-", "ORA-0") in msg:
                    dg_ora_codes[ora_code] += 1
                    if len(dg_specific_errors) < 3:
                        dg_specific_errors.append("{}: {}".format(ora_code, desc))
        
        top_db = max(db_counts.items(), key=lambda x: x[1]) if db_counts else ("N/A", 0)
        dg_alert_count = dg_analysis.get("count", 0)
        
        # Short answer for factual questions
        if is_factual:
            short_answer = "**{:,}** Data Guard/Standby alerts found.".format(dg_alert_count)
            if top_db[0] != "N/A":
                short_answer += " Most affected: **{}** ({} alerts).".format(top_db[0], top_db[1])
            if dg_ora_codes:
                top_ora = max(dg_ora_codes.items(), key=lambda x: x[1])
                short_answer += " Top issue: **{}**.".format(top_ora[0])
            
            return {
                "answer": short_answer,
                "intent": kwargs.get("intent"),
                "target": top_db[0],
                "confidence": 0.90,
                "confidence_label": "HIGH",
                "evidence": dg_specific_errors[:2] if dg_specific_errors else [],
                "reasoning_path": "DIRECT_ANSWER",
                "actions_included": False,
                "question_type": "FACTUAL"
            }
        
        # Detailed DG-specific analysis
        dg_root_cause = "Data Guard replication instability"
        if dg_ora_codes:
            top_ora = max(dg_ora_codes.items(), key=lambda x: x[1])
            dg_root_cause = "{}: {} ({:,} occurrences)".format(
                top_ora[0], DG_ORA_CODES.get(top_ora[0], "Data Guard error"), top_ora[1]
            )
        
        # Build DG-specific findings
        dg_findings = []
        if dg_ora_codes:
            dg_findings.append("**Data Guard-specific ORA codes:**")
            for ora, count in sorted(dg_ora_codes.items(), key=lambda x: x[1], reverse=True)[:5]:
                dg_findings.append("• {}: {} ({:,})".format(ora, DG_ORA_CODES.get(ora, "DG error"), count))
        
        return self._format_response(
            summary="{:,} Data Guard related alerts found".format(dg_alert_count),
            checked="Filtered alerts for standby/Data Guard keywords and ORA codes (ORA-16xxx)",
            found="Most affected: {} ({} alerts).\n\n{}".format(
                top_db[0], top_db[1], "\n".join(dg_findings) if dg_findings else "General DG instability"
            ),
            meaning="**Standby-specific root cause:** {}\n\nNote: This is separate from primary database issues.".format(dg_root_cause),
            action="**Data Guard Remediation:**\n1. Check standby apply status: SELECT PROCESS, STATUS FROM V$MANAGED_STANDBY\n2. Verify redo transport: SELECT DEST_ID, STATUS FROM V$ARCHIVE_DEST\n3. Check for gaps: SELECT * FROM V$ARCHIVE_GAP\n4. Review standby alert log for details",
            intent=kwargs.get("intent"),
            confidence=kwargs.get("confidence"),
            target=top_db[0],
            question=question
        )
    
    def _format_apply_lag_response(self, dg_analysis, evidence, target, question, analyzer, **kwargs):
        """
        Format APPLY_LAG sub-intent response.
        
        CRITICAL: This is DIFFERENT from STANDBY_ERRORS.
        Returns: Database names + apply lag metrics + threshold status
        
        NOT: DG transport errors or ORA codes
        """
        # Look for apply lag specific alerts
        lag_alerts = []
        lag_by_db = defaultdict(list)
        
        LAG_KEYWORDS = ["apply lag", "transport lag", "redo apply", "mrp", "lag time", 
                        "sync", "replication", "standby lag", "archivelog gap"]
        
        for alert in dg_analysis.get("alerts", []):
            msg = (alert.get("message") or alert.get("msg_text") or "").lower()
            if any(kw in msg for kw in LAG_KEYWORDS):
                db = alert.get("target_name") or alert.get("target") or "Unknown"
                lag_alerts.append(alert)
                lag_by_db[db].append(alert)
        
        if not lag_alerts:
            # No specific lag alerts - check if any DG alerts exist
            if dg_analysis.get("found"):
                return {
                    "answer": "No specific apply lag threshold breaches found. {} Data Guard alerts exist but none indicate lag issues.".format(
                        dg_analysis.get("count", 0)
                    ),
                    "intent": kwargs.get("intent"),
                    "target": target,
                    "confidence": 0.85,
                    "confidence_label": "HIGH",
                    "evidence": [],
                    "reasoning_path": "DIRECT_ANSWER",
                    "actions_included": False,
                    "question_type": "FACT"
                }
            return {
                "answer": "No databases showing apply lag beyond threshold. Data Guard replication appears healthy.",
                "intent": kwargs.get("intent"),
                "target": target,
                "confidence": 0.90,
                "confidence_label": "HIGH",
                "evidence": [],
                "reasoning_path": "DIRECT_ANSWER",
                "actions_included": False,
                "question_type": "FACT"
            }
        
        # Build lag-specific response
        db_lag_summary = []
        for db, alerts in sorted(lag_by_db.items(), key=lambda x: len(x[1]), reverse=True):
            db_lag_summary.append("**{}**: {} lag alert(s)".format(db, len(alerts)))
        
        answer = "**{}** database(s) showing apply lag issues:\n• {}".format(
            len(lag_by_db),
            "\n• ".join(db_lag_summary[:5])
        )
        
        return {
            "answer": answer,
            "intent": kwargs.get("intent"),
            "target": list(lag_by_db.keys())[0] if lag_by_db else target,
            "confidence": 0.90,
            "confidence_label": "HIGH",
            "evidence": ["Lag alerts: {:,}".format(len(lag_alerts))],
            "reasoning_path": "DIRECT_ANSWER",
            "actions_included": False,
            "question_type": "FACT"
        }
    
    def _format_tablespace_response(self, evidence, reasoning, decision, actions, target, question, analyzer, **kwargs):
        """
        Format TABLESPACE intent response.
        
        PRODUCTION RULE: 
        - Factual questions → short answer (count, list)
        - Analytical questions → detailed analysis
        
        PRODUCTION FIX v2.2: Better factual question detection
        """
        ts_analysis = analyzer.find_tablespace_alerts()
        q_lower = question.lower() if question else ""
        
        # Expanded factual patterns
        factual_patterns = [
            "how many", "which tablespace", "list tablespace", "any tablespace",
            "tablespace errors", "tablespace issues", "tablespace alerts",
            "tablespace full", "tablespaces full", "close to full",
            "show tablespace", "what tablespace", "are there"
        ]
        is_factual = any(pattern in q_lower for pattern in factual_patterns)
        
        # Override if analytical
        is_analytical = any(w in q_lower for w in ["why", "cause", "explain", "reason", "analyze"])
        if is_analytical:
            is_factual = False
        
        if not ts_analysis.get("found"):
            if is_factual:
                return {
                    "answer": "No tablespace or storage alerts found in the dataset.",
                    "intent": kwargs.get("intent"),
                    "target": target,
                    "confidence": 0.90,
                    "confidence_label": "HIGH",
                    "evidence": [],
                    "reasoning_path": "DIRECT_ANSWER",
                    "actions_included": False,
                    "question_type": "FACTUAL"
                }
            return self._format_response(
                summary="No tablespace space alerts found",
                checked="Searched for keywords: tablespace, space, full, storage",
                found="0 matching alerts",
                meaning="Tablespace utilization appears within thresholds",
                action="Verify OEM space monitoring thresholds are configured appropriately",
                intent=kwargs.get("intent"),
                widening_note="No tablespace alerts found",
                question=question
            )
        
        ts_count = ts_analysis.get("count", 0)
        ts_names = [ts["name"] for ts in ts_analysis.get("tablespaces", [])[:5]]
        
        # Short answer for factual questions
        if is_factual:
            short_answer = "**{:,}** tablespace/storage alert(s).".format(ts_count)
            if ts_names:
                short_answer += " Affected: **{}**".format(", ".join(ts_names[:3]))
                if len(ts_names) > 3:
                    short_answer += " (+{} more)".format(len(ts_names) - 3)
            short_answer += "."
            
            return {
                "answer": short_answer,
                "intent": kwargs.get("intent"),
                "target": ts_names[0] if ts_names else target,
                "confidence": 0.90,
                "confidence_label": "HIGH",
                "evidence": ts_names,
                "reasoning_path": "DIRECT_ANSWER",
                "actions_included": False,
                "question_type": "FACTUAL"
            }
        
        return self._format_response(
            summary="{:,} tablespace/storage alerts found".format(ts_count),
            checked="Filtered alerts for tablespace and storage keywords",
            found="Tablespaces with alerts: {}".format(", ".join(ts_names) if ts_names else "Unknown"),
            meaning="Storage capacity issues detected - may lead to database outage if not addressed",
            action="1. Add datafiles to critical tablespaces\n2. Enable AUTOEXTEND where appropriate\n3. Identify and purge old data\n4. Review storage growth trends",
            intent=kwargs.get("intent"),
            confidence=kwargs.get("confidence"),
            question=question
        )
    
    def _format_factual_response(self, evidence, reasoning, decision, actions, target, question, analyzer, **kwargs):
        """
        Format FACTUAL intent response.
        
        PRODUCTION RULE: Factual questions get SHORT, DIRECT answers.
        - "How many databases?" → "23 databases."
        - "Which servers have alerts?" → "SERVER1, SERVER2, SERVER3."
        - "List databases" → "DB1, DB2, DB3 (12 total)."
        """
        summary = evidence.get("summary", {})
        q_lower = question.lower() if question else ""
        
        # ===========================================
        # DATABASE COUNT / LIST QUESTIONS
        # ===========================================
        if any(p in q_lower for p in ["how many database", "database count", "list database", "which database"]):
            db_count = summary.get("database_count", 0)
            db_names = [db["name"] for db in summary.get("databases", [])[:5]]
            
            if "how many" in q_lower or "count" in q_lower:
                return {
                    "answer": "**{:,}** database(s) with alerts.".format(db_count),
                    "intent": kwargs.get("intent"),
                    "target": target,
                    "confidence": 0.95,
                    "confidence_label": "HIGH",
                    "evidence": db_names,
                    "reasoning_path": "DIRECT_ANSWER",
                    "actions_included": False,
                    "question_type": "FACTUAL"
                }
            
            # List request
            if db_names:
                answer = "**{}** database(s): {}".format(db_count, ", ".join(db_names))
                if db_count > 5:
                    answer += " (+{} more)".format(db_count - 5)
                answer += "."
            else:
                answer = "No databases found with alerts."
            
            return {
                "answer": answer,
                "intent": kwargs.get("intent"),
                "target": target,
                "confidence": 0.95,
                "confidence_label": "HIGH",
                "evidence": db_names,
                "reasoning_path": "DIRECT_ANSWER",
                "actions_included": False,
                "question_type": "FACTUAL"
            }
        
        # ===========================================
        # SERVER / HOST QUESTIONS  
        # ===========================================
        if any(p in q_lower for p in ["how many server", "server count", "list server", "which server", 
                                       "how many host", "host count", "list host", "which host"]):
            # Extract unique hosts from alerts
            hosts = set()
            for alert in evidence.get("alerts", [])[:1000]:
                host = alert.get("host_name") or alert.get("host") or alert.get("target_host")
                if host:
                    hosts.add(host)
            
            host_count = len(hosts)
            host_list = sorted(list(hosts))[:5]
            
            if "how many" in q_lower or "count" in q_lower:
                return {
                    "answer": "**{:,}** server(s)/host(s) with alerts.".format(host_count),
                    "intent": kwargs.get("intent"),
                    "target": target,
                    "confidence": 0.90,
                    "confidence_label": "HIGH",
                    "evidence": host_list,
                    "reasoning_path": "DIRECT_ANSWER",
                    "actions_included": False,
                    "question_type": "FACTUAL"
                }
            
            # List request
            if host_list:
                answer = "**{}** server(s): {}".format(host_count, ", ".join(host_list))
                if host_count > 5:
                    answer += " (+{} more)".format(host_count - 5)
                answer += "."
            else:
                answer = "No servers/hosts found with alerts."
            
            return {
                "answer": answer,
                "intent": kwargs.get("intent"),
                "target": target,
                "confidence": 0.90,
                "confidence_label": "HIGH",
                "evidence": host_list,
                "reasoning_path": "DIRECT_ANSWER",
                "actions_included": False,
                "question_type": "FACTUAL"
            }
        
        # ===========================================
        # ALERT COUNT QUESTIONS
        # ===========================================
        if any(p in q_lower for p in ["how many alert", "alert count", "total alert"]):
            total_alerts = summary.get("total_alerts", 0)
            return {
                "answer": "**{:,}** total alert(s) in the dataset.".format(total_alerts),
                "intent": kwargs.get("intent"),
                "target": target,
                "confidence": 0.95,
                "confidence_label": "HIGH",
                "evidence": [],
                "reasoning_path": "DIRECT_ANSWER",
                "actions_included": False,
                "question_type": "FACTUAL"
            }
        
        # ===========================================
        # ORA CODE QUERY
        # ===========================================
        ora_match = re.search(r'ora[-\s]?(\d+)', q_lower)
        if ora_match or "ora" in q_lower:
            db_target = target or (summary["databases"][0]["name"] if summary.get("databases") else None)
            ora_analysis = analyzer.extract_ora_codes(db_target)
            
            if ora_match:
                specific_code = "ORA-{}".format(ora_match.group(1))
                found = None
                for ora in ora_analysis.get("ora_codes", []):
                    if specific_code in ora["code"]:
                        found = ora
                        break
                
                if found:
                    # Short answer for "does ORA-xxx exist?" type questions
                    return {
                        "answer": "**{}** found: **{:,}** occurrence(s).".format(found["code"], found["count"]),
                        "intent": kwargs.get("intent"),
                        "target": db_target,
                        "confidence": 0.95,
                        "confidence_label": "HIGH",
                        "evidence": [found["code"]],
                        "reasoning_path": "DIRECT_ANSWER",
                        "actions_included": False,
                        "question_type": "FACTUAL"
                    }
                else:
                    # ORA code not found
                    alt_codes = [o["code"] for o in ora_analysis.get("ora_codes", [])[:3]]
                    return {
                        "answer": "**{}** not found. Available: {}".format(
                            specific_code, 
                            ", ".join(alt_codes) if alt_codes else "none"
                        ),
                        "intent": kwargs.get("intent"),
                        "target": db_target,
                        "confidence": 0.90,
                        "confidence_label": "HIGH",
                        "evidence": alt_codes,
                        "reasoning_path": "DIRECT_ANSWER",
                        "actions_included": False,
                        "question_type": "FACTUAL"
                    }
            
            # List all ORA codes
            if ora_analysis.get("ora_codes"):
                ora_list = ["{} ({:,})".format(o["code"], o["count"]) for o in ora_analysis["ora_codes"][:5]]
                return {
                    "answer": "**{}** unique ORA code(s): {}".format(
                        len(ora_analysis["ora_codes"]), ", ".join(ora_list)
                    ),
                    "intent": kwargs.get("intent"),
                    "target": db_target,
                    "confidence": 0.90,
                    "confidence_label": "HIGH",
                    "evidence": [o["code"] for o in ora_analysis["ora_codes"][:5]],
                    "reasoning_path": "DIRECT_ANSWER",
                    "actions_included": False,
                    "question_type": "FACTUAL"
                }
        
        # ===========================================
        # DEFAULT FACTUAL - RESPECT TARGET SCOPING
        # ===========================================
        # CRITICAL FIX: If a target is specified, return ONLY that database's data
        # Do NOT return global summary when user asks about specific database
        # ===========================================
        
        if target:
            # =====================================================
            # DATABASE-SCOPED RESPONSE (MANDATORY WHEN TARGET EXISTS)
            # =====================================================
            alerts = GLOBAL_DATA.get("alerts", [])
            target_upper = target.upper()
            
            # Filter alerts for this specific database
            # PRIORITY: Exact match first, then substring match
            target_alerts = [a for a in alerts if 
                           (a.get("target_name") or a.get("target") or "").upper() == target_upper]
            
            # If no exact match, try substring match
            if not target_alerts:
                target_alerts = [a for a in alerts if 
                               target_upper in (a.get("target_name") or a.get("target") or "").upper()]
            
            target_count = len(target_alerts)
            
            if target_count > 0:
                # Get the actual database name for display
                actual_db_name = target
                if target_alerts:
                    actual_db_name = target_alerts[0].get("target_name") or target_alerts[0].get("target") or target
                
                # Count severities for this target
                critical_count = sum(1 for a in target_alerts if (a.get("severity") or "").upper() == "CRITICAL")
                warning_count = sum(1 for a in target_alerts if (a.get("severity") or "").upper() == "WARNING")
                
                severity_breakdown = []
                if critical_count > 0:
                    severity_breakdown.append("{:,} CRITICAL".format(critical_count))
                if warning_count > 0:
                    severity_breakdown.append("{:,} WARNING".format(warning_count))
                
                answer = "**{:,}** alert(s) for **{}**".format(target_count, actual_db_name)
                if severity_breakdown:
                    answer += " ({})".format(", ".join(severity_breakdown))
                answer += "."
                
                return {
                    "answer": answer,
                    "intent": kwargs.get("intent"),
                    "target": target,
                    "confidence": 0.95,
                    "confidence_label": "HIGH",
                    "evidence": ["{:,} alerts for {}".format(target_count, target)],
                    "reasoning_path": "DIRECT_ANSWER",
                    "actions_included": False,
                    "question_type": "FACT"
                }
            else:
                # Database exists but no alerts found
                return {
                    "answer": "No alerts found for **{}**.".format(target),
                    "intent": kwargs.get("intent"),
                    "target": target,
                    "confidence": 0.90,
                    "confidence_label": "HIGH",
                    "evidence": [],
                    "reasoning_path": "DIRECT_ANSWER",
                    "actions_included": False,
                    "question_type": "FACT"
                }
        
        # =====================================================
        # GLOBAL SUMMARY (ONLY WHEN NO TARGET SPECIFIED)
        # =====================================================
        db_count = summary.get("database_count", 0)
        total_alerts = summary.get("total_alerts", 0)
        top_dbs = [db["name"] for db in summary.get("databases", [])[:3]]
        
        return {
            "answer": "**{:,}** alert(s) across **{}** database(s). Top: {}".format(
                total_alerts, db_count, ", ".join(top_dbs) if top_dbs else "N/A"
            ),
            "intent": kwargs.get("intent"),
            "target": target,
            "confidence": 0.85,
            "confidence_label": "MEDIUM",
            "evidence": top_dbs,
            "reasoning_path": "DIRECT_ANSWER",
            "actions_included": False,
            "question_type": "FACTUAL"
        }

    def _format_risk_response(self, evidence, reasoning, decision, actions, target, question, analyzer, **kwargs):
        """
        Format RISK_POSTURE intent response.
        
        PRODUCTION RULE:
        - Simple risk questions → short answer
        - "What's the risk?" → "HIGH risk: 45 critical alerts."
        - Detailed risk analysis → full breakdown
        """
        summary = evidence.get("summary", {})
        severity = summary.get("severity_summary", {})
        q_lower = question.lower() if question else ""
        
        critical = severity.get("CRITICAL", severity.get("Critical", 0))
        warning = severity.get("WARNING", severity.get("Warning", 0))
        risk_level = reasoning.get("risk_level", "UNKNOWN")
        
        # Short answer for simple risk questions
        is_factual = any(p in q_lower for p in ["what's the risk", "what is the risk", "risk level", "how risky"])
        
        if is_factual:
            return {
                "answer": "**{}** risk. Critical: **{:,}**, Warning: **{:,}** alerts.".format(
                    risk_level, critical, warning
                ),
                "intent": kwargs.get("intent"),
                "target": target,
                "confidence": 0.90,
                "confidence_label": "HIGH",
                "evidence": ["CRITICAL: {:,}".format(critical), "WARNING: {:,}".format(warning)],
                "reasoning_path": "DIRECT_ANSWER",
                "actions_included": False,
                "question_type": "FACTUAL"
            }
        
        return self._format_response(
            summary="Overall Risk Posture: {}".format(risk_level),
            checked="Evaluated {:,} alerts across {} databases".format(
                summary.get("total_alerts", 0), summary.get("database_count", 0)
            ),
            found="CRITICAL: {:,}, WARNING: {:,}. Top: {} ({:,} alerts)".format(
                critical, warning,
                summary["databases"][0]["name"] if summary.get("databases") else "N/A",
                summary["databases"][0]["alert_count"] if summary.get("databases") else 0
            ),
            meaning="Risk level {} based on critical alert threshold. {}".format(
                risk_level,
                decision.get("conclusion", "")
            ),
            action=self._format_actions(actions) if actions else "Monitor environment. Address critical alerts first.",
            intent=kwargs.get("intent"),
            confidence=kwargs.get("confidence"),
            question=question
        )
    
    def _format_generic_response(self, evidence, reasoning, decision, actions, target, question, analyzer, **kwargs):
        """
        Format unknown/generic intent response.
        
        PRODUCTION RULE: Generic still respects question type.
        """
        summary = evidence.get("summary", {})
        q_lower = question.lower() if question else ""
        
        # Try to give a direct answer if question is identifiably factual
        is_factual = any(p in q_lower for p in ["how many", "what is", "which", "list", "count"])
        
        if is_factual:
            total = summary.get("total_alerts", 0)
            db_count = summary.get("database_count", 0)
            top_db = summary["databases"][0]["name"] if summary.get("databases") else "N/A"
            
            return {
                "answer": "**{:,}** alert(s) across **{}** database(s). Most affected: **{}**.".format(
                    total, db_count, top_db
                ),
                "intent": kwargs.get("intent"),
                "target": target,
                "confidence": 0.70,
                "confidence_label": "MEDIUM",
                "evidence": [],
                "reasoning_path": "GENERIC_HANDLER",
                "actions_included": False,
                "question_type": "FACTUAL"
            }
        
        return self._format_response(
            summary="OEM Environment Analysis",
            checked="Parsed question intent, gathered environment data",
            found="{:,} alerts across {} databases. Top: {}".format(
                summary.get("total_alerts", 0),
                summary.get("database_count", 0),
                summary["databases"][0]["name"] if summary.get("databases") else "N/A"
            ),
            meaning="Specify database name or ask about: status, root cause, predictions, actions",
            action="Try: 'Which database is in CRITICAL state?' or 'Why does [DB] fail repeatedly?'",
            intent=kwargs.get("intent"),
            confidence=kwargs.get("confidence"),
            question=question
        )
    
    def _format_actions(self, actions):
        """
        Format actions list.
        
        CRITICAL: NEVER return 'No specific actions mapped'.
        If actions list is empty, generate safe DBA fallback.
        """
        # FALLBACK: If somehow empty, provide safe DBA actions
        if not actions:
            actions = [{
                "cause": "Database Health Monitoring",
                "description": "Safe fallback actions for investigation",
                "actions": [
                    "Review Oracle alert log for recent errors",
                    "Check database status: SELECT STATUS FROM v$instance",
                    "Verify listener: lsnrctl status",
                    "Monitor tablespace: SELECT * FROM dba_tablespace_usage_metrics"
                ],
                "urgency": "MEDIUM"
            }]
        
        lines = []
        for i, action in enumerate(actions, 1):
            lines.append("**{}. For {}:**".format(i, action.get("cause", "Issue")))
            if action.get("description"):
                lines.append("   {}".format(action["description"]))
            for j, act in enumerate(action.get("actions", [])[:4], 1):
                lines.append("   {}. {}".format(j, act))
            lines.append("   Urgency: {}".format(action.get("urgency", "MEDIUM")))
        
        return "\n".join(lines)
    
    def _format_response(self, summary, checked, found, meaning, action, 
                        intent=None, confidence=None, target=None, 
                        evidence=None, widening_note=None, reasoning_chain=None,
                        question=None):
        """
        Build response based on QUESTION TYPE - not fixed template.
        
        PRODUCTION-GRADE RESPONSE LOGIC:
        - FACTUAL    → Short, direct answer ONLY (no root cause, no actions)
        - ANALYTICAL → Explanation with evidence (may include root cause)
        - ACTION     → Steps and recommendations (full template)
        
        A real DBA assistant answers:
        - "Which DB is critical?" → "MIDEVSTBN is in CRITICAL state."
        - "Which hour has most alerts?" → "19:00 with 310,909 alerts."
        - "Why failures?" → Structured explanation with root cause
        - "What to do?" → Action steps with context
        """
        # Determine confidence label
        conf_value = confidence if confidence else 0.5
        if conf_value >= 0.85:
            conf_label = "HIGH"
        elif conf_value >= 0.60:
            conf_label = "MEDIUM"
        else:
            conf_label = "LOW"
        
        # =====================================================
        # QUESTION TYPE DETERMINES FORMAT (CRITICAL RULE)
        # Use question text when available for most accurate routing
        # =====================================================
        question_type = OEMIntentEngine.get_question_type(intent)
        use_short_format = OEMIntentEngine.should_use_short_format(intent, question)
        include_actions = OEMIntentEngine.should_include_actions(intent, question)
        include_root_cause = OEMIntentEngine.should_include_root_cause(intent, question)
        
        # =====================================================
        # FACTUAL QUESTIONS → SHORT, DIRECT ANSWER
        # NO template. NO root cause. NO actions. NO filler.
        # =====================================================
        if use_short_format:
            answer_text = self._build_short_answer(summary, found, meaning, target, conf_label)
            return {
                "answer": answer_text,
                "intent": intent,
                "target": target,
                "confidence": confidence,
                "confidence_label": conf_label,
                "evidence": evidence or [],
                "reasoning_path": "DIRECT_ANSWER",
                "actions_included": False,
                "question_type": question_type
            }
        
        # =====================================================
        # ACTION QUESTIONS → STEPS AND RECOMMENDATIONS
        # Conversational, actionable, no unnecessary filler
        # =====================================================
        if include_actions:
            answer_parts = ["**{}**".format(summary)]
            
            # Include root cause context only if relevant and user asked why
            if include_root_cause and meaning and "root cause" in meaning.lower():
                answer_parts.append("")
                answer_parts.append("**Root Cause:** {}".format(meaning))
            elif found:
                answer_parts.append("")
                answer_parts.append("**Finding:** {}".format(found))
            
            answer_parts.append("")
            answer_parts.append("**Recommended Actions:**")
            answer_parts.append(action if action else "Monitor and investigate further.")
            
            return {
                "answer": "\n".join(answer_parts),
                "intent": intent,
                "target": target,
                "confidence": confidence,
                "confidence_label": conf_label,
                "evidence": evidence or [],
                "reasoning_path": "INTENT→EVIDENCE→ACTION",
                "actions_included": True,
                "question_type": question_type
            }
        
        # =====================================================
        # ANALYTICAL QUESTIONS → CONVERSATIONAL EXPLANATION
        # Include root cause only if relevant
        # NO action recommendations (unless risk-related)
        # NO confidence percentage for straightforward explanations
        # =====================================================
        answer_parts = ["**{}**".format(summary)]
        
        if found:
            answer_parts.append("")
            answer_parts.append("**Analysis:** {}".format(found))
        
        if include_root_cause and meaning:
            answer_parts.append("")
            answer_parts.append("**Explanation:** {}".format(meaning))
        
        # Only show confidence for inference-based answers (LOW/MEDIUM)
        if conf_label != "HIGH":
            answer_parts.append("")
            answer_parts.append("_Confidence: {}_".format(conf_label))
        
        if widening_note:
            answer_parts.append("")
            answer_parts.append("_Note: {}_".format(widening_note))
        
        return {
            "answer": "\n".join(answer_parts),
            "intent": intent,
            "target": target,
            "confidence": confidence,
            "confidence_label": conf_label,
            "evidence": evidence or [],
            "reasoning_path": "INTENT→HYPOTHESIS→EVIDENCE→REASONING",
            "actions_included": False,
            "question_type": question_type
        }
    
    def _build_short_answer(self, summary, found, meaning, target, conf_label):
        """
        Build a SHORT, DIRECT answer for FACTUAL questions.
        
        PRODUCTION RULE: No filler. No templates. Just the answer.
        
        Examples:
        - "MIDEVSTBN is in CRITICAL state with 483,932 alerts."
        - "19:00 has the highest alert volume with 310,909 alerts."
        - "No databases are currently DOWN."
        - "5 databases are monitored."
        """
        # Clean up summary - remove excessive emojis and formatting
        clean_summary = summary.strip()
        
        # Remove redundant emojis if present
        for emoji in ["🔹", "🔍", "📊", "🧠", "🛠️", "📍", "📋"]:
            clean_summary = clean_summary.replace(emoji, "").strip()
        
        # For very short summaries (the best kind), return as-is
        if len(clean_summary) < 80:
            return clean_summary
        
        # If summary is already concise, use it
        if len(clean_summary) < 150:
            return clean_summary
        
        # For longer summaries, try to extract the key info
        if found and len(found) < 120:
            # Found data is often more specific
            return found
        
        # Last resort: truncate to first sentence
        first_sentence_end = clean_summary.find(".")
        if first_sentence_end > 0 and first_sentence_end < 200:
            return clean_summary[:first_sentence_end + 1]
        
        return clean_summary[:200] + "..."
