"""
DBA Intelligence Engine - Phase 6 Master Orchestrator
======================================================
Production-Grade DBA Intelligence Partner

This is the master orchestrator that combines:
- Phase 4: Incident Intelligence
- Phase 5: Predictive Intelligence
- Phase 6: DBA Knowledge + Memory + Confidence + Question Understanding

The engine thinks like a senior human DBA:
- Uses stored knowledge, not just raw data
- Learns from past incidents
- Answers any DBA question naturally
- Never hallucinates or fabricates

SAFETY RULES:
- Never invent causes or resolutions
- Never say "this will definitely fail"
- Never give patch names, SQL, or commands
- Never claim access to live DB
- Always use uncertainty language for predictions
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Phase 6 components
from .dba_knowledge_base import DBA_KNOWLEDGE_BASE, OracleErrorKnowledge
from .incident_memory import INCIDENT_MEMORY, IncidentOutcome
from .confidence_engine import CONFIDENCE_ENGINE, ConfidenceScore
from .question_understanding import QUESTION_ENGINE, QuestionType, QuestionInterpretation
from .human_dba_style import HUMAN_STYLE, DBAResponseContext
from .knowledge_merger import KNOWLEDGE_MERGER, MergedIntelligence

# Check Phase 4/5 availability
try:
    from .incident_intelligence_engine import INCIDENT_ENGINE
    PHASE4_AVAILABLE = True
except ImportError:
    INCIDENT_ENGINE = None
    PHASE4_AVAILABLE = False

try:
    from .predictive_intelligence_engine import PREDICTIVE_INTELLIGENCE
    PHASE5_AVAILABLE = True
except ImportError:
    PREDICTIVE_INTELLIGENCE = None
    PHASE5_AVAILABLE = False


class DBAIntelligenceEngine:
    """
    Phase 6 Master DBA Intelligence Engine.
    
    Capabilities:
    1. Understands any DBA question naturally
    2. Uses knowledge base for Oracle error context
    3. Learns from historical incidents
    4. Calculates and displays confidence
    5. Responds like a senior human DBA
    6. Merges all intelligence sources
    
    NEVER:
    - Fabricates data or causes
    - Issues SQL commands
    - Guarantees outcomes
    - Claims live DB access
    """
    
    def __init__(self):
        self.knowledge_base = DBA_KNOWLEDGE_BASE
        self.incident_memory = INCIDENT_MEMORY
        self.confidence_engine = CONFIDENCE_ENGINE
        self.question_engine = QUESTION_ENGINE
        self.human_style = HUMAN_STYLE
        self.knowledge_merger = KNOWLEDGE_MERGER
        
        # Session context for follow-ups
        self._session_context = {}
        
        print("[Phase6] DBA Intelligence Engine initialized")
        print(f"  - Knowledge Base: {len(OracleErrorKnowledge.get_all_errors())} Oracle errors")
        print(f"  - Incident Memory: {self.incident_memory.get_memory_stats()['total_incidents']} incidents")
        print(f"  - Phase 4 (Incident): {'Available' if PHASE4_AVAILABLE else 'Not loaded'}")
        print(f"  - Phase 5 (Predictive): {'Available' if PHASE5_AVAILABLE else 'Not loaded'}")
    
    def process_question(self, question: str, alerts: List[Dict] = None,
                        incidents: List[Dict] = None) -> str:
        """
        Process any DBA question and generate intelligent response.
        
        This is the main entry point for the DBA Intelligence Partner.
        """
        alerts = alerts or []
        incidents = incidents or []
        
        # Step 1: Understand the question
        interpretation = self.question_engine.understand(
            question, self._session_context
        )
        
        # Update session context
        self._update_session_context(interpretation)
        
        # Step 2: Assess question confidence
        question_confidence = self.confidence_engine.assess_question(question)
        
        # Step 3: Gather intelligence from all sources
        intelligence = self._gather_intelligence(
            interpretation, alerts, incidents
        )
        
        # Step 4: Calculate answer confidence
        answer_confidence = self.confidence_engine.assess_answer(
            has_data=len(alerts) > 0,
            data_count=len(alerts),
            has_knowledge=intelligence['knowledge'].get('has_knowledge', False),
            has_history=intelligence['history'].get('has_history', False),
            has_conflicting_signals=False,
            is_extrapolating=False
        )
        
        # Step 5: Combine confidence scores
        combined_confidence = self.confidence_engine.combine_confidence(
            question_confidence, answer_confidence
        )
        
        # Step 6: Generate response based on question type
        response = self._generate_response(
            interpretation, intelligence, combined_confidence, alerts
        )
        
        # Step 7: Learn from this interaction (update memory)
        self._learn_from_interaction(incidents)
        
        return response
    
    def _gather_intelligence(self, interpretation: QuestionInterpretation,
                            alerts: List[Dict],
                            incidents: List[Dict]) -> Dict:
        """
        Gather intelligence from all available sources.
        """
        intelligence = {
            'data': {},
            'incident_analysis': {},
            'predictive': {},
            'knowledge': {},
            'history': {}
        }
        
        # Data facts
        intelligence['data'] = self._extract_data_facts(alerts, incidents)
        
        # Get representative error type for knowledge lookup
        # First check if the question itself mentions an ORA code
        error_codes = interpretation.extracted_entities.get('error_codes', [])
        error_type = ''
        
        if error_codes:
            # Question explicitly mentions ORA codes - use those for knowledge lookup
            error_type = error_codes[0]
        elif incidents:
            error_type = incidents[0].get('error_type', incidents[0].get('message', ''))
        elif alerts:
            error_type = alerts[0].get('message', '')[:100]
        
        # Knowledge base lookup
        if error_type:
            intelligence['knowledge'] = self.knowledge_base.get_advisory_for_alert_type(error_type)
        
        # Also check if question mentions ORA codes directly for cause questions
        if interpretation.question_type == QuestionType.CAUSE and error_codes:
            # For cause questions about specific errors, ensure we have knowledge
            for code in error_codes:
                kb = self.knowledge_base.get_advisory_for_alert_type(code)
                if kb and kb.get('has_knowledge'):
                    intelligence['knowledge'] = kb
                    break
        
        # Historical lookup
        database = interpretation.extracted_entities.get('database', 'UNKNOWN')
        category = 'GENERAL'
        if incidents:
            category = incidents[0].get('category', 'GENERAL')
        
        if error_type:
            intelligence['history'] = self.incident_memory.get_historical_context(
                database, error_type, category
            )
        
        return intelligence
    
    def _extract_data_facts(self, alerts: List[Dict], 
                           incidents: List[Dict]) -> Dict:
        """
        Extract factual data from alerts and incidents.
        """
        facts = {
            'alert_count': len(alerts),
            'incident_count': len(incidents),
            'severity_breakdown': {},
            'top_databases': [],
            'top_errors': []
        }
        
        # Severity breakdown
        for alert in alerts:
            severity = alert.get('severity', 'UNKNOWN')
            facts['severity_breakdown'][severity] = facts['severity_breakdown'].get(severity, 0) + 1
        
        # Top databases
        db_counts = {}
        for alert in alerts:
            db = alert.get('database', alert.get('target', 'UNKNOWN'))
            db_counts[db] = db_counts.get(db, 0) + 1
        facts['top_databases'] = sorted(db_counts.keys(), 
                                        key=lambda x: db_counts[x], 
                                        reverse=True)[:5]
        
        # Top errors
        error_counts = {}
        for incident in incidents[:10]:
            error = incident.get('error_type', incident.get('message', ''))[:50]
            error_counts[error] = error_counts.get(error, 0) + 1
        facts['top_errors'] = sorted(error_counts.keys(),
                                    key=lambda x: error_counts[x],
                                    reverse=True)[:5]
        
        return facts
    
    def _generate_response(self, interpretation: QuestionInterpretation,
                          intelligence: Dict,
                          confidence: ConfidenceScore,
                          alerts: List[Dict]) -> str:
        """
        Generate response based on question type and available intelligence.
        """
        question_type = interpretation.question_type
        data = intelligence['data']
        knowledge = intelligence['knowledge']
        history = intelligence['history']
        
        # Build response parts
        response_parts = []
        
        # Handle different question types
        if question_type == QuestionType.COUNT:
            response_parts.append(self._format_count_response(data, interpretation))
        
        elif question_type == QuestionType.MEANING:
            response_parts.append(self._format_meaning_response(knowledge, data))
        
        elif question_type == QuestionType.RISK:
            response_parts.append(self._format_risk_response(data, knowledge))
        
        elif question_type == QuestionType.CAUSE:
            response_parts.append(self._format_cause_response(knowledge))
        
        elif question_type == QuestionType.HISTORY:
            response_parts.append(self._format_history_response(history))
        
        elif question_type == QuestionType.ACTION:
            response_parts.append(self._format_action_response(knowledge, data))
        
        elif question_type == QuestionType.VAGUE:
            response_parts.append(self._format_worry_response(data, knowledge))
        
        elif question_type == QuestionType.PRIORITY:
            response_parts.append(self._format_priority_response(data, alerts))
        
        elif question_type == QuestionType.TREND:
            response_parts.append(self._format_trend_response(data))
        
        elif question_type == QuestionType.COMPARISON:
            response_parts.append(self._format_comparison_response(data))
        
        else:
            # General question - provide overview
            response_parts.append(self._format_general_response(data, knowledge))
        
        # Add knowledge context if available
        if knowledge.get('has_knowledge'):
            response_parts.append("")
            response_parts.append(self.knowledge_base.format_human_advisory(
                intelligence['data'].get('top_errors', [''])[0] if intelligence['data'].get('top_errors') else ''
            ))
        
        # Add historical context if available
        if history.get('has_history'):
            response_parts.append("")
            database = interpretation.extracted_entities.get('database', 'UNKNOWN')
            error_type = data.get('top_errors', [''])[0] if data.get('top_errors') else ''
            response_parts.append(self.incident_memory.format_historical_insight(
                database, error_type, 'GENERAL'
            ))
        
        # Add confidence disclosure for non-high confidence
        if confidence.level != 'HIGH':
            response_parts.append("")
            response_parts.append("---")
            response_parts.append(self.confidence_engine.format_confidence_disclosure(confidence))
        
        # Add interpretation disclosure if needed
        if interpretation.confidence < 0.8:
            disclosure = self.question_engine.format_interpretation_disclosure(interpretation)
            if disclosure:
                response_parts.append(disclosure)
        
        return "\n".join(filter(None, response_parts))
    
    def _format_count_response(self, data: Dict, 
                               interpretation: QuestionInterpretation) -> str:
        """Format response for count questions."""
        count = data.get('alert_count', 0)
        severity = interpretation.extracted_entities.get('severity', '')
        database = interpretation.extracted_entities.get('database', '')
        
        if database and severity:
            return f"There are **{count:,}** {severity.lower()} alerts for **{database}**."
        elif database:
            return f"**{database}** has **{count:,}** alerts."
        elif severity:
            return f"There are **{count:,}** {severity.lower()} alerts across all databases."
        else:
            return f"There are **{count:,}** total alerts in the current view."
    
    def _format_meaning_response(self, knowledge: Dict, data: Dict) -> str:
        """Format response for 'what does this mean' questions."""
        lines = []
        
        if knowledge.get('has_knowledge'):
            meaning = knowledge.get('typical_meaning', '')
            lines.append(f"### 🔍 What This Means")
            lines.append("")
            lines.append(meaning if meaning else "This alert indicates an issue that warrants investigation.")
            lines.append("")
            
            if knowledge.get('common_causes'):
                lines.append("**This typically indicates:**")
                for cause in knowledge['common_causes'][:3]:
                    lines.append(f"- {cause}")
        else:
            lines.append("### 🔍 Interpretation")
            lines.append("")
            lines.append("Based on the alert data, this represents an operational condition "
                        "that the monitoring system has flagged for attention.")
            lines.append("")
            lines.append("Without specific Oracle error codes in the message, "
                        "I'd recommend reviewing the alert log for more context.")
        
        return "\n".join(lines)
    
    def _format_risk_response(self, data: Dict, knowledge: Dict) -> str:
        """Format response for risk assessment questions."""
        lines = []
        
        critical_count = data.get('severity_breakdown', {}).get('CRITICAL', 0)
        alert_count = data.get('alert_count', 0)
        
        # Determine risk level
        if critical_count > 1000:
            risk = 'HIGH'
            opener = "**Yes, this is a significant risk.**"
        elif critical_count > 100:
            risk = 'MEDIUM'
            opener = "**There is moderate risk here.**"
        elif critical_count > 0:
            risk = 'LOW-MEDIUM'
            opener = "**There is some risk, but it appears manageable.**"
        else:
            risk = 'LOW'
            opener = "**The risk level appears low.**"
        
        lines.append(opener)
        lines.append("")
        lines.append(f"**Risk Assessment: {risk}**")
        lines.append("")
        
        # Risk factors
        lines.append("**Contributing factors:**")
        if critical_count > 0:
            lines.append(f"- {critical_count:,} critical-severity alerts present")
        if alert_count > 10000:
            lines.append(f"- High overall alert volume ({alert_count:,})")
        if knowledge.get('risk_level') == 'HIGH':
            lines.append("- Error type is typically high-impact")
        
        lines.append("")
        lines.append("*Risk assessment based on current data. Actual impact depends on "
                    "your specific environment and workload.*")
        
        return "\n".join(lines)
    
    def _format_cause_response(self, knowledge: Dict) -> str:
        """Format response for 'what causes this' questions."""
        lines = []
        lines.append("### 🧠 Common Causes")
        lines.append("")
        
        if knowledge.get('has_knowledge'):
            causes = knowledge.get('common_causes', [])
            if causes:
                lines.append("Based on typical Oracle DBA experience, this is commonly caused by:")
                lines.append("")
                for cause in causes:
                    lines.append(f"- {cause}")
                lines.append("")
                lines.append("*These are common patterns. The actual cause in your "
                            "environment requires investigation.*")
            else:
                lines.append("I don't have specific cause information for this pattern.")
        else:
            lines.append("Without more specific error information, I can suggest "
                        "common investigation areas:")
            lines.append("")
            lines.append("- Recent changes (deployments, patches, configuration)")
            lines.append("- Resource constraints (CPU, memory, storage)")
            lines.append("- External dependencies (network, storage arrays)")
            lines.append("- Workload patterns (batch jobs, unusual activity)")
        
        return "\n".join(lines)
    
    def _format_history_response(self, history: Dict) -> str:
        """Format response for 'have we seen this before' questions."""
        lines = []
        lines.append("### 📚 Historical Pattern")
        lines.append("")
        
        if history.get('has_history'):
            count = history.get('similar_incidents', 0)
            lines.append(f"**Yes, similar patterns have been observed {count} times before.**")
            lines.append("")
            
            for insight in history.get('historical_insights', []):
                lines.append(f"- {insight}")
            
            lines.append("")
            lines.append(f"*Historical confidence: {history.get('confidence', 'LOW')}*")
        else:
            lines.append("**I don't have historical records of a similar pattern.**")
            lines.append("")
            lines.append("This could mean:")
            lines.append("- This is a new type of incident for your environment")
            lines.append("- Historical data hasn't been collected for this pattern")
            lines.append("- The pattern is unique to current conditions")
        
        return "\n".join(lines)
    
    def _format_action_response(self, knowledge: Dict, data: Dict) -> str:
        """Format response for 'what should I do' questions."""
        lines = []
        lines.append("### 🧭 What a DBA Would Typically Check")
        lines.append("")
        
        if knowledge.get('dba_first_checks'):
            lines.append("Based on this type of issue, experienced DBAs typically:")
            lines.append("")
            for check in knowledge['dba_first_checks'][:5]:
                lines.append(f"- {check}")
        else:
            lines.append("General investigation steps:")
            lines.append("")
            lines.append("- Review the alert log for the affected database(s)")
            lines.append("- Check for any recent changes or deployments")
            lines.append("- Look at the timing - is this correlated with any scheduled activity?")
            lines.append("- Compare current behavior with historical baselines")
            lines.append("- Check related systems and dependencies")
        
        lines.append("")
        lines.append("**Important:** These are investigation guidelines, not automated actions. "
                    "No changes have been or will be made to your systems.")
        
        return "\n".join(lines)
    
    def _format_worry_response(self, data: Dict, knowledge: Dict) -> str:
        """Format response for 'should I worry' questions."""
        critical = data.get('severity_breakdown', {}).get('CRITICAL', 0)
        total = data.get('alert_count', 0)
        
        if critical > 1000:
            return self.human_style.format_worry_assessment(
                should_worry=True,
                reason=f"You have {critical:,} critical alerts, which is significant. "
                      f"This volume typically indicates an active issue that needs attention.",
                risk_level='HIGH'
            )
        elif critical > 100:
            return self.human_style.format_worry_assessment(
                should_worry=True,
                reason=f"There are {critical:,} critical alerts present. "
                      f"While not a crisis, this warrants investigation.",
                risk_level='MEDIUM'
            )
        elif critical > 0:
            return self.human_style.format_worry_assessment(
                should_worry=False,
                reason=f"There are {critical:,} critical alerts, which is relatively modest. "
                      f"Worth monitoring but not immediately alarming.",
                risk_level='LOW'
            )
        else:
            return self.human_style.format_worry_assessment(
                should_worry=False,
                reason=f"I'm seeing {total:,} alerts but none are critical severity. "
                      f"This appears to be normal operational activity.",
                risk_level='LOW'
            )
    
    def _format_priority_response(self, data: Dict, alerts: List[Dict]) -> str:
        """Format response for 'what should I focus on' questions."""
        lines = []
        lines.append("### 🎯 Priority Focus")
        lines.append("")
        
        critical = data.get('severity_breakdown', {}).get('CRITICAL', 0)
        
        if critical > 0:
            lines.append(f"**Primary focus:** The {critical:,} critical alerts should be your first priority.")
            lines.append("")
            
            # Get top errors
            if data.get('top_errors'):
                lines.append("**Most common issues:**")
                for i, error in enumerate(data['top_errors'][:3], 1):
                    lines.append(f"{i}. {error}")
            
            lines.append("")
            lines.append("**Top databases affected:**")
            for db in data.get('top_databases', [])[:3]:
                lines.append(f"- {db}")
        else:
            lines.append("**No critical alerts requiring immediate attention.**")
            lines.append("")
            lines.append("You may want to:")
            lines.append("- Review warning-level alerts for emerging patterns")
            lines.append("- Check for any unusual trends")
            lines.append("- Ensure monitoring coverage is complete")
        
        return "\n".join(lines)
    
    def _format_trend_response(self, data: Dict) -> str:
        """Format response for trend questions."""
        lines = []
        lines.append("### 📈 Trend Analysis")
        lines.append("")
        
        # Without historical comparison data, be honest
        lines.append("**Current snapshot:**")
        lines.append(f"- Total alerts: {data.get('alert_count', 0):,}")
        
        severity = data.get('severity_breakdown', {})
        if severity:
            for sev, count in severity.items():
                lines.append(f"- {sev}: {count:,}")
        
        lines.append("")
        lines.append("*To determine if this is increasing or decreasing, "
                    "I would need historical comparison data. "
                    "Consider comparing with yesterday's or last week's snapshot.*")
        
        return "\n".join(lines)
    
    def _format_comparison_response(self, data: Dict) -> str:
        """Format response for comparison questions."""
        lines = []
        lines.append("### 📊 Comparison")
        lines.append("")
        lines.append("**Current state:**")
        lines.append(f"- Alert count: {data.get('alert_count', 0):,}")
        lines.append(f"- Incident count: {data.get('incident_count', 0):,}")
        lines.append("")
        lines.append("*For a meaningful comparison, I would need access to the "
                    "baseline you want to compare against (yesterday, last week, etc.). "
                    "Could you specify the comparison timeframe?*")
        
        return "\n".join(lines)
    
    def _format_general_response(self, data: Dict, knowledge: Dict) -> str:
        """Format general overview response."""
        context = DBAResponseContext(
            question_type='general',
            alert_count=data.get('alert_count', 0),
            incident_count=data.get('incident_count', 0),
            severity_breakdown=data.get('severity_breakdown', {}),
            top_databases=data.get('top_databases', []),
            top_errors=data.get('top_errors', []),
            risk_level='MEDIUM',
            has_critical=data.get('severity_breakdown', {}).get('CRITICAL', 0) > 0,
            has_escalating=False,
            confidence_level='MEDIUM'
        )
        
        return self.human_style.format_full_response(
            context=context,
            data=data,
            knowledge=knowledge,
            include_all_sections=True
        )
    
    def _update_session_context(self, interpretation: QuestionInterpretation):
        """Update session context for follow-up questions."""
        entities = interpretation.extracted_entities
        
        if entities.get('database'):
            self._session_context['database'] = entities['database']
        if entities.get('severity'):
            self._session_context['severity'] = entities['severity']
        if entities.get('time_frame'):
            self._session_context['time_frame'] = entities['time_frame']
        
        self._session_context['last_question'] = interpretation.original_question
        self._session_context['last_type'] = interpretation.question_type
    
    def _learn_from_interaction(self, incidents: List[Dict]):
        """Learn from current incidents to build memory."""
        if incidents:
            self.incident_memory.learn_from_current_data(incidents)
    
    def get_capabilities(self) -> Dict:
        """Return current engine capabilities."""
        return {
            'phase6_available': True,
            'knowledge_base': True,
            'incident_memory': True,
            'confidence_engine': True,
            'question_understanding': True,
            'human_style': True,
            'knowledge_merger': True,
            'phase4_available': PHASE4_AVAILABLE,
            'phase5_available': PHASE5_AVAILABLE,
            'oracle_errors_known': len(OracleErrorKnowledge.get_all_errors()),
            'incidents_in_memory': self.incident_memory.get_memory_stats()['total_incidents']
        }


# Singleton instance
DBA_INTELLIGENCE = DBAIntelligenceEngine()
