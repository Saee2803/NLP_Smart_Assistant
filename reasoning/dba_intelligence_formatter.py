"""
DBA INTELLIGENCE FORMATTER - Enterprise-Grade Conversational Intelligence
==========================================================================

Transforms raw data responses into intelligent, DBA-level communications.

🧠 CORE RESPONSIBILITIES (5 Layers of Intelligence):

1️⃣ FACTUAL ACCURACY - Use ONLY provided data, never hallucinate
2️⃣ INCIDENT REASONING - Detect duplicates vs unique incidents  
3️⃣ CONTEXTUAL DBA EXPLANATION - What/Why/Normal or Abnormal
4️⃣ HUMAN-LIKE RESPONSE STYLE - Calm, professional, non-robotic
5️⃣ ACTIONABLE DBA GUIDANCE - Recommendations without fabrication

This module ensures responses feel like a Senior DBA is speaking.
"""

from typing import Dict, List, Any, Optional, Tuple
from collections import Counter
from datetime import datetime
import re


class DBAIntelligenceFormatter:
    """
    Formats responses with enterprise DBA intelligence.
    
    Transforms machine output into human DBA conversation.
    """
    
    # Severity awareness thresholds
    CRITICAL_THRESHOLD = 10  # More than this = needs attention
    WARNING_THRESHOLD = 50   # More than this = needs review
    HIGH_VOLUME_THRESHOLD = 10000  # Large volumes trigger deduplication analysis
    
    # Known Oracle error patterns for incident reasoning
    ORA_ERROR_PATTERNS = [
        r'ORA-\d+',
        r'TNS-\d+',
        r'IMP-\d+',
        r'EXP-\d+',
        r'RMAN-\d+',
        r'DRG-\d+',
    ]
    
    def __init__(self):
        """Initialize the DBA Intelligence Formatter."""
        self.last_response_context = {}
    
    # =========================================================================
    # PRIMARY API
    # =========================================================================
    
    def format_response(
        self,
        raw_data: Dict[str, Any],
        query_type: str,
        intent: Dict[str, Any] = None,
        context: Dict[str, Any] = None
    ) -> str:
        """
        Transform raw query results into intelligent DBA response.
        
        Args:
            raw_data: Query result data
            query_type: Type of query (COUNT, LIST, STATUS, etc.)
            intent: Parsed intent
            context: Conversation context
            
        Returns:
            Human-readable, DBA-intelligent response
        """
        if not raw_data:
            return self._format_no_data_response(intent, context)
        
        # Route to appropriate formatter
        if query_type == "COUNT":
            return self._format_count_response(raw_data, intent, context)
        elif query_type == "LIST":
            return self._format_list_response(raw_data, intent, context)
        elif query_type == "STATUS":
            return self._format_status_response(raw_data, intent, context)
        elif query_type == "FACT":
            return self._format_fact_response(raw_data, intent, context)
        elif query_type == "COMPARISON":
            return self._format_comparison_response(raw_data, intent, context)
        elif query_type == "TREND":
            return self._format_trend_response(raw_data, intent, context)
        else:
            return self._format_general_response(raw_data, intent, context)
    
    # =========================================================================
    # LAYER 1: FACTUAL ACCURACY
    # =========================================================================
    
    def _ensure_factual(self, value: Any, fallback: str = "not available") -> str:
        """Ensure we only return factual data, never fabricate."""
        if value is None:
            return fallback
        if isinstance(value, (int, float)):
            return "{:,}".format(int(value)) if value == int(value) else "{:.2f}".format(value)
        return str(value) if value else fallback
    
    def _get_data_bounds(self, alerts: List[Dict]) -> Dict[str, Any]:
        """Get factual bounds of the data (earliest/latest timestamps, etc.)."""
        if not alerts:
            return {"has_data": False}
        
        timestamps = []
        for a in alerts:
            ts = a.get("alert_time") or a.get("time") or a.get("first_seen")
            if ts:
                timestamps.append(str(ts))
        
        return {
            "has_data": True,
            "count": len(alerts),
            "has_timestamps": len(timestamps) > 0,
            "earliest": min(timestamps) if timestamps else None,
            "latest": max(timestamps) if timestamps else None
        }
    
    # =========================================================================
    # LAYER 2: INCIDENT REASONING
    # =========================================================================
    
    def _analyze_incident_patterns(self, alerts: List[Dict]) -> Dict[str, Any]:
        """
        Analyze alerts for incident patterns - detect duplicates vs unique issues.
        
        This is CRITICAL for accurate DBA communication.
        """
        if not alerts:
            return {"analysis": "no_data", "unique_incidents": 0}
        
        total_count = len(alerts)
        
        # Analyze by message/error pattern
        message_counter = Counter()
        error_code_counter = Counter()
        
        for a in alerts:
            msg = (a.get("message") or a.get("description") or 
                   a.get("issue_type") or a.get("alert_type") or "").upper()
            message_counter[msg] += 1
            
            # Extract Oracle error codes
            for pattern in self.ORA_ERROR_PATTERNS:
                matches = re.findall(pattern, msg)
                for m in matches:
                    error_code_counter[m] += 1
        
        # Calculate deduplication ratio
        unique_messages = len(message_counter)
        dedup_ratio = unique_messages / total_count if total_count > 0 else 1.0
        
        # Top repeating issues
        top_issues = message_counter.most_common(5)
        top_error_codes = error_code_counter.most_common(5)
        
        # Determine if this is likely a single incident appearing multiple times
        is_likely_single_incident = (
            dedup_ratio < 0.1 and  # Less than 10% unique messages
            total_count > 100 and  # High volume
            len(top_issues) > 0 and
            top_issues[0][1] / total_count > 0.5  # Top issue is >50% of alerts
        )
        
        return {
            "analysis": "complete",
            "total_alerts": total_count,
            "unique_messages": unique_messages,
            "dedup_ratio": dedup_ratio,
            "is_likely_single_incident": is_likely_single_incident,
            "top_issues": top_issues,
            "top_error_codes": top_error_codes,
            "dominant_error": top_error_codes[0][0] if top_error_codes else None
        }
    
    def _explain_incident_reasoning(self, pattern_analysis: Dict) -> str:
        """Generate human explanation of incident patterns."""
        if pattern_analysis.get("analysis") != "complete":
            return ""
        
        total = pattern_analysis.get("total_alerts", 0)
        unique = pattern_analysis.get("unique_messages", 0)
        is_single = pattern_analysis.get("is_likely_single_incident", False)
        top_issues = pattern_analysis.get("top_issues", [])
        dominant_error = pattern_analysis.get("dominant_error")
        
        if total < 10:
            return ""  # Not enough data for pattern analysis
        
        if is_single and dominant_error:
            return (
                f"Although there are {total:,} alerts, most appear to be repeated instances "
                f"of the same {dominant_error} error, indicating a single ongoing issue "
                "rather than thousands of independent failures."
            )
        elif is_single:
            top_msg = top_issues[0][0][:50] + "..." if top_issues and len(top_issues[0][0]) > 50 else (top_issues[0][0] if top_issues else "")
            return (
                f"The high volume of {total:,} alerts appears to stem from a single "
                f"recurring issue rather than multiple independent failures."
            )
        elif unique < total * 0.5:
            return (
                f"Of {total:,} alerts, approximately {unique:,} represent unique issues. "
                "The remaining alerts are likely repeated occurrences of the same problems."
            )
        
        return ""
    
    # =========================================================================
    # LAYER 3: CONTEXTUAL DBA EXPLANATION
    # =========================================================================
    
    def _assess_severity_context(
        self, 
        count: int, 
        severity: str = None,
        database: str = None
    ) -> Dict[str, str]:
        """
        Assess the severity context in DBA terms.
        
        Returns: {what, why, assessment}
        """
        severity_upper = (severity or "").upper()
        
        if severity_upper == "CRITICAL":
            if count == 0:
                return {
                    "what": "No critical alerts found",
                    "why": "This typically indicates the database is operating normally",
                    "assessment": "healthy"
                }
            elif count <= 5:
                return {
                    "what": f"{count} critical alert{'s' if count > 1 else ''} detected",
                    "why": "A small number of critical alerts may indicate isolated incidents",
                    "assessment": "attention_needed"
                }
            elif count <= self.CRITICAL_THRESHOLD:
                return {
                    "what": f"{count} critical alerts detected",
                    "why": "This level of critical alerts warrants review by a DBA",
                    "assessment": "review_recommended"
                }
            else:
                return {
                    "what": f"{count:,} critical alerts detected",
                    "why": "This volume is significantly higher than normal and likely indicates a systemic problem",
                    "assessment": "immediate_investigation"
                }
        
        elif severity_upper == "WARNING":
            if count == 0:
                return {
                    "what": "No warning alerts found",
                    "why": "The monitored components are within normal thresholds",
                    "assessment": "healthy"
                }
            elif count <= self.WARNING_THRESHOLD:
                return {
                    "what": f"{count} warning alert{'s' if count > 1 else ''} present",
                    "why": "Warnings indicate conditions that may need attention but are not outages",
                    "assessment": "monitor"
                }
            else:
                return {
                    "what": f"{count:,} warning alerts present",
                    "why": "High warning volume may indicate degrading conditions",
                    "assessment": "proactive_review"
                }
        
        else:
            # General alert assessment
            if count == 0:
                return {
                    "what": "No alerts found",
                    "why": "This usually indicates a healthy state",
                    "assessment": "healthy"
                }
            elif count <= 100:
                return {
                    "what": f"{count} alert{'s' if count > 1 else ''} recorded",
                    "why": "Normal monitoring activity",
                    "assessment": "normal"
                }
            elif count <= self.HIGH_VOLUME_THRESHOLD:
                return {
                    "what": f"{count:,} alerts recorded",
                    "why": "Moderate alert volume - review for patterns recommended",
                    "assessment": "review"
                }
            else:
                return {
                    "what": f"{count:,} alerts recorded",
                    "why": "Unusually high alert volume",
                    "assessment": "investigation_needed"
                }
    
    def _get_standby_context(self, alerts: List[Dict], database: str = None) -> str:
        """Get context for standby/Data Guard related queries."""
        if not alerts:
            return "No standby or Data Guard alerts found, which typically indicates healthy replication."
        
        count = len(alerts)
        
        if count <= 5:
            return (
                f"Found {count} standby-related alert{'s' if count > 1 else ''}. "
                "Review the alert details to assess replication health."
            )
        else:
            return (
                f"Found {count:,} standby-related alerts. This volume may indicate "
                "ongoing replication issues that could impact DR readiness."
            )
    
    # =========================================================================
    # LAYER 4: HUMAN-LIKE RESPONSE FORMATTING
    # =========================================================================
    
    def _format_count_response(
        self,
        data: Dict[str, Any],
        intent: Dict[str, Any] = None,
        context: Dict[str, Any] = None
    ) -> str:
        """Format count response with DBA intelligence."""
        count = data.get("count", 0)
        database = data.get("database") or (intent or {}).get("database")
        severity = data.get("severity") or (intent or {}).get("severity")
        category = data.get("category") or (intent or {}).get("category")
        alerts = data.get("alerts", [])
        
        # Layer 2: Incident reasoning (for high volumes)
        incident_analysis = None
        incident_explanation = ""
        if count > self.HIGH_VOLUME_THRESHOLD and alerts:
            incident_analysis = self._analyze_incident_patterns(alerts)
            incident_explanation = self._explain_incident_reasoning(incident_analysis)
        
        # Layer 3: Contextual assessment
        severity_context = self._assess_severity_context(count, severity, database)
        
        # Layer 4: Build human-like response
        response_parts = []
        
        # Direct answer (always first)
        if database and database.upper() != "ALL":
            if severity and severity.upper() != "ALL":
                response_parts.append(
                    f"Yes — **{database}** currently has **{count:,}** {severity.lower()} alerts"
                )
            else:
                response_parts.append(
                    f"**{database}** has **{count:,}** alerts"
                )
        else:
            if severity and severity.upper() != "ALL":
                response_parts.append(
                    f"There are **{count:,}** {severity.lower()} alerts across all databases"
                )
            else:
                response_parts.append(
                    f"The system has **{count:,}** total alerts"
                )
        
        # Add category context
        if category:
            cat_lower = category.lower()
            if "standby" in cat_lower or "dataguard" in cat_lower:
                response_parts[0] += " related to standby/Data Guard"
        
        response_parts[0] += "."
        
        # Add interpretation (Layer 3)
        assessment = severity_context.get("assessment", "normal")
        
        if assessment == "immediate_investigation":
            response_parts.append(
                "\n\nThis is **significantly higher than normal** and likely requires immediate investigation."
            )
        elif assessment == "review_recommended":
            response_parts.append(
                "\n\nThis warrants review by a DBA to determine if action is needed."
            )
        elif assessment == "healthy" and count == 0:
            response_parts.append(
                "\n\nNo matching alerts is typically a healthy indicator."
            )
        
        # Add incident reasoning (Layer 2)
        if incident_explanation:
            response_parts.append(f"\n\n{incident_explanation}")
        
        return "".join(response_parts)
    
    def _format_list_response(
        self,
        data: Dict[str, Any],
        intent: Dict[str, Any] = None,
        context: Dict[str, Any] = None
    ) -> str:
        """Format list response with DBA intelligence."""
        alerts = data.get("alerts", [])
        total = data.get("total_count", len(alerts))
        shown = data.get("shown_count", len(alerts))
        database = data.get("database") or (intent or {}).get("database")
        severity = data.get("severity") or (intent or {}).get("severity")
        
        if not alerts:
            return self._format_no_alerts_response(database, severity, intent)
        
        response_parts = []
        
        # Header with context
        header = self._build_list_header(shown, total, database, severity)
        response_parts.append(header)
        response_parts.append("\n")
        
        # Format alert list
        for i, alert in enumerate(alerts, 1):
            db = alert.get("database") or alert.get("target") or alert.get("target_name") or "UNKNOWN"
            sev = alert.get("severity") or alert.get("alert_state") or "UNKNOWN"
            msg = alert.get("message") or alert.get("description") or alert.get("issue_type") or "No details"
            
            # Truncate long messages
            if len(msg) > 120:
                msg = msg[:117] + "..."
            
            response_parts.append(f"\n{i}. **[{sev}]** {db}: {msg}")
        
        # Add summary context for large sets
        if total > shown:
            response_parts.append(f"\n\n*Showing {shown} of {total:,} alerts. Ask to see more if needed.*")
        
        # Add incident pattern insight for large volumes
        if total > 100:
            pattern_analysis = self._analyze_incident_patterns(alerts)
            if pattern_analysis.get("top_error_codes"):
                top_code = pattern_analysis["top_error_codes"][0]
                response_parts.append(
                    f"\n\n**Note:** The most common error code is `{top_code[0]}` "
                    f"({top_code[1]:,} occurrences)."
                )
        
        return "".join(response_parts)
    
    def _format_status_response(
        self,
        data: Dict[str, Any],
        intent: Dict[str, Any] = None,
        context: Dict[str, Any] = None
    ) -> str:
        """Format status response with DBA intelligence."""
        database = data.get("database")
        
        if database:
            return self._format_single_db_status(data, database)
        else:
            return self._format_system_status(data)
    
    def _format_single_db_status(self, data: Dict, database: str) -> str:
        """Format single database status."""
        status = data.get("status", "UNKNOWN")
        critical = data.get("critical_count", 0)
        warning = data.get("warning_count", 0)
        total = data.get("total_alerts", critical + warning)
        
        response_parts = []
        
        # Status line with DBA context
        if status == "HEALTHY" or (critical == 0 and warning == 0):
            response_parts.append(
                f"**{database}** is operating normally with no active alerts."
            )
        elif critical == 0:
            response_parts.append(
                f"**{database}** has {warning:,} warning alert{'s' if warning != 1 else ''} "
                "but no critical issues. The database is operational."
            )
        else:
            response_parts.append(
                f"**{database}** requires attention:\n\n"
                f"- 🔴 **CRITICAL:** {critical:,}\n"
                f"- 🟡 **WARNING:** {warning:,}\n"
                f"- **Total alerts:** {total:,}"
            )
            
            # Add severity assessment
            if critical > self.CRITICAL_THRESHOLD:
                response_parts.append(
                    "\n\nThis volume of critical alerts is unusually high and typically indicates "
                    "a systemic problem rather than routine monitoring noise."
                )
        
        return "".join(response_parts)
    
    def _format_system_status(self, data: Dict) -> str:
        """Format overall system status."""
        databases = data.get("databases", {})
        total_alerts = data.get("total_alerts", 0)
        db_count = data.get("database_count", len(databases))
        
        if db_count == 0:
            return "No database monitoring data is currently available."
        
        # Sort by severity
        sorted_dbs = sorted(
            databases.items(),
            key=lambda x: (x[1].get("critical", 0) * 1000 + x[1].get("warning", 0)),
            reverse=True
        )
        
        response_parts = []
        response_parts.append(
            f"**System Overview:** Monitoring {db_count} databases with {total_alerts:,} total alerts.\n"
        )
        
        # Count databases by status
        critical_dbs = sum(1 for _, s in sorted_dbs if s.get("critical", 0) > 0)
        warning_only = sum(1 for _, s in sorted_dbs if s.get("critical", 0) == 0 and s.get("warning", 0) > 0)
        healthy = db_count - critical_dbs - warning_only
        
        response_parts.append(f"\n- 🔴 Databases with critical alerts: **{critical_dbs}**")
        response_parts.append(f"\n- 🟡 Databases with warnings only: **{warning_only}**")
        response_parts.append(f"\n- 🟢 Healthy databases: **{healthy}**")
        
        # Show top problematic databases
        if critical_dbs > 0:
            response_parts.append("\n\n**Databases requiring attention:**\n")
            shown = 0
            for db, stats in sorted_dbs:
                if stats.get("critical", 0) > 0 and shown < 5:
                    response_parts.append(
                        f"- **{db}**: {stats.get('critical', 0)} critical, "
                        f"{stats.get('warning', 0)} warning\n"
                    )
                    shown += 1
        
        return "".join(response_parts)
    
    def _format_fact_response(
        self,
        data: Dict[str, Any],
        intent: Dict[str, Any] = None,
        context: Dict[str, Any] = None
    ) -> str:
        """Format fact/summary response with DBA intelligence."""
        total = data.get("total_alerts", 0)
        severity_breakdown = data.get("severity_breakdown", {})
        database = data.get("database")
        
        if total == 0:
            if database:
                return f"No alerts are recorded for **{database}** in the current dataset."
            return "No alerts are recorded in the current dataset."
        
        response_parts = []
        
        # Headline
        if database:
            response_parts.append(f"**Alert Summary for {database}:**\n")
        else:
            response_parts.append("**System Alert Summary:**\n")
        
        response_parts.append(f"\n**Total:** {total:,} alerts\n")
        
        # Severity breakdown with context
        if severity_breakdown:
            critical = severity_breakdown.get("CRITICAL", 0)
            warning = severity_breakdown.get("WARNING", 0)
            
            response_parts.append("\n**By Severity:**")
            for sev in ["CRITICAL", "WARNING", "INFO"]:
                if sev in severity_breakdown:
                    count = severity_breakdown[sev]
                    pct = (count / total * 100) if total > 0 else 0
                    response_parts.append(f"\n- {sev}: {count:,} ({pct:.1f}%)")
            
            # Add interpretation
            if critical > 0:
                crit_pct = (critical / total * 100)
                if crit_pct > 50:
                    response_parts.append(
                        f"\n\n**Assessment:** Over half of all alerts are critical, "
                        "which is unusual and warrants immediate review."
                    )
                elif crit_pct > 20:
                    response_parts.append(
                        f"\n\n**Assessment:** A significant portion ({crit_pct:.0f}%) of alerts "
                        "are critical. Prioritize investigating these first."
                    )
        
        return "".join(response_parts)
    
    def _format_comparison_response(
        self,
        data: Dict[str, Any],
        intent: Dict[str, Any] = None,
        context: Dict[str, Any] = None
    ) -> str:
        """Format comparison response."""
        items = data.get("items", [])
        comparison_type = data.get("comparison_type", "count")
        
        if not items:
            return "No comparison data available."
        
        response_parts = []
        response_parts.append("**Comparison Results:**\n")
        
        for i, item in enumerate(items[:10], 1):
            name = item.get("name") or item.get("database") or "Unknown"
            value = item.get("count", 0)
            response_parts.append(f"\n{i}. **{name}**: {value:,}")
        
        return "".join(response_parts)
    
    def _format_trend_response(
        self,
        data: Dict[str, Any],
        intent: Dict[str, Any] = None,
        context: Dict[str, Any] = None
    ) -> str:
        """Format trend response with temporal intelligence."""
        time_range = data.get("time_range", {})
        trend_data = data.get("trend", [])
        
        if not trend_data:
            start = time_range.get("start", "unknown")
            end = time_range.get("end", "unknown")
            return (
                f"I don't see alert data for the specified time range ({start} to {end}). "
                "This may mean alerts were not captured for that period or the CSV "
                "does not include that range."
            )
        
        response_parts = []
        response_parts.append("**Trend Analysis:**\n")
        
        for period in trend_data:
            label = period.get("label", "Period")
            count = period.get("count", 0)
            response_parts.append(f"\n- {label}: {count:,} alerts")
        
        return "".join(response_parts)
    
    def _format_general_response(
        self,
        data: Dict[str, Any],
        intent: Dict[str, Any] = None,
        context: Dict[str, Any] = None
    ) -> str:
        """Format general response with DBA intelligence."""
        # Extract what we can from the data
        if "count" in data:
            return self._format_count_response(data, intent, context)
        elif "alerts" in data and isinstance(data["alerts"], list):
            return self._format_list_response(data, intent, context)
        elif "status" in data:
            return self._format_status_response(data, intent, context)
        else:
            # Fallback - describe what we found
            return "I've processed your request. Please let me know if you need more specific information."
    
    # =========================================================================
    # LAYER 5: ACTIONABLE DBA GUIDANCE
    # =========================================================================
    
    def add_dba_guidance(
        self,
        response: str,
        severity: str = None,
        alert_count: int = 0,
        error_code: str = None,
        include_guidance: bool = True
    ) -> str:
        """
        Add actionable DBA guidance to response (without hallucination).
        
        Recommendations are clearly marked as suggestions, not facts.
        """
        if not include_guidance:
            return response
        
        guidance_parts = []
        
        # Add guidance based on severity
        severity_upper = (severity or "").upper()
        
        if severity_upper == "CRITICAL" and alert_count > 0:
            if error_code and error_code.startswith("ORA-600"):
                guidance_parts.append(
                    "\n\n**Suggested Next Step:** Based on similar Oracle incidents, "
                    "DBAs typically start by reviewing the alert log around the first "
                    f"occurrence of {error_code} to identify the triggering condition."
                )
            elif error_code and error_code.startswith("ORA-"):
                guidance_parts.append(
                    f"\n\n**Suggested Next Step:** Review the alert log entries "
                    f"associated with {error_code} and check Oracle Support for "
                    "known issues matching this error pattern."
                )
            elif alert_count > self.CRITICAL_THRESHOLD:
                guidance_parts.append(
                    "\n\n**Suggested Next Step:** Review the alert log for the "
                    "earliest critical alert to identify the initial trigger. "
                    "High volumes often indicate a cascading failure from a single root cause."
                )
        
        elif severity_upper == "WARNING" and alert_count > self.WARNING_THRESHOLD:
            guidance_parts.append(
                "\n\n**Suggested Next Step:** Consider reviewing warning patterns "
                "to identify if any are precursors to potential issues. "
                "Proactive resolution of warnings can prevent escalation to critical."
            )
        
        if guidance_parts:
            response += "".join(guidance_parts)
        
        return response
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _format_no_data_response(
        self,
        intent: Dict[str, Any] = None,
        context: Dict[str, Any] = None
    ) -> str:
        """Format response when no data is available."""
        database = (intent or {}).get("database")
        severity = (intent or {}).get("severity")
        
        if database:
            return (
                f"I don't see any alerts for **{database}** in the current dataset. "
                "This may indicate the database is healthy, or it's not included "
                "in the monitoring scope."
            )
        elif severity:
            return (
                f"No {severity.lower()} alerts are recorded in the current dataset. "
                "This is typically a healthy indicator."
            )
        else:
            return (
                "No alert data is available. This may indicate a healthy state "
                "or that data has not been loaded yet."
            )
    
    def _format_no_alerts_response(
        self,
        database: str = None,
        severity: str = None,
        intent: Dict[str, Any] = None
    ) -> str:
        """Format response when no alerts match the query."""
        if database and severity:
            return (
                f"No {severity.lower()} alerts found for **{database}**. "
                "This usually indicates the database is healthy for this severity level."
            )
        elif database:
            return (
                f"No alerts are recorded for **{database}**, which usually indicates a healthy state."
            )
        elif severity:
            return (
                f"No {severity.lower()} alerts are recorded, which is typically positive."
            )
        else:
            return "No alerts match your query criteria."
    
    def _build_list_header(
        self,
        shown: int,
        total: int,
        database: str = None,
        severity: str = None
    ) -> str:
        """Build contextual header for list responses."""
        parts = []
        
        if severity and severity.upper() != "ALL":
            parts.append(f"**{severity.upper()}**")
        
        parts.append("Alerts")
        
        if database and database.upper() != "ALL":
            parts.append(f"for **{database}**")
        
        header = " ".join(parts)
        
        if shown < total:
            header += f" (showing {shown} of {total:,})"
        else:
            header += f" ({total:,} total)"
        
        return header + ":"
    
    # =========================================================================
    # UNCERTAINTY & CONFIDENCE HANDLING
    # =========================================================================
    
    def format_low_confidence_response(
        self,
        confidence: float,
        parsed_intent: Dict[str, Any] = None,
        suggestions: List[str] = None
    ) -> str:
        """
        Generate clarifying question when confidence is low.
        
        Used when intent confidence < 0.7
        """
        database = (parsed_intent or {}).get("database")
        severity = (parsed_intent or {}).get("severity")
        
        if database and not severity:
            return (
                f"I understand you're asking about **{database}**. "
                "Could you clarify — do you want the total count, only critical alerts, "
                "or a specific type of information?"
            )
        elif severity and not database:
            return (
                f"You're asking about {severity.lower()} alerts. "
                "Would you like the count across all databases, or for a specific database?"
            )
        elif suggestions:
            suggestion_text = ", ".join(f'"{s}"' for s in suggestions[:3])
            return (
                "I'm not entirely sure what you're asking. "
                f"Did you mean one of these: {suggestion_text}?"
            )
        else:
            return (
                "I want to make sure I understand your question correctly. "
                "Could you please rephrase or provide more details?"
            )
    
    # =========================================================================
    # CONTEXT SWITCH HANDLING
    # =========================================================================
    
    def format_context_switch_notice(
        self,
        from_context: Dict[str, Any],
        to_context: Dict[str, Any]
    ) -> str:
        """Generate notice when context is switching."""
        from_db = from_context.get("database")
        to_db = to_context.get("database")
        
        if from_db and to_db and from_db != to_db:
            return f"*Switching from {from_db} alerts to {to_db} alerts.*\n\n"
        elif from_db and not to_db:
            return f"*Switching from {from_db} alerts to system-wide alerts.*\n\n"
        elif not from_db and to_db:
            return f"*Focusing on {to_db} alerts.*\n\n"
        
        return ""


# Singleton instance
_formatter_instance = None


def get_dba_formatter() -> DBAIntelligenceFormatter:
    """Get or create the DBA Intelligence Formatter instance."""
    global _formatter_instance
    if _formatter_instance is None:
        _formatter_instance = DBAIntelligenceFormatter()
    return _formatter_instance


def format_dba_response(
    raw_data: Dict[str, Any],
    query_type: str,
    intent: Dict[str, Any] = None,
    context: Dict[str, Any] = None
) -> str:
    """Convenience function to format a DBA-intelligent response."""
    formatter = get_dba_formatter()
    return formatter.format_response(raw_data, query_type, intent, context)
