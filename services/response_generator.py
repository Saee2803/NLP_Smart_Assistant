# -*- coding: utf-8 -*-
"""
Response Generator - Generates natural language responses from query results
Formats answers based on question type and query results
"""

from typing import Dict, Any, List, Optional


class ResponseGenerator:
    """Generates formatted responses from query results"""
    
    def __init__(self):
        self.templates = self._init_templates()
    
    def _init_templates(self) -> Dict[str, str]:
        """Initialize response templates"""
        return {
            'count_simple': "There are **{count}** alerts{filter_desc}.",
            'count_with_breakdown': "There are **{count}** alerts{filter_desc}.\n\n**Breakdown by Severity:**\n{breakdown}",
            'summary': "**Alert Summary{filter_desc}:**\n\nTotal: **{count}** alerts\n\n{details}",
            'list_header': "Showing **{showing}** of **{total}** alerts{filter_desc}:\n",
            'no_results': "No alerts found{filter_desc}.",
            'comparison': "**Comparison{filter_desc}:**\n\n{details}",
            'error': "Sorry, I encountered an error: {error}",
        }
    
    def generate(self, 
                 query_result, 
                 query_plan, 
                 intent: str = None,
                 question_type: str = 'FACT') -> str:
        """Generate a natural language response from query result"""
        
        if not query_result.success:
            return self.templates['error'].format(error=query_result.error_message)
        
        # Route to appropriate generator
        if query_result.query_type == 'COUNT':
            return self._generate_count_response(query_result, query_plan)
        elif query_result.query_type == 'SUMMARY':
            return self._generate_summary_response(query_result, query_plan)
        elif query_result.query_type == 'LIST':
            return self._generate_list_response(query_result, query_plan)
        elif query_result.query_type == 'AGGREGATE':
            return self._generate_aggregate_response(query_result, query_plan)
        elif query_result.query_type == 'DETAIL':
            return self._generate_detail_response(query_result, query_plan)
        elif query_result.query_type == 'COMPARE':
            return self._generate_compare_response(query_result, query_plan)
        else:
            return self._generate_summary_response(query_result, query_plan)
    
    def _build_filter_description(self, filters: Dict[str, Any]) -> str:
        """Build a human-readable filter description"""
        if not filters:
            return ""
        
        parts = []
        
        if filters.get('database'):
            parts.append(f"for **{filters['database']}**")
        elif filters.get('databases'):
            dbs = ', '.join(filters['databases'])
            parts.append(f"for databases **{dbs}**")
        
        if filters.get('severity'):
            parts.append(f"with **{filters['severity']}** severity")
        elif filters.get('severities'):
            sevs = ', '.join(filters['severities'])
            parts.append(f"with **{sevs}** severities")
        
        if filters.get('alert_type'):
            parts.append(f"related to **{filters['alert_type']}**")
        
        if filters.get('issue_type'):
            parts.append(f"about **{filters['issue_type'].lower()}** issues")
        
        if filters.get('time_range'):
            time_map = {
                'today': 'from today',
                'last_24h': 'from last 24 hours',
                'last_hour': 'from last hour',
                'this_week': 'from this week',
                'last_7_days': 'from last 7 days',
                'this_month': 'from this month'
            }
            time_desc = time_map.get(filters['time_range'], '')
            if time_desc:
                parts.append(time_desc)
        
        if not parts:
            return ""
        
        return " " + " ".join(parts)
    
    def _format_severity_breakdown(self, by_severity: Dict[str, int]) -> str:
        """Format severity breakdown as bullet list"""
        if not by_severity:
            return ""
        
        lines = []
        # Order: Critical first, then Warning, then others
        order = ['Critical', 'CRITICAL', 'Warning', 'WARNING', 'Info', 'INFO']
        
        # Add in preferred order
        for sev in order:
            if sev in by_severity:
                count = by_severity[sev]
                emoji = self._get_severity_emoji(sev)
                lines.append(f"- {emoji} **{sev}**: {count}")
        
        # Add any remaining
        for sev, count in by_severity.items():
            if sev not in order:
                lines.append(f"- **{sev}**: {count}")
        
        return "\n".join(lines)
    
    def _get_severity_emoji(self, severity: str) -> str:
        """Get emoji for severity level"""
        severity_upper = severity.upper() if severity else ''
        if 'CRITICAL' in severity_upper:
            return "🔴"
        elif 'WARNING' in severity_upper:
            return "🟡"
        elif 'INFO' in severity_upper:
            return "🔵"
        else:
            return "⚪"
    
    def _generate_count_response(self, result, plan) -> str:
        """Generate response for COUNT query"""
        count = result.filtered_count
        filter_desc = self._build_filter_description(plan.filters)
        
        if count == 0:
            return self.templates['no_results'].format(filter_desc=filter_desc)
        
        by_severity = result.aggregations.get('by_severity', {})
        
        if by_severity and len(by_severity) > 1:
            breakdown = self._format_severity_breakdown(by_severity)
            return self.templates['count_with_breakdown'].format(
                count=count,
                filter_desc=filter_desc,
                breakdown=breakdown
            )
        else:
            return self.templates['count_simple'].format(
                count=count,
                filter_desc=filter_desc
            )
    
    def _generate_summary_response(self, result, plan) -> str:
        """Generate response for SUMMARY query"""
        count = result.filtered_count
        filter_desc = self._build_filter_description(plan.filters)
        
        if count == 0:
            return self.templates['no_results'].format(filter_desc=filter_desc)
        
        details_parts = []
        
        # Severity breakdown
        by_severity = result.aggregations.get('by_severity', {})
        if by_severity:
            details_parts.append("**By Severity:**\n" + self._format_severity_breakdown(by_severity))
        
        # Database breakdown (if no specific database filter)
        if not plan.filters.get('database') and not plan.filters.get('databases'):
            by_db = result.aggregations.get('by_database', {})
            if by_db:
                db_lines = [f"- **{db}**: {count}" for db, count in list(by_db.items())[:5]]
                details_parts.append("**By Database:**\n" + "\n".join(db_lines))
        
        # Top messages
        top_msgs = result.aggregations.get('top_messages', {})
        if top_msgs:
            msg_lines = []
            for msg, count in list(top_msgs.items())[:3]:
                short_msg = msg[:80] + "..." if len(msg) > 80 else msg
                msg_lines.append(f"- `{short_msg}` ({count})")
            details_parts.append("**Top Alert Types:**\n" + "\n".join(msg_lines))
        
        details = "\n\n".join(details_parts)
        
        return self.templates['summary'].format(
            filter_desc=filter_desc,
            count=count,
            details=details
        )
    
    def _generate_list_response(self, result, plan) -> str:
        """Generate response for LIST query"""
        count = result.filtered_count
        filter_desc = self._build_filter_description(plan.filters)
        
        if count == 0:
            return self.templates['no_results'].format(filter_desc=filter_desc)
        
        showing = result.metadata.get('showing', len(result.data))
        
        response_parts = []
        
        # Header
        response_parts.append(self.templates['list_header'].format(
            showing=showing,
            total=count,
            filter_desc=filter_desc
        ))
        
        # Alert list
        for i, alert in enumerate(result.data, 1):
            target = alert.get('target_name', 'Unknown')
            severity = alert.get('alert_state', 'Unknown')
            message = alert.get('message', 'No message')
            alert_time = alert.get('alert_time', '')
            
            # Truncate message if too long
            if len(message) > 100:
                message = message[:100] + "..."
            
            emoji = self._get_severity_emoji(severity)
            
            response_parts.append(f"{i}. {emoji} **{target}** - {severity}")
            response_parts.append(f"   `{message}`")
            if alert_time:
                response_parts.append(f"   📅 {alert_time}")
            response_parts.append("")
        
        # Pagination info
        if result.metadata.get('has_more'):
            offset = result.metadata.get('offset', 0)
            limit = result.metadata.get('limit', 10)
            response_parts.append(f"\n*Showing {offset + 1}-{offset + showing}. Ask for \"next\" or \"more\" to see more alerts.*")
        
        return "\n".join(response_parts)
    
    def _generate_aggregate_response(self, result, plan) -> str:
        """Generate response for AGGREGATE query"""
        group_by = result.aggregations.get('group_by', 'category')
        counts = result.aggregations.get('counts', {})
        total = result.aggregations.get('total', 0)
        filter_desc = self._build_filter_description(plan.filters)
        
        if total == 0:
            return self.templates['no_results'].format(filter_desc=filter_desc)
        
        lines = [f"**Alerts grouped by {group_by}{filter_desc}:**\n"]
        lines.append(f"Total: **{total}** alerts\n")
        
        for key, count in counts.items():
            pct = (count / total * 100) if total > 0 else 0
            lines.append(f"- **{key}**: {count} ({pct:.1f}%)")
        
        return "\n".join(lines)
    
    def _generate_detail_response(self, result, plan) -> str:
        """Generate response for DETAIL query"""
        filter_desc = self._build_filter_description(plan.filters)
        
        if not result.data:
            return self.templates['no_results'].format(filter_desc=filter_desc)
        
        lines = [f"**Alert Details{filter_desc}:**\n"]
        
        for i, alert in enumerate(result.data, 1):
            lines.append(f"### Alert {i}")
            lines.append(f"- **Database**: {alert.get('target_name', 'Unknown')}")
            lines.append(f"- **Severity**: {alert.get('alert_state', 'Unknown')}")
            lines.append(f"- **Time**: {alert.get('alert_time', 'Unknown')}")
            lines.append(f"- **Message**: {alert.get('message', 'No message')}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_compare_response(self, result, plan) -> str:
        """Generate response for COMPARE query"""
        aggs = result.aggregations
        
        if not aggs:
            return "Unable to generate comparison."
        
        lines = ["**Comparison:**\n"]
        
        for entity, data in aggs.items():
            if isinstance(data, dict):
                total = data.get('total', 0)
                by_sev = data.get('by_severity', {})
                
                lines.append(f"**{entity}**: {total} total alerts")
                if by_sev:
                    for sev, count in by_sev.items():
                        emoji = self._get_severity_emoji(sev)
                        lines.append(f"  - {emoji} {sev}: {count}")
                lines.append("")
        
        return "\n".join(lines)
    
    def generate_followup_suggestions(self, result, plan, intent: str) -> List[str]:
        """Generate suggested follow-up questions"""
        suggestions = []
        
        filters = plan.filters or {}
        by_severity = result.aggregations.get('by_severity', {})
        
        # If showing summary, suggest filtering by severity
        if result.query_type in ['COUNT', 'SUMMARY']:
            if 'Critical' in by_severity or 'CRITICAL' in by_severity:
                suggestions.append("Show me the critical alerts")
            if 'Warning' in by_severity or 'WARNING' in by_severity:
                suggestions.append("What about warning alerts?")
        
        # If showing list with more available
        if result.query_type == 'LIST' and result.metadata.get('has_more'):
            suggestions.append("Show me more alerts")
            suggestions.append("Show next 10")
        
        # If filtered by database, suggest comparison
        if filters.get('database'):
            suggestions.append("Compare with other databases")
        
        # Suggest root cause if looking at critical alerts
        severity_val = filters.get('severity', '')
        if isinstance(severity_val, str) and severity_val.upper() == 'CRITICAL':
            suggestions.append("What is the root cause?")
        
        return suggestions[:3]  # Return max 3 suggestions


# Singleton instance
_generator = None

def get_generator() -> ResponseGenerator:
    """Get singleton response generator instance"""
    global _generator
    if _generator is None:
        _generator = ResponseGenerator()
    return _generator


# Test
if __name__ == '__main__':
    from data_engine.query_executor import QueryResult
    
    generator = ResponseGenerator()
    
    # Create mock result
    result = QueryResult()
    result.success = True
    result.query_type = 'SUMMARY'
    result.filtered_count = 150
    result.aggregations = {
        'by_severity': {'Critical': 50, 'Warning': 100},
        'by_database': {'MIDEVSTB': 75, 'MIDEVSTBN': 75}
    }
    
    # Create mock plan
    class MockPlan:
        filters = {'database': 'MIDEVSTB'}
    
    response = generator.generate(result, MockPlan())
    print(response)
