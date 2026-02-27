# nlp_engine/smart_intent.py
"""
==============================================================
SMART INTENT CLASSIFIER - Semantic intent understanding
==============================================================

Classifies user queries into intents with confidence scores.
Uses pattern matching with semantic understanding.

Intents:
- ALERT_COUNT: "how many alerts", "count alerts"
- ALERT_LIST: "show alerts", "list issues"
- ALERT_SUMMARY: "alerts for DBNAME" (summary with breakdown)
- SEVERITY_FILTER: "only critical", "just warnings"
- DATABASE_QUERY: "which database has most"
- ROOT_CAUSE: "why", "explain", "reason"
- RECOMMENDATION: "what to do", "how to fix"
- COMPARISON: "compare", "which is worse"
- PREDICTION: "predict", "risk", "will fail"
- HEALTH_CHECK: "status", "health", "is it ok"
- ISSUE_TYPE: "standby issues", "tablespace problems"
- FOLLOWUP: "show 20", "next", "more"

Python 3.6.8 compatible.
"""

import re
from typing import Dict, Tuple, Optional, Any


class SmartIntentClassifier:
    """
    Semantic intent classification for DBA assistant queries.
    
    Features:
    - Multi-pattern matching with priority
    - Confidence scoring
    - Question type detection (FACT, ANALYSIS, ACTION)
    - Follow-up detection
    """
    
    # Intent definitions with patterns and priority
    INTENT_PATTERNS = {
        # Follow-up intents (highest priority - check first)
        "FOLLOWUP_LIMIT": {
            "patterns": [
                r"^(?:ok\s+)?show\s+(?:me\s+)?(\d+)",
                r"^(?:ok\s+)?(?:top|first|next|last)\s+(\d+)",
                r"^(?:ok\s+)?(\d+)\s+(?:alerts?|more)",
                r"^(?:ok|yes|sure)\s+show",
                r"^show\s+more",
                r"^next\s*(?:\d+)?",
                r"^more\s+alerts?"
            ],
            "priority": 100,
            "question_type": "FACT"
        },
        
        "FOLLOWUP_SEVERITY": {
            "patterns": [
                r"^(?:ok\s+)?(?:only|just|fakt)\s+(critical|warning|warnings?|info)",
                r"^(?:ok\s+)?(critical|warning|warnings?)\s+(?:only|ones?|fakt|dakhav|show)",
                r"^(?:ok\s+)?show\s+(?:me\s+)?(?:only\s+)?(?:\d+\s+)?(critical|warning|warnings?)(?:\s+ones?)?",
                r"excluding?\s+(critical|warning|warnings?)",
                r"show\s+(?:me\s+)?(?:only\s+)?(critical|warning|warnings?)\s+(?:ones?|alerts?)?",
                r"only\s+(warning|warnings?|critical)\s+(?:alerts?|show|dakhav|ones?)?"
            ],
            "priority": 95,
            "question_type": "FACT"
        },
        
        "FRESH_QUERY": {
            "patterns": [
                # Only match "show all" when it's standalone or followed by "alerts" without severity
                r"^(?:now\s+)?show\s+(?:me\s+)?all\s*$",
                r"^(?:now\s+)?show\s+(?:me\s+)?all\s+alerts?\s*$",
                r"^reset\b",
                r"^clear\b",
                r"^fresh\s+(?:query|search)",
                r"^start\s+(?:over|fresh|new)"
            ],
            "priority": 98,
            "question_type": "FACT"
        },
        
        # Primary intents
        "ALERT_SUMMARY": {
            "patterns": [
                r"(?:show|get|display)\s+(?:me\s+)?alerts?\s+(?:for|on|from|of)\s+[A-Z]",
                r"alerts?\s+(?:for|on|from)\s+[A-Z][A-Z0-9_]+",
                r"[A-Z][A-Z0-9_]{3,}(?:STB|STBN|DB)\s+alerts?",
                r"what\s+(?:are\s+)?(?:the\s+)?alerts?\s+(?:for|on)\s+[A-Z]"
            ],
            "priority": 90,
            "question_type": "FACT"
        },
        
        "ALERT_COUNT": {
            "patterns": [
                r"how\s+many\s+(?:alerts?|issues?|errors?)",
                r"how\s+many\s+(?:critical|warning|warnings?)\s+(?:alerts?)?",
                r"count\s+(?:of\s+)?(?:alerts?|issues?)",
                r"count\s+(?:of\s+)?(?:critical|warning)\s+(?:alerts?)?",
                r"total\s+(?:number\s+of\s+)?(?:alerts?|issues?)",
                r"kiti\s+(?:alerts?|issues?)",
                r"number\s+of\s+(?:alerts?|issues?)"
            ],
            "priority": 85,
            "question_type": "FACT"
        },
        
        "MAX_DATABASE_QUERY": {
            "patterns": [
                r"(?:which|konti|konty)\s+(?:database|db)\s+(?:has|have|madhe|la)\s+(?:the\s+)?(?:most|maximum|highest|max|jaast)\s+(?:alerts?|issues?)?",
                r"maximum\s+(?:alerts?|issues?)\s+(?:konti|konty|which)\s+(?:database|db)",
                r"(?:maximum|most|highest|jaast)\s+(?:alerts?|issues?)\s+(?:database|db|konta)?",
                r"(?:database|db|konta)\s+(?:with|madhe)\s+(?:most|maximum|jaast)\s+(?:alerts?)?",
                r"konty\s+db\s+la\s+(?:max|maximum|jaast)\s+alerts?"
            ],
            "priority": 92,
            "question_type": "FACT"
        },
        
        "ALERT_LIST": {
            "patterns": [
                r"(?:show|list|display|get)\s+(?:me\s+)?(?:all\s+)?(?:critical|warning)?\s*(?:the\s+)?alerts?",
                r"(?:show|list|display)\s+(?:me\s+)?(?:\d+\s+)?(?:critical|warning)?\s*alerts?",
                r"(?:show|list)\s+(?:me\s+)?issues?",
                r"(?:what|which)\s+alerts?"
            ],
            "priority": 80,
            "question_type": "FACT"
        },
        
        "ISSUE_TYPE_QUERY": {
            "patterns": [
                r"(?:show|list)\s+(?:me\s+)?standby\s+(?:issues?|alerts?|problems?)",
                r"(?:show|list)\s+(?:me\s+)?(?:data\s*guard|dataguard)\s+(?:issues?|alerts?)",
                r"(?:show|list)\s+(?:me\s+)?tablespace\s+(?:issues?|alerts?|problems?)",
                r"(?:show|list)\s+(?:me\s+)?connection\s+(?:issues?|errors?)",
                r"standby\s+(?:issues?|problems?|alerts?)",
                r"(?:data\s*guard|dataguard)\s+(?:issues?|status)"
            ],
            "priority": 88,
            "question_type": "FACT"
        },
        
        "DATABASE_QUERY": {
            "patterns": [
                r"which\s+(?:database|db)\s+(?:has|have)\s+(?:the\s+)?(?:most|maximum|highest)",
                r"(?:database|db)\s+with\s+(?:most|maximum|highest)",
                r"highest\s+(?:risk|alert)\s+(?:database|db)",
                r"most\s+(?:problematic|affected)\s+(?:database|db)",
                r"top\s+(?:database|db)\s+by\s+alerts?"
            ],
            "priority": 82,
            "question_type": "FACT"
        },
        
        "ROOT_CAUSE": {
            "patterns": [
                r"\bwhy\b",
                r"(?:what\s+is\s+)?(?:the\s+)?(?:root\s+)?cause",
                r"(?:what\s+is\s+)?(?:the\s+)?reason",
                r"explain\s+(?:why|the)",
                r"ka\s+(?:ho|ahe|zala)",  # Marathi
                r"karan\s+(?:kay|sanag)"
            ],
            "priority": 75,
            "question_type": "ANALYSIS"
        },
        
        "RECOMMENDATION": {
            "patterns": [
                r"(?:what\s+)?(?:should\s+)?(?:i|we)\s+do",
                r"how\s+(?:to|do\s+i)\s+(?:fix|resolve|solve)",
                r"(?:what\s+is\s+)?(?:the\s+)?(?:solution|fix|resolution)",
                r"recommend(?:ation)?",
                r"(?:action|step)s?\s+(?:to\s+)?(?:take|fix)",
                r"kay\s+karaycha"  # Marathi
            ],
            "priority": 70,
            "question_type": "ACTION"
        },
        
        "HEALTH_CHECK": {
            "patterns": [
                r"(?:what\s+is\s+)?(?:the\s+)?(?:health|status)\s+(?:of|for)",
                r"is\s+(?:it|the\s+database)\s+(?:ok|healthy|stable|running)",
                r"(?:database|db)\s+(?:health|status)",
                r"overall\s+(?:health|status|state)",
                r"kasa\s+(?:ahe|challay)"  # Marathi
            ],
            "priority": 72,
            "question_type": "FACT"
        },
        
        "COMPARISON": {
            "patterns": [
                r"compare\s+(?:between)?",
                r"(?:which|what)\s+is\s+(?:worse|better|more)",
                r"vs\b",
                r"versus\b",
                r"difference\s+between"
            ],
            "priority": 68,
            "question_type": "ANALYSIS"
        },
        
        "PREDICTION": {
            "patterns": [
                r"(?:will|can)\s+(?:it|the\s+database)\s+(?:fail|crash|go\s+down)",
                r"predict(?:ion)?",
                r"(?:outage|failure)\s+(?:risk|probability)",
                r"(?:what\s+is\s+)?(?:the\s+)?risk",
                r"(?:is\s+there\s+)?(?:a\s+)?chance\s+(?:of|that)"
            ],
            "priority": 65,
            "question_type": "ANALYSIS"
        },
        
        "TIME_BASED": {
            "patterns": [
                r"(?:when|what\s+time)\s+(?:did|was|is)",
                r"(?:last|past)\s+(?:hour|day|week|month)",
                r"(?:peak|busiest)\s+(?:hour|time)",
                r"(?:at|during)\s+(?:what\s+)?(?:time|hour)"
            ],
            "priority": 60,
            "question_type": "FACT"
        }
    }
    
    # Default intent for unrecognized queries
    DEFAULT_INTENT = "UNKNOWN"
    DEFAULT_QUESTION_TYPE = "FACT"
    
    def classify(self, query: str, entities: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Classify a query into an intent.
        
        Args:
            query: User's natural language query
            entities: Optional pre-extracted entities
            
        Returns:
            Dict with:
            - intent: Classified intent name
            - confidence: Confidence score (0-1)
            - question_type: FACT, ANALYSIS, or ACTION
            - is_followup: Boolean indicating if this is a follow-up
            - matched_pattern: The pattern that matched (for debugging)
        """
        q_lower = query.lower().strip()
        
        best_match = {
            "intent": self.DEFAULT_INTENT,
            "confidence": 0.3,
            "question_type": self.DEFAULT_QUESTION_TYPE,
            "is_followup": False,
            "matched_pattern": None
        }
        
        highest_priority = -1
        
        for intent_name, intent_def in self.INTENT_PATTERNS.items():
            for pattern in intent_def["patterns"]:
                try:
                    match = re.search(pattern, q_lower, re.IGNORECASE)
                    if match:
                        priority = intent_def["priority"]
                        if priority > highest_priority:
                            highest_priority = priority
                            # Calculate confidence based on pattern complexity and match quality
                            confidence = self._calculate_confidence(match, pattern, query)
                            best_match = {
                                "intent": intent_name,
                                "confidence": confidence,
                                "question_type": intent_def["question_type"],
                                "is_followup": intent_name.startswith("FOLLOWUP"),
                                "matched_pattern": pattern
                            }
                except re.error:
                    continue
        
        # Enhance with entity information
        if entities:
            best_match = self._enhance_with_entities(best_match, entities)
        
        return best_match
    
    def _calculate_confidence(self, match, pattern: str, query: str) -> float:
        """Calculate confidence score based on match quality."""
        base_confidence = 0.7
        
        # Longer matches are more confident
        match_len = match.end() - match.start()
        query_len = len(query)
        coverage = match_len / query_len if query_len > 0 else 0
        
        # Complex patterns are more specific
        pattern_complexity = len(pattern) / 50  # Normalize
        
        confidence = base_confidence + (coverage * 0.2) + min(pattern_complexity, 0.1)
        return min(confidence, 0.99)
    
    def _enhance_with_entities(self, result: Dict, entities: Dict) -> Dict:
        """Enhance classification with entity information."""
        # If we have a database but intent is UNKNOWN, it's likely ALERT_SUMMARY
        if result["intent"] == "UNKNOWN" and entities.get("databases"):
            result["intent"] = "ALERT_SUMMARY"
            result["confidence"] = 0.75
            result["question_type"] = "FACT"
        
        # If we have severity only with no context, it's FOLLOWUP_SEVERITY
        if entities.get("severity") and not entities.get("databases"):
            if result["intent"] == "UNKNOWN":
                result["intent"] = "FOLLOWUP_SEVERITY"
                result["is_followup"] = True
                result["confidence"] = 0.7
        
        # If we have limit only, it's FOLLOWUP_LIMIT
        if entities.get("limit") and not entities.get("databases"):
            if result["intent"] == "UNKNOWN" or result["intent"] == "ALERT_LIST":
                result["intent"] = "FOLLOWUP_LIMIT"
                result["is_followup"] = True
                result["confidence"] = 0.75
        
        return result
    
    def is_followup(self, query: str) -> Tuple[bool, str]:
        """
        Quick check if query is a follow-up.
        
        Returns:
            Tuple of (is_followup, followup_type)
        """
        q_lower = query.lower().strip()
        
        # Quick pattern checks
        followup_indicators = [
            (r"^(?:ok|yes|sure|yeah)\s", "CONTINUATION"),
            (r"^show\s+(?:me\s+)?\d+", "LIMIT"),
            (r"^(?:only|just)\s+(?:critical|warning)", "SEVERITY"),
            (r"^(?:top|first|next)\s+\d+", "LIMIT"),
            (r"^\d+\s+(?:alerts?|more)", "LIMIT"),
            (r"^(?:next|more)\b", "CONTINUATION"),
            (r"^show\s+(?:me\s+)?(?:\d+\s+)?(?:warning|critical)", "SEVERITY_LIMIT")
        ]
        
        for pattern, ftype in followup_indicators:
            if re.search(pattern, q_lower):
                return True, ftype
        
        return False, None


# Singleton instance
_classifier = None

def get_intent_classifier() -> SmartIntentClassifier:
    """Get the singleton intent classifier instance."""
    global _classifier
    if _classifier is None:
        _classifier = SmartIntentClassifier()
    return _classifier


# Convenience function
def classify_intent(query: str, entities: Dict = None) -> Dict[str, Any]:
    """Classify intent using the singleton classifier."""
    return get_intent_classifier().classify(query, entities)


# Test
if __name__ == "__main__":
    classifier = SmartIntentClassifier()
    
    test_queries = [
        "show me alerts for MIDEVSTB",
        "ok show me 18 warning",
        "how many critical alerts",
        "why is MIDEVSTBN failing",
        "what should I do to fix it",
        "show standby issues",
        "which database has the most alerts",
        "is MIDEVSTB healthy",
        "top 10 critical alerts",
        "next 20",
        "only critical"
    ]
    
    for q in test_queries:
        result = classifier.classify(q)
        print("\nQuery:", q)
        print("Intent:", result["intent"], "| Confidence:", round(result["confidence"], 2))
        print("Type:", result["question_type"], "| Follow-up:", result["is_followup"])
