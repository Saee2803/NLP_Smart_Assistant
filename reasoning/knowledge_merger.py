"""
Knowledge Merger - Phase 6 Component
=====================================
Combines all intelligence sources into unified response.

Sources merged:
1. CSV facts (counts, incidents) - PRIMARY SOURCE
2. Incident Intelligence (Phase 4)
3. Predictive signals (Phase 5)
4. DBA Knowledge Base (Phase 6)
5. Incident Memory (Phase 6)

RULE: If knowledge contradicts data → DATA WINS
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class MergedIntelligence:
    """Result of merging all intelligence sources."""
    
    # From CSV data (Phase 1-3) - PRIMARY
    data_facts: Dict
    alert_count: int
    incident_count: int
    
    # From Incident Intelligence (Phase 4)
    incident_analysis: Dict
    priority_assessment: str
    executive_summary: str
    
    # From Predictive Intelligence (Phase 5)
    trend_analysis: Dict
    trajectory_prediction: str
    early_warnings: List[str]
    
    # From Knowledge Base (Phase 6)
    knowledge_context: Dict
    typical_meaning: str
    common_causes: List[str]
    dba_checks: List[str]
    
    # From Incident Memory (Phase 6)
    historical_context: Dict
    similar_incidents: int
    typical_outcome: str
    
    # Combined assessment
    overall_risk: str
    confidence_level: str
    key_insights: List[str]
    recommended_focus: str


class KnowledgeMerger:
    """
    Merges intelligence from all sources.
    
    Priority order (highest first):
    1. CSV data facts - always authoritative
    2. Incident Intelligence - clustered analysis
    3. Predictive Intelligence - forward-looking signals
    4. Knowledge Base - curated DBA knowledge
    5. Incident Memory - historical patterns
    
    RULE: Data wins over knowledge if conflict exists.
    """
    
    def __init__(self):
        self.conflict_log = []
    
    def merge(self,
             data_facts: Dict = None,
             incident_analysis: Dict = None,
             predictive_analysis: Dict = None,
             knowledge_context: Dict = None,
             historical_context: Dict = None) -> MergedIntelligence:
        """
        Merge all intelligence sources into unified view.
        """
        self.conflict_log = []
        
        # Initialize with defaults
        data_facts = data_facts or {}
        incident_analysis = incident_analysis or {}
        predictive_analysis = predictive_analysis or {}
        knowledge_context = knowledge_context or {}
        historical_context = historical_context or {}
        
        # Extract and validate core data
        alert_count = data_facts.get('alert_count', 0)
        incident_count = data_facts.get('incident_count', 0)
        
        # Get incident intelligence
        priority = incident_analysis.get('priority', 'P3')
        executive_summary = incident_analysis.get('executive_summary', '')
        
        # Get predictive signals
        trend = predictive_analysis.get('trend', {})
        trajectory = predictive_analysis.get('trajectory', 'Unknown')
        early_warnings = predictive_analysis.get('early_warnings', [])
        
        # Get knowledge context
        typical_meaning = knowledge_context.get('typical_meaning', '')
        common_causes = knowledge_context.get('common_causes', [])
        dba_checks = knowledge_context.get('dba_first_checks', [])
        
        # Get historical context
        similar_incidents = historical_context.get('similar_incidents', 0)
        typical_outcome = historical_context.get('typical_outcome', 'Unknown')
        
        # Resolve conflicts and generate insights
        overall_risk = self._determine_risk(
            alert_count, incident_count, priority, trend
        )
        
        confidence = self._determine_confidence(
            has_data=alert_count > 0,
            has_incidents=incident_count > 0,
            has_knowledge=bool(typical_meaning),
            has_history=similar_incidents > 0
        )
        
        key_insights = self._generate_insights(
            data_facts, incident_analysis, predictive_analysis,
            knowledge_context, historical_context
        )
        
        recommended_focus = self._determine_focus(
            priority, trend, early_warnings
        )
        
        return MergedIntelligence(
            data_facts=data_facts,
            alert_count=alert_count,
            incident_count=incident_count,
            incident_analysis=incident_analysis,
            priority_assessment=priority,
            executive_summary=executive_summary,
            trend_analysis=trend,
            trajectory_prediction=trajectory,
            early_warnings=early_warnings,
            knowledge_context=knowledge_context,
            typical_meaning=typical_meaning,
            common_causes=common_causes,
            dba_checks=dba_checks,
            historical_context=historical_context,
            similar_incidents=similar_incidents,
            typical_outcome=typical_outcome,
            overall_risk=overall_risk,
            confidence_level=confidence,
            key_insights=key_insights,
            recommended_focus=recommended_focus
        )
    
    def _determine_risk(self, alert_count: int, incident_count: int,
                       priority: str, trend: Dict) -> str:
        """
        Determine overall risk level based on all signals.
        Data-driven signals take precedence.
        """
        risk_score = 0
        
        # Alert volume signals
        if alert_count > 10000:
            risk_score += 3
        elif alert_count > 1000:
            risk_score += 2
        elif alert_count > 100:
            risk_score += 1
        
        # Priority signals
        if priority == 'P1':
            risk_score += 3
        elif priority == 'P2':
            risk_score += 2
        elif priority == 'P3':
            risk_score += 1
        
        # Trend signals
        trend_direction = trend.get('direction', 'stable')
        if trend_direction == 'deteriorating':
            risk_score += 2
        elif trend_direction == 'improving':
            risk_score -= 1
        
        # Convert to risk level
        if risk_score >= 6:
            return 'HIGH'
        elif risk_score >= 3:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _determine_confidence(self, has_data: bool, has_incidents: bool,
                             has_knowledge: bool, has_history: bool) -> str:
        """
        Determine confidence level in the merged intelligence.
        """
        score = 0
        
        if has_data:
            score += 40
        if has_incidents:
            score += 25
        if has_knowledge:
            score += 20
        if has_history:
            score += 15
        
        if score >= 80:
            return 'HIGH'
        elif score >= 50:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _generate_insights(self, data_facts: Dict, incident_analysis: Dict,
                          predictive_analysis: Dict, knowledge_context: Dict,
                          historical_context: Dict) -> List[str]:
        """
        Generate key insights from merged intelligence.
        """
        insights = []
        
        # Data-driven insight
        alert_count = data_facts.get('alert_count', 0)
        if alert_count > 0:
            severity = data_facts.get('severity_breakdown', {})
            critical = severity.get('CRITICAL', 0)
            if critical > 0:
                insights.append(
                    f"Active situation: {alert_count:,} alerts including {critical:,} critical"
                )
        
        # Incident pattern insight
        if incident_analysis.get('top_incident'):
            top = incident_analysis['top_incident']
            insights.append(
                f"Primary incident: {top.get('error_type', 'Unknown')} "
                f"({top.get('count', 0):,} alerts)"
            )
        
        # Trend insight
        trend = predictive_analysis.get('trend', {})
        if trend.get('direction'):
            direction = trend['direction']
            if direction == 'deteriorating':
                insights.append("Trend: Situation appears to be worsening")
            elif direction == 'improving':
                insights.append("Trend: Situation appears to be improving")
        
        # Knowledge-based insight
        if knowledge_context.get('risk_level'):
            risk = knowledge_context['risk_level']
            insights.append(f"Knowledge context: Typically {risk} risk pattern")
        
        # Historical insight
        if historical_context.get('similar_incidents', 0) > 0:
            count = historical_context['similar_incidents']
            outcome = historical_context.get('typical_outcome', 'varied')
            insights.append(
                f"Historical: Similar pattern seen {count} times, "
                f"typically {outcome}"
            )
        
        return insights
    
    def _determine_focus(self, priority: str, trend: Dict,
                        early_warnings: List[str]) -> str:
        """
        Determine recommended focus based on all signals.
        """
        if priority == 'P1':
            return "Immediate attention required - P1 priority incident"
        
        if early_warnings:
            return f"Monitor early warning: {early_warnings[0]}"
        
        trend_direction = trend.get('direction', 'stable')
        if trend_direction == 'deteriorating':
            return "Watch the escalating trend closely"
        
        if priority == 'P2':
            return "Review P2 incidents when available"
        
        return "Routine monitoring - no immediate action needed"
    
    def resolve_conflict(self, data_value: Any, knowledge_value: Any,
                        source: str) -> Any:
        """
        Resolve conflict between data and knowledge.
        DATA ALWAYS WINS.
        """
        if data_value != knowledge_value:
            self.conflict_log.append({
                'source': source,
                'data_says': data_value,
                'knowledge_says': knowledge_value,
                'resolved_to': data_value,
                'reason': 'Data takes precedence over knowledge'
            })
        
        return data_value
    
    def format_merged_response(self, merged: MergedIntelligence) -> str:
        """
        Format merged intelligence into readable response.
        """
        lines = []
        
        # Key insights first
        if merged.key_insights:
            lines.append("### 💡 Key Insights")
            lines.append("")
            for insight in merged.key_insights:
                lines.append(f"- {insight}")
            lines.append("")
        
        # Risk and confidence
        lines.append(f"**Overall Risk:** {merged.overall_risk}")
        lines.append(f"**Confidence:** {merged.confidence_level}")
        lines.append("")
        
        # Recommended focus
        if merged.recommended_focus:
            lines.append(f"**Recommended Focus:** {merged.recommended_focus}")
            lines.append("")
        
        # Knowledge context if available
        if merged.typical_meaning:
            lines.append("### 🧠 What This Usually Means")
            lines.append("")
            lines.append(merged.typical_meaning)
            lines.append("")
            
            if merged.common_causes:
                lines.append("**Common causes:**")
                for cause in merged.common_causes[:3]:
                    lines.append(f"- {cause}")
                lines.append("")
        
        # Historical context if available
        if merged.similar_incidents > 0:
            lines.append("### 📚 Historical Context")
            lines.append("")
            lines.append(
                f"Similar pattern observed {merged.similar_incidents} times before."
            )
            if merged.typical_outcome and merged.typical_outcome != 'Unknown':
                lines.append(f"Typical outcome: {merged.typical_outcome}")
            lines.append("")
        
        # DBA checks
        if merged.dba_checks:
            lines.append("### 🧭 What a DBA Would Check")
            lines.append("")
            for check in merged.dba_checks[:4]:
                lines.append(f"- {check}")
        
        return "\n".join(lines)


# Singleton instance
KNOWLEDGE_MERGER = KnowledgeMerger()
