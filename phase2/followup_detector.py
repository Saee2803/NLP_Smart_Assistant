"""
PHASE 2: Follow-up Question Detector
=====================================
Detects and classifies follow-up questions.

FOLLOW-UP TYPES (MANDATORY):
- LIMIT: "ok show me 20", "show more", "first 10"
- FILTER: "only critical", "just warning", "filter by severity"
- LIMIT_FILTER: "show me 5 critical", "first 10 warning"
- CONTEXTUAL_SWITCH: "now show me standby" (keeps db context)
- CONTEXT_RESET: "how many total alerts exist" (new independent question)
- NEW_QUESTION: Completely new topic, no context needed

DETECTION RULES:
1. If starts with "ok", "now", "and", "but", "also" → likely follow-up
2. If lacks subject (db, category) but has limit/filter → follow-up
3. If complete question with all info → context reset or new question
"""

import re
from typing import Dict, Any, Optional, Tuple
from enum import Enum
from .context_manager import ConversationContext


class FollowUpType(Enum):
    """Types of follow-up questions."""
    LIMIT = "LIMIT"                     # "ok show me 20"
    FILTER = "FILTER"                   # "only critical"
    LIMIT_FILTER = "LIMIT_FILTER"       # "show me 5 critical"
    CONTEXTUAL_SWITCH = "CONTEXTUAL_SWITCH"  # "now show standby"
    CONTEXT_RESET = "CONTEXT_RESET"     # "how many total alerts"
    NEW_QUESTION = "NEW_QUESTION"       # New independent question
    NOT_FOLLOWUP = "NOT_FOLLOWUP"       # No context exists


