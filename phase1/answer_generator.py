"""
PHASE 1: Answer Generator
=========================
Generates human-readable, factual answers from query results.

RULES:
- Responses MUST be 100% based on CSV data
- Be factual and verifiable
- Use simple, human DBA language
- Avoid technical AI wording
- If data missing → say so explicitly

🧠 ENTERPRISE DBA INTELLIGENCE (5 Layers):
1️⃣ FACTUAL ACCURACY - Use ONLY provided data
2️⃣ INCIDENT REASONING - Detect duplicates vs unique issues
3️⃣ CONTEXTUAL DBA EXPLANATION - What/Why/Assessment
4️⃣ HUMAN-LIKE RESPONSE STYLE - Calm, professional, helpful
5️⃣ ACTIONABLE DBA GUIDANCE - Recommendations without fabrication

EXAMPLES:
✓ Correct: "Yes — MIDEVSTB currently has 649,769 critical alerts, which is 
           significantly higher than normal and likely requires immediate investigation."
✗ Incorrect: "649,769 CRITICAL alerts exist."
"""

from typing import Dict, Any

# Import DBA Intelligence Formatter
try:
    from reasoning.dba_intelligence_formatter import (
        get_dba_formatter, DBAIntelligenceFormatter
    )
    HAS_DBA_FORMATTER = True
except ImportError:
    HAS_DBA_FORMATTER = False


