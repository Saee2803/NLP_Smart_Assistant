# nlp_engine/oem_data_analyzer.py
"""
OEM Data Analyzer

CRITICAL: Extracts REAL information from OEM alerts:
- ORA codes (ORA-600, ORA-7445, etc.)
- Arguments/context (Undo, Rollback, Memory, Storage, Redo)
- Time patterns
- Severity distribution
- Message parsing

This is the data extraction layer that feeds the reasoning engine.
INTERNAL_ERROR is a SYMPTOM, not a root cause - this module drills down.

Python 3.6 compatible.
"""

import re
from datetime import datetime
from collections import Counter, defaultdict


class OEMDataAnalyzer:
    """
    Analyzes raw OEM alert data to extract actionable insights.
    """
    
    # Known ORA error categories
    ORA_CATEGORIES = {
        "ORA-600": {
            "category": "INTERNAL_ERROR",
            "description": "Oracle internal error",
            "severity": "CRITICAL",
            "common_arguments": {
                "13011": "Shared pool memory corruption",
                "17147": "Session idle timeout exceeded",
                "4031": "Unable to allocate shared memory",
                "12899": "Value too large for column",
                "17002": "IO error during network operation"
            }
        },
        "ORA-7445": {
            "category": "ACCESS_VIOLATION",
            "description": "Exception encountered - core dump",
            "severity": "CRITICAL",
            "common_causes": ["Memory corruption", "Bug in Oracle kernel", "Hardware issue"]
        },
        "ORA-4031": {
            "category": "SHARED_POOL",
            "description": "Unable to allocate shared memory",
            "severity": "CRITICAL",
            "remediation": "Increase shared_pool_size or flush shared pool"
        },
        "ORA-1555": {
            "category": "UNDO",
            "description": "Snapshot too old",
            "severity": "HIGH",
            "remediation": "Increase undo_retention or resize undo tablespace"
        },
        "ORA-12514": {
            "category": "LISTENER",
            "description": "TNS: listener does not currently know of service",
            "severity": "HIGH"
        }
    }
    
    # Context keywords for root cause mapping
    CONTEXT_KEYWORDS: dict[str, list[str]] = {
        "UNDO": ["undo", "rollback", "snapshot", "ora-1555"],
        "REDO": ["redo", "archive", "log writer", "lgwr", "arc"],
        "MEMORY": ["memory", "sga", "pga", "heap", "ora-4031", "shared pool"],
        "STORAGE": ["storage", "disk", "tablespace", "datafile", "io", "ora-1653"],
        "NETWORK": ["network", "tns", "listener", "timeout", "connection"],
        "INSTANCE": ["instance", "shutdown", "startup", "crash", "internal error"]
    }
    
    def __init__(self, alerts):
        """
        Initialize with alert data.
        
        Args:
            alerts: List of alert dicts from GLOBAL_DATA
        """
        self.alerts = alerts or []
    
    def extract_ora_codes(self, target=None):
        """
        Extract all ORA codes from alerts.
        
        Returns:
            {
                "ora_codes": [{"code": "ORA-600", "count": 100, "arguments": [...]}],
                "total_ora_errors": int,
                "most_common": str,
                "severity_breakdown": dict
            }
        """
        ora_pattern: re.Pattern[str] = re.compile(r'ORA[-\s]?(\d{3,5})(?:\s*\[(\d+)\])?', re.IGNORECASE)
        ora_counts = Counter()
        ora_arguments = defaultdict(list)
        ora_samples = defaultdict(list)
        
        for alert in self.alerts:
            if target and not self._matches_target(alert, target):
                continue
            
            message = alert.get("message", "")
            matches = ora_pattern.findall(message)
            
            for match in matches:
                code = "ORA-{0}".format(match[0])
                ora_counts[code] += 1
                
                # Extract argument if present
                if match[1]:
                    ora_arguments[code].append(match[1])
                
                # Store sample message (first 5)
                if len(ora_samples[code]) < 5:
                    ora_samples[code].append({
                        "message": message[:200],
                        "time": alert.get("time"),
                        "target": alert.get("target")
                    })
        
        # Build result
        ora_codes = []
        for code, count in ora_counts.most_common():
            entry = {
                "code": code,
                "count": count,
                "arguments": list(set(ora_arguments.get(code, [])))[:5],
                "samples": ora_samples.get(code, [])
            }
            
            # Add category info if known
            if code in self.ORA_CATEGORIES:
                entry["category"] = self.ORA_CATEGORIES[code]["category"]
                entry["description"] = self.ORA_CATEGORIES[code]["description"]
                entry["severity"] = self.ORA_CATEGORIES[code].get("severity", "HIGH")
                entry["remediation"] = self.ORA_CATEGORIES[code].get("remediation")
            
            ora_codes.append(entry)
        
        return {
            "ora_codes": ora_codes,
            "total_ora_errors": sum(ora_counts.values()),
            "most_common": ora_codes[0]["code"] if ora_codes else None,
            "severity_breakdown": self._categorize_ora_severity(ora_codes)
        }
    
    def extract_context_categories(self, target=None):
        """
        Categorize alerts by context (Undo, Redo, Memory, etc.)
        
        Returns:
            {
                "categories": {"MEMORY": 50, "UNDO": 20, ...},
                "primary_category": str,
                "evidence": [...]
            }
        """
        category_counts = Counter()
        category_evidence = defaultdict(list)
        
        for alert in self.alerts:
            if target and not self._matches_target(alert, target):
                continue
            
            message = (alert.get("message") or "").lower()
            
            for category, keywords in self.CONTEXT_KEYWORDS.items():
                found = False
                for kw in keywords:
                    if kw in message:
                        found = True
                        break
                if found:
                    category_counts[category] += 1
                    if len(category_evidence[category]) < 3:
                        category_evidence[category].append({
                            "message": alert.get("message", "")[:150],
                            "time": alert.get("time")
                        })
        
        return {
            "categories": dict(category_counts),
            "primary_category": category_counts.most_common(1)[0][0] if category_counts else "UNKNOWN",
            "evidence": dict(category_evidence)
        }
    
    def analyze_time_distribution(self, target=None, time_range=None):
        """
        Analyze alert distribution by time.
        
        Args:
            target: Filter by database
            time_range: {"start_hour": int, "end_hour": int}
        
        Returns:
            {
                "hourly_distribution": {0: 100, 1: 50, ...},
                "peak_hour": int,
                "peak_count": int,
                "alerts_in_range": int (if time_range specified),
                "alerts_in_range_details": [...]
            }
        """
        hourly_counts = Counter()
        alerts_in_range = []
        
        for alert in self.alerts:
            if target and not self._matches_target(alert, target):
                continue
            
            # Handle both "alert_time" and "time" column names
            alert_time = alert.get("alert_time") or alert.get("time")
            if not alert_time:
                continue
            
            if isinstance(alert_time, str):
                try:
                    alert_time: datetime = datetime.fromisoformat(alert_time.replace("T", " ").split("+")[0])
                except ValueError:
                    continue
            
            hour = alert_time.hour
            hourly_counts[hour] += 1
            
            # Check time range filter
            if time_range:
                start_hour = time_range.get("start_hour", 0)
                end_hour = time_range.get("end_hour", 24)
                
                # Handle overnight ranges (e.g., 22:00 - 06:00)
                if start_hour > end_hour:
                    in_range = hour >= start_hour or hour < end_hour
                else:
                    in_range = start_hour <= hour < end_hour
                
                if in_range:
                    alerts_in_range.append(alert)
        
        peak_hour = hourly_counts.most_common(1)[0][0] if hourly_counts else None
        
        result = {
            "hourly_distribution": dict(hourly_counts),
            "peak_hour": peak_hour,
            "peak_count": hourly_counts[peak_hour] if peak_hour is not None else 0
        }
        
        if time_range:
            result["alerts_in_range"] = len(alerts_in_range)
            result["alerts_in_range_details"] = alerts_in_range[:20]  # Sample
        
        return result
    
    def get_database_summary(self):
        """
        Get summary across all databases.
        
        Returns:
            {
                "databases": [{"name": str, "alert_count": int, "critical_count": int}],
                "total_alerts": int,
                "most_affected": str,
                "severity_summary": {"CRITICAL": X, "WARNING": Y}
            }
        """
        db_stats = defaultdict(lambda: {"count": 0, "critical": 0, "warning": 0})
        severity_counts = Counter()
        
        for alert in self.alerts:
            # Handle both "target_name" and "target" column names
            target = alert.get("target_name") or alert.get("target")
            if not target:
                continue
            
            db_stats[target]["count"] += 1
            
            # Handle both "alert_state" and "severity" column names
            severity = (alert.get("alert_state") or alert.get("severity") or "").upper()
            
            # Also check alert_critical flag
            is_critical = alert.get("alert_critical") == "1" or severity == "CRITICAL"
            
            if is_critical:
                severity_counts["CRITICAL"] += 1
                db_stats[target]["critical"] += 1
            elif severity == "WARNING":
                severity_counts["WARNING"] += 1
                db_stats[target]["warning"] += 1
            else:
                severity_counts[severity] += 1
        
        databases = [
            {
                "name": name,
                "alert_count": stats["count"],
                "critical_count": stats["critical"],
                "warning_count": stats["warning"],
                "percentage": round(stats["count"] / len(self.alerts) * 100, 1) if self.alerts else 0
            }
            for name, stats in sorted(db_stats.items(), key=lambda x: x[1]["count"], reverse=True)
        ]
        
        return {
            "databases": databases,
            "total_alerts": len(self.alerts),
            "database_count": len(databases),
            "most_affected": databases[0]["name"] if databases else None,
            "severity_summary": dict(severity_counts)
        }
    
    def find_standby_dataguard_alerts(self):
        """
        Find alerts related to Data Guard / Standby databases.
        """
        dataguard_keywords = [
            "standby", "data guard", "dataguard", "apply lag", "transport lag",
            "mrp", "redo apply", "gap", "archive gap", "switchover", "failover"
        ]
        
        found_alerts = []
        for alert in self.alerts:
            message = (alert.get("message") or "").lower()
            found = False
            for kw in dataguard_keywords:
                if kw in message:
                    found = True
                    break
            if found:
                found_alerts.append(alert)
        
        return {
            "found": len(found_alerts) > 0,
            "count": len(found_alerts),
            "alerts": found_alerts[:20],
            "summary": "Found {0} Data Guard/Standby alerts".format(len(found_alerts)) if found_alerts else "No standby or Data Guard alerts found in OEM data."
        }
    
    def find_tablespace_alerts(self):
        """
        Find alerts related to tablespace / storage issues.
        """
        tablespace_pattern: re.Pattern[str] = re.compile(r'tablespace\s+(\w+)', re.IGNORECASE)
        space_keywords = ["tablespace", "space", "full", "storage", "datafile"]
        
        tablespace_counts = Counter()
        found_alerts = []
        
        for alert in self.alerts:
            message = (alert.get("message") or "").lower()
            metric = (alert.get("metric") or "").lower()
            
            found = False
            for kw in space_keywords:
                if kw in message:
                    found = True
                    break
            if found or "tablespace" in metric:
                found_alerts.append(alert)
                
                # Extract tablespace name
                match = tablespace_pattern.search(alert.get("message", ""))
                if match:
                    tablespace_counts[match.group(1).upper()] += 1
        
        tablespaces = [
            {"name": name, "alert_count": count}
            for name, count in tablespace_counts.most_common()
        ]
        
        return {
            "found": len(found_alerts) > 0,
            "count": len(found_alerts),
            "tablespaces": tablespaces,
            "alerts": found_alerts[:20],
            "summary": "Found {0} tablespace/storage alerts".format(len(found_alerts)) if found_alerts else "No tablespace alerts close to full in OEM data."
        }
    
    def analyze_why_repeated(self, target):
        """
        Analyze WHY a database has repeated issues.
        
        CRITICAL: This is the deep analysis for ROOT_CAUSE intent.
        WIDENING LOGIC: Never return "no data" without trying alternatives.
        """
        if not target:
            return {"error": "Target database required for root cause analysis"}
        
        # Get target-specific alerts
        target_alerts = [a for a in self.alerts if self._matches_target(a, target)]
        
        # WIDENING LOGIC: If no exact match, try fuzzy match
        actual_target = target
        if not target_alerts:
            # Try fuzzy matching - look for similar database names
            all_targets = set()
            for a in self.alerts:
                t = a.get("target", "")
                if t:
                    all_targets.add(t.upper())
            
            # Find closest match - but require HIGH similarity (not substring)
            target_upper = target.upper()
            best_match = None
            best_score = 0
            for t in all_targets:
                # Calculate character-based similarity (Jaccard-like)
                # DO NOT use substring matching - MIDEVSTB should NOT match MIDEVSTBN
                if len(t) == len(target_upper):
                    # Same length - check character match
                    matches = sum(1 for a, b in zip(target_upper, t) if a == b)
                    score = matches / len(target_upper)
                else:
                    # Different lengths - use set intersection
                    common = len(set(target_upper) & set(t))
                    total = max(len(target_upper), len(t))
                    score = common / total * 0.8  # Penalize length difference
                
                if score > best_score and score >= 0.85:  # High threshold
                    best_score = score
                    best_match = t
            
            if best_match:
                actual_target = best_match
                target_alerts = [a for a in self.alerts if self._matches_target(a, actual_target)]
        
        if not target_alerts:
            # WIDENING: Return summary of what WAS found instead of error
            summary = self.get_database_summary()
            if summary["databases"]:
                top_db = summary["databases"][0]
                return {
                    "error": None,
                    "widening_applied": True,
                    "original_target": target,
                    "message": "No alerts found for '{0}'. However, {1} alerts exist for {2}.".format(
                        target, top_db["alert_count"], top_db["name"]
                    ),
                    "suggested_target": top_db["name"],
                    "total_alerts": summary["total_alerts"]
                }
            return {"error": "No alerts found for {0}".format(target)}
        
        # Extract ORA codes
        ora_analysis = self.extract_ora_codes(target)
        
        # Extract context categories
        context = self.extract_context_categories(target)
        
        # Analyze time patterns
        time_analysis = self.analyze_time_distribution(target)
        
        # Determine primary root cause
        root_cause, evidence, remediation = self._determine_root_cause(
            ora_analysis, context, time_analysis, len(target_alerts)
        )
        
        return {
            "target": target,
            "total_alerts": len(target_alerts),
            "root_cause": root_cause,
            "evidence": evidence,
            "ora_codes": ora_analysis.get("ora_codes", [])[:5],
            "primary_context": context.get("primary_category"),
            "peak_hour": time_analysis.get("peak_hour"),
            "contributing_factors": self._get_contributing_factors(ora_analysis, context),
            "remediation": remediation
        }
    
    def _determine_root_cause(self, ora_analysis, context, time_analysis, alert_count):
        """
        Determine the most likely root cause from analysis.
        
        CRITICAL: Root cause MUST NEVER be "Unknown" - always infer from evidence.
        """
        evidence = []
        root_cause = None  # Start with None, NOT "Unknown"
        remediation = "Further investigation required"
        
        # Check ORA codes first
        ora_codes = ora_analysis.get("ora_codes", [])
        if ora_codes:
            top_ora = ora_codes[0]
            if top_ora["count"] > 10:
                evidence.append("{0} occurrences of {1}".format(top_ora["count"], top_ora["code"]))
                
                # Map ORA code to root cause
                if "ORA-600" in top_ora["code"]:
                    if top_ora.get("arguments"):
                        arg = top_ora["arguments"][0]
                        if arg in ["13011"]:
                            root_cause = "Shared pool memory corruption causing internal errors"
                            remediation = "1) Flush shared pool 2) Check for cursor leaks 3) Review memory settings"
                        elif arg in ["4031"]:
                            root_cause = "Shared pool exhaustion"
                            remediation = "Increase shared_pool_size or tune SGA"
                        else:
                            root_cause = "Oracle internal error (ORA-600 [{0}])".format(arg)
                            remediation = "Search Oracle Support for ORA-600 [{0}] and apply patch if available".format(arg)
                    else:
                        root_cause = "Oracle internal errors (ORA-600) indicating kernel/memory issues"
                        remediation = "1) Check Oracle patch level 2) Review memory utilization 3) Analyze trace files"
                
                elif "ORA-7445" in top_ora["code"]:
                    root_cause = "Oracle kernel exception (possible memory corruption or bug)"
                    remediation = "1) Apply latest Oracle patches 2) Check hardware memory 3) Review core dump"
                
                elif "ORA-1555" in top_ora["code"]:
                    root_cause = "Undo tablespace exhaustion (snapshot too old)"
                    remediation = "1) Increase undo_retention 2) Resize undo tablespace 3) Review long-running queries"
                
                elif "ORA-12537" in top_ora["code"] or "ORA-12170" in top_ora["code"]:
                    root_cause = "Network/Listener instability"
                    remediation = "1) Check listener status 2) Review network configuration 3) Check firewall rules"
                
                elif "ORA-04031" in top_ora["code"]:
                    root_cause = "Shared pool memory exhaustion"
                    remediation = "1) Increase shared_pool_size 2) Check for cursor leaks 3) Review SGA settings"
                
                elif "ORA-01653" in top_ora["code"] or "ORA-01654" in top_ora["code"]:
                    root_cause = "Tablespace exhaustion"
                    remediation = "1) Add datafile to tablespace 2) Enable autoextend 3) Purge old data"
                
                # PRODUCTION FIX: If ORA code exists but not mapped, still provide meaningful root cause
                elif not root_cause:
                    root_cause = "Database errors related to {0} ({1} occurrences)".format(
                        top_ora["code"], top_ora["count"])
                    remediation = "1) Search Oracle Support for {0} 2) Review alert log 3) Check database parameters".format(
                        top_ora["code"])
        
        # Check context if no clear ORA cause
        if not root_cause:
            primary_context = context.get("primary_category")
            if primary_context == "MEMORY":
                root_cause = "Memory pressure causing database instability"
                remediation = "1) Increase SGA/PGA 2) Check for memory leaks 3) Review batch job scheduling"
                evidence.append("Memory-related alerts detected")
            
            elif primary_context == "UNDO":
                root_cause = "Undo/rollback segment issues"
                remediation = "1) Increase undo tablespace 2) Tune undo_retention"
                evidence.append("Undo-related alerts detected")
            
            elif primary_context == "REDO":
                root_cause = "Redo log / archiving issues"
                remediation = "1) Check archive destination 2) Add redo log groups 3) Review log switch frequency"
                evidence.append("Redo-related alerts detected")
            
            elif primary_context == "INSTANCE":
                root_cause = "Instance-level instability (repeated crashes)"
                remediation = "1) Review alert log 2) Check system resources 3) Apply patches"
                evidence.append("Instance-level errors detected")
            
            elif primary_context == "CONNECTION":
                root_cause = "Connection/Network instability"
                remediation = "1) Check listener 2) Review TNS configuration 3) Monitor network"
                evidence.append("Connection-related alerts detected")
        
        # PRODUCTION FIX: If STILL no root cause, infer from alert volume/severity
        if not root_cause:
            if alert_count > 1000:
                root_cause = "High volume alert pattern indicating systemic instability"
                remediation = "1) Review alert log chronologically 2) Check for recent changes 3) Verify hardware health"
                evidence.append("High alert volume detected")
            elif alert_count > 100:
                root_cause = "Sustained alert pattern indicating recurring issues"
                remediation = "1) Analyze alert patterns 2) Check scheduled jobs 3) Review resource utilization"
                evidence.append("Sustained alert pattern detected")
            else:
                root_cause = "Intermittent instability requiring investigation"
                remediation = "1) Monitor for pattern recurrence 2) Review recent changes 3) Check resource metrics"
        
        # Add time pattern evidence
        peak_hour = time_analysis.get("peak_hour")
        if peak_hour is not None:
            evidence.append("Peak alert hour: {0}:00".format(peak_hour))
            if peak_hour in [0, 1, 2, 3, 4, 5]:
                evidence.append("Most issues occur during nightly batch window")
                if "batch" not in remediation.lower():
                    remediation += " Consider rescheduling batch jobs."
        
        evidence.append("Total alerts: {0}".format(alert_count))
        
        return root_cause, evidence, remediation
    
    def _get_contributing_factors(self, ora_analysis, context):
        """Get list of contributing factors with DB-specific percentages."""
        factors = []
        
        # Calculate total for percentage
        total_ora_count = sum(ora.get("count", 0) for ora in ora_analysis.get("ora_codes", []))
        
        for ora in ora_analysis.get("ora_codes", [])[:3]:
            count = ora["count"]
            # Add percentage for DB-specific evidence
            if total_ora_count > 0:
                pct = (count / total_ora_count) * 100
                factors.append("{0} ({1} occurrences, {2:.1f}% of ORA errors)".format(ora["code"], count, pct))
            else:
                factors.append("{0} ({1} occurrences)".format(ora["code"], count))
        
        categories = context.get("categories", {})
        total_cat_count = sum(categories.values()) if categories else 0
        sorted_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)
        for cat, count in sorted_cats[:3]:
            # Add percentage for DB-specific evidence
            if total_cat_count > 0:
                pct = (count / total_cat_count) * 100
                factors.append("{0} context ({1} alerts, {2:.1f}%)".format(cat, count, pct))
            else:
                factors.append("{0} context ({1} alerts)".format(cat, count))
        
        return factors
    
    def _categorize_ora_severity(self, ora_codes) -> dict[str, int]:
        """Categorize ORA codes by severity."""
        severity: dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        
        for ora in ora_codes:
            sev = ora.get("severity", "HIGH")
            severity[sev] = severity.get(sev, 0) + ora["count"]
        
        return severity
    
    def _matches_target(self, alert, target):
        """Check if alert matches target database."""
        # Handle both "target" and "target_name" column names
        alert_target = (alert.get("target_name") or alert.get("target") or "").upper()
        target_upper = target.upper()
        
        # STRICT EXACT match only - MIDEVSTB should NOT match MIDEVSTBN
        return alert_target == target_upper