class FollowUpDetector:
    """
    Detects whether a question is a follow-up and classifies its type.
    """
    
    # Patterns for follow-up detection
    FOLLOWUP_STARTERS = [
        r'^ok\b', r'^okay\b', r'^now\b', r'^and\b', r'^but\b', 
        r'^also\b', r'^then\b', r'^what about\b', r'^how about\b',
        r'^show me\b', r'^give me\b', r'^just\b', r'^only\b'
    ]
    
    # Limit patterns - detect number requests
    LIMIT_PATTERNS = [
        r'(?:show|give|display|list)\s*(?:me)?\s*(\d+)',     # "show me 20"
        r'^(\d+)\s*(?:alerts?)?$',                            # "20" or "20 alerts"
        r'(?:first|top|next)\s*(\d+)',                        # "first 10"
        r'(\d+)\s*more',                                      # "10 more"
        r'limit\s*(?:to)?\s*(\d+)',                           # "limit to 50"
    ]
    
    # Filter patterns - detect severity/category filters
    FILTER_SEVERITY_PATTERNS = [
        r'\b(?:only|just|filter)\s+(critical|warning)\b',     # "only critical"
        r'^(critical|warning)\s*(?:ones?|alerts?)?$',          # "critical" or "critical ones"
        r'\b(critical|warning)\s+(?:only|ones?|alerts?)\b',    # "critical only"
    ]
    
    # Context switch patterns - new category but same db
    CONTEXT_SWITCH_PATTERNS = [
        r'(?:now|what about|how about|show)\s+(?:me\s+)?(?:the\s+)?(standby|tablespace|listener|dataguard)',
        r'(?:switch to|change to)\s+(standby|tablespace|listener)',
    ]
    
    # Reset indicators - complete new questions
    RESET_INDICATORS = [
        r'\bhow many total\b',
        r'\ball alerts?\b',
        r'\bwhat is the status\b',
        r'\bshow me alerts for\s+\w+\b',  # Explicit db mention
        r'\bhow many\s+\w+\s+alerts?\s+(?:for|in|on)\s+\w+\b',  # Full question
    ]
    
    def __init__(self):
        # Compile patterns for efficiency
        self._followup_re = [re.compile(p, re.IGNORECASE) for p in self.FOLLOWUP_STARTERS]
        self._limit_re = [re.compile(p, re.IGNORECASE) for p in self.LIMIT_PATTERNS]
        self._filter_re = [re.compile(p, re.IGNORECASE) for p in self.FILTER_SEVERITY_PATTERNS]
        self._switch_re = [re.compile(p, re.IGNORECASE) for p in self.CONTEXT_SWITCH_PATTERNS]
        self._reset_re = [re.compile(p, re.IGNORECASE) for p in self.RESET_INDICATORS]
    
    def detect(
        self, 
        question: str, 
        context: ConversationContext
    ) -> Tuple[FollowUpType, Dict[str, Any]]:
        """
        Detect if question is a follow-up and extract relevant info.
        
        Args:
            question: Current question
            context: Current conversation context
            
        Returns:
            Tuple of (FollowUpType, extracted_info)
            
            extracted_info contains:
            - limit: int or None
            - severity: str or None
            - category: str or None
            - confidence: float
        """
        question = question.strip()
        
        # If no context, it's not a follow-up
        if not context.has_context:
            return FollowUpType.NOT_FOLLOWUP, {"confidence": 1.0}
        
        # Check for context reset (complete new question)
        if self._is_context_reset(question):
            return FollowUpType.CONTEXT_RESET, {"confidence": 0.9}
        
        # Extract potential follow-up info
        limit = self._extract_limit(question)
        severity = self._extract_severity(question)
        category = self._extract_category_switch(question)
        
        # Determine follow-up type
        has_followup_starter = self._has_followup_starter(question)
        
        # CASE 1: Limit + Filter combination
        if limit is not None and severity is not None:
            return FollowUpType.LIMIT_FILTER, {
                "limit": limit,
                "severity": severity,
                "confidence": 0.95
            }
        
        # CASE 2: Just limit change
        if limit is not None:
            return FollowUpType.LIMIT, {
                "limit": limit,
                "confidence": 0.90
            }
        
        # CASE 3: Just filter (severity) change
        if severity is not None:
            return FollowUpType.FILTER, {
                "severity": severity,
                "confidence": 0.90
            }
        
        # CASE 4: Category switch (keeps db context)
        if category is not None:
            return FollowUpType.CONTEXTUAL_SWITCH, {
                "category": category,
                "confidence": 0.85
            }
        
        # CASE 5: Has follow-up starter but no specific modification
        if has_followup_starter:
            # Could be a general follow-up, let Phase 1 handle with context
            return FollowUpType.CONTEXTUAL_SWITCH, {
                "confidence": 0.6
            }
        
        # Default: Likely a new question
        return FollowUpType.NEW_QUESTION, {"confidence": 0.7}
    
    def _has_followup_starter(self, question: str) -> bool:
        """Check if question starts with follow-up indicator."""
        q_lower = question.lower()
        return any(pattern.search(q_lower) for pattern in self._followup_re)
    
    def _extract_limit(self, question: str) -> Optional[int]:
        """Extract limit (number of results) from question."""
        for pattern in self._limit_re:
            match = pattern.search(question)
            if match:
                try:
                    limit = int(match.group(1))
                    if 1 <= limit <= 1000:  # Reasonable limit
                        return limit
                except (ValueError, IndexError):
                    continue
        return None
    
    def _extract_severity(self, question: str) -> Optional[str]:
        """Extract severity filter from question."""
        q_lower = question.lower()
        
        for pattern in self._filter_re:
            match = pattern.search(q_lower)
            if match:
                sev = match.group(1).upper()
                if sev in ["CRITICAL", "WARNING"]:
                    return sev
        
        # Simple word check as fallback
        words = q_lower.split()
        if "critical" in words:
            return "CRITICAL"
        if "warning" in words:
            return "WARNING"
        
        return None
    
    def _extract_category_switch(self, question: str) -> Optional[str]:
        """Extract category switch from question."""
        for pattern in self._switch_re:
            match = pattern.search(question)
            if match:
                cat = match.group(1).lower()
                # Normalize category names
                if cat in ["standby", "dataguard"]:
                    return "standby"
                return cat
        
        return None
    
    def _is_context_reset(self, question: str) -> bool:
        """Check if question should reset context (new independent question)."""
        # Check reset patterns
        for pattern in self._reset_re:
            if pattern.search(question):
                # Additional check: if mentions specific db, definitely reset
                if re.search(r'\b(MIDEVSTB|MIDEVSTBN)\b', question, re.IGNORECASE):
                    return True
                # Check for "total" without current context filters
                if "total" in question.lower():
                    return True
        
        return False
    
    def is_followup(self, question: str, context: ConversationContext) -> bool:
        """
        Simple check if question is any type of follow-up.
        
        Args:
            question: Current question
            context: Conversation context
            
        Returns:
            True if question is a follow-up
        """
        followup_type, _ = self.detect(question, context)
        return followup_type not in [
            FollowUpType.NOT_FOLLOWUP, 
            FollowUpType.NEW_QUESTION,
            FollowUpType.CONTEXT_RESET
        ]


