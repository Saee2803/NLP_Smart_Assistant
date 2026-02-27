"""
PHASE 1: Intent Parser
======================
Extracts structured intent from natural language DBA questions.

OUTPUT STRUCTURE:
{
    "intent_type": "COUNT" | "LIST" | "STATUS" | "FACT" | "UNKNOWN",
    "database": str | "ALL" | None,
    "severity": "CRITICAL" | "WARNING" | "ALL" | None,
    "category": "ALERT" | "STANDBY" | "DATAGUARD" | "ALL" | None,
    "limit": int | None,
    "confidence": float (0.0 - 1.0)
}

RULES:
- Uses pattern + semantic logic (not just keyword matching)
- If confidence < 0.7 → intent_type = UNKNOWN
- No guessing or hallucination
"""

import re
from typing import Dict, Any, Optional, List, Tuple


class Phase1IntentParser:
    """
    Lightweight NLP intent parser for DBA questions.
    
    Converts natural language to structured intent objects.
    No ML dependencies - uses pattern matching + semantic rules.
    """
    
    # =========================================================
    # PATTERN DEFINITIONS
    # =========================================================
    
    # Intent type patterns
    COUNT_PATTERNS = [
        r'\bhow\s+many\b',
        r'\bcount\s+(?:of|the)?\b',
        r'\btotal\s+(?:number|count)?\b',
        r'\bnumber\s+of\b',
        r'\bare\s+there\s+any\b',  # "are there any" implies count check
    ]
    
    LIST_PATTERNS = [
        r'\bshow\s+(?:me\s+)?(?:all\s+)?',
        r'\blist\s+(?:all\s+)?',
        r'\bdisplay\s+(?:all\s+)?',
        r'\bget\s+(?:me\s+)?(?:all\s+)?',
        r'\bwhat\s+(?:are\s+)?(?:the\s+)?',
        r'\bfetch\b',
    ]
    
    STATUS_PATTERNS = [
        r'\bstatus\s+(?:of|for)\s+\w+',
        r'\bstatus\b',
        r'\bis\s+\w+\s+(?:down|up|healthy|critical|running)\b',
        r'\bhow\s+is\s+\w+\s+doing\b',
        r'\bcheck\s+(?:the\s+)?status\b',
        r'\bhealth\s+(?:of|check|status)\b',
        r'\bwhat\s+is\s+the\s+status\b',
    ]
    
    # Severity patterns
    SEVERITY_PATTERNS = {
        'CRITICAL': [
            r'\bcritical\b',
            r'\bcrit\b',
            r'\bsevere\b',
            r'\bhigh\s+severity\b',
            r'\bhigh\s+priority\b',
            r'\burgent\b',
        ],
        'WARNING': [
            r'\bwarning\b',
            r'\bwarn\b',
            r'\bmedium\s+severity\b',
            r'\bcaution\b',
        ],
    }
    
    # Category patterns
    CATEGORY_PATTERNS = {
        'STANDBY': [
            r'\bstandby\b',
            r'\bdata\s*guard\b',
            r'\bdataguard\b',
            r'\bdr\s+database\b',
            r'\breplica\b',
            r'\bapply\s+lag\b',
            r'\btransport\s+lag\b',
            r'\bmrp\b',
            r'\bredo\s+apply\b',
        ],
        'DATAGUARD': [
            r'\bdata\s*guard\b',
            r'\bdataguard\b',
            r'\bdg\s+broker\b',
            r'\bswitchover\b',
            r'\bfailover\b',
        ],
    }
    
    # Database name patterns
    DB_PATTERNS = [
        r'\bfor\s+(?:database\s+)?([A-Z][A-Z0-9_]{2,})\b',
        r'\bon\s+(?:database\s+)?([A-Z][A-Z0-9_]{2,})\b',
        r'\bin\s+(?:database\s+)?([A-Z][A-Z0-9_]{2,})\b',
        r'\b([A-Z][A-Z0-9_]{2,}(?:STB|STBN|DB|PRD|DEV|TST))\b',
        r'\bdatabase\s+([A-Z][A-Z0-9_]{2,})\b',
        r'\bdb\s+([A-Z][A-Z0-9_]{2,})\b',
    ]
    
    # Limit patterns
    LIMIT_PATTERNS = [
        r'\btop\s+(\d+)\b',
        r'\bfirst\s+(\d+)\b',
        r'\blast\s+(\d+)\b',
        r'\b(\d+)\s+alerts?\b',
        r'\bshow\s+(?:me\s+)?(\d+)\b',
    ]
    
    # Excluded words (not database names)
    EXCLUDED_WORDS = {
        'THE', 'FOR', 'AND', 'WITH', 'SHOW', 'THIS', 'THAT', 'FROM',
        'ONLY', 'ALERTS', 'CRITICAL', 'DATABASE', 'STATUS', 'WHAT',
        'WHICH', 'WHERE', 'WHEN', 'WHY', 'HOW', 'ARE', 'THERE', 'ANY',
        'ALL', 'SOME', 'MANY', 'WARNING', 'STANDBY', 'ISSUES', 'ERRORS',
        'PROBLEMS', 'LIST', 'SHOW', 'DISPLAY', 'GET', 'FETCH', 'COUNT',
        'TOTAL', 'NUMBER', 'CHECK', 'HEALTH', 'SEVERITY', 'HIGH', 'LOW',
        'MEDIUM', 'INFO', 'ERROR', 'MESSAGE', 'ALERT', 'ISSUE', 'PROBLEM'
    }
    
    def __init__(self, known_databases: List[str] = None):
        """
        Initialize the parser.
        
        Args:
            known_databases: List of valid database names from CSV data
        """
        self.known_databases = set(db.upper() for db in (known_databases or []))
    
    def set_known_databases(self, databases: List[str]):
        """Update the list of known databases."""
        self.known_databases = set(db.upper() for db in databases)
    
    def parse(self, question: str) -> Dict[str, Any]:
        """
        Parse a natural language question into structured intent.
        
        Args:
            question: User's question in natural language
            
        Returns:
            Structured intent object
        """
        if not question or not question.strip():
            return self._make_intent(
                intent_type="UNKNOWN",
                confidence=0.0,
                raw_question=""
            )
        
        q_lower = question.lower().strip()
        q_upper = question.upper().strip()
        
        # Extract components
        intent_type, intent_confidence = self._detect_intent_type(q_lower)
        database = self._extract_database(q_upper)
        severity = self._extract_severity(q_lower)
        category = self._extract_category(q_lower)
        limit = self._extract_limit(q_lower)
        
        # Calculate overall confidence
        confidence = self._calculate_confidence(
            intent_type, intent_confidence, database, severity, category
        )
        
        # If confidence too low, mark as UNKNOWN
        if confidence < 0.7:
            intent_type = "UNKNOWN"
        
        return self._make_intent(
            intent_type=intent_type,
            database=database,
            severity=severity,
            category=category,
            limit=limit,
            confidence=confidence,
            raw_question=question
        )
    
    def _detect_intent_type(self, q_lower: str) -> Tuple[str, float]:
        """Detect the intent type from the question."""
        scores = {
            'COUNT': 0.0,
            'LIST': 0.0,
            'STATUS': 0.0,
            'FACT': 0.0,
        }
        
        # Check COUNT patterns
        for pattern in self.COUNT_PATTERNS:
            if re.search(pattern, q_lower):
                scores['COUNT'] += 0.4
        
        # Check LIST patterns
        for pattern in self.LIST_PATTERNS:
            if re.search(pattern, q_lower):
                scores['LIST'] += 0.4
        
        # Check STATUS patterns
        for pattern in self.STATUS_PATTERNS:
            if re.search(pattern, q_lower):
                scores['STATUS'] += 0.5
        
        # "alerts" keyword boosts LIST/COUNT
        if 'alert' in q_lower:
            scores['LIST'] += 0.2
            scores['COUNT'] += 0.1
        
        # "issues" or "problems" keywords
        if any(w in q_lower for w in ['issue', 'problem', 'error']):
            scores['LIST'] += 0.15
        
        # Question words
        if q_lower.startswith('how many'):
            scores['COUNT'] = max(scores['COUNT'], 0.9)
        elif q_lower.startswith(('what', 'which')):
            scores['FACT'] += 0.3
            scores['LIST'] += 0.2
        elif q_lower.startswith(('show', 'list', 'display', 'get')):
            scores['LIST'] = max(scores['LIST'], 0.8)
        elif q_lower.startswith(('is ', 'are ', 'does ', 'do ')):
            if 'how many' not in q_lower:
                scores['STATUS'] += 0.3
        
        # Find best match
        best_type = max(scores, key=scores.get)
        best_score = scores[best_type]
        
        # If no clear winner, default to FACT
        if best_score < 0.3:
            return ('FACT', 0.5)
        
        return (best_type, min(best_score, 1.0))
    
    def _extract_database(self, q_upper: str) -> Optional[str]:
        """Extract database name from the question."""
        # Check each pattern
        for pattern in self.DB_PATTERNS:
            match = re.search(pattern, q_upper)
            if match:
                potential_db = match.group(1)
                # Validate it's not an excluded word
                if potential_db not in self.EXCLUDED_WORDS:
                    # Check if it's in known databases
                    if self.known_databases:
                        # EXACT match first (case-insensitive)
                        for known in self.known_databases:
                            if potential_db.upper() == known.upper():
                                return known
                        # Only if no exact match, try fuzzy matching
                        # But require the potential_db to be the full match
                        for known in self.known_databases:
                            if potential_db.upper() == known.upper().rstrip('N'):
                                # Still prefer exact match
                                continue
                    # If no known DBs or valid pattern, accept it
                    if len(potential_db) >= 4:
                        return potential_db
        
        # Check for "this database" or "this db" (context needed)
        if re.search(r'\bthis\s+(?:database|db)\b', q_upper.lower()):
            return None  # Needs context (not Phase 1)
        
        # Check for "all databases"
        if re.search(r'\ball\s+(?:databases?|dbs?)\b', q_upper.lower()):
            return "ALL"
        
        return None
    
    def _extract_severity(self, q_lower: str) -> Optional[str]:
        """Extract severity filter from the question."""
        for severity, patterns in self.SEVERITY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, q_lower):
                    return severity
        
        # Check for "all severities" or no severity mentioned
        if re.search(r'\ball\s+(?:severity|severities|types?)\b', q_lower):
            return "ALL"
        
        return None
    
    def _extract_category(self, q_lower: str) -> Optional[str]:
        """Extract category filter from the question."""
        for category, patterns in self.CATEGORY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, q_lower):
                    return category
        
        # Default: if just asking about "alerts", it's general ALERT category
        if re.search(r'\balerts?\b', q_lower) and not any(
            re.search(p, q_lower) for patterns in self.CATEGORY_PATTERNS.values() for p in patterns
        ):
            return "ALERT"
        
        return None
    
    def _extract_limit(self, q_lower: str) -> Optional[int]:
        """Extract result limit from the question."""
        for pattern in self.LIMIT_PATTERNS:
            match = re.search(pattern, q_lower)
            if match:
                try:
                    return int(match.group(1))
                except (ValueError, IndexError):
                    pass
        return None
    
    def _calculate_confidence(
        self,
        intent_type: str,
        intent_confidence: float,
        database: Optional[str],
        severity: Optional[str],
        category: Optional[str]
    ) -> float:
        """Calculate overall confidence score."""
        confidence = intent_confidence
        
        # Boost confidence if we have specific filters
        if database and database != "ALL":
            confidence += 0.1
        if severity:
            confidence += 0.1
        if category:
            confidence += 0.05
        
        # Cap at 1.0
        return min(confidence, 1.0)
    
    def _make_intent(
        self,
        intent_type: str,
        database: Optional[str] = None,
        severity: Optional[str] = None,
        category: Optional[str] = None,
        limit: Optional[int] = None,
        confidence: float = 0.0,
        raw_question: str = ""
    ) -> Dict[str, Any]:
        """Create the structured intent object."""
        return {
            "intent_type": intent_type,
            "database": database,
            "severity": severity,
            "category": category,
            "limit": limit,
            "confidence": round(confidence, 2),
            "raw_question": raw_question
        }


# Singleton instance for easy import
_parser_instance = None

def get_parser(known_databases: List[str] = None) -> Phase1IntentParser:
    """Get or create the parser instance."""
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = Phase1IntentParser(known_databases)
    elif known_databases:
        _parser_instance.set_known_databases(known_databases)
    return _parser_instance


def parse_intent(question: str, known_databases: List[str] = None) -> Dict[str, Any]:
    """Convenience function to parse a question."""
    parser = get_parser(known_databases)
    return parser.parse(question)
