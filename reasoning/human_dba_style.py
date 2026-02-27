"""
Human DBA Response Style - Phase 6 Component
=============================================
Formats responses to sound like a calm, senior DBA.

Response style:
- Conversational but professional
- Structured but not robotic
- Confident but not overconfident
- Helpful but honest about limitations

Response structure:
🔍 What's happening
⚠️ Why it matters
🧠 What this usually indicates
🧭 What a DBA would typically check

RULES:
- NO SQL commands
- NO exact fix instructions
- NO overconfident predictions
- NO assumptions stated as facts
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class DBAResponseContext:
    """Context for generating DBA-style response."""
    question_type: str
    alert_count: int
    incident_count: int
    severity_breakdown: Dict[str, int]
    top_databases: List[str]
    top_errors: List[str]
    risk_level: str
    has_critical: bool
    has_escalating: bool
    confidence_level: str


class HumanPhrasing:
    """
    Human-friendly phrases for DBA responses.
    Replaces robotic language with natural DBA speech.
    """
    
    # Opening phrases based on severity
    SEVERITY_OPENERS = {
        'critical_high': [
            "This needs your attention.",
            "There's something significant here.",
            "I'd take a closer look at this.",
        ],
        'critical_moderate': [
            "There's elevated activity here.",
            "Worth keeping an eye on.",
            "Something to be aware of.",
        ],
        'warning_only': [
            "Nothing alarming, but worth noting.",
            "Mostly routine, with some items to watch.",
            "Generally normal, with a few things to note.",
        ],
        'normal': [
            "Things look relatively stable.",
            "Nothing stands out as concerning.",
            "Appears to be routine activity.",
        ]
    }
    
    # Risk assessment phrases
    RISK_PHRASES = {
        'HIGH': [
            "This situation warrants immediate attention.",
            "I'd prioritize investigating this now.",
            "This could impact operations if not addressed.",
        ],
        'MEDIUM': [
            "This deserves monitoring but isn't urgent.",
            "Worth investigating when you have a moment.",
            "Keep an eye on this over the next few hours.",
        ],
        'LOW': [
            "This is likely routine activity.",
            "Probably nothing to worry about.",
            "This appears to be normal noise.",
        ]
    }
    
    # Uncertainty phrases
    UNCERTAINTY_PHRASES = {
        'high_confidence': [
            "Based on the data,",
            "The alerts clearly show",
            "I can see that",
        ],
        'medium_confidence': [
            "Based on available data,",
            "From what I can see,",
            "It appears that",
        ],
        'low_confidence': [
            "Based on limited information,",
            "I'm not entirely certain, but",
            "With the data available,",
        ]
    }
    
    # DBA wisdom phrases
    DBA_WISDOM = {
        'internal_error': [
            "Internal errors like this typically indicate something at the Oracle engine level.",
            "ORA-600 errors usually point to Oracle internals - often needing Oracle Support input.",
            "Internal errors are tricky - they often require trace file analysis.",
        ],
        'network_issue': [
            "Network-related errors often come in bursts when there's instability.",
            "Connection issues frequently point to something between the app and database.",
            "These kinds of network errors usually warrant checking the listener and infrastructure.",
        ],
        'space_issue': [
            "Space issues can escalate quickly if left unchecked.",
            "Storage-related alerts tend to need immediate attention to prevent outages.",
            "When space runs out, things tend to stop quickly.",
        ],
        'standby_issue': [
            "Standby database issues can affect your disaster recovery readiness.",
            "Data Guard problems often relate to network or apply process status.",
            "Keeping standby synchronized is important for your recovery options.",
        ]
    }
    
    @classmethod
    def get_opener(cls, severity_category: str) -> str:
        """Get appropriate opening phrase."""
        import random
        phrases = cls.SEVERITY_OPENERS.get(severity_category, cls.SEVERITY_OPENERS['normal'])
        return random.choice(phrases)
    
    @classmethod
    def get_risk_phrase(cls, risk_level: str) -> str:
        """Get risk assessment phrase."""
        import random
        phrases = cls.RISK_PHRASES.get(risk_level, cls.RISK_PHRASES['MEDIUM'])
        return random.choice(phrases)
    
    @classmethod
    def get_uncertainty_phrase(cls, confidence: str) -> str:
        """Get uncertainty disclosure phrase."""
        import random
        key = f"{confidence.lower()}_confidence"
        phrases = cls.UNCERTAINTY_PHRASES.get(key, cls.UNCERTAINTY_PHRASES['medium_confidence'])
        return random.choice(phrases)


class ResponseTemplates:
    """
    Templates for different types of DBA responses.
    All templates are structured but conversational.
    """
    
    @staticmethod
    def format_whats_happening(data: Dict) -> str:
        """Format the 'What's happening' section."""
        lines = []
        lines.append("### 🔍 What's Happening")
        lines.append("")
        
        count = data.get('alert_count', 0)
        databases = data.get('top_databases', [])
        severities = data.get('severity_breakdown', {})
        
        if count > 0:
            lines.append(f"I'm seeing **{count:,}** alerts in the current view.")
            
            if severities:
                sev_parts = []
                for sev, cnt in severities.items():
                    sev_parts.append(f"{cnt:,} {sev.lower()}")
                lines.append(f"Breakdown: {', '.join(sev_parts)}")
            
            if databases:
                lines.append(f"Primary databases involved: {', '.join(databases[:3])}")
        else:
            lines.append("I don't see any alerts matching your criteria.")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_why_it_matters(context: DBAResponseContext) -> str:
        """Format the 'Why it matters' section."""
        lines = []
        lines.append("### ⚠️ Why This Matters")
        lines.append("")
        
        if context.has_critical and context.has_escalating:
            lines.append("This is a priority situation. You have critical alerts that are increasing in frequency.")
            lines.append("Left unattended, this pattern often leads to service impact.")
        elif context.has_critical:
            lines.append("You have critical-level alerts that warrant attention.")
            lines.append("Critical alerts typically indicate conditions that could affect availability or data.")
        elif context.has_escalating:
            lines.append("While not critical severity, the alert volume is increasing.")
            lines.append("Escalating patterns sometimes precede more serious issues.")
        else:
            lines.append("The current situation appears manageable.")
            lines.append("No immediate action required, but worth staying aware.")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_what_it_indicates(error_types: List[str], knowledge: Dict = None) -> str:
        """Format the 'What this usually indicates' section."""
        lines = []
        lines.append("### 🧠 What This Usually Indicates")
        lines.append("")
        
        if knowledge and knowledge.get('has_knowledge'):
            meaning = knowledge.get('typical_meaning', '')
            if meaning:
                lines.append(f"**Typical interpretation:** {meaning}")
                lines.append("")
            
            causes = knowledge.get('common_causes', [])
            if causes:
                lines.append("**Common causes from experience:**")
                for cause in causes[:3]:
                    lines.append(f"- {cause}")
                lines.append("")
        else:
            if error_types:
                lines.append(f"The primary issue type is: **{error_types[0]}**")
            lines.append("")
            lines.append("This pattern could have multiple explanations depending on your environment.")
        
        lines.append("*Note: These are typical patterns. Your specific situation may vary.*")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_dba_checks(checks: List[str] = None) -> str:
        """Format the 'What a DBA would check' section."""
        lines = []
        lines.append("### 🧭 What a DBA Would Typically Check")
        lines.append("")
        
        if checks:
            for check in checks[:5]:
                lines.append(f"- {check}")
        else:
            # Default DBA checks
            lines.append("- Review the alert log for the affected database(s)")
            lines.append("- Check for any recent changes (deployments, patches, config)")
            lines.append("- Look at the timing - is this correlated with any activity?")
            lines.append("- Compare with historical patterns for this database")
        
        lines.append("")
        lines.append("*These are investigation starting points, not required actions.*")
        
        return "\n".join(lines)