class ContextResolver:
    """
    Resolves the effective intent by merging follow-up with context.
    """
    
    def resolve(
        self,
        question: str,
        followup_type: FollowUpType,
        followup_info: Dict[str, Any],
        context: ConversationContext
    ) -> Dict[str, Any]:
        """
        Resolve the effective query parameters by merging follow-up with context.
        
        Args:
            question: Current question
            followup_type: Type of follow-up
            followup_info: Extracted follow-up information
            context: Current conversation context
            
        Returns:
            Resolved query parameters:
            {
                "database": str or None,
                "severity": str or None,
                "category": str or None,
                "limit": int or None,
                "intent_type": str,
                "from_context": bool
            }
        """
        resolved = {
            "database": None,
            "severity": None,
            "category": None,
            "limit": None,
            "intent_type": context.last_intent or "LIST",
            "from_context": True
        }
        
        if followup_type == FollowUpType.LIMIT:
            # Keep all context, just change limit
            resolved["database"] = context.last_database
            resolved["severity"] = context.last_severity
            resolved["category"] = context.last_category
            resolved["limit"] = followup_info.get("limit")
            resolved["intent_type"] = "LIST"
            
        elif followup_type == FollowUpType.FILTER:
            # Keep db/category context, change severity
            resolved["database"] = context.last_database
            resolved["category"] = context.last_category
            resolved["severity"] = followup_info.get("severity")
            resolved["intent_type"] = "LIST"
            
        elif followup_type == FollowUpType.LIMIT_FILTER:
            # Keep db context, change severity and limit
            resolved["database"] = context.last_database
            resolved["category"] = context.last_category
            resolved["severity"] = followup_info.get("severity")
            resolved["limit"] = followup_info.get("limit")
            resolved["intent_type"] = "LIST"
            
        elif followup_type == FollowUpType.CONTEXTUAL_SWITCH:
            # Keep db context, switch category
            resolved["database"] = context.last_database
            resolved["category"] = followup_info.get("category")
            resolved["severity"] = None  # Reset severity on category switch
            resolved["intent_type"] = "LIST"
            
        else:
            # CONTEXT_RESET, NEW_QUESTION, NOT_FOLLOWUP
            resolved["from_context"] = False
        
        return resolved


# Convenience functions
_detector = None
_resolver = None

def get_followup_detector() -> FollowUpDetector:
    """Get singleton follow-up detector."""
    global _detector
    if _detector is None:
        _detector = FollowUpDetector()
    return _detector


def get_context_resolver() -> ContextResolver:
    """Get singleton context resolver."""
    global _resolver
    if _resolver is None:
        _resolver = ContextResolver()
    return _resolver


def detect_followup(question: str, context: ConversationContext) -> Tuple[FollowUpType, Dict]:
    """Convenience function to detect follow-up."""
    return get_followup_detector().detect(question, context)


def resolve_context(
    question: str,
    followup_type: FollowUpType,
    followup_info: Dict,
    context: ConversationContext
) -> Dict:
    """Convenience function to resolve context."""
    return get_context_resolver().resolve(question, followup_type, followup_info, context)
