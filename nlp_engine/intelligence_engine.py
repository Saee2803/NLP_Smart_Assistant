"""
OEM Intelligence Engine - 8 Logic Modules for DBA-Level Reasoning

This engine transforms the system from:
    Intent → Query → Print result
into:
    Intent → Hypothesis → Evidence → Decision → Action

Modules:
1. Anti-False-Zero (Widening Logic)
2. Current vs Historical Awareness
3. Temporal Intelligence
4. Root Cause Scoring Engine
5. Metric-Alert Correlation
6. Action Mapping Engine
7. Reasoning Memory (Stateful Context)
8. Standard Answer Pipeline
"""

from datetime import datetime, timedelta
from collections import Counter, defaultdict
from typing import Dict, List, Any, Optional, Tuple
import re


# ============================================================
# MODULE 7: REASONING MEMORY (Stateful Context)
# ============================================================
class ReasoningMemory:
    """
    Stores conversation context for follow-up questions.
    
    Purpose: Enable stateful reasoning across questions
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        self.last_target = None
        self.last_root_cause = None
        self.last_intent = None
        self.last_findings = {}
        self.last_time_range = None
        self.session_history = []
    
    def update(self, **kwargs):
        """Update memory with new findings."""
        if kwargs.get("target"):
            self.last_target = kwargs["target"]
        if kwargs.get("root_cause"):
            self.last_root_cause = kwargs["root_cause"]
        if kwargs.get("intent"):
            self.last_intent = kwargs["intent"]
        if kwargs.get("findings"):
            self.last_findings = kwargs["findings"]
        if kwargs.get("time_range"):
            self.last_time_range = kwargs["time_range"]
        
        # Store in history
        self.session_history.append({
            "timestamp": datetime.now().isoformat(),
            **kwargs
        })
        
        # Keep only last 10 interactions
        if len(self.session_history) > 10:
            self.session_history = self.session_history[-10:]
    
    def get_context(self):
        """Get current context for follow-up reasoning."""
        return {
            "last_target": self.last_target,
            "last_root_cause": self.last_root_cause,
            "last_intent": self.last_intent,
            "last_findings": self.last_findings,
            "last_time_range": self.last_time_range
        }
    
    def reset(self):
        """Reset memory for new session."""
        self._initialize()


# Global memory instance
REASONING_MEMORY = ReasoningMemory()


# ============================================================
# MODULE 1: ANTI-FALSE-ZERO (Widening Logic)
# ============================================================
class AntiFalseZero:
    """
    Prevents false "no data found" responses by widening search criteria.
    
    Purpose: When strict filter returns 0, relax and report alternatives.
    
    Algorithm:
    1. Execute strict query
    2. If 0 results → widen step by step
    3. Track what was checked
    4. Return alternative findings
    """
    
    @staticmethod
    def widen_target_search(target: str, alerts: List[Dict]) -> Tuple[str, List[Dict], str]:
        """
        Find alerts for a target, widening search if needed.
        
        Returns: (matched_target, matching_alerts, search_explanation)
        """
        if not target or not alerts:
            return None, [], "No target or alerts provided"
        
        target_upper = target.upper().strip()
        search_steps = []
        
        # Step 1: Exact match
        exact_matches = []
        for a in alerts:
            t = (a.get("target") or a.get("target_name") or "").upper()
            if t == target_upper:
                exact_matches.append(a)
        
        if exact_matches:
            return target_upper, exact_matches, "Exact match found"
        search_steps.append("exact match: 0")
        
        # Step 2: Contains match - DISABLED to avoid MIDEVSTB matching MIDEVSTBN
        # Only use this for TYPO correction, not substring matching
        contains_matches = []
        matched_target = None
        for a in alerts:
            t = (a.get("target") or a.get("target_name") or "").upper()
            # STRICT: Only match if lengths are similar (typo correction, not substring)
            if len(target_upper) > 0 and len(t) > 0:
                if len(t) == len(target_upper) and t != target_upper:
                    # Same length, different - might be typo
                    matches = sum(1 for c1, c2 in zip(target_upper, t) if c1 == c2)
                    if matches / len(target_upper) >= 0.85:  # 85% character match
                        contains_matches.append(a)
                        matched_target = t
        
        if contains_matches:
            return matched_target, contains_matches, "Typo correction: searched '{}', matched '{}'".format(target_upper, matched_target)
        search_steps.append("contains match: 0")
        
        # Step 3: Fuzzy match (handle typos like MIDDEVSTBN vs MIDEVSTBN)
        def similarity(s1, s2):
            """Simple character-based similarity."""
            if not s1 or not s2:
                return 0
            s1, s2 = s1.upper(), s2.upper()
            matches = sum(1 for c in s1 if c in s2)
            return matches / max(len(s1), len(s2))
        
        best_match = None
        best_score = 0
        best_target_name = None
        
        known_targets = set()
        for a in alerts:
            t = (a.get("target") or a.get("target_name") or "").upper()
            if t:
                known_targets.add(t)
        
        for known in known_targets:
            score = similarity(target_upper, known)
            if score > best_score and score > 0.7:  # 70% threshold
                best_score = score
                best_target_name = known
        
        if best_target_name:
            fuzzy_matches = [a for a in alerts 
                          if (a.get("target") or a.get("target_name") or "").upper() == best_target_name]
            return best_target_name, fuzzy_matches, "Fuzzy match: '{}' interpreted as '{}' ({}% similar)".format(
                target_upper, best_target_name, int(best_score * 100))
        search_steps.append("fuzzy match: 0")
        
        # Step 4: Return all alerts with available targets as alternative
        all_targets = Counter()
        for a in alerts:
            t = (a.get("target") or a.get("target_name") or "").upper()
            if t:
                all_targets[t] += 1
        
        explanation = "No alerts for '{}'. Checked: {}. Available databases: {}".format(
            target_upper,
            ", ".join(search_steps),
            ", ".join("{} ({})".format(t, c) for t, c in all_targets.most_common(5))
        )
        
        return None, [], explanation
    
    @staticmethod
    def widen_condition_search(alerts: List[Dict], 
                               primary_condition: str,
                               field: str = "alert_state") -> Tuple[List[Dict], str]:
        """
        Search for alerts matching a condition, widening if needed.
        
        Example: No STOP alerts → but 483,932 INTERNAL_ERROR alerts exist
        """
        if not alerts:
            return [], "No alerts available"
        
        primary_upper = primary_condition.upper()
        search_report = []
        
        # Step 1: Exact condition match
        exact = [a for a in alerts if (a.get(field) or "").upper() == primary_upper]
        if exact:
            return exact, "Found {} {} alerts".format(len(exact), primary_upper)
        search_report.append("No {} alerts".format(primary_upper))
        
        # Step 2: Contains match
        contains = [a for a in alerts if primary_upper in (a.get(field) or "").upper()]
        if contains:
            return contains, "Found {} alerts containing '{}'".format(len(contains), primary_upper)
        
        # Step 3: Report what DOES exist
        field_counts = Counter()
        for a in alerts:
            val = (a.get(field) or a.get("issue_type") or a.get("alert_type") or "UNKNOWN").upper()
            field_counts[val] += 1
        
        alternatives = []
        for val, count in field_counts.most_common(5):
            alternatives.append("{}: {:,}".format(val, count))
        
        explanation = "{}. However, found: {}".format(
            search_report[0] if search_report else "No exact match",
            ", ".join(alternatives)
        )
        
        return [], explanation
    
    @staticmethod
    def widen_time_search(alerts: List[Dict],
                         hour_start: int,
                         hour_end: int) -> Tuple[List[Dict], str]:
        """
        Search alerts in time range, widening if needed.
        """
        if not alerts:
            return [], "No alerts available"
        
        # Parse times from alerts
        time_filtered = []
        all_hours = Counter()
        
        for a in alerts:
            time_str = a.get("alert_time") or a.get("time") or a.get("first_seen") or ""
            if not time_str:
                continue
            
            try:
                if isinstance(time_str, str):
                    # Try multiple formats
                    for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d-%b-%y %I.%M.%S.%f %p"]:
                        try:
                            dt = datetime.strptime(time_str[:19], fmt[:len(time_str[:19])+2])
                            break
                        except:
                            continue
                    else:
                        # Try to extract hour directly
                        hour_match = re.search(r'(\d{1,2})[:.](\d{2})', time_str)
                        if hour_match:
                            dt = datetime.now().replace(hour=int(hour_match.group(1)))
                        else:
                            continue
                else:
                    continue
                
                all_hours[dt.hour] += 1
                
                if hour_start <= dt.hour <= hour_end:
                    time_filtered.append(a)
                elif hour_start > hour_end:  # Overnight range like 22:00 - 03:00
                    if dt.hour >= hour_start or dt.hour <= hour_end:
                        time_filtered.append(a)
            except:
                continue
        
        if time_filtered:
            return time_filtered, "Found {:,} alerts between {:02d}:00 - {:02d}:00".format(
                len(time_filtered), hour_start, hour_end)
        
        # Report peak hours instead
        if all_hours:
            peak_hours = all_hours.most_common(3)
            explanation = "No alerts between {:02d}:00 - {:02d}:00. Peak hours: {}".format(
                hour_start, hour_end,
                ", ".join("{:02d}:00 ({:,} alerts)".format(h, c) for h, c in peak_hours)
            )
            return [], explanation
        
        return [], "No timestamp data available in alerts"


# ============================================================
# MODULE 2: CURRENT vs HISTORICAL AWARENESS
# ============================================================
class TemporalAwareness:
    """
    Distinguishes between "current" and "historical" queries.
    
    Rule: "Currently" = most recent observed state in data
    """
    
    @staticmethod
    def get_current_state(alerts: List[Dict], target: str = None) -> Dict:
        """
        Get the most recent state (treating dataset as "current").
        
        Returns: {
            "most_recent_critical": alert,
            "most_recent_timestamp": datetime,
            "active_issues": [issues],
            "state_assessment": str
        }
        """
        if not alerts:
            return {"state_assessment": "No data available"}
        
        # Filter by target if provided
        if target:
            target_upper = target.upper()
            alerts = [a for a in alerts 
                     if target_upper in (a.get("target") or a.get("target_name") or "").upper()]
        
        if not alerts:
            return {"state_assessment": "No alerts for specified target"}
        
        # Find most recent alerts
        def parse_time(a):
            time_str = a.get("alert_time") or a.get("time") or a.get("first_seen") or ""
            if not time_str:
                return datetime.min
            try:
                for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d-%b-%y %I.%M.%S.%f %p"]:
                    try:
                        return datetime.strptime(str(time_str)[:19], fmt[:21])
                    except:
                        continue
                return datetime.min
            except:
                return datetime.min
        
        sorted_alerts = sorted(alerts, key=parse_time, reverse=True)
        
        # Get most recent
        most_recent = sorted_alerts[0] if sorted_alerts else None
        most_recent_time = parse_time(most_recent) if most_recent else None
        
        # Get recent critical alerts
        critical_alerts = [a for a in sorted_alerts[:1000] 
                         if (a.get("severity") or a.get("alert_state") or "").upper() in ["CRITICAL", "CLEAR"]]
        
        # Determine current state
        severity_counts = Counter()
        for a in sorted_alerts[:100]:  # Look at 100 most recent
            sev = (a.get("severity") or a.get("alert_state") or "INFO").upper()
            severity_counts[sev] += 1
        
        if severity_counts.get("CRITICAL", 0) > 50:
            state = "CRITICAL - High volume of recent critical alerts"
        elif severity_counts.get("CRITICAL", 0) > 10:
            state = "WARNING - Elevated critical alert activity"
        else:
            state = "STABLE - Normal alert levels"
        
        return {
            "most_recent_alert": most_recent,
            "most_recent_timestamp": most_recent_time,
            "recent_severity_distribution": dict(severity_counts),
            "state_assessment": state,
            "total_analyzed": len(sorted_alerts[:100])
        }
    
    @staticmethod
    def is_current_query(question: str) -> bool:
        """Detect if user is asking about current state."""
        current_keywords = [
            "current", "currently", "right now", "now", "at the moment",
            "presently", "today", "active", "ongoing", "live"
        ]
        q_lower = question.lower()
        return any(kw in q_lower for kw in current_keywords)
    
    @staticmethod
    def get_most_recent_by_condition(alerts: List[Dict], 
                                     condition_field: str,
                                     condition_value: str) -> Optional[Dict]:
        """Get most recent alert matching a condition."""
        matching = [a for a in alerts 
                   if condition_value.upper() in (a.get(condition_field) or "").upper()]
        
        if not matching:
            return None
        
        def parse_time(a):
            time_str = a.get("alert_time") or a.get("time") or ""
            try:
                return datetime.strptime(str(time_str)[:19], "%Y-%m-%dT%H:%M:%S")
            except:
                return datetime.min
        
        return max(matching, key=parse_time)


# ============================================================
# MODULE 3: TEMPORAL INTELLIGENCE
# ============================================================
class TemporalIntelligence:
    """
    Reasons over time patterns, not just filters.
    
    Computes:
    - Hour-of-day distribution
    - Repeating time windows
    - Night vs day ratios
    - Peak failure windows
    """
    
    @staticmethod
    def analyze_time_patterns(alerts: List[Dict]) -> Dict:
        """
        Comprehensive temporal analysis.
        
        Returns: {
            "hourly_distribution": {hour: count},
            "peak_hour": (hour, count),
            "night_ratio": float,
            "pattern_insight": str,
            "day_of_week": {day: count}
        }
        """
        if not alerts:
            return {"pattern_insight": "No data for temporal analysis"}
        
        hourly = Counter()
        daily = Counter()
        night_count = 0  # 18:00 - 06:00
        day_count = 0    # 06:00 - 18:00
        
        for a in alerts:
            time_str = a.get("alert_time") or a.get("time") or a.get("first_seen") or ""
            if not time_str:
                continue
            
            try:
                dt = None
                for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d-%b-%y %I.%M.%S.%f %p"]:
                    try:
                        dt = datetime.strptime(str(time_str)[:19], fmt[:21])
                        break
                    except:
                        continue
                
                if dt:
                    hourly[dt.hour] += 1
                    daily[dt.strftime("%A")] += 1
                    
                    if dt.hour >= 18 or dt.hour < 6:
                        night_count += 1
                    else:
                        day_count += 1
            except:
                continue
        
        total_with_time = night_count + day_count
        
        # Find peak hour
        peak_hour = hourly.most_common(1)[0] if hourly else (0, 0)
        
        # Calculate night ratio
        night_ratio = night_count / total_with_time if total_with_time > 0 else 0
        
        # Generate insight
        if night_ratio > 0.6:
            insight = "Evening/Night workload correlation: {:.1%} of alerts occur 18:00-06:00. Likely batch jobs or maintenance windows.".format(night_ratio)
        elif night_ratio < 0.3:
            insight = "Daytime workload correlation: {:.1%} of alerts occur during business hours 06:00-18:00. Likely user-driven activity.".format(1 - night_ratio)
        else:
            insight = "Balanced distribution across day/night. Peak activity at {:02d}:00.".format(peak_hour[0])
        
        # Find repeating patterns
        consecutive_peaks = []
        sorted_hours = sorted(hourly.items(), key=lambda x: x[1], reverse=True)
        if len(sorted_hours) >= 2:
            top_hours = [h for h, c in sorted_hours[:5]]
            # Check if peaks are consecutive
            for i in range(len(top_hours) - 1):
                if abs(top_hours[i] - top_hours[i+1]) <= 2:
                    consecutive_peaks.append((top_hours[i], top_hours[i+1]))
        
        return {
            "hourly_distribution": dict(hourly),
            "peak_hour": peak_hour,
            "peak_hours_top5": sorted_hours[:5],
            "night_ratio": night_ratio,
            "day_ratio": 1 - night_ratio,
            "pattern_insight": insight,
            "day_of_week": dict(daily),
            "consecutive_peak_windows": consecutive_peaks,
            "total_with_timestamps": total_with_time
        }
    
    @staticmethod
    def find_failure_windows(alerts: List[Dict], 
                            severity_filter: str = "CRITICAL") -> List[Dict]:
        """
        Identify recurring failure time windows.
        
        Returns windows where failures cluster.
        """
        hourly_severity = defaultdict(Counter)
        
        for a in alerts:
            time_str = a.get("alert_time") or a.get("time") or ""
            severity = (a.get("severity") or a.get("alert_state") or "").upper()
            
            if severity_filter.upper() not in severity:
                continue
            
            try:
                dt = datetime.strptime(str(time_str)[:19], "%Y-%m-%dT%H:%M:%S")
                hourly_severity[dt.hour][severity] += 1
            except:
                continue
        
        # Find hours with high critical concentration
        failure_windows = []
        for hour, counts in hourly_severity.items():
            critical_count = counts.get(severity_filter.upper(), 0)
            if critical_count > 100:  # Threshold
                failure_windows.append({
                    "hour": hour,
                    "count": critical_count,
                    "risk": "HIGH" if critical_count > 1000 else "MEDIUM"
                })
        
        return sorted(failure_windows, key=lambda x: x["count"], reverse=True)


# ============================================================
# MODULE 4: ROOT CAUSE SCORING ENGINE
# ============================================================
class RootCauseScorer:
    """
    Scores potential root causes instead of just classifying.
    
    Formula:
    cause_score = frequency_weight + recency_weight + 
                  metric_correlation_weight + time_pattern_weight
    """
    
    # Weights for scoring
    FREQUENCY_WEIGHT = 0.35
    RECENCY_WEIGHT = 0.25
    PATTERN_WEIGHT = 0.25
    SEVERITY_WEIGHT = 0.15
    
    @staticmethod
    def score_root_causes(alerts: List[Dict], target: str = None) -> List[Dict]:
        """
        Score all potential root causes for a target.
        
        Returns: Sorted list of {cause, score, evidence}
        """
        if not alerts:
            return []
        
        # Filter by target if provided - STRICT EXACT MATCHING
        if target:
            target_upper = target.upper()
            alerts = [a for a in alerts 
                     if (a.get("target") or a.get("target_name") or "").upper() == target_upper]
        
        if not alerts:
            return []
        
        # Count causes
        cause_counts = Counter()
        cause_severity = defaultdict(Counter)
        cause_times = defaultdict(list)
        
        now = datetime.now()
        
        for a in alerts:
            # Get cause category
            cause = RootCauseScorer._categorize_cause(a)
            cause_counts[cause] += 1
            
            # Track severity
            sev = (a.get("severity") or a.get("alert_state") or "INFO").upper()
            cause_severity[cause][sev] += 1
            
            # Track time for recency
            time_str = a.get("alert_time") or a.get("time") or ""
            try:
                dt = datetime.strptime(str(time_str)[:19], "%Y-%m-%dT%H:%M:%S")
                cause_times[cause].append(dt)
            except:
                pass
        
        total_alerts = len(alerts)
        
        # Score each cause
        scored_causes = []
        for cause, count in cause_counts.items():
            # Frequency score (0-1)
            freq_score = count / total_alerts
            
            # Recency score (0-1) - based on most recent occurrence
            times = cause_times.get(cause, [])
            if times:
                most_recent = max(times)
                days_ago = (now - most_recent).days
                recency_score = max(0, 1 - (days_ago / 365))  # Decay over a year
            else:
                recency_score = 0.5  # Neutral if no time data
            
            # Severity score (0-1)
            sev_counts = cause_severity[cause]
            critical_ratio = sev_counts.get("CRITICAL", 0) / count if count > 0 else 0
            severity_score = critical_ratio
            
            # Pattern score - check for time clustering
            if len(times) > 10:
                hours = [t.hour for t in times]
                hour_counts = Counter(hours)
                max_hour_concentration = max(hour_counts.values()) / len(times)
                pattern_score = max_hour_concentration  # Higher if clustered
            else:
                pattern_score = 0.3  # Neutral
            
            # Combined score
            total_score = (
                RootCauseScorer.FREQUENCY_WEIGHT * freq_score +
                RootCauseScorer.RECENCY_WEIGHT * recency_score +
                RootCauseScorer.PATTERN_WEIGHT * pattern_score +
                RootCauseScorer.SEVERITY_WEIGHT * severity_score
            )
            
            scored_causes.append({
                "cause": cause,
                "score": round(total_score, 3),
                "count": count,
                "percentage": round(freq_score * 100, 1),
                "critical_ratio": round(critical_ratio * 100, 1),
                "evidence": {
                    "frequency_contribution": round(freq_score * RootCauseScorer.FREQUENCY_WEIGHT, 3),
                    "recency_contribution": round(recency_score * RootCauseScorer.RECENCY_WEIGHT, 3),
                    "pattern_contribution": round(pattern_score * RootCauseScorer.PATTERN_WEIGHT, 3),
                    "severity_contribution": round(severity_score * RootCauseScorer.SEVERITY_WEIGHT, 3)
                }
            })
        
        return sorted(scored_causes, key=lambda x: x["score"], reverse=True)
    
    @staticmethod
    def _categorize_cause(alert: Dict) -> str:
        """Categorize an alert into a root cause category."""
        message = (alert.get("message") or alert.get("alert_message") or "").upper()
        issue_type = (alert.get("issue_type") or alert.get("alert_type") or "").upper()
        
        # Check for ORA codes
        ora_match = re.search(r'ORA-(\d+)', message)
        if ora_match:
            ora_code = ora_match.group(1)
            if ora_code in ["600", "7445"]:
                return "INTERNAL_DATABASE_ERROR"
            elif ora_code.startswith("12"):
                return "NETWORK_CONNECTIVITY"
            elif ora_code in ["1555", "30036"]:
                return "UNDO_TABLESPACE"
            elif ora_code in ["1652", "1653", "1654"]:
                return "TABLESPACE_FULL"
            elif ora_code in ["4031"]:
                return "SHARED_POOL_MEMORY"
        
        # Check message patterns
        if "DATA GUARD" in message or "STANDBY" in message or "APPLY LAG" in message:
            return "DATAGUARD_REPLICATION"
        elif "TABLESPACE" in message or "STORAGE" in message or "SPACE" in message:
            return "STORAGE_CAPACITY"
        elif "MEMORY" in message or "SGA" in message or "PGA" in message:
            return "MEMORY_PRESSURE"
        elif "CPU" in message or "LOAD" in message:
            return "CPU_RESOURCE"
        elif "LISTENER" in message or "TNS" in message or "CONNECTION" in message:
            return "NETWORK_CONNECTIVITY"
        elif "INTERNAL" in issue_type or "INTERNAL" in message:
            return "INTERNAL_DATABASE_ERROR"
        elif "DOWN" in issue_type or "STOP" in message:
            return "DATABASE_UNAVAILABLE"
        
        return "OTHER_OPERATIONAL"
    
    @staticmethod
    def get_primary_root_cause(alerts: List[Dict], target: str = None) -> Dict:
        """Get the highest-scored root cause with full analysis."""
        scored = RootCauseScorer.score_root_causes(alerts, target)
        
        if not scored:
            return {"cause": "UNKNOWN", "score": 0, "analysis": "Insufficient data"}
        
        primary = scored[0]
        
        # Add detailed analysis
        primary["analysis"] = RootCauseScorer._get_cause_analysis(primary["cause"])
        primary["is_confident"] = primary["score"] > 0.3
        primary["alternatives"] = scored[1:3] if len(scored) > 1 else []
        
        return primary
    
    @staticmethod
    def _get_cause_analysis(cause: str) -> str:
        """Get DBA-level analysis for a cause."""
        analyses = {
            "INTERNAL_DATABASE_ERROR": "ORA-600/ORA-7445 errors indicate internal Oracle bugs or memory corruption. Check patch levels and shared pool configuration.",
            "NETWORK_CONNECTIVITY": "TNS/listener errors suggest network instability or listener configuration issues. Verify TNS entries and firewall rules.",
            "DATAGUARD_REPLICATION": "Data Guard issues indicate standby synchronization problems. Check apply lag, network bandwidth, and redo transport.",
            "STORAGE_CAPACITY": "Storage alerts indicate approaching capacity limits. Review tablespace autoextend and datafile sizing.",
            "MEMORY_PRESSURE": "Memory pressure from SGA/PGA exhaustion. Review memory_target, sga_target, and pga_aggregate_target.",
            "CPU_RESOURCE": "High CPU indicates resource contention. Check for runaway queries or insufficient CPU allocation.",
            "DATABASE_UNAVAILABLE": "Database down events indicate critical failures. Check alert logs, listener status, and background processes.",
            "UNDO_TABLESPACE": "Undo tablespace issues cause transaction failures. Check undo_retention and undo tablespace sizing.",
            "TABLESPACE_FULL": "Tablespace capacity exhausted. Add datafiles or enable autoextend.",
            "SHARED_POOL_MEMORY": "Shared pool exhaustion (ORA-4031). Check shared_pool_size and cursor management.",
            "OTHER_OPERATIONAL": "Generic operational alerts. Review specific alert messages for categorization."
        }
        return analyses.get(cause, "Review alert details for specific diagnosis.")


# ============================================================
# MODULE 5: METRIC-ALERT CORRELATION
# ============================================================
class MetricAlertCorrelator:
    """
    Correlates alerts with metrics to find resource patterns.
    
    Logic:
    - For each major alert, look at metrics 30-60 min BEFORE
    - Detect spikes in CPU, memory, storage
    """
    
    LOOKBACK_MINUTES = 60
    SPIKE_THRESHOLD = 0.8  # 80% threshold for spike detection
    
    @staticmethod
    def correlate_alert_with_metrics(alert: Dict, 
                                     metrics: List[Dict],
                                     lookback_minutes: int = 60) -> Dict:
        """
        Find metrics correlated with an alert.
        
        Returns: {
            "correlated_metrics": [],
            "spike_detected": bool,
            "resource_pattern": str
        }
        """
        alert_time_str = alert.get("alert_time") or alert.get("time") or ""
        if not alert_time_str or not metrics:
            return {"correlated_metrics": [], "spike_detected": False, "resource_pattern": "No data"}
        
        try:
            alert_time = datetime.strptime(str(alert_time_str)[:19], "%Y-%m-%dT%H:%M:%S")
        except:
            return {"correlated_metrics": [], "spike_detected": False, "resource_pattern": "Invalid time"}
        
        window_start = alert_time - timedelta(minutes=lookback_minutes)
        window_end = alert_time
        
        # Find metrics in window
        correlated = []
        for m in metrics:
            metric_time_str = m.get("timestamp") or m.get("time") or ""
            try:
                metric_time = datetime.strptime(str(metric_time_str)[:19], "%Y-%m-%dT%H:%M:%S")
                if window_start <= metric_time <= window_end:
                    correlated.append(m)
            except:
                continue
        
        # Analyze for spikes
        spike_detected = False
        resource_pattern = "Normal"
        
        if correlated:
            # Group by metric name
            metric_values = defaultdict(list)
            for m in correlated:
                name = m.get("metric_name", "unknown")
                try:
                    value = float(m.get("metric_value", 0))
                    metric_values[name].append(value)
                except:
                    continue
            
            # Check for high values
            for name, values in metric_values.items():
                if not values:
                    continue
                max_val = max(values)
                name_lower = name.lower()
                
                if "cpu" in name_lower and max_val > 80:
                    spike_detected = True
                    resource_pattern = "CPU spike detected ({}%)".format(max_val)
                elif "memory" in name_lower and max_val > 85:
                    spike_detected = True
                    resource_pattern = "Memory pressure detected ({}%)".format(max_val)
                elif "storage" in name_lower or "tablespace" in name_lower:
                    if max_val > 90:
                        spike_detected = True
                        resource_pattern = "Storage critical ({}%)".format(max_val)
        
        return {
            "correlated_metrics": correlated[:10],  # Limit to 10
            "spike_detected": spike_detected,
            "resource_pattern": resource_pattern,
            "window": "{} to {}".format(window_start.isoformat(), window_end.isoformat())
        }
    
    @staticmethod
    def find_resource_patterns(alerts: List[Dict], 
                               metrics: List[Dict],
                               target: str = None) -> Dict:
        """
        Find overall resource patterns correlated with alerts.
        """
        if not alerts or not metrics:
            return {"pattern": "Insufficient data for correlation"}
        
        # Filter by target - STRICT EXACT MATCHING
        if target:
            target_upper = target.upper()
            alerts = [a for a in alerts 
                     if (a.get("target") or a.get("target_name") or "").upper() == target_upper]
        
        # Sample alerts for correlation (performance)
        sample_size = min(100, len(alerts))
        sampled = alerts[:sample_size]
        
        patterns = Counter()
        for alert in sampled:
            correlation = MetricAlertCorrelator.correlate_alert_with_metrics(alert, metrics)
            if correlation["spike_detected"]:
                patterns[correlation["resource_pattern"]] += 1
        
        if not patterns:
            return {
                "pattern": "No clear resource correlation found",
                "analyzed_alerts": sample_size,
                "recommendation": "Review metric collection for the affected time windows"
            }
        
        dominant_pattern = patterns.most_common(1)[0]
        return {
            "pattern": dominant_pattern[0],
            "occurrence_count": dominant_pattern[1],
            "analyzed_alerts": sample_size,
            "all_patterns": dict(patterns),
            "recommendation": MetricAlertCorrelator._get_pattern_recommendation(dominant_pattern[0])
        }
    
    @staticmethod
    def _get_pattern_recommendation(pattern: str) -> str:
        """Get recommendation based on resource pattern."""
        if "CPU" in pattern:
            return "Review active sessions and identify resource-intensive queries. Consider CPU allocation increase."
        elif "Memory" in pattern:
            return "Check SGA/PGA allocation. Review large pool and shared pool sizing."
        elif "Storage" in pattern:
            return "Add datafiles or enable autoextend. Review tablespace growth trends."
        return "Monitor resource utilization trends."


# ============================================================
# MODULE 6: ACTION MAPPING ENGINE
# ============================================================
class ActionMapper:
    """
    Maps root causes to specific DBA actions.
    
    Provides actionable remediation steps.
    """
    
    # Comprehensive cause-to-action mapping
    ACTION_MAP = {
        "INTERNAL_DATABASE_ERROR": {
            "immediate": [
                "Check alert log for ORA-600/ORA-7445 arguments",
                "Flush shared pool: ALTER SYSTEM FLUSH SHARED_POOL",
                "Review recent DDL changes"
            ],
            "diagnostic": [
                "Search MOS for matching bug ID",
                "Generate AWR report for the affected period",
                "Check Oracle patch level vs recommended"
            ],
            "preventive": [
                "Schedule Oracle patch update",
                "Review memory configuration",
                "Implement regular health checks"
            ],
            "priority": "HIGH"
        },
        "NETWORK_CONNECTIVITY": {
            "immediate": [
                "Verify listener status: lsnrctl status",
                "Test TNS connectivity: tnsping <service>",
                "Check network firewall rules"
            ],
            "diagnostic": [
                "Review listener.log for errors",
                "Check MTU settings on network interfaces",
                "Verify DNS resolution for database hosts"
            ],
            "preventive": [
                "Implement listener monitoring",
                "Configure backup listener",
                "Document network requirements"
            ],
            "priority": "HIGH"
        },
        "DATAGUARD_REPLICATION": {
            "immediate": [
                "Check Data Guard status: DGMGRL> show configuration",
                "Verify redo apply status on standby",
                "Check archive log gap"
            ],
            "diagnostic": [
                "Review v$dataguard_stats for transport lag",
                "Check network bandwidth between primary/standby",
                "Verify standby redo log sizing"
            ],
            "preventive": [
                "Configure Data Guard Broker monitoring",
                "Implement lag alerting thresholds",
                "Document failover procedures"
            ],
            "priority": "HIGH"
        },
        "STORAGE_CAPACITY": {
            "immediate": [
                "Check tablespace usage: DBA_TABLESPACE_USAGE_METRICS",
                "Identify largest segments: DBA_SEGMENTS",
                "Review autoextend settings"
            ],
            "diagnostic": [
                "Analyze segment growth trends",
                "Check for table bloat (DBMS_SPACE)",
                "Review archivelog destination space"
            ],
            "preventive": [
                "Implement proactive space monitoring",
                "Configure autoextend with limits",
                "Schedule regular maintenance (shrink, rebuild)"
            ],
            "priority": "MEDIUM"
        },
        "MEMORY_PRESSURE": {
            "immediate": [
                "Check SGA/PGA usage: V$SGA, V$PGASTAT",
                "Identify memory-intensive sessions",
                "Review shared pool reserved size"
            ],
            "diagnostic": [
                "Analyze memory advisor: V$MEMORY_TARGET_ADVICE",
                "Check for cursor leaks",
                "Review large pool allocation"
            ],
            "preventive": [
                "Right-size memory parameters",
                "Implement AMM or ASMM appropriately",
                "Monitor memory utilization trends"
            ],
            "priority": "MEDIUM"
        },
        "DATABASE_UNAVAILABLE": {
            "immediate": [
                "Check database status: SELECT STATUS FROM V$INSTANCE",
                "Verify background processes: ps -ef | grep ora_",
                "Check alert log for shutdown reason"
            ],
            "diagnostic": [
                "Review OS logs for OOM or resource exhaustion",
                "Check archivelog destination availability",
                "Verify datafile accessibility"
            ],
            "preventive": [
                "Implement HA/DR solution",
                "Configure automated restart",
                "Document recovery procedures"
            ],
            "priority": "CRITICAL"
        },
        "CPU_RESOURCE": {
            "immediate": [
                "Identify top CPU sessions: V$SESSION, V$PROCESS",
                "Check for parallel query storms",
                "Review Resource Manager settings"
            ],
            "diagnostic": [
                "Generate ASH report for CPU analysis",
                "Check for inefficient execution plans",
                "Review SQL with high CPU consumption"
            ],
            "preventive": [
                "Implement SQL Plan Baselines",
                "Configure Resource Manager plans",
                "Schedule resource-intensive jobs off-peak"
            ],
            "priority": "MEDIUM"
        },
        "SHARED_POOL_MEMORY": {
            "immediate": [
                "Flush shared pool: ALTER SYSTEM FLUSH SHARED_POOL",
                "Check for unpinned large objects",
                "Review cursor_sharing parameter"
            ],
            "diagnostic": [
                "Analyze V$SHARED_POOL_ADVICE",
                "Check for literal SQL usage",
                "Review V$LIBRARYCACHE hit ratios"
            ],
            "preventive": [
                "Increase shared_pool_size",
                "Pin frequently used packages",
                "Implement cursor_sharing=FORCE if appropriate"
            ],
            "priority": "HIGH"
        },
        "OTHER_OPERATIONAL": {
            "immediate": [
                "Review alert log for specific errors",
                "Check OEM for alert details",
                "Verify database availability"
            ],
            "diagnostic": [
                "Generate diagnostic report",
                "Review recent changes",
                "Check for environmental issues"
            ],
            "preventive": [
                "Implement comprehensive monitoring",
                "Document standard procedures",
                "Regular health checks"
            ],
            "priority": "LOW"
        }
    }
    
    @staticmethod
    def get_actions(root_cause: str) -> Dict:
        """
        Get recommended actions for a root cause.
        
        Returns: {
            "immediate": [...],
            "diagnostic": [...],
            "preventive": [...],
            "priority": str
        }
        """
        actions = ActionMapper.ACTION_MAP.get(root_cause)
        if actions:
            return actions
        
        # Fuzzy match
        for cause, action_set in ActionMapper.ACTION_MAP.items():
            if cause in root_cause or root_cause in cause:
                return action_set
        
        return ActionMapper.ACTION_MAP["OTHER_OPERATIONAL"]
    
    @staticmethod
    def generate_action_plan(root_cause: str, 
                            context: Dict = None) -> str:
        """
        Generate a formatted action plan.
        """
        actions = ActionMapper.get_actions(root_cause)
        
        plan = "**Recommended Actions for {}**\n\n".format(root_cause.replace("_", " ").title())
        plan += "**Priority: {}**\n\n".format(actions["priority"])
        
        plan += "**Immediate Actions:**\n"
        for i, action in enumerate(actions["immediate"], 1):
            plan += "{}. {}\n".format(i, action)
        
        plan += "\n**Diagnostic Steps:**\n"
        for i, action in enumerate(actions["diagnostic"], 1):
            plan += "{}. {}\n".format(i, action)
        
        plan += "\n**Preventive Measures:**\n"
        for i, action in enumerate(actions["preventive"], 1):
            plan += "{}. {}\n".format(i, action)
        
        # Add context-specific notes if available
        if context:
            if context.get("last_target"):
                plan += "\n**Target Database:** {}\n".format(context["last_target"])
            if context.get("last_findings"):
                plan += "**Related Findings:** Based on previous analysis\n"
        
        return plan


# ============================================================
# MODULE 8: STANDARD ANSWER PIPELINE
# ============================================================
class AnswerBuilder:
    """
    Builds structured, consistent answers.
    
    Every answer follows:
    1. Summary
    2. What was checked
    3. What was found
    4. What it means
    5. What to do
    """
    
    @staticmethod
    def build_answer(summary: str,
                    checked: List[str],
                    findings: List[str],
                    interpretation: str,
                    actions: List[str],
                    data_stats: Dict = None) -> str:
        """
        Build a structured analytical answer.
        """
        answer = "**{}**\n\n".format(summary)
        
        # What was checked
        if checked:
            answer += "**Analysis Scope:**\n"
            for item in checked[:5]:
                answer += "- {}\n".format(item)
            answer += "\n"
        
        # Data stats if available
        if data_stats:
            answer += "**Data Analyzed:**\n"
            for key, value in data_stats.items():
                if isinstance(value, int):
                    answer += "- {}: {:,}\n".format(key.replace("_", " ").title(), value)
                else:
                    answer += "- {}: {}\n".format(key.replace("_", " ").title(), value)
            answer += "\n"
        
        # What was found
        if findings:
            answer += "**Key Findings:**\n"
            for finding in findings[:7]:
                answer += "- {}\n".format(finding)
            answer += "\n"
        
        # Interpretation
        if interpretation:
            answer += "**Assessment:**\n{}\n\n".format(interpretation)
        
        # Actions
        if actions:
            answer += "**Recommended Actions:**\n"
            for i, action in enumerate(actions[:5], 1):
                answer += "{}. {}\n".format(i, action)
        
        return answer
    
    @staticmethod
    def build_no_data_response(query_type: str,
                               searched: str,
                               alternatives: List[str] = None,
                               suggestion: str = None) -> str:
        """
        Build a helpful response when no data is found.
        
        NEVER just say "No data found" - always provide alternatives.
        """
        answer = "**No {} Found**\n\n".format(query_type)
        answer += "**Searched:** {}\n\n".format(searched)
        
        if alternatives:
            answer += "**Available Alternatives:**\n"
            for alt in alternatives[:5]:
                answer += "- {}\n".format(alt)
            answer += "\n"
        
        if suggestion:
            answer += "**Suggestion:** {}\n".format(suggestion)
        
        return answer
    
    @staticmethod
    def build_comparison_answer(items: List[Dict],
                               compare_field: str,
                               title: str) -> str:
        """Build a comparison table answer."""
        if not items:
            return "No data available for comparison."
        
        answer = "**{}**\n\n".format(title)
        
        for i, item in enumerate(items[:10], 1):
            name = item.get("name", item.get("target", "Unknown"))
            value = item.get(compare_field, item.get("count", 0))
            percentage = item.get("percentage", "")
            
            if percentage:
                answer += "{}. **{}**: {:,} ({}%)\n".format(i, name, value, percentage)
            else:
                answer += "{}. **{}**: {:,}\n".format(i, name, value)
        
        return answer


# ============================================================
# INTELLIGENCE ENGINE - Main Interface
# ============================================================
class IntelligenceEngine:
    """
    Main interface combining all 8 modules.
    
    Usage:
        engine = IntelligenceEngine(alerts, metrics)
        result = engine.analyze(question)
    """
    
    def __init__(self, alerts: List[Dict] = None, metrics: List[Dict] = None):
        self.alerts = alerts or []
        self.metrics = metrics or []
        self.memory = REASONING_MEMORY
        
        # Initialize modules
        self.anti_false_zero = AntiFalseZero()
        self.temporal_awareness = TemporalAwareness()
        self.temporal_intelligence = TemporalIntelligence()
        self.root_cause_scorer = RootCauseScorer()
        self.metric_correlator = MetricAlertCorrelator()
        self.action_mapper = ActionMapper()
        self.answer_builder = AnswerBuilder()
    
    def analyze_target(self, target: str) -> Dict:
        """
        Comprehensive analysis for a target database.
        """
        # Use anti-false-zero to find target
        matched_target, matching_alerts, search_explanation = \
            self.anti_false_zero.widen_target_search(target, self.alerts)
        
        if not matching_alerts:
            # Build helpful no-data response
            all_targets = set()
            for a in self.alerts:
                t = (a.get("target") or a.get("target_name") or "").upper()
                if t:
                    all_targets.add(t)
            
            return {
                "found": False,
                "search_explanation": search_explanation,
                "available_targets": list(all_targets)[:10],
                "answer": self.answer_builder.build_no_data_response(
                    "alerts for {}".format(target),
                    search_explanation,
                    list(all_targets)[:5],
                    "Try one of the available database names"
                )
            }
        
        # Get root cause analysis
        root_causes = self.root_cause_scorer.score_root_causes(matching_alerts)
        primary_cause = root_causes[0] if root_causes else None
        
        # Get temporal patterns
        time_patterns = self.temporal_intelligence.analyze_time_patterns(matching_alerts)
        
        # Get current state
        current_state = self.temporal_awareness.get_current_state(matching_alerts)
        
        # Update memory
        self.memory.update(
            target=matched_target,
            root_cause=primary_cause["cause"] if primary_cause else None,
            findings={
                "alert_count": len(matching_alerts),
                "primary_cause": primary_cause,
                "time_pattern": time_patterns.get("pattern_insight")
            }
        )
        
        # Build comprehensive answer
        summary = "Analysis for {}".format(matched_target)
        
        checked = [
            search_explanation,
            "Analyzed {:,} alerts".format(len(matching_alerts)),
            "Scored {} root cause categories".format(len(root_causes)),
            "Computed temporal patterns"
        ]
        
        findings = [
            "Total alerts: {:,}".format(len(matching_alerts)),
        ]
        
        if primary_cause:
            findings.append("Primary root cause: {} (score: {}, {}% of alerts)".format(
                primary_cause["cause"], primary_cause["score"], primary_cause["percentage"]))
        
        if time_patterns.get("peak_hour"):
            findings.append("Peak alert hour: {:02d}:00 ({:,} alerts)".format(
                time_patterns["peak_hour"][0], time_patterns["peak_hour"][1]))
        
        findings.append("Current state: {}".format(current_state.get("state_assessment", "Unknown")))
        
        interpretation = time_patterns.get("pattern_insight", "")
        if primary_cause:
            interpretation += " " + primary_cause.get("analysis", "")
        
        actions = []
        if primary_cause:
            action_set = self.action_mapper.get_actions(primary_cause["cause"])
            actions = action_set.get("immediate", [])[:3]
        
        return {
            "found": True,
            "target": matched_target,
            "alert_count": len(matching_alerts),
            "root_causes": root_causes[:5],
            "primary_cause": primary_cause,
            "time_patterns": time_patterns,
            "current_state": current_state,
            "answer": self.answer_builder.build_answer(
                summary, checked, findings, interpretation, actions,
                {"total_alerts": len(matching_alerts), "databases": 1}
            )
        }
    
    def analyze_condition(self, condition: str, field: str = "alert_state") -> Dict:
        """
        Analyze alerts matching a condition (e.g., CRITICAL, DOWN).
        """
        matching, explanation = self.anti_false_zero.widen_condition_search(
            self.alerts, condition, field)
        
        if not matching:
            # Use widening explanation to show what exists
            return {
                "found": False,
                "condition": condition,
                "explanation": explanation,
                "answer": "**No {} Alerts**\n\n{}".format(condition, explanation)
            }
        
        # Analyze matching alerts
        db_counts = Counter()
        for a in matching:
            db = (a.get("target") or a.get("target_name") or "Unknown").upper()
            db_counts[db] += 1
        
        findings = [
            "Found {:,} {} alerts".format(len(matching), condition),
        ]
        for db, count in db_counts.most_common(5):
            findings.append("{}: {:,} alerts".format(db, count))
        
        return {
            "found": True,
            "count": len(matching),
            "by_database": dict(db_counts),
            "answer": self.answer_builder.build_answer(
                "{} Alert Analysis".format(condition),
                ["Searched for {} in {}".format(condition, field)],
                findings,
                explanation,
                ["Review alert details for affected databases"],
                {"matching_alerts": len(matching)}
            )
        }
    
    def analyze_time_range(self, hour_start: int, hour_end: int) -> Dict:
        """
        Analyze alerts in a time range with widening.
        """
        matching, explanation = self.anti_false_zero.widen_time_search(
            self.alerts, hour_start, hour_end)
        
        # Get full temporal analysis
        time_patterns = self.temporal_intelligence.analyze_time_patterns(self.alerts)
        
        if not matching:
            # Provide alternatives
            peak_hours = time_patterns.get("peak_hours_top5", [])
            
            findings = ["No alerts found between {:02d}:00 - {:02d}:00".format(hour_start, hour_end)]
            findings.append("Data shows peak activity at different hours:")
            for hour, count in peak_hours[:3]:
                findings.append("  {:02d}:00 - {:,} alerts".format(hour, count))
            
            return {
                "found": False,
                "explanation": explanation,
                "peak_hours": peak_hours,
                "answer": self.answer_builder.build_answer(
                    "Time-Based Analysis ({:02d}:00 - {:02d}:00)".format(hour_start, hour_end),
                    ["Filtered alerts by hour of day"],
                    findings,
                    time_patterns.get("pattern_insight", ""),
                    ["Query for peak hours instead"],
                    {"total_alerts_analyzed": time_patterns.get("total_with_timestamps", 0)}
                )
            }
        
        # Analyze the matching alerts
        db_counts = Counter()
        for a in matching:
            db = (a.get("target") or a.get("target_name") or "Unknown").upper()
            db_counts[db] += 1
        
        findings = [
            "Found {:,} alerts in time window".format(len(matching))
        ]
        for db, count in db_counts.most_common(3):
            findings.append("{}: {:,} alerts".format(db, count))
        
        return {
            "found": True,
            "count": len(matching),
            "by_database": dict(db_counts),
            "time_patterns": time_patterns,
            "answer": self.answer_builder.build_answer(
                "Time-Based Analysis ({:02d}:00 - {:02d}:00)".format(hour_start, hour_end),
                ["Filtered alerts by hour of day", "Analyzed temporal patterns"],
                findings,
                time_patterns.get("pattern_insight", ""),
                ["Focus investigation on peak hours", "Correlate with batch job schedules"],
                {"alerts_in_window": len(matching)}
            )
        }
    
    def get_action_plan(self, root_cause: str = None, target: str = None) -> str:
        """
        Generate action plan, using memory if root cause not specified.
        """
        # Use memory if no root cause specified
        if not root_cause:
            context = self.memory.get_context()
            root_cause = context.get("last_root_cause")
            if not target:
                target = context.get("last_target")
        
        if not root_cause:
            # Compute root cause from target or all alerts
            if target:
                result = self.analyze_target(target)
                if result.get("primary_cause"):
                    root_cause = result["primary_cause"]["cause"]
            else:
                # Use all alerts
                root_causes = self.root_cause_scorer.score_root_causes(self.alerts)
                if root_causes:
                    root_cause = root_causes[0]["cause"]
        
        if not root_cause:
            return "Unable to determine root cause. Please specify a database or issue type for analysis."
        
        context = self.memory.get_context()
        return self.action_mapper.generate_action_plan(root_cause, context)
    
    def get_prediction(self) -> Dict:
        """
        Predict which database is most likely to fail next.
        """
        # Score all databases
        db_scores = {}
        
        # Group alerts by database
        db_alerts = defaultdict(list)
        for a in self.alerts:
            db = (a.get("target") or a.get("target_name") or "").upper()
            if db:
                db_alerts[db].append(a)
        
        for db, alerts in db_alerts.items():
            # Get root cause scores
            root_causes = self.root_cause_scorer.score_root_causes(alerts)
            max_score = root_causes[0]["score"] if root_causes else 0
            
            # Count critical ratio
            critical_count = sum(1 for a in alerts 
                               if "CRITICAL" in (a.get("severity") or a.get("alert_state") or "").upper())
            critical_ratio = critical_count / len(alerts) if alerts else 0
            
            # Combined risk score
            risk_score = (max_score * 0.6) + (critical_ratio * 0.4)
            
            db_scores[db] = {
                "score": round(risk_score, 3),
                "alert_count": len(alerts),
                "critical_ratio": round(critical_ratio * 100, 1),
                "primary_cause": root_causes[0]["cause"] if root_causes else "UNKNOWN"
            }
        
        # Sort by risk
        sorted_dbs = sorted(db_scores.items(), key=lambda x: x[1]["score"], reverse=True)
        
        if not sorted_dbs:
            return {"prediction": "Insufficient data for prediction"}
        
        highest_risk = sorted_dbs[0]
        
        # Determine risk level
        if highest_risk[1]["score"] > 0.5:
            risk_level = "HIGH"
        elif highest_risk[1]["score"] > 0.3:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        findings = [
            "Highest risk: {} (score: {})".format(highest_risk[0], highest_risk[1]["score"]),
            "Alert volume: {:,}".format(highest_risk[1]["alert_count"]),
            "Critical ratio: {}%".format(highest_risk[1]["critical_ratio"]),
            "Primary issue: {}".format(highest_risk[1]["primary_cause"])
        ]
        
        for db, data in sorted_dbs[1:4]:
            findings.append("{}: score {} ({:,} alerts)".format(db, data["score"], data["alert_count"]))
        
        return {
            "highest_risk_db": highest_risk[0],
            "risk_level": risk_level,
            "all_scores": dict(sorted_dbs[:5]),
            "answer": self.answer_builder.build_answer(
                "Failure Prediction Analysis",
                ["Scored {} databases by risk".format(len(sorted_dbs)),
                 "Computed root cause scores",
                 "Analyzed critical alert ratios"],
                findings,
                "{} has the highest risk based on alert volume and critical alert ratio. Risk Level: {}".format(
                    highest_risk[0], risk_level),
                self.action_mapper.get_actions(highest_risk[1]["primary_cause"]).get("immediate", [])[:3],
                {"databases_analyzed": len(sorted_dbs)}
            )
        }
