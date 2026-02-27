# nlp_engine/entity_extractor.py
"""
==============================================================
ENTITY EXTRACTOR - Extract structured entities from natural language
==============================================================

Extracts:
- Database names (MIDEVSTB, MIDEVSTBN, etc.)
- Severity levels (CRITICAL, WARNING, INFO)
- Numeric limits (top 10, show 20, first 5)
- Time ranges (last hour, today, yesterday)
- Issue types (standby, tablespace, dataguard, ORA codes)
- Actions (show, count, list, explain, fix)

Python 3.6.8 compatible.
"""

import re
from typing import Dict, List, Optional, Any


class EntityExtractor:
    """
    Extracts structured entities from user queries.
    
    Supports:
    - Multi-language patterns (English + Marathi/Hindi keywords)
    - Fuzzy matching for database names
    - Numeric extraction with word-to-number conversion
    """
    
    # Word to number mapping
    WORD_NUMBERS = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20,
        "twenty-five": 25, "thirty": 30, "fifty": 50, "hundred": 100,
        "ek": 1, "don": 2, "teen": 3, "char": 4, "paach": 5,  # Marathi
        "daha": 10, "vees": 20
    }
    
    # Severity mappings (including variations)
    SEVERITY_PATTERNS = {
        "critical": "CRITICAL",
        "criticals": "CRITICAL",
        "crit": "CRITICAL",
        "high": "CRITICAL",
        "error": "CRITICAL",
        "errors": "CRITICAL",
        "warning": "WARNING",
        "warnings": "WARNING",
        "warn": "WARNING",
        "medium": "WARNING",
        "info": "INFO",
        "informational": "INFO",
        "low": "INFO"
    }
    
    # Issue type keywords
    ISSUE_TYPE_PATTERNS = {
        "standby": ["standby", "data guard", "dataguard", "dg", "dr", "replica", "apply lag", "transport lag", "mrp", "redo"],
        "tablespace": ["tablespace", "space", "storage", "full", "extent", "disk", "ora-1654", "ora-1653"],
        "connection": ["connection", "listener", "tns", "ora-12541", "ora-12537", "connect", "session"],
        "memory": ["memory", "pga", "sga", "ora-4031", "ram"],
        "performance": ["slow", "performance", "hang", "wait", "lock", "blocking"],
        "backup": ["backup", "rman", "archive", "archivelog"],
        "internal": ["internal error", "ora-600", "ora-7445", "kernel"]
    }
    
    # Time range patterns
    TIME_PATTERNS = {
        "last_hour": [r"last\s+hour", r"past\s+hour", r"1\s*h", r"one\s+hour"],
        "last_day": [r"last\s+day", r"today", r"past\s+24", r"24\s*h"],
        "yesterday": [r"yesterday", r"last\s+night"],
        "last_week": [r"last\s+week", r"past\s+week", r"7\s*days?", r"this\s+week"],
        "last_month": [r"last\s+month", r"past\s+month", r"30\s*days?"]
    }
    
    # Action patterns
    ACTION_PATTERNS = {
        "list": [r"\bshow\b", r"\blist\b", r"\bdisplay\b", r"\bget\b", r"\bgive\b", r"\bdakhav\b", r"\bsang\b"],
        "count": [r"\bhow\s+many\b", r"\bcount\b", r"\btotal\b", r"\bkiti\b", r"\bnumber\s+of\b"],
        "explain": [r"\bwhy\b", r"\bexplain\b", r"\breason\b", r"\bka\b", r"\bkaran\b", r"\bcause\b"],
        "fix": [r"\bfix\b", r"\bresolve\b", r"\bsolve\b", r"\brecommend\b", r"\bwhat\s+to\s+do\b", r"\bkay\s+karaycha\b"],
        "compare": [r"\bcompare\b", r"\bvs\b", r"\bversus\b", r"\bdifference\b", r"\bwhich\s+is\b"],
        "predict": [r"\bpredict\b", r"\bwill\b", r"\bfuture\b", r"\brisk\b", r"\boutage\b"]
    }
    
    def __init__(self, known_databases: List[str] = None):
        """
        Initialize the entity extractor.
        
        Args:
            known_databases: List of known database names for fuzzy matching
        """
        self.known_databases = set(db.upper() for db in (known_databases or []))
    
    def set_known_databases(self, databases: List[str]):
        """Update the list of known databases."""
        self.known_databases = set(db.upper() for db in databases)
    
    def extract(self, query: str) -> Dict[str, Any]:
        """
        Extract all entities from a user query.
        
        Args:
            query: Natural language query
            
        Returns:
            Dict with extracted entities:
            {
                "databases": ["MIDEVSTB"],
                "severity": "WARNING",
                "limit": 18,
                "offset": 0,
                "time_range": "last_day",
                "issue_type": "standby",
                "action": "list",
                "ora_codes": ["ORA-12537"],
                "raw_query": "show me 18 warning alerts for MIDEVSTB"
            }
        """
        q_lower = query.lower().strip()
        q_upper = query.upper()
        
        entities = {
            "databases": self._extract_databases(query, q_upper),
            "severity": self._extract_severity(q_lower),
            "limit": self._extract_limit(q_lower),
            "offset": self._extract_offset(q_lower),
            "time_range": self._extract_time_range(q_lower),
            "issue_type": self._extract_issue_type(q_lower),
            "action": self._extract_action(q_lower),
            "ora_codes": self._extract_ora_codes(q_upper),
            "raw_query": query,
            "tokens": self._tokenize(q_lower)
        }
        
        return entities
    
    def _extract_databases(self, query: str, q_upper: str) -> List[str]:
        """Extract database names from query."""
        databases = []
        
        # Pattern 1: Standard DB suffixes
        db_patterns = [
            r'\b([A-Z][A-Z0-9_]{2,}(?:STB|STBN|DB|PRD|DEV|TST|UAT|SIT|DR))\b',
            r'(?:for|about|on|from)\s+([A-Z][A-Z0-9_]{3,})\b',
            r'\balerts?\s+(?:for|on|from)\s+([A-Z][A-Z0-9_]{3,})\b'
        ]
        
        excluded = {"THE", "FOR", "AND", "WITH", "SHOW", "THIS", "THAT", 
                   "FROM", "ONLY", "ALERTS", "CRITICAL", "DATABASE", "STATUS",
                   "WARNING", "INFO", "ERROR", "STANDBY", "DATAGUARD", "TABLESPACE",
                   "LAST", "FIRST", "TOP", "ALL", "MANY", "SOME", "ORA"}
        
        for pattern in db_patterns:
            matches = re.findall(pattern, q_upper)
            for match in matches:
                if match not in excluded and len(match) >= 4:
                    # Check against known databases
                    if self.known_databases:
                        # Exact match
                        if match in self.known_databases:
                            databases.append(match)
                        # Partial match (MIDEVSTB matches MIDEVSTBN)
                        else:
                            for known_db in self.known_databases:
                                if match in known_db or known_db in match:
                                    databases.append(match)
                                    break
                    else:
                        databases.append(match)
        
        return list(set(databases))
    
    def _extract_severity(self, q_lower: str) -> Optional[str]:
        """Extract severity level from query."""
        # Priority 1: Check for exclusion patterns (most specific)
        if re.search(r'exclud(?:e|ing)?\s+warning', q_lower):
            return "CRITICAL"
        if re.search(r'exclud(?:e|ing)?\s+critical', q_lower):
            return "WARNING"
        
        # Priority 2: Check for "only" patterns
        if re.search(r'(?:only|just|fakt)\s+critical', q_lower):
            return "CRITICAL"
        if re.search(r'(?:only|just|fakt)\s+warnings?', q_lower):
            return "WARNING"
        if re.search(r'critical\s+(?:only|fakt)', q_lower):
            return "CRITICAL"
        if re.search(r'warnings?\s+(?:only|fakt)', q_lower):
            return "WARNING"
        
        # Priority 3: Check for show only patterns
        if re.search(r'show\s+(?:me\s+)?(?:only\s+)?warnings?', q_lower):
            return "WARNING"
        if re.search(r'show\s+(?:me\s+)?(?:only\s+)?critical', q_lower):
            return "CRITICAL"
            
        # Priority 4: Check for "how many X" patterns
        if re.search(r'how\s+many\s+(?:warning|warnings)', q_lower):
            return "WARNING"
        if re.search(r'how\s+many\s+critical', q_lower):
            return "CRITICAL"
        
        # Priority 5: Check for explicit severity mentions at word boundaries
        # But avoid matching in "no warning alerts" context
        if re.search(r'(?<!no\s)\bwarnings?\b', q_lower) and not re.search(r'\bcritical\b', q_lower):
            return "WARNING"
        if re.search(r'(?<!no\s)\bcritical\b', q_lower) and not re.search(r'\bwarnings?\b', q_lower):
            return "CRITICAL"
        
        # If both mentioned, check context
        has_warning = re.search(r'\bwarnings?\b', q_lower)
        has_critical = re.search(r'\bcritical\b', q_lower)
        if has_warning and has_critical:
            # Check which is the focus
            if re.search(r'(?:show|list|get)\s+(?:me\s+)?(?:the\s+)?warnings?', q_lower):
                return "WARNING"
            if re.search(r'(?:show|list|get)\s+(?:me\s+)?(?:the\s+)?critical', q_lower):
                return "CRITICAL"
        
        return None
    
    def _extract_limit(self, q_lower: str) -> Optional[int]:
        """Extract numeric limit from query."""
        # Pattern: "show me 18", "top 10", "first 5", "20 alerts"
        limit_patterns = [
            r'(?:show|display|list|get|give)\s+(?:me\s+)?(\d+)',
            r'(?:top|first|last)\s+(\d+)',
            r'(\d+)\s+(?:alerts?|issues?|errors?|warnings?)',
            r'only\s+(\d+)',
            r'limit\s+(\d+)'
        ]
        
        for pattern in limit_patterns:
            match = re.search(pattern, q_lower)
            if match:
                try:
                    return int(match.group(1))
                except (ValueError, IndexError):
                    pass
        
        # Check word numbers
        for word, num in self.WORD_NUMBERS.items():
            if re.search(r'\b' + word + r'\b', q_lower):
                if any(kw in q_lower for kw in ["show", "top", "first", "last", "give"]):
                    return num
        
        return None
    
    def _extract_offset(self, q_lower: str) -> int:
        """Extract pagination offset from query."""
        # Pattern: "next 10", "10-20", "from 20"
        
        # Range pattern: "10-20", "alerts 10 to 20"
        range_match = re.search(r'(\d+)\s*[-–to]\s*(\d+)', q_lower)
        if range_match:
            return int(range_match.group(1))
        
        # "next" implies continuation
        if re.search(r'\bnext\b', q_lower):
            # Will be resolved by context manager
            return -1  # Special value indicating "continue from last"
        
        # "from X"
        from_match = re.search(r'from\s+(\d+)', q_lower)
        if from_match:
            return int(from_match.group(1))
        
        return 0
    
    def _extract_time_range(self, q_lower: str) -> Optional[str]:
        """Extract time range from query."""
        for time_key, patterns in self.TIME_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, q_lower):
                    return time_key
        return None
    
    def _extract_issue_type(self, q_lower: str) -> Optional[str]:
        """Extract issue type from query."""
        for issue_type, keywords in self.ISSUE_TYPE_PATTERNS.items():
            for keyword in keywords:
                if keyword in q_lower:
                    return issue_type
        return None
    
    def _extract_action(self, q_lower: str) -> str:
        """Extract the primary action from query."""
        for action, patterns in self.ACTION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, q_lower):
                    return action
        return "list"  # Default action
    
    def _extract_ora_codes(self, q_upper: str) -> List[str]:
        """Extract ORA error codes from query."""
        ora_pattern = r'ORA[-\s]?(\d{3,5})'
        matches = re.findall(ora_pattern, q_upper)
        return ["ORA-{}".format(m) for m in matches]
    
    def _tokenize(self, q_lower: str) -> List[str]:
        """Tokenize query into meaningful words."""
        # Remove punctuation and split
        tokens = re.findall(r'\b[a-z0-9]+\b', q_lower)
        # Filter stop words
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                     "being", "have", "has", "had", "do", "does", "did", "will",
                     "would", "could", "should", "may", "might", "must", "shall",
                     "can", "need", "dare", "ought", "used", "to", "of", "in",
                     "for", "on", "with", "at", "by", "from", "as", "into",
                     "through", "during", "before", "after", "above", "below",
                     "between", "under", "again", "further", "then", "once",
                     "me", "my", "i", "you", "your", "we", "our", "they", "their",
                     "it", "its", "this", "that", "these", "those"}
        return [t for t in tokens if t not in stop_words]


# Singleton instance
_extractor = None

def get_entity_extractor() -> EntityExtractor:
    """Get the singleton entity extractor instance."""
    global _extractor
    if _extractor is None:
        _extractor = EntityExtractor()
    return _extractor


# Convenience function
def extract_entities(query: str) -> Dict[str, Any]:
    """Extract entities from a query using the singleton extractor."""
    return get_entity_extractor().extract(query)


# Test
if __name__ == "__main__":
    extractor = EntityExtractor(["MIDEVSTB", "MIDEVSTBN", "FINDB", "HRDB"])
    
    test_queries = [
        "show me alerts for MIDEVSTB",
        "ok show me 18 warning",
        "top 10 critical alerts",
        "why is MIDEVSTBN having issues",
        "show standby issues from last hour",
        "count alerts excluding warning severity",
        "ORA-12537 errors for FINDB"
    ]
    
    for q in test_queries:
        print("\nQuery:", q)
        entities = extractor.extract(q)
        print("Entities:", {k: v for k, v in entities.items() if v and k != 'tokens'})