class Phase1AnswerGenerator:
    """
    Generates deterministic, data-backed answers with DBA intelligence.
    
    No hallucination - every statement is backed by query results.
    Uses DBA Intelligence Formatter for enterprise-grade responses.
    """
    
    def __init__(self):
        """Initialize with DBA formatter if available."""
        self.dba_formatter = None
        if HAS_DBA_FORMATTER:
            try:
                self.dba_formatter = get_dba_formatter()
            except Exception:
                pass
    
    def generate(self, query_result: Dict[str, Any], intent: Dict[str, Any]) -> str:
        """
        Generate a human-readable answer from query result.
        
        Uses DBA Intelligence Formatter for enterprise-grade responses.
        
        Args:
            query_result: Result from Phase1QueryEngine
            intent: Original parsed intent
            
        Returns:
            Human-readable answer string with DBA context
        """
        if not query_result.get("success"):
            return self._generate_error_response(query_result)
        
        intent_type = query_result.get("intent_type", "UNKNOWN")
        data = query_result.get("data", {})
        
        # Try DBA Intelligence Formatter first for enhanced responses
        if self.dba_formatter:
            try:
                response = self.dba_formatter.format_response(
                    raw_data=data,
                    query_type=intent_type,
                    intent=intent
                )
                if response:
                    # Add DBA guidance for high-severity situations
                    severity = intent.get("severity") or data.get("severity")
                    count = data.get("count", 0)
                    response = self.dba_formatter.add_dba_guidance(
                        response, 
                        severity=severity,
                        alert_count=count
                    )
                    return response
            except Exception:
                pass  # Fall back to basic formatting
        
        # Fallback to basic formatting
        if intent_type == "COUNT":
            return self._generate_count_answer(data, intent)
        elif intent_type == "LIST":
            return self._generate_list_answer(data, intent)
        elif intent_type == "STATUS":
            return self._generate_status_answer(data, intent)
        elif intent_type == "FACT":
            return self._generate_fact_answer(data, intent)
        else:
            return "I don't have enough information in the current dataset to answer this."
    
    def _generate_error_response(self, query_result: Dict) -> str:
        """Generate error response with DBA-friendly language."""
        error = query_result.get("error", "UNKNOWN_ERROR")
        message = query_result.get("message", "")
        
        if error == "DATA_NOT_LOADED":
            return "Alert data is not currently available. Please wait for the monitoring system to initialize."
        elif error == "UNKNOWN_INTENT":
            return (
                "I want to make sure I understand your question correctly. "
                "Could you please rephrase or provide more details?"
            )
        elif error == "UNSUPPORTED_INTENT":
            return message or "This type of question is not supported in the current version."
        elif error == "NO_DATA":
            return message or "No data matching your query was found in the monitoring dataset."
        else:
            return "I encountered an issue processing your request. Please try rephrasing your question."
    
    def _generate_count_answer(self, data: Dict, intent: Dict) -> str:
        """Generate answer for COUNT queries with DBA intelligence."""
        count = data.get("count", 0)
        database = data.get("database")
        severity = data.get("severity")
        category = data.get("category")
        
        # Build DBA-style response
        response_parts = []
        
        # Direct answer first (DBA-friendly style)
        if database and database.upper() != "ALL":
            if severity and severity.upper() != "ALL":
                if count == 0:
                    response_parts.append(
                        f"**{database}** has no {severity.lower()} alerts — "
                        "this is typically a healthy indicator."
                    )
                else:
                    response_parts.append(
                        f"Yes — **{database}** currently has **{count:,}** {severity.lower()} "
                        f"alert{'s' if count != 1 else ''}."
                    )
            else:
                if count == 0:
                    response_parts.append(
                        f"No alerts are recorded for **{database}**, which usually indicates a healthy state."
                    )
                else:
                    response_parts.append(
                        f"**{database}** has **{count:,}** alert{'s' if count != 1 else ''}."
                    )
        else:
            if severity and severity.upper() != "ALL":
                if count == 0:
                    response_parts.append(
                        f"There are no {severity.lower()} alerts across all databases. "
                        "This is typically a positive indicator."
                    )
                else:
                    response_parts.append(
                        f"There are **{count:,}** {severity.lower()} alert{'s' if count != 1 else ''} "
                        "across all monitored databases."
                    )
            else:
                if count == 0:
                    response_parts.append(
                        "No alerts are recorded in the current dataset."
                    )
                else:
                    response_parts.append(
                        f"The system has **{count:,}** total alert{'s' if count != 1 else ''}."
                    )
        
        # Add category context
        if category and category.upper() in ("STANDBY", "DATAGUARD"):
            response_parts.append(" (related to standby/Data Guard)")
        
        # Add severity assessment for high volumes
        if count > 10 and severity and severity.upper() == "CRITICAL":
            response_parts.append(
                "\n\nThis volume of critical alerts is higher than typical and "
                "likely requires investigation."
            )
        elif count > 10000:
            response_parts.append(
                "\n\nThis is a high volume of alerts. Consider reviewing for "
                "duplicate or recurring issues."
            )
        
        return "".join(response_parts)
    
    def _generate_list_answer(self, data: Dict, intent: Dict) -> str:
        """Generate answer for LIST queries with DBA context."""
        alerts = data.get("alerts", [])
        total = data.get("total_count", 0)
        shown = data.get("shown_count", 0)
        database = data.get("database")
        severity = data.get("severity")
        
        if total == 0:
            # No alerts found
            filter_parts = []
            if severity:
                filter_parts.append(severity.lower())
            if database and database != "ALL":
                filter_parts.append(f"for {database}")
            
            filter_desc = " ".join(filter_parts) if filter_parts else ""
            return f"No {filter_desc} alerts found in the dataset.".strip()
        
        # Build header
        header_parts = []
        if severity and severity != "ALL":
            header_parts.append(f"**{severity}**")
        header_parts.append("Alerts")
        if database and database != "ALL":
            header_parts.append(f"for **{database}**")
        
        header = " ".join(header_parts)
        
        # Show count info
        if shown < total:
            answer = f"{header} (showing {shown} of {total:,}):\n\n"
        else:
            answer = f"{header} ({total:,} total):\n\n"
        
        # List alerts
        for i, alert in enumerate(alerts, 1):
            db = alert.get("database", "UNKNOWN")
            sev = alert.get("severity", "UNKNOWN")
            msg = alert.get("message", "No message")
            
            # Truncate long messages
            if len(msg) > 100:
                msg = msg[:97] + "..."
            
            answer += f"{i}. [{sev}] **{db}**: {msg}\n"
        
        return answer.strip()
    
    def _generate_status_answer(self, data: Dict, intent: Dict) -> str:
        """Generate answer for STATUS queries."""
        database = data.get("database")
        
        if database:
            # Single database status
            status = data.get("status", "UNKNOWN")
            critical = data.get("critical_count", 0)
            warning = data.get("warning_count", 0)
            total = data.get("total_alerts", 0)
            
            if status == "HEALTHY":
                return f"Database **{database}** has no alerts. Status: **HEALTHY**."
            
            answer = f"Database **{database}** status: **{status}**\n\n"
            answer += f"- CRITICAL alerts: {critical:,}\n"
            answer += f"- WARNING alerts: {warning:,}\n"
            answer += f"- Total alerts: {total:,}"
            
            return answer
        else:
            # All databases status
            databases = data.get("databases", {})
            total_alerts = data.get("total_alerts", 0)
            db_count = data.get("database_count", 0)
            
            if db_count == 0:
                return "No databases found in the dataset."
            
            answer = f"**Status Summary** ({db_count} databases, {total_alerts:,} total alerts):\n\n"
            
            # Sort by critical count (highest first)
            sorted_dbs = sorted(
                databases.items(),
                key=lambda x: (x[1].get("critical", 0), x[1].get("warning", 0)),
                reverse=True
            )
            
            for db, stats in sorted_dbs[:10]:  # Limit to top 10
                critical = stats.get("critical", 0)
                warning = stats.get("warning", 0)
                total = stats.get("total", 0)
                
                status_emoji = "🔴" if critical > 0 else ("🟡" if warning > 0 else "🟢")
                answer += f"{status_emoji} **{db}**: {critical} critical, {warning} warning ({total} total)\n"
            
            if len(sorted_dbs) > 10:
                answer += f"\n*...and {len(sorted_dbs) - 10} more databases*"
            
            return answer.strip()
    
    def _generate_fact_answer(self, data: Dict, intent: Dict) -> str:
        """Generate answer for FACT queries."""
        total = data.get("total_alerts", 0)
        severity_breakdown = data.get("severity_breakdown", {})
        db_breakdown = data.get("database_breakdown", {})
        database = data.get("database")
        
        if total == 0:
            if database and database != "ALL":
                return f"No alerts found for database **{database}** in the dataset."
            return "No alerts found in the dataset."
        
        # Build fact summary
        if database and database != "ALL":
            answer = f"**Alert Summary for {database}:**\n\n"
        else:
            answer = f"**Alert Summary:**\n\n"
        
        answer += f"**Total Alerts:** {total:,}\n\n"
        
        # Severity breakdown
        if severity_breakdown:
            answer += "**By Severity:**\n"
            for sev in ["CRITICAL", "WARNING", "INFO"]:
                if sev in severity_breakdown:
                    answer += f"- {sev}: {severity_breakdown[sev]:,}\n"
            # Add any other severities
            for sev, count in severity_breakdown.items():
                if sev not in ["CRITICAL", "WARNING", "INFO"]:
                    answer += f"- {sev}: {count:,}\n"
        
        # Database breakdown (only if not filtering by specific DB)
        if not database or database == "ALL":
            if db_breakdown and len(db_breakdown) <= 5:
                answer += "\n**By Database:**\n"
                for db, count in sorted(db_breakdown.items(), key=lambda x: -x[1]):
                    answer += f"- {db}: {count:,}\n"
            elif db_breakdown:
                answer += f"\n**Across {len(db_breakdown)} databases**"
        
        return answer.strip()


# Singleton instance
_generator_instance = None

def get_generator() -> Phase1AnswerGenerator:
    """Get or create the answer generator instance."""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = Phase1AnswerGenerator()
    return _generator_instance


def generate_answer(query_result: Dict[str, Any], intent: Dict[str, Any]) -> str:
    """Convenience function to generate an answer."""
    generator = get_generator()
    return generator.generate(query_result, intent)
