"""
Question Understanding Engine - Phase 6 Component
==================================================
Handles ANY DBA question naturally.

Question types handled:
- Counts ("how many alerts")
- Comparisons ("is this worse than yesterday")
- Meaning ("is this dangerous")
- Priority ("what should I look at first")
- Risk ("can this cause outage")
- Trend ("is this increasing")
- Follow-ups ("what about standby")
- Vague questions ("should I worry?")

RULES:
- NEVER reply "Invalid question" or "I don't understand"
- Instead: "Here's how I interpret your question…"
- Always provide a best-effort interpretation
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class QuestionInterpretation:
    """Result of question understanding."""
    original_question: str
    interpreted_intent: str
    question_type: str
    extracted_entities: Dict
    confidence: float
    interpretation_explanation: str
    needs_clarification: bool
    suggested_clarification: str


class QuestionType:
    """Question type constants."""
    COUNT = 'count'
    COMPARISON = 'comparison'
    MEANING = 'meaning'
    PRIORITY = 'priority'
    RISK = 'risk'
    TREND = 'trend'
    FOLLOWUP = 'followup'
    HISTORY = 'history'
    CAUSE = 'cause'
    ACTION = 'action'
    VAGUE = 'vague'
    GENERAL = 'general'


class EntityExtractor:
    """
    Extracts entities from DBA questions.
    """
    
    # Database patterns
    DATABASE_PATTERNS = [
        r'\b(MIDEVSTB\w*)\b',
        r'\b([A-Z]{3,}DB\w*)\b',
        r'\b([A-Z]{3,}PROD\w*)\b',
        r'\b([A-Z]{3,}STB\w*)\b',
        r'database[:\s]+([A-Za-z0-9_]+)',
        r'for\s+([A-Z][A-Z0-9_]+)',
    ]
    
    # Severity patterns
    SEVERITY_KEYWORDS = {
        'critical': 'CRITICAL',
        'warning': 'WARNING',
        'error': 'ERROR',
        'info': 'INFO',
        'informational': 'INFO'
    }
    
    # Time patterns
    TIME_PATTERNS = {
        'today': 'today',
        'yesterday': 'yesterday',
        'last hour': 'last_hour',
        'last 24 hours': 'last_24h',
        'last week': 'last_week',
        'this week': 'this_week',
        'now': 'current',
        'recent': 'recent'
    }
    
    # Error code patterns
    ERROR_PATTERNS = [
        r'ORA[-\s]?(\d+)',
        r'(ORA[-\s]?\d+)',
    ]
    
    def extract_database(self, text: str) -> Optional[str]:
        """Extract database name from text."""
        text_upper = text.upper()
        
        for pattern in self.DATABASE_PATTERNS:
            match = re.search(pattern, text_upper, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def extract_severity(self, text: str) -> Optional[str]:
        """Extract severity level from text."""
        text_lower = text.lower()
        
        for keyword, severity in self.SEVERITY_KEYWORDS.items():
            if keyword in text_lower:
                return severity
        
        return None
    
    def extract_time_frame(self, text: str) -> Optional[str]:
        """Extract time frame from text."""
        text_lower = text.lower()
        
        for pattern, value in self.TIME_PATTERNS.items():
            if pattern in text_lower:
                return value
        
        return None
    
    def extract_error_codes(self, text: str) -> List[str]:
        """Extract ORA error codes from text."""
        codes = []
        
        for pattern in self.ERROR_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                code = match.upper().replace(' ', '-')
                if not code.startswith('ORA-'):
                    code = f'ORA-{code}'
                if code not in codes:
                    codes.append(code)
        
        return codes
    
    def extract_all(self, text: str) -> Dict:
        """Extract all entities from text."""
        return {
            'database': self.extract_database(text),
            'severity': self.extract_severity(text),
            'time_frame': self.extract_time_frame(text),
            'error_codes': self.extract_error_codes(text)
        }


class IntentClassifier:
    """
    Classifies user intent from question.
    """
    
    # Intent patterns
    INTENT_PATTERNS = {
        QuestionType.COUNT: [
            r'how many',
            r'count',
            r'number of',
            r'total',
            r'how much',
        ],
        QuestionType.COMPARISON: [
            r'worse than',
            r'better than',
            r'compared to',
            r'vs\b',
            r'versus',
            r'more than',
            r'less than',
            r'higher than',
            r'lower than',
            r'different from',
        ],
        QuestionType.MEANING: [
            r'what does .* mean',
            r'what is',
            r'what are',
            r'explain',
            r'tell me about',
            r'meaning of',
            r'what\'s this',
            r'in simple terms',
        ],
        QuestionType.PRIORITY: [
            r'what should i',
            r'which .* first',
            r'most important',
            r'priority',
            r'focus on',
            r'start with',
            r'critical first',
        ],
        QuestionType.RISK: [
            r'risk',
            r'dangerous',
            r'cause outage',
            r'impact',
            r'serious',
            r'affect production',
            r'damage',
            r'harm',
        ],
        QuestionType.TREND: [
            r'increas',
            r'decreas',
            r'trend',
            r'getting worse',
            r'getting better',
            r'going up',
            r'going down',
            r'over time',
        ],
        QuestionType.HISTORY: [
            r'have we seen',
            r'seen before',
            r'previous',
            r'last time',
            r'history',
            r'in the past',
            r'historically',
        ],
        QuestionType.CAUSE: [
            r'what causes',
            r'what usually causes',
            r'why is',
            r'why are',
            r'root cause',
            r'reason for',
            r'caused by',
            r'source of',
            r'causes',
        ],
        QuestionType.ACTION: [
            r'what to do',
            r'how to fix',
            r'how do i',
            r'resolve',
            r'check first',
            r'next step',
            r'what would .* do',
        ],
        QuestionType.VAGUE: [
            r'should i worry',
            r'worried',
            r'concern',
            r'is this normal',
            r'is this bad',
            r'is this okay',
            r'is this fine',
            r'is this good',
        ],
    }
    
    def classify(self, question: str) -> Tuple[str, float]:
        """
        Classify question intent.
        Returns (question_type, confidence)
        """
        question_lower = question.lower()
        
        # Check each intent type
        scores = {}
        for intent_type, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, question_lower):
                    scores[intent_type] = scores.get(intent_type, 0) + 1
        
        if not scores:
            return QuestionType.GENERAL, 0.5
        
        # Return highest scoring intent
        best_intent = max(scores.items(), key=lambda x: x[1])
        confidence = min(0.9, 0.6 + (best_intent[1] * 0.1))
        
        return best_intent[0], confidence


class QuestionReinterpreter:
    """
    Reinterprets unclear questions into actionable queries.
    Handles vague and informal questions.
    """
    
    REINTERPRETATIONS = {
        'should i worry': 'Assess whether the current alert situation requires immediate attention',
        'is this normal': 'Compare current alert volume and patterns against typical baselines',
        'is this bad': 'Evaluate the severity and risk level of the current situation',
        'what\'s going on': 'Provide an overview of current alerts and incidents',
        'what happened': 'Summarize recent alert activity and any incidents',
        'help': 'Provide guidance on the current alert situation',
        'status': 'Give current system alert status overview',
        'anything urgent': 'Identify highest priority alerts requiring immediate attention',
        'what\'s wrong': 'Identify and explain current issues or anomalies',
        'update me': 'Provide summary of current alert situation and any changes',
    }
    
    def reinterpret(self, question: str) -> Tuple[str, str]:
        """
        Reinterpret a vague question into a clear intent.
        Returns (interpreted_intent, explanation)
        """
        question_lower = question.lower().strip()
        
        # Check for known vague patterns
        for pattern, interpretation in self.REINTERPRETATIONS.items():
            if pattern in question_lower:
                explanation = f"I interpret '{question}' as: {interpretation}"
                return interpretation, explanation
        
        # For unknown patterns, make best guess
        if len(question.split()) <= 2:
            return (
                'Provide general alert status and any items needing attention',
                f"I'll provide a general overview based on your question: '{question}'"
            )
        
        # Default: treat as general inquiry
        return (
            question,
            f"I understand you're asking about: {question}"
        )


class FollowUpHandler:
    """
    Handles follow-up questions that reference previous context.
    """
    
    FOLLOWUP_INDICATORS = [
        'what about',
        'and for',
        'also',
        'same for',
        'how about',
        'only',
        'just the',
        'show me',
        'tell me more',
        'more details',
        'expand on',
    ]
    
    def is_followup(self, question: str) -> bool:
        """Determine if question is a follow-up."""
        question_lower = question.lower()
        
        # Check for follow-up indicators
        for indicator in self.FOLLOWUP_INDICATORS:
            if indicator in question_lower:
                return True
        
        # Very short questions are often follow-ups
        if len(question.split()) <= 3:
            return True
        
        # Questions that are just a filter value
        filter_only = ['critical', 'warning', 'standby', 'primary']
        if question_lower.strip().rstrip('?') in filter_only:
            return True
        
        return False
    
    def interpret_followup(self, question: str, previous_context: Dict) -> str:
        """
        Interpret follow-up question using previous context.
        """
        question_lower = question.lower()
        
        # Get previous database context
        prev_db = previous_context.get('database', '')
        prev_severity = previous_context.get('severity', '')
        
        # Handle "only critical" type follow-ups
        if 'only critical' in question_lower or question_lower.strip() == 'critical':
            return f"Show critical alerts for {prev_db}" if prev_db else "Show critical alerts"
        
        if 'only warning' in question_lower or question_lower.strip() == 'warning':
            return f"Show warning alerts for {prev_db}" if prev_db else "Show warning alerts"
        
        # Handle "what about standby" type
        if 'standby' in question_lower:
            return "Show alerts for standby databases"
        
        if 'primary' in question_lower:
            return "Show alerts for primary databases"
        
        # Default interpretation
        return f"Continue with context of {prev_db or 'all databases'}: {question}"


class QuestionUnderstandingEngine:
    """
    Master Question Understanding Engine - Phase 6 Component.
    
    Handles ANY DBA question naturally:
    - Counts, Comparisons, Meaning, Priority
    - Risk, Trend, Follow-ups, Vague questions
    
    RULES:
    - NEVER reply "Invalid question"
    - Always provide interpretation
    - Ask for clarification gracefully when needed
    """
    
    def __init__(self):
        self.entity_extractor = EntityExtractor()
        self.intent_classifier = IntentClassifier()
        self.reinterpreter = QuestionReinterpreter()
        self.followup_handler = FollowUpHandler()
    
    def understand(self, question: str, 
                  previous_context: Dict = None) -> QuestionInterpretation:
        """
        Understand a DBA question and return structured interpretation.
        """
        if previous_context is None:
            previous_context = {}
        
        # Extract entities
        entities = self.entity_extractor.extract_all(question)
        
        # Check if follow-up
        is_followup = self.followup_handler.is_followup(question)
        
        # Classify intent
        question_type, intent_confidence = self.intent_classifier.classify(question)
        
        # Determine interpreted intent
        if is_followup:
            interpreted_intent = self.followup_handler.interpret_followup(
                question, previous_context
            )
            interpretation_explanation = (
                f"This appears to be a follow-up to your previous question. "
                f"I'll apply filters: {interpreted_intent}"
            )
        elif question_type == QuestionType.VAGUE:
            interpreted_intent, interpretation_explanation = self.reinterpreter.reinterpret(question)
        else:
            interpreted_intent = question
            interpretation_explanation = f"Understanding: {self._get_type_explanation(question_type)}"
        
        # Carry forward context from previous question if entities missing
        if not entities['database'] and previous_context.get('database'):
            entities['database'] = previous_context['database']
        if not entities['severity'] and previous_context.get('severity'):
            entities['severity'] = previous_context['severity']
        
        # Determine if clarification needed
        needs_clarification = False
        suggested_clarification = ""
        
        if intent_confidence < 0.5:
            needs_clarification = True
            suggested_clarification = "Could you tell me more about what you're looking for?"
        
        return QuestionInterpretation(
            original_question=question,
            interpreted_intent=interpreted_intent,
            question_type=question_type,
            extracted_entities=entities,
            confidence=intent_confidence,
            interpretation_explanation=interpretation_explanation,
            needs_clarification=needs_clarification,
            suggested_clarification=suggested_clarification
        )
    
    def _get_type_explanation(self, question_type: str) -> str:
        """Get human-readable explanation of question type."""
        explanations = {
            QuestionType.COUNT: "You want to know quantities or totals",
            QuestionType.COMPARISON: "You want to compare against a baseline",
            QuestionType.MEANING: "You want to understand what something means",
            QuestionType.PRIORITY: "You want to know what to focus on first",
            QuestionType.RISK: "You're assessing risk or potential impact",
            QuestionType.TREND: "You want to understand if things are changing",
            QuestionType.HISTORY: "You want to know about past occurrences",
            QuestionType.CAUSE: "You want to understand root causes",
            QuestionType.ACTION: "You want to know what steps to take",
            QuestionType.VAGUE: "You're looking for a general assessment",
            QuestionType.GENERAL: "General inquiry about the system",
            QuestionType.FOLLOWUP: "Following up on previous context"
        }
        return explanations.get(question_type, "General database inquiry")
    
    def format_interpretation_disclosure(self, interpretation: QuestionInterpretation) -> str:
        """
        Format interpretation for transparent disclosure to user.
        Used when there's ambiguity in the question.
        """
        if interpretation.confidence >= 0.8:
            return ""  # High confidence, no need to disclose
        
        lines = []
        lines.append("---")
        lines.append(f"💬 *{interpretation.interpretation_explanation}*")
        
        if interpretation.needs_clarification:
            lines.append("")
            lines.append(f"*{interpretation.suggested_clarification}*")
        
        return "\n".join(lines)
    
    def get_query_parameters(self, interpretation: QuestionInterpretation) -> Dict:
        """
        Convert interpretation into query parameters for data lookup.
        """
        params = {
            'target': interpretation.extracted_entities.get('database'),
            'severity': interpretation.extracted_entities.get('severity'),
            'time_frame': interpretation.extracted_entities.get('time_frame'),
            'error_codes': interpretation.extracted_entities.get('error_codes', []),
            'question_type': interpretation.question_type,
            'intent': interpretation.interpreted_intent
        }
        return params


# Singleton instance
QUESTION_ENGINE = QuestionUnderstandingEngine()
