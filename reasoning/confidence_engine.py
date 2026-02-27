"""
Confidence & Uncertainty Engine - Phase 6 Component
====================================================
Every response calculates confidence score (0-1).
Exposes as HIGH / MEDIUM / LOW.

RULES:
- LOW confidence → ask clarifying question
- NEVER guess if confidence < 0.7
- Be transparent about uncertainty
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ConfidenceScore:
    """Represents a confidence assessment."""
    value: float  # 0.0 to 1.0
    level: str    # HIGH, MEDIUM, LOW
    factors: List[str]  # What contributed to this score
    uncertainties: List[str]  # What caused uncertainty
    clarifying_questions: List[str]  # Questions to ask if LOW
    
    def is_high(self) -> bool:
        return self.value >= 0.8
    
    def is_medium(self) -> bool:
        return 0.5 <= self.value < 0.8
    
    def is_low(self) -> bool:
        return self.value < 0.5


class ConfidenceFactors:
    """Factors that affect confidence scoring."""
    
    # Positive factors (increase confidence)
    POSITIVE = {
        'has_data': 0.25,              # Have actual data to work with
        'single_database': 0.10,       # Clear database target
        'clear_severity': 0.10,        # Clear severity filter
        'specific_question': 0.15,     # Question is specific
        'known_error_type': 0.10,      # Error type is in knowledge base
        'has_historical_data': 0.15,   # Have historical comparison
        'single_interpretation': 0.10, # Question has one clear meaning
        'time_frame_specified': 0.05,  # Time frame is clear
    }
    
    # Negative factors (decrease confidence)
    NEGATIVE = {
        'vague_question': -0.20,       # Question is ambiguous
        'multiple_databases': -0.10,   # Multiple databases involved
        'no_data': -0.40,              # No data available
        'unknown_error': -0.15,        # Error not in knowledge base
        'conflicting_signals': -0.20,  # Data shows mixed signals
        'missing_context': -0.15,      # Need more context
        'first_time_pattern': -0.10,   # Never seen this before
    }


class QuestionConfidenceScorer:
    """
    Scores confidence for understanding the user's question.
    """
    
    # Question patterns and their base confidence
    QUESTION_PATTERNS = {
        'count': {
            'keywords': ['how many', 'count', 'number of', 'total'],
            'base_confidence': 0.9,
            'typical_uncertainties': [],
        },
        'comparison': {
            'keywords': ['worse than', 'better than', 'compared to', 'vs', 'versus', 'more than', 'less than'],
            'base_confidence': 0.7,
            'typical_uncertainties': ['comparison baseline unclear'],
        },
        'meaning': {
            'keywords': ['what does', 'what is', 'explain', 'tell me about', 'meaning'],
            'base_confidence': 0.8,
            'typical_uncertainties': [],
        },
        'priority': {
            'keywords': ['what should', 'first', 'most important', 'priority', 'focus on'],
            'base_confidence': 0.75,
            'typical_uncertainties': ['priority criteria may vary'],
        },
        'risk': {
            'keywords': ['risk', 'dangerous', 'cause outage', 'impact', 'serious'],
            'base_confidence': 0.7,
            'typical_uncertainties': ['risk depends on many factors'],
        },
        'trend': {
            'keywords': ['increasing', 'decreasing', 'trend', 'getting worse', 'getting better'],
            'base_confidence': 0.75,
            'typical_uncertainties': ['trend detection requires historical data'],
        },
        'worry': {
            'keywords': ['should i worry', 'worried', 'concern', 'normal', 'abnormal'],
            'base_confidence': 0.65,
            'typical_uncertainties': ['normal varies by environment'],
        },
        'cause': {
            'keywords': ['what causes', 'why', 'root cause', 'reason'],
            'base_confidence': 0.6,
            'typical_uncertainties': ['root cause often requires investigation'],
        },
        'history': {
            'keywords': ['have we seen', 'before', 'previous', 'last time', 'history'],
            'base_confidence': 0.7,
            'typical_uncertainties': ['depends on available history'],
        },
        'action': {
            'keywords': ['what to do', 'how to fix', 'resolve', 'check first'],
            'base_confidence': 0.7,
            'typical_uncertainties': ['actions depend on specific situation'],
        },
    }
    
    def identify_question_type(self, question: str) -> Tuple[str, float]:
        """Identify the type of question and base confidence."""
        question_lower = question.lower()
        
        for q_type, config in self.QUESTION_PATTERNS.items():
            for keyword in config['keywords']:
                if keyword in question_lower:
                    return q_type, config['base_confidence']
        
        # Default: general question
        return 'general', 0.6
    
    def score_question_understanding(self, question: str) -> ConfidenceScore:
        """
        Score confidence in understanding the question.
        """
        question_lower = question.lower()
        factors = []
        uncertainties = []
        clarifying = []
        
        # Identify question type
        q_type, base_score = self.identify_question_type(question)
        factors.append(f"Question type: {q_type}")
        
        # Check for database specification
        db_keywords = ['midevstb', 'database', 'db', 'oracle', 'standby', 'primary']
        if any(kw in question_lower for kw in db_keywords):
            base_score += 0.1
            factors.append("Database context provided")
        else:
            uncertainties.append("No specific database mentioned")
            clarifying.append("Which database are you asking about?")
        
        # Check for severity specification
        severity_keywords = ['critical', 'warning', 'error', 'alert']
        if any(kw in question_lower for kw in severity_keywords):
            base_score += 0.05
            factors.append("Severity specified")
        
        # Check for time frame
        time_keywords = ['today', 'yesterday', 'last', 'hour', 'day', 'week', 'now']
        if any(kw in question_lower for kw in time_keywords):
            base_score += 0.05
            factors.append("Time frame specified")
        else:
            uncertainties.append("Time frame not specified")
        
        # Penalize very short questions
        if len(question.split()) < 3:
            base_score -= 0.15
            uncertainties.append("Question is very brief")
            clarifying.append("Could you provide more details about what you'd like to know?")
        
        # Penalize vague terms without context
        vague_terms = ['this', 'that', 'it', 'these']
        if any(term in question_lower.split() for term in vague_terms):
            if len(question.split()) < 5:  # Short question with vague terms
                base_score -= 0.1
                uncertainties.append("Contains ambiguous references")
        
        # Cap at 1.0
        final_score = min(max(base_score, 0.0), 1.0)
        
        # Determine level
        if final_score >= 0.8:
            level = 'HIGH'
        elif final_score >= 0.5:
            level = 'MEDIUM'
        else:
            level = 'LOW'
        
        return ConfidenceScore(
            value=final_score,
            level=level,
            factors=factors,
            uncertainties=uncertainties,
            clarifying_questions=clarifying
        )


class AnswerConfidenceScorer:
    """
    Scores confidence in the answer being provided.
    """
    
    def score_answer_confidence(self, 
                                has_data: bool,
                                data_count: int,
                                has_knowledge: bool,
                                has_history: bool,
                                has_conflicting_signals: bool,
                                is_extrapolating: bool) -> ConfidenceScore:
        """
        Score confidence in the answer quality.
        """
        factors = []
        uncertainties = []
        clarifying = []
        score = 0.0
        
        # Data availability is critical
        if has_data:
            if data_count > 100:
                score += 0.35
                factors.append(f"Based on {data_count:,} data points")
            elif data_count > 10:
                score += 0.25
                factors.append(f"Based on {data_count} data points")
            else:
                score += 0.15
                factors.append(f"Limited data ({data_count} points)")
                uncertainties.append("Small sample size")
        else:
            uncertainties.append("No matching data available")
            clarifying.append("Could you specify a different filter or time range?")
        
        # Knowledge base match
        if has_knowledge:
            score += 0.20
            factors.append("Matches known DBA patterns")
        else:
            score += 0.05
            uncertainties.append("Pattern not in knowledge base")
        
        # Historical context
        if has_history:
            score += 0.20
            factors.append("Historical data available for comparison")
        else:
            score += 0.05
            uncertainties.append("Limited historical context")
        
        # Conflicting signals reduce confidence
        if has_conflicting_signals:
            score -= 0.15
            uncertainties.append("Mixed signals in the data")
        
        # Extrapolation reduces confidence
        if is_extrapolating:
            score -= 0.10
            uncertainties.append("Some extrapolation required")
        
        # Base minimum for having any response
        score = max(score, 0.1)
        
        # Cap at 1.0
        final_score = min(score, 1.0)
        
        # Determine level
        if final_score >= 0.8:
            level = 'HIGH'
        elif final_score >= 0.5:
            level = 'MEDIUM'
        else:
            level = 'LOW'
        
        return ConfidenceScore(
            value=final_score,
            level=level,
            factors=factors,
            uncertainties=uncertainties,
            clarifying_questions=clarifying
        )


class ConfidenceEngine:
    """
    Master Confidence Engine - Phase 6 Component.
    
    Calculates and exposes confidence for:
    1. Question understanding
    2. Answer quality
    3. Recommendations
    
    RULES:
    - LOW confidence → ask clarifying question
    - NEVER guess if confidence < 0.7
    - Be transparent about uncertainty
    """
    
    def __init__(self):
        self.question_scorer = QuestionConfidenceScorer()
        self.answer_scorer = AnswerConfidenceScorer()
    
    def assess_question(self, question: str) -> ConfidenceScore:
        """Assess confidence in understanding the question."""
        return self.question_scorer.score_question_understanding(question)
    
    def assess_answer(self, 
                     has_data: bool = False,
                     data_count: int = 0,
                     has_knowledge: bool = False,
                     has_history: bool = False,
                     has_conflicting_signals: bool = False,
                     is_extrapolating: bool = False) -> ConfidenceScore:
        """Assess confidence in the answer."""
        return self.answer_scorer.score_answer_confidence(
            has_data=has_data,
            data_count=data_count,
            has_knowledge=has_knowledge,
            has_history=has_history,
            has_conflicting_signals=has_conflicting_signals,
            is_extrapolating=is_extrapolating
        )
    
    def combine_confidence(self, question_conf: ConfidenceScore, 
                          answer_conf: ConfidenceScore) -> ConfidenceScore:
        """
        Combine question and answer confidence into overall confidence.
        Uses weighted average (question 30%, answer 70%).
        """
        combined_value = (question_conf.value * 0.3) + (answer_conf.value * 0.7)
        
        # Combine factors and uncertainties
        all_factors = question_conf.factors + answer_conf.factors
        all_uncertainties = question_conf.uncertainties + answer_conf.uncertainties
        all_clarifying = question_conf.clarifying_questions + answer_conf.clarifying_questions
        
        # Remove duplicates while preserving order
        factors = list(dict.fromkeys(all_factors))
        uncertainties = list(dict.fromkeys(all_uncertainties))
        clarifying = list(dict.fromkeys(all_clarifying))
        
        # Determine level
        if combined_value >= 0.8:
            level = 'HIGH'
        elif combined_value >= 0.5:
            level = 'MEDIUM'
        else:
            level = 'LOW'
        
        return ConfidenceScore(
            value=combined_value,
            level=level,
            factors=factors,
            uncertainties=uncertainties,
            clarifying_questions=clarifying
        )
    
    def format_confidence_disclosure(self, score: ConfidenceScore) -> str:
        """
        Format confidence for human-readable disclosure.
        """
        lines = []
        
        # Confidence indicator with emoji
        if score.level == 'HIGH':
            lines.append(f"**Confidence:** 🟢 HIGH ({score.value:.0%})")
        elif score.level == 'MEDIUM':
            lines.append(f"**Confidence:** 🟡 MEDIUM ({score.value:.0%})")
        else:
            lines.append(f"**Confidence:** 🔴 LOW ({score.value:.0%})")
        
        # For low confidence, show clarifying questions
        if score.level == 'LOW' and score.clarifying_questions:
            lines.append("")
            lines.append("**To improve this answer, I'd need to know:**")
            for q in score.clarifying_questions[:3]:
                lines.append(f"- {q}")
        
        # Show key uncertainties for medium/low
        if score.level in ['MEDIUM', 'LOW'] and score.uncertainties:
            lines.append("")
            lines.append("**Uncertainties:**")
            for u in score.uncertainties[:3]:
                lines.append(f"- {u}")
        
        return "\n".join(lines)
    
    def should_ask_clarification(self, score: ConfidenceScore) -> bool:
        """Determine if we should ask a clarifying question."""
        return score.level == 'LOW' and len(score.clarifying_questions) > 0
    
    def get_clarifying_response(self, score: ConfidenceScore, 
                                partial_answer: str = "") -> str:
        """
        Generate a response that includes clarifying questions.
        """
        lines = []
        
        if partial_answer:
            lines.append(partial_answer)
            lines.append("")
            lines.append("---")
            lines.append("")
        
        lines.append("**I want to give you a better answer.** Could you help me understand:")
        lines.append("")
        for q in score.clarifying_questions[:3]:
            lines.append(f"- {q}")
        
        return "\n".join(lines)


# Singleton instance
CONFIDENCE_ENGINE = ConfidenceEngine()