class HumanDBAStyleFormatter:
    """
    Master Human DBA Style Formatter - Phase 6 Component.
    
    Transforms technical data into human DBA language.
    
    Style characteristics:
    - Calm and measured tone
    - Acknowledges uncertainty
    - Structured but conversational
    - Actionable but not prescriptive
    """
    
    def __init__(self):
        self.phrasing = HumanPhrasing()
        self.templates = ResponseTemplates()
    
    def format_full_response(self, context: DBAResponseContext,
                            data: Dict,
                            knowledge: Dict = None,
                            include_all_sections: bool = True) -> str:
        """
        Format a complete DBA-style response.
        """
        lines = []
        
        # Opening
        opener = self._get_appropriate_opener(context)
        lines.append(opener)
        lines.append("")
        
        # What's happening
        lines.append(self.templates.format_whats_happening(data))
        lines.append("")
        
        if include_all_sections:
            # Why it matters
            lines.append(self.templates.format_why_it_matters(context))
            lines.append("")
            
            # What it indicates
            lines.append(self.templates.format_what_it_indicates(
                context.top_errors, knowledge
            ))
            lines.append("")
            
            # DBA checks
            checks = knowledge.get('dba_first_checks', []) if knowledge else None
            lines.append(self.templates.format_dba_checks(checks))
        
        return "\n".join(lines)
    
    def _get_appropriate_opener(self, context: DBAResponseContext) -> str:
        """Determine appropriate opening based on context."""
        critical_count = context.severity_breakdown.get('CRITICAL', 0)
        warning_count = context.severity_breakdown.get('WARNING', 0)
        
        if critical_count > 1000:
            category = 'critical_high'
        elif critical_count > 0:
            category = 'critical_moderate'
        elif warning_count > 0:
            category = 'warning_only'
        else:
            category = 'normal'
        
        return HumanPhrasing.get_opener(category)
    
    def format_simple_answer(self, question_type: str, answer: str,
                            confidence: str = 'MEDIUM') -> str:
        """
        Format a simple, direct answer in DBA style.
        """
        uncertainty = HumanPhrasing.get_uncertainty_phrase(confidence)
        return f"{uncertainty} {answer}"
    
    def format_worry_assessment(self, should_worry: bool, 
                                reason: str,
                                risk_level: str) -> str:
        """
        Format response to "should I worry" type questions.
        """
        lines = []
        
        if should_worry:
            lines.append("**Yes, this warrants attention.**")
            lines.append("")
            lines.append(reason)
            lines.append("")
            lines.append(HumanPhrasing.get_risk_phrase('HIGH'))
        else:
            lines.append("**This doesn't look immediately concerning.**")
            lines.append("")
            lines.append(reason)
            lines.append("")
            lines.append(HumanPhrasing.get_risk_phrase(risk_level))
        
        return "\n".join(lines)
    
    def format_comparison(self, current_value: int, baseline_value: int,
                         metric_name: str) -> str:
        """
        Format comparison response.
        """
        if baseline_value == 0:
            return f"I don't have a baseline to compare {current_value:,} {metric_name} against."
        
        ratio = current_value / baseline_value
        
        if ratio > 2:
            change = f"significantly higher ({ratio:.1f}x)"
        elif ratio > 1.2:
            change = f"somewhat elevated ({ratio:.1f}x)"
        elif ratio > 0.8:
            change = "about the same"
        elif ratio > 0.5:
            change = f"somewhat lower ({ratio:.1f}x)"
        else:
            change = f"significantly lower ({ratio:.1f}x)"
        
        return f"Currently seeing {current_value:,} {metric_name}, which is {change} compared to baseline of {baseline_value:,}."
    
    def format_risk_assessment(self, risk_level: str, factors: List[str]) -> str:
        """
        Format risk assessment in DBA language.
        """
        lines = []
        
        risk_intro = HumanPhrasing.get_risk_phrase(risk_level)
        lines.append(f"**Risk Level: {risk_level}**")
        lines.append("")
        lines.append(risk_intro)
        lines.append("")
        
        if factors:
            lines.append("**Contributing factors:**")
            for factor in factors[:4]:
                lines.append(f"- {factor}")
        
        return "\n".join(lines)
    
    def humanize_text(self, technical_text: str) -> str:
        """
        Convert technical text to more human-friendly language.
        """
        # Replace technical terms with friendlier versions
        replacements = {
            'CRITICAL': 'critical',
            'WARNING': 'warning',
            'INTERNAL ERROR': 'internal error',
            'ORA-': 'Oracle error ORA-',
            'TNS': 'network (TNS)',
            'RDBMS': 'database',
            'DG': 'Data Guard',
            'ASM': 'storage (ASM)',
        }
        
        result = technical_text
        for technical, friendly in replacements.items():
            result = result.replace(technical, friendly)
        
        return result
    
    def add_disclaimer(self, response: str, disclaimer_type: str = 'general') -> str:
        """
        Add appropriate disclaimer to response.
        """
        disclaimers = {
            'general': "\n\n*This assessment is based on the available alert data. "
                      "Actual conditions may differ and require direct verification.*",
            'prediction': "\n\n*This is a pattern-based observation, not a prediction. "
                         "Actual outcomes will depend on many factors.*",
            'cause': "\n\n*These are common causes based on experience. "
                    "The actual root cause requires investigation.*",
            'action': "\n\n*These are typical investigation steps. "
                     "No automated actions have been or will be taken.*"
        }
        
        return response + disclaimers.get(disclaimer_type, disclaimers['general'])


# Singleton instance
HUMAN_STYLE = HumanDBAStyleFormatter()
