# nlp_engine/intent_response_router.py
"""
==============================================================
INTENT-BASED RESPONSE ROUTER (PRODUCTION-GRADE)
==============================================================

CRITICAL: This module enforces INTENT-FIRST response generation.

MANDATORY 5-INTENT CLASSIFICATION:
1. FACT     → counts, hours, lists, numbers → SHORT answer (1-3 lines)
2. STATUS   → DOWN/CRITICAL/RUNNING        → SHORT answer (1-3 lines)
3. ANALYSIS → WHY/root cause/pattern       → Explanation ONLY, NO actions
4. PREDICTION → risk/forecast              → Risk logic + timeframe, NO action spam
5. ACTION   → what to do/fix/steps         → ONLY then show action plan

CONVERSATIONAL INTELLIGENCE UPGRADE:
6. FOLLOWUP_LIMIT     → "show me 10", "top 5", "only 20"
7. FOLLOWUP_REFERENCE → "this database", "same one", "these alerts"
8. FOLLOWUP_FILTER    → "only critical", "just errors", "high severity"

RULES (NON-NEGOTIABLE):
❌ DO NOT show action plans for FACT/STATUS/ANALYSIS questions
❌ DO NOT use same response template everywhere
✅ Response format MUST match question intent
✅ Sound natural and intelligent like a senior DBA
✅ Follow-up queries use session context intelligently

Python 3.6.8 compatible.
"""

import re


class IntentResponseRouter(object):
    """
    Routes intents to appropriate response formatters.
    
    CORE PRINCIPLE: The response format MUST match the question type.
    A DBA asking "which hour has highest alerts?" doesn't want an action plan.
    
    CONVERSATIONAL UPGRADE: Detects follow-up queries and routes to context-aware handlers.
    """
    
    # =====================================================
    # 5-INTENT CLASSIFICATION CONSTANTS
    # =====================================================
    TYPE_FACT = "FACT"           # counts, hours, lists, numbers
    TYPE_STATUS = "STATUS"       # DOWN/CRITICAL/RUNNING
    TYPE_ANALYSIS = "ANALYSIS"   # WHY/root cause/pattern
    TYPE_PREDICTION = "PREDICTION"  # risk/forecast
    TYPE_ACTION = "ACTION"       # what to do/fix/steps
    
    # Backward compatibility aliases
    TYPE_FACTUAL = "FACT"
    TYPE_ANALYTICAL = "ANALYSIS"
    
    # =====================================================
    # FOLLOWUP INTENT CONSTANTS (NEW - CONVERSATIONAL)
    # =====================================================
    TYPE_FOLLOWUP_LIMIT = "FOLLOWUP_LIMIT"         # "show me 10", "top 5"
    TYPE_FOLLOWUP_REFERENCE = "FOLLOWUP_REFERENCE"  # "this database", "same one"
    TYPE_FOLLOWUP_FILTER = "FOLLOWUP_FILTER"        # "only critical", "just errors"
    
    # =====================================================
    # QUERY MODE CONSTANTS (INTELLIGENCE UPGRADE)
    # =====================================================
    # Every question has an INTENT and a MODE.
    # MODE determines response format strictly:
    #   COUNT   - Return NUMBER only (no time, no lists)
    #   LIST    - Return alert LIST only
    #   FILTER  - Apply filter to previous result
    #   ENTITY  - Return data for specific database/server
    #   EXPLAIN - Return reasoning/root cause
    #   ACTION  - Return DBA action steps
    #   PREDICT - Return risk prediction
    #   FOLLOWUP - Use previous context
    # =====================================================
    MODE_COUNT = "COUNT"
    MODE_LIST = "LIST"
    MODE_FILTER = "FILTER"
    MODE_ENTITY = "ENTITY"
    MODE_EXPLAIN = "EXPLAIN"
    MODE_ACTION = "ACTION"
    MODE_PREDICT = "PREDICT"
    MODE_FOLLOWUP = "FOLLOWUP"
    MODE_AMBIGUOUS = "AMBIGUOUS"  # Requires clarification
    
    # =====================================================
    # FACT SUB-INTENT CONSTANTS (STRICT SEMANTIC ROUTING)
    # =====================================================
    # FACT is NOT a single category. It MUST be sub-classified:
    #   FACT_COUNT  - "how many", "total", "count" → NUMBER only
    #   FACT_TIME   - "which hour", "peak", "highest" → TIME only
    #   FACT_ENTITY - "which database", "list", "show" → NAMES only
    # =====================================================
    FACT_COUNT = "FACT_COUNT"
    FACT_TIME = "FACT_TIME"
    FACT_ENTITY = "FACT_ENTITY"
    
    # =====================================================
    # FOLLOWUP DETECTION PATTERNS (CONVERSATIONAL)
    # =====================================================
    
    # FOLLOWUP_LIMIT - questions asking for specific number of items
    FOLLOWUP_LIMIT_PATTERNS = [
        r"show\s+(me\s+)?(\d+|ten|twenty|five|fifty)",
        r"(top|first|last)\s+(\d+|ten|twenty|five|fifty)",
        r"only\s+(\d+)",
        r"give\s+me\s+(\d+)",
        r"list\s+(\d+)",
        r"(\d+)\s+(alerts?|incidents?|databases?|errors?)"
    ]
    
    # FOLLOWUP_REFERENCE - questions referencing prior context
    FOLLOWUP_REFERENCE_PATTERNS = [
        r"\b(this|that|these|those)\s+(database|db|server|alert|one)",
        r"\bsame\s+(database|db|server|one)",
        r"\bfor\s+(this|that|these|it)",
        r"\babout\s+(this|that|it)",
        r"\bthe\s+same\b"
    ]
    
    # FOLLOWUP_FILTER - questions applying filters to prior results
    FOLLOWUP_FILTER_PATTERNS = [
        r"\bonly\s+(critical|high|medium|low|error|warning)",
        r"\bjust\s+(critical|high|medium|low|error|warning)",
        r"(critical|high)\s+(only|ones?)",
        r"filter\s+(to|by|for)",
        r"exclude\s+",
        r"without\s+"
    ]
    
    # =====================================================
    # FACT SUB-INTENT PATTERNS (PRIORITY ORDER)
    # COUNT ALWAYS WINS when "how many/total/count" is present
    # =====================================================
    
    # FACT_COUNT - questions asking for numbers or totals
    FACT_COUNT_PATTERNS = [
        r"how\s+many",
        r"\btotal\b",
        r"\bcount\b",
        r"number\s+of",
        r"how\s+much"
    ]
    
    # FACT_TIME - questions asking about time, peak, frequency
    FACT_TIME_PATTERNS = [
        r"which\s+hour",
        r"what\s+hour",
        r"peak\s+hour",
        r"highest\s+hour",
        r"\bpeak\b",
        r"\bfrequency\b",
        r"\bwhen\b"
    ]
    
    # FACT_ENTITY - questions asking for names or lists
    FACT_ENTITY_PATTERNS = [
        r"which\s+(database|db|server|tablespace|target)",
        r"what\s+(database|db|server|tablespace)s?",
        r"\blist\b",
        r"\bshow\b",
        r"names?\s+of"
    ]
    
    # =====================================================
    # EXPLICIT QUESTION TYPE PATTERNS (5-INTENT SYSTEM)
    # =====================================================
    
    # FACT patterns - counts, hours, lists, numbers
    FACT_PATTERNS = [
        # Count questions
        r"how\s+many",
        r"count\s+of",
        r"total\s+number",
        r"number\s+of",
        
        # Which/What factual
        r"which\s+(hour|database|db|server|target|error|ora)",
        r"what\s+(hour|database|db|server|target|error|ora)\s+(has|have|is|are|show)",
        r"what\s+is\s+the\s+(most|highest|lowest|top|peak)",
        
        # List questions
        r"list\s+(all|the)?",
        r"show\s+(me\s+)?(all|the)?",
        r"what\s+are\s+the",
        r"names?\s+of",
        
        # Specific value questions  
        r"peak\s+hour",
        r"highest\s+(alert|error|count|number)",
        r"most\s+(alerts?|errors?|affected)"
    ]
    
    # STATUS patterns - DOWN/CRITICAL/RUNNING questions
    STATUS_PATTERNS = [
        r"is\s+.*\s+(down|up|running|critical|stable)",
        r"are\s+(any|there)\s+.*\s+(down|critical)",
        r"current\s+(status|state)",
        r"currently\s+(in|is|down|up|running)",
        r"which\s+(database|db).*\s+(critical|down)",
        r"what.*status",
        r"down\s+right\s+now",
        r"databases?\s+down",
        r"is\s+.+\s+down",
        r"online|offline|available|unavailable"
    ]
    
    # ANALYSIS patterns - WHY/root cause/pattern (NO actions)
    ANALYSIS_PATTERNS = [
        # Why questions (root cause)
        r"\bwhy\b",
        r"\breason\b",
        r"what\s+caused",
        r"what\s+causes",
        r"what\s+is\s+causing",
        r"what'?s\s+causing",
        r"the\s+cause\s+of",
        r"causing\s+the",
        r"root\s+cause",
        r"due\s+to",
        r"\bexplain\b",
        
        # Pattern/Trend analysis
        r"\bpattern\b",
        r"\btrend\b",
        r"analysis\b",
        r"analyze\b",
        r"correlation",
        
        # Comparison
        r"\bcompare\b",
        r"\bversus\b",
        r"\bvs\b",
        r"difference\s+between"
    ]
    
    # PREDICTION patterns - risk/forecast
    PREDICTION_PATTERNS = [
        r"\brisk\b",
        r"\bpredict",
        r"likely\s+to",
        r"going\s+to\s+fail",
        r"will\s+(it|this)\s+fail",
        r"fail\s+next",
        r"forecast",
        r"might\s+fail",
        r"expected\s+to\s+(fail|crash)"
    ]
    
    # ACTION patterns - what to do/fix/steps (ONLY these get action plans)
    ACTION_PATTERNS = [
        # Explicit action requests
        r"what\s+(should|can)\s+(i|we)\s+do",
        r"how\s+(do\s+i|to)\s+fix",
        r"how\s+(do\s+i|to)\s+resolve",
        r"how\s+(do\s+i|can\s+i)\s+",
        r"what\s+action",
        r"immediate\s+action",
        r"next\s+steps?",
        r"\brecommend\b",
        r"solution\s+for",
        r"fix\s+for",
        r"remediate",
        r"taken\s+for",
        r"steps\s+to\s+(fix|resolve|address)",
        r"give\s+me\s+steps",
        r"what\s+to\s+do\s+now",
        r"dba\s+(should|needs\s+to)"
    ]
    
    # Legacy aliases for backward compatibility
    FACTUAL_PATTERNS = FACT_PATTERNS
    ANALYTICAL_PATTERNS = ANALYSIS_PATTERNS
    
    # =====================================================
    # FOLLOWUP DETECTION METHODS (NEW - CONVERSATIONAL)
    # =====================================================
    
    @classmethod
    def is_followup_question(cls, question):
        """
        Detect if this is a follow-up question requiring prior context.
        
        Follow-up indicators:
        - "show me 20", "top 10", "only 5"
        - "this database", "same one", "these alerts"
        - "only critical", "just errors", "high severity"
        
        Args:
            question: The user's question text
            
        Returns:
            tuple: (is_followup: bool, followup_type: str or None)
                followup_type can be: LIMIT, REFERENCE, FILTER
        """
        q_lower = question.lower().strip()
        
        # Check LIMIT patterns (highest priority - very specific)
        for pattern in cls.FOLLOWUP_LIMIT_PATTERNS:
            if re.search(pattern, q_lower, re.IGNORECASE):
                return (True, "LIMIT")
        
        # Check REFERENCE patterns (medium priority)
        for pattern in cls.FOLLOWUP_REFERENCE_PATTERNS:
            if re.search(pattern, q_lower, re.IGNORECASE):
                return (True, "REFERENCE")
        
        # Check FILTER patterns (lower priority - could be standalone)
        for pattern in cls.FOLLOWUP_FILTER_PATTERNS:
            if re.search(pattern, q_lower, re.IGNORECASE):
                # Only treat as follow-up if question is SHORT (< 8 words)
                # "only critical" = follow-up
                # "show me only critical alerts for MIDEVSTBN" = standalone
                word_count = len(q_lower.split())
                if word_count <= 8:
                    return (True, "FILTER")
        
        return (False, None)
    
    @classmethod
    def extract_limit_number(cls, question):
        """
        Extract the limit number from a FOLLOWUP_LIMIT question.
        
        Examples:
        - "show me 20" → 20
        - "top 10" → 10
        - "first five" → 5
        
        Args:
            question: The user's question text
            
        Returns:
            int or None: The limit number, or None if not found
        """
        q_lower = question.lower().strip()
        
        # Try to find digit
        digit_match = re.search(r"\b(\d+)\b", q_lower)
        if digit_match:
            return int(digit_match.group(1))
        
        # Try word numbers
        word_numbers = {
            "five": 5, "ten": 10, "twenty": 20, "thirty": 30,
            "forty": 40, "fifty": 50, "hundred": 100
        }
        for word, num in word_numbers.items():
            if word in q_lower:
                return num
        
        return None
    
    @classmethod
    def extract_filter_severity(cls, question):
        """
        Extract severity filter from a FOLLOWUP_FILTER question.
        
        Examples:
        - "only critical" → "CRITICAL"
        - "just errors" → "ERROR"
        - "high severity" → "HIGH"
        
        Args:
            question: The user's question text
            
        Returns:
            str or None: Severity level, or None if not found
        """
        q_lower = question.lower().strip()
        
        severity_map = {
            "critical": "CRITICAL",
            "high": "CRITICAL",
            "error": "CRITICAL",
            "medium": "WARNING",
            "warning": "WARNING",
            "low": "INFO",
            "info": "INFO"
        }
        
        for keyword, severity in severity_map.items():
            if keyword in q_lower:
                return severity
        
        return None
    
    @classmethod
    def _extract_entity_from_question(cls, q_upper):
        """
        Extract database/entity name from question text.
        
        INTELLIGENCE: Finds entity references in various phrasings.
        Used by EXPLAIN/ACTION/PREDICT modes to know WHAT to analyze.
        
        Args:
            q_upper: Uppercase version of question text
            
        Returns:
            str or None: Entity name if found
        """
        # Entity extraction patterns (uppercase for q_upper search)
        entity_patterns = [
            # Standard suffixes (highest confidence)
            r'\b([A-Z][A-Z0-9_]{2,}(?:STB|STBN|DB|PRD|DEV|TST|PROD))\b',
            # Preposition patterns
            r'(?:FOR|ABOUT|ON|OF|WITH|IS)\s+([A-Z][A-Z0-9_]{3,})',
            # Underscore pattern (common in Oracle)
            r'\b([A-Z][A-Z0-9]*_[A-Z0-9_]+)\b',
        ]
        
        excluded = {"THE", "FOR", "AND", "WITH", "SHOW", "THIS", "THAT", 
                   "FROM", "ONLY", "ALERTS", "CRITICAL", "DATABASE", "STATUS",
                   "WHAT", "WHICH", "THERE", "MANY", "TOTAL", "WRONG", "ISSUES",
                   "PROBLEMS", "ORA", "ERROR", "WARNING", "INFO", "FAILING",
                   "WHY", "HOW", "SHOULD", "STEPS", "ACTION", "FIX", "REASON"}
        
        for pattern in entity_patterns:
            match = re.search(pattern, q_upper)
            if match:
                entity = match.group(1)
                if entity not in excluded and len(entity) >= 4:
                    return entity
        
        return None
    
    @classmethod
    def detect_query_mode(cls, question, has_prior_context=False):
        """
        INTELLIGENCE UPGRADE: Detect the QUERY MODE for intelligent routing.
        
        Every question has an INTENT (what it's about) and a MODE (how to respond).
        MODE determines response format strictly:
        
        MODE_COUNT    → Return NUMBER only (no time, no lists, no analysis)
        MODE_LIST     → Return alert LIST only
        MODE_FILTER   → Apply filter to previous result
        MODE_ENTITY   → Return data for specific database/server
        MODE_EXPLAIN  → Return reasoning/root cause
        MODE_ACTION   → Return DBA action steps only
        MODE_PREDICT  → Return risk prediction
        MODE_FOLLOWUP → Use previous context
        MODE_AMBIGUOUS → Intent unclear, requires clarification
        
        Args:
            question: The user's question text
            has_prior_context: Whether prior conversation context exists
            
        Returns:
            dict: {
                "mode": MODE constant,
                "sub_mode": optional sub-classification,
                "entity": extracted entity if any,
                "filters": extracted filters,
                "limit": extracted limit if any,
                "requires_clarification": bool
            }
        """
        q_lower = question.lower().strip()
        q_upper = question.upper()
        word_count = len(q_lower.split())
        
        result = {
            "mode": None,
            "sub_mode": None,
            "entity": None,
            "filters": {},
            "limit": None,
            "requires_clarification": False
        }
        
        # =====================================================
        # PRIORITY 1: COUNT MODE (ABSOLUTE - HARD GUARD)
        # =====================================================
        # INTELLIGENCE: Recognize quantitative intent through various phrasings
        count_keywords = ["how many", "total", "count", "number of", "tally", "sum of", "amount of"]
        is_count = any(kw in q_lower for kw in count_keywords)
        
        # Exception: "which hour" type questions are TIME, not COUNT
        is_time_question = any(kw in q_lower for kw in ["which hour", "what hour", "peak hour"])
        
        if is_count and not is_time_question:
            result["mode"] = cls.MODE_COUNT
            
            # Detect what to count
            if "critical" in q_lower:
                result["filters"]["severity"] = "CRITICAL"
            if "warning" in q_lower:
                result["filters"]["severity"] = "WARNING"
            if "standby" in q_lower or "dataguard" in q_lower:
                result["filters"]["alert_type"] = "dataguard"
            if "tablespace" in q_lower:
                result["filters"]["alert_type"] = "tablespace"
            
            return result
        
        # =====================================================
        # PRIORITY 2: EXPLAIN MODE (why, reason, root cause)
        # =====================================================
        explain_keywords = ["why", "reason", "root cause", "what caused", "explain"]
        if any(kw in q_lower for kw in explain_keywords):
            result["mode"] = cls.MODE_EXPLAIN
            # INTELLIGENCE: Still extract entity for targeted explanation
            entity = cls._extract_entity_from_question(q_upper)
            if entity:
                result["entity"] = entity
            return result
        
        # =====================================================
        # PRIORITY 3: ACTION MODE (what to do, fix, steps)
        # =====================================================
        action_keywords = ["what should", "how to fix", "how do i", "recommend", 
                          "action", "steps", "remediate", "solution"]
        if any(kw in q_lower for kw in action_keywords):
            result["mode"] = cls.MODE_ACTION
            # INTELLIGENCE: Still extract entity for targeted actions
            entity = cls._extract_entity_from_question(q_upper)
            if entity:
                result["entity"] = entity
            return result
        
        # =====================================================
        # PRIORITY 4: PREDICT MODE (risk, likely, will fail)
        # =====================================================
        predict_keywords = ["risk", "predict", "likely to fail", "will fail", "forecast"]
        if any(kw in q_lower for kw in predict_keywords):
            result["mode"] = cls.MODE_PREDICT
            # INTELLIGENCE: Still extract entity for targeted prediction
            entity = cls._extract_entity_from_question(q_upper)
            if entity:
                result["entity"] = entity
            return result
        
        # =====================================================
        # PRIORITY 5: ENTITY MODE (specific database mentioned)
        # =====================================================
        # Pattern: Database names are typically uppercase with specific suffixes
        # INTELLIGENCE: Detect database names in various phrasings
        # NOTE: Patterns use uppercase because we search in q_upper
        db_patterns = [
            # Standard suffixes (highest confidence)
            r'\b([A-Z][A-Z0-9_]{2,}(?:STB|STBN|DB|PRD|DEV|TST|PROD))\b',
            # Preposition patterns: "FOR/ABOUT/ON/OF/WITH DBNAME" (uppercase)
            r'(?:FOR|ABOUT|ON|OF|WITH)\s+([A-Z][A-Z0-9_]{3,})',
            # Explicit: "DATABASE DBNAME"
            r'DATABASE\s+([A-Z][A-Z0-9_]{3,})',
            # Status pattern: "DBNAME STATUS" or "STATUS OF DBNAME"
            r'STATUS\s+(?:OF\s+)?([A-Z][A-Z0-9_]{3,})',
            r'([A-Z][A-Z0-9_]{3,})\s+STATUS',
            # Issues/alerts pattern: "ISSUES ON DBNAME"
            r'(?:ISSUES?|ALERTS?|PROBLEMS?)\s+(?:ON|FOR|WITH)\s+([A-Z][A-Z0-9_]{3,})',
            # What's wrong pattern: "WRONG WITH DBNAME"
            r'WRONG\s+WITH\s+([A-Z][A-Z0-9_]{3,})',
            # Underscore pattern (common in Oracle): DATABASE_NAME
            r'\b([A-Z][A-Z0-9]*_[A-Z0-9_]+)\b',
        ]
        
        excluded_words = {"THE", "FOR", "AND", "WITH", "SHOW", "THIS", "THAT", 
                        "FROM", "ONLY", "ALERTS", "CRITICAL", "DATABASE", "STATUS",
                        "WHAT", "WHICH", "THERE", "MANY", "TOTAL", "WRONG", "ISSUES",
                        "PROBLEMS", "ORA", "ERROR", "WARNING", "INFO"}
        
        for pattern in db_patterns:
            match = re.search(pattern, q_upper)
            if match:
                potential_db = match.group(1)
                if potential_db not in excluded_words and len(potential_db) >= 4:
                    result["mode"] = cls.MODE_ENTITY
                    result["entity"] = potential_db
                    return result
        
        # =====================================================
        # PRIORITY 6: FOLLOWUP MODE (short queries with context)
        # =====================================================
        # Detect follow-up patterns
        is_followup, followup_type = cls.is_followup_question(question)
        if is_followup:
            result["mode"] = cls.MODE_FOLLOWUP
            result["sub_mode"] = followup_type
            
            if followup_type == "LIMIT":
                result["limit"] = cls.extract_limit_number(question)
            elif followup_type == "FILTER":
                sev = cls.extract_filter_severity(question)
                if sev:
                    result["filters"]["severity"] = sev
            
            # Check if we need context
            if not has_prior_context:
                result["requires_clarification"] = True
            
            return result
        
        # =====================================================
        # PRIORITY 7: LIST MODE (show, list, give)
        # =====================================================
        list_keywords = ["show", "list", "give me", "display", "what are"]
        if any(kw in q_lower for kw in list_keywords):
            result["mode"] = cls.MODE_LIST
            
            # Extract filters
            if "critical" in q_lower:
                result["filters"]["severity"] = "CRITICAL"
            if "standby" in q_lower or "dataguard" in q_lower:
                result["filters"]["alert_type"] = "dataguard"
            if "tablespace" in q_lower:
                result["filters"]["alert_type"] = "tablespace"
            
            # Extract limit
            limit = cls.extract_limit_number(question)
            if limit:
                result["limit"] = limit
            
            return result
        
        # =====================================================
        # PRIORITY 8: FILTER MODE (only critical, without X)
        # =====================================================
        filter_keywords = ["only", "just", "filter", "exclude", "without"]
        if any(kw in q_lower for kw in filter_keywords):
            result["mode"] = cls.MODE_FILTER
            sev = cls.extract_filter_severity(question)
            if sev:
                result["filters"]["severity"] = sev
            
            # Needs context to filter
            if not has_prior_context:
                result["requires_clarification"] = True
            
            return result
        
        # =====================================================
        # AMBIGUOUS: Short query with no clear mode
        # =====================================================
        if word_count <= 3:
            # Very short query - likely needs clarification
            ambiguous_shorts = ["ok", "yes", "no", "more", "continue", "and", "also"]
            if q_lower in ambiguous_shorts or any(q_lower.startswith(s) for s in ambiguous_shorts):
                result["mode"] = cls.MODE_AMBIGUOUS
                result["requires_clarification"] = not has_prior_context
                return result
        
        # =====================================================
        # DEFAULT: List mode (safest default for DBA queries)
        # =====================================================
        result["mode"] = cls.MODE_LIST
        return result
    
    @classmethod
    def needs_clarification(cls, question, has_prior_context=False):
        """
        Determine if we need to ask a clarification question.
        
        INTELLIGENCE RULE: Ask clarification rather than guess wrong.
        
        Triggers clarification when:
        1. Very short query (1-2 words) without context
        2. Ambiguous pronouns without context ("this", "that", "it")
        3. Filter request without knowing what to filter
        4. Follow-up reference without prior topic
        
        Args:
            question: The user's question text
            has_prior_context: Whether prior conversation context exists
            
        Returns:
            tuple: (needs_clarification: bool, clarification_type: str or None)
        """
        q_lower = question.lower().strip()
        word_count = len(q_lower.split())
        
        # =====================================================
        # Rule 1: Very short queries without context
        # =====================================================
        if word_count <= 2 and not has_prior_context:
            # "ok", "show 20", "critical" - need context
            return (True, "SHORT_QUERY")
        
        # =====================================================
        # Rule 2: Pronouns without prior context
        # =====================================================
        pronouns = ["this", "that", "these", "those", "it", "them", "same"]
        has_pronoun = any(p in q_lower.split() for p in pronouns)
        if has_pronoun and not has_prior_context:
            return (True, "PRONOUN_REFERENCE")
        
        # =====================================================
        # Rule 3: Filter without target
        # =====================================================
        is_filter = any(kw in q_lower for kw in ["only", "just", "filter"])
        has_target = any(kw in q_lower for kw in ["database", "alert", "standby", "tablespace"])
        if is_filter and not has_target and not has_prior_context:
            return (True, "FILTER_NO_TARGET")
        
        # =====================================================
        # Rule 4: Ambiguous questions
        # =====================================================
        ambiguous_queries = ["show me", "give me", "list", "more", "continue"]
        is_ambiguous = any(q_lower.startswith(a) or q_lower == a for a in ambiguous_queries)
        if is_ambiguous and word_count <= 3 and not has_prior_context:
            return (True, "AMBIGUOUS")
        
        return (False, None)
    
    @classmethod
    def get_clarification_question(cls, clarification_type, question=None):
        """
        Generate an appropriate clarification question.
        
        INTELLIGENCE RULE: Clarifications must be:
        1. SHORT (one question only)
        2. SPECIFIC (give options when possible)
        3. HELPFUL (guide user to valid inputs)
        
        Args:
            clarification_type: Type of clarification needed
            question: Original question for context
            
        Returns:
            str: Clarification question to ask user
        """
        clarifications = {
            "SHORT_QUERY": (
                "What would you like to know?\n\n"
                "Examples:\n"
                "- 'How many critical alerts?'\n"
                "- 'Show standby issues'\n"
                "- 'Which database has most alerts?'"
            ),
            "PRONOUN_REFERENCE": (
                "Which database are you referring to?\n\n"
                "Please specify a database name, or ask about:\n"
                "- Standby/Data Guard alerts\n"
                "- Critical alerts\n"
                "- A specific database (e.g., 'alerts for MIDEVSTBN')"
            ),
            "FILTER_NO_TARGET": (
                "What would you like me to filter?\n\n"
                "Options:\n"
                "- 'Show critical alerts'\n"
                "- 'Only standby alerts'\n"
                "- 'Critical alerts for DBNAME'"
            ),
            "AMBIGUOUS": (
                "Could you be more specific?\n\n"
                "Try:\n"
                "- 'How many alerts?' (for counts)\n"
                "- 'Show standby issues' (for lists)\n"
                "- 'Why is DBNAME failing?' (for analysis)"
            ),
            "NO_CONTEXT": (
                "I don't have context from a previous question.\n\n"
                "Please specify what you'd like to see:\n"
                "- Alert counts\n"
                "- Standby/Data Guard status\n"
                "- Alerts for a specific database"
            )
        }
        
        return clarifications.get(clarification_type, clarifications["AMBIGUOUS"])
    
    @classmethod
    def get_fact_sub_intent(cls, question):
        """
        STRICT FACT SUB-INTENT CLASSIFICATION.
        
        RULE: COUNT ALWAYS WINS when "how many / total / count" is present.
        
        Args:
            question: The user's question text
            
        Returns:
            str: FACT_COUNT, FACT_TIME, or FACT_ENTITY (or None if not a FACT question)
        """
        q_lower = question.lower().strip()
        
        # =====================================================
        # PRIORITY 1: FACT_COUNT (ALWAYS WINS)
        # If COUNT keywords present, NEVER return TIME
        # =====================================================
        for pattern in cls.FACT_COUNT_PATTERNS:
            if re.search(pattern, q_lower, re.IGNORECASE):
                # Double-check: if question is ONLY about hour/time, it's TIME
                # But if it says "how many" + anything, it's COUNT
                is_pure_time_question = any(re.search(p, q_lower, re.IGNORECASE) 
                                           for p in [r"which\s+hour", r"what\s+hour", r"peak\s+hour"])
                # COUNT keywords override EVERYTHING except pure time questions
                if not is_pure_time_question or "how many" in q_lower or "total" in q_lower or "count" in q_lower:
                    return cls.FACT_COUNT
        
        # =====================================================
        # PRIORITY 2: FACT_TIME (only if not COUNT)
        # =====================================================
        for pattern in cls.FACT_TIME_PATTERNS:
            if re.search(pattern, q_lower, re.IGNORECASE):
                return cls.FACT_TIME
        
        # =====================================================
        # PRIORITY 3: FACT_ENTITY
        # =====================================================
        for pattern in cls.FACT_ENTITY_PATTERNS:
            if re.search(pattern, q_lower, re.IGNORECASE):
                return cls.FACT_ENTITY
        
        return None  # Not a FACT sub-intent
    
    @classmethod
    def is_count_question(cls, question):
        """
        Check if question is asking for a COUNT (number/total).
        
        CRITICAL GUARD RULE: If this returns True, response MUST be a COUNT (number),
        NEVER a time-based aggregation or other format.
        
        This prevents the bug where:
        "how many standby alerts" → peak hour (WRONG)
        "how many standby alerts" → 123 (CORRECT)
        
        Args:
            question: The user's question text
            
        Returns:
            bool: True if this is a count question
        """
        q_lower = question.lower().strip()
        count_keywords = ["how many", "total", "count", "number of", "how much"]
        
        # STRICT: If ANY count keyword is present, this is a COUNT question
        has_count_keyword = any(kw in q_lower for kw in count_keywords)
        
        # Exception: "how many hours" or "how many times" might be frequency
        # But still treat as COUNT if combined with entity
        if has_count_keyword:
            # Check if it's asking "how many TIMES did X happen" (frequency)
            is_frequency = "times" in q_lower or "hours" in q_lower
            if is_frequency and ("database" not in q_lower and "alert" not in q_lower):
                return False  # It's asking about frequency pattern, not count
            return True  # It's a count question
        
        return False
    
    @classmethod
    def is_time_question(cls, question):
        """
        Check if question is asking about TIME/HOUR/PEAK.
        
        Only returns True if NOT a count question.
        
        Args:
            question: The user's question text
            
        Returns:
            bool: True if this is a time question (and NOT a count question)
        """
        if cls.is_count_question(question):
            return False  # COUNT always wins
        
        q_lower = question.lower().strip()
        time_keywords = ["which hour", "what hour", "peak hour", "highest hour", 
                        "peak", "frequency", "when"]
        return any(kw in q_lower for kw in time_keywords)
    
    @classmethod
    def get_question_type(cls, question, intent=None):
        """
        Determine the 5-intent question type based on question text.
        
        MANDATORY CLASSIFICATION ORDER:
        1. ACTION   → check first (most restrictive)
        2. STATUS   → DOWN/CRITICAL/RUNNING questions
        3. PREDICTION → risk/forecast questions
        4. ANALYSIS → WHY/root cause questions (NO actions)
        5. FACT     → default for factual queries
        
        RULE: Question text OVERRIDES intent classification for response format.
        
        Args:
            question: The user's question text
            intent: Optional classified intent (for context)
            
        Returns:
            str: FACT, STATUS, ANALYSIS, PREDICTION, or ACTION
        """
        q_lower = question.lower().strip()
        
        # Check ACTION patterns first (most restrictive - user must EXPLICITLY ask)
        for pattern in cls.ACTION_PATTERNS:
            if re.search(pattern, q_lower, re.IGNORECASE):
                return cls.TYPE_ACTION
        
        # Check STATUS patterns (DOWN/CRITICAL/RUNNING)
        for pattern in cls.STATUS_PATTERNS:
            if re.search(pattern, q_lower, re.IGNORECASE):
                return cls.TYPE_STATUS
        
        # Check PREDICTION patterns (risk/forecast)
        for pattern in cls.PREDICTION_PATTERNS:
            if re.search(pattern, q_lower, re.IGNORECASE):
                return cls.TYPE_PREDICTION
        
        # Check ANALYSIS patterns (WHY questions - NO actions)
        for pattern in cls.ANALYSIS_PATTERNS:
            if re.search(pattern, q_lower, re.IGNORECASE):
                return cls.TYPE_ANALYSIS
        
        # Check FACT patterns
        for pattern in cls.FACT_PATTERNS:
            if re.search(pattern, q_lower, re.IGNORECASE):
                return cls.TYPE_FACT
        
        # Default based on intent if no pattern matched
        if intent:
            return cls._infer_from_intent(intent)
        
        # Ultimate default - treat as FACT (short answer)
        return cls.TYPE_FACT
    
    @classmethod
    def _infer_from_intent(cls, intent):
        """Infer question type from classified intent."""
        intent_upper = intent.upper()
        
        # FACT intents - these NEVER get root cause or actions by default
        fact_intents = {
            "FACTUAL", "ENTITY_COUNT", "ENTITY_LIST",
            "TIME_BASED", "FREQUENCY_PATTERN", "COMPARISON",
            # CRITICAL FIX: STANDBY_DATAGUARD and TABLESPACE are FACTUAL by default
            # They only become ANALYSIS when the question contains "why"
            "STANDBY_DATAGUARD", "TABLESPACE"
        }
        
        # STATUS intents
        status_intents = {
            "HEALTH_STATUS"
        }
        
        # ANALYSIS intents (NO actions)
        # NOTE: STANDBY_DATAGUARD and TABLESPACE are FACT unless question contains "why"
        analysis_intents = {
            "ROOT_CAUSE"
        }
        
        # PREDICTION intents
        prediction_intents = {
            "PREDICTIVE", "RISK_POSTURE"
        }
        
        # ACTION intents (ONLY these get action plans)
        action_intents = {
            "RECOMMENDATION"
        }
        
        if intent_upper in action_intents:
            return cls.TYPE_ACTION
        elif intent_upper in prediction_intents:
            return cls.TYPE_PREDICTION
        elif intent_upper in status_intents:
            return cls.TYPE_STATUS
        elif intent_upper in analysis_intents:
            return cls.TYPE_ANALYSIS
        else:
            return cls.TYPE_FACT
    
    @classmethod  
    def should_include_root_cause(cls, question, intent=None):
        """
        Determine if response should include root cause analysis.
        
        RULE: Root cause belongs ONLY to:
        - ANALYSIS questions (WHY questions)
        - ACTION questions (need context for recommendations)
        
        NEVER include root cause for:
        - FACT questions (inventory, counts, lists)
        - STATUS questions (simple up/down state)
        """
        question_type = cls.get_question_type(question, intent)
        
        # Only ANALYSIS and ACTION types get root cause
        if question_type in [cls.TYPE_ANALYSIS, cls.TYPE_ACTION, cls.TYPE_PREDICTION]:
            return True
        
        # Explicit root cause request overrides
        q_lower = question.lower()
        if "root cause" in q_lower or "why" in q_lower.split()[:3]:  # "why" at start
            return True
        
        return False
    
    @classmethod
    def should_include_actions(cls, question, intent=None):
        """
        Determine if response should include action recommendations.
        
        =====================================================
        STRICT RULE (NON-NEGOTIABLE):
        =====================================================
        
        IF intent ≠ ACTION:
            DO NOT include action plan, DBA steps, escalation lists
        
        Actions should ONLY appear for EXPLICIT ACTION REQUESTS:
        - "what should I do?"
        - "how do I fix?"
        - "give me steps"
        - "recommend actions"
        - "what actions should be taken?"
        
        ❌ NEVER include actions for:
        - FACT queries ("how many", "which", "list")
        - STATUS queries ("is X down?", "which is critical?")
        - ANALYSIS queries ("why", "root cause", "explain")
        - PREDICTION queries (unless explicitly asking for actions)
        =====================================================
        """
        question_type = cls.get_question_type(question, intent)
        
        # ONLY ACTION type gets action plans
        if question_type == cls.TYPE_ACTION:
            return True
        
        # All other types: NO ACTIONS (strict rule)
        return False
    
    @classmethod
    def get_response_format(cls, question, intent=None):
        """
        Get the recommended response format for a question.
        
        5-INTENT FORMAT SPECIFICATION:
        
        FACT     → 1-3 lines, direct answer, NO actions, NO root cause
        STATUS   → 1-3 lines, state indicator, NO actions, NO analysis
        ANALYSIS → Explanation with evidence, NO action plans
        PREDICTION → Risk logic + timeframe, NO action spam
        ACTION   → Steps and recommendations with context
        
        Returns:
            dict with format specifications
        """
        question_type = cls.get_question_type(question, intent)
        
        if question_type == cls.TYPE_FACT:
            return {
                "type": "FACT",
                "use_template": False,
                "include_root_cause": False,
                "include_actions": False,
                "include_evidence": False,
                "style": "direct",
                "max_lines": 3,
                "description": "Short, direct answer. No analysis, no actions."
            }
        
        elif question_type == cls.TYPE_STATUS:
            return {
                "type": "STATUS",
                "use_template": False,
                "include_root_cause": False,
                "include_actions": False,
                "include_evidence": False,
                "style": "status",
                "max_lines": 3,
                "description": "State indicator with brief context. No actions."
            }
        
        elif question_type == cls.TYPE_ANALYSIS:
            return {
                "type": "ANALYSIS",
                "use_template": True,
                "include_root_cause": True,
                "include_actions": False,  # NO ACTIONS for analysis
                "include_evidence": True,
                "style": "explanatory",
                "max_lines": 10,
                "description": "Explanation with evidence. NO action plans."
            }
        
        elif question_type == cls.TYPE_PREDICTION:
            return {
                "type": "PREDICTION",
                "use_template": True,
                "include_root_cause": False,
                "include_actions": False,  # No action spam
                "include_evidence": True,
                "style": "predictive",
                "max_lines": 8,
                "description": "Risk logic with timeframe. No action spam."
            }
        
        else:  # ACTION
            return {
                "type": "ACTION",
                "use_template": True,
                "include_root_cause": True,
                "include_actions": True,  # ONLY ACTION gets actions
                "include_evidence": True,
                "style": "prescriptive",
                "max_lines": 15,
                "description": "Steps and recommendations with root cause context"
            }


class FactualResponseGenerator(object):
    """
    Generates SHORT, DIRECT responses for factual questions.
    
    NO templates. NO filler. NO unnecessary analysis.
    Just the answer.
    """
    
    @classmethod
    def generate_count_response(cls, entity_type, count, details=None):
        """Generate response for count questions."""
        if entity_type.upper() == "DATABASE":
            response = "{} databases are monitored in OEM.".format(count)
        elif entity_type.upper() == "SERVER":
            response = "{} servers are monitored in OEM.".format(count)
        elif entity_type.upper() == "ALERT":
            response = "{:,} alerts total.".format(count)
        else:
            response = "{:,} {}.".format(count, entity_type.lower())
        
        if details and count <= 10:
            response += "\n\n" + ", ".join(details)
        
        return response
    
    @classmethod
    def generate_hour_response(cls, peak_hour, count, context=None):
        """Generate response for hour/time questions."""
        # Format hour nicely
        hour_str = "{}:00".format(peak_hour)
        if peak_hour == 0:
            hour_str = "12:00 AM (midnight)"
        elif peak_hour < 12:
            hour_str = "{}:00 AM".format(peak_hour)
        elif peak_hour == 12:
            hour_str = "12:00 PM (noon)"
        else:
            hour_str = "{}:00 PM".format(peak_hour - 12)
        
        response = "Peak hour: {} with {:,} alerts.".format(hour_str, count)
        
        if context:
            response += " " + context
        
        return response
    
    @classmethod
    def generate_which_response(cls, entity_name, attribute, value=None, reason=None):
        """Generate response for 'which X has Y' questions."""
        if value:
            response = "{} has {} {}.".format(entity_name, value, attribute)
        else:
            response = "{}.".format(entity_name)
        
        if reason:
            response += " " + reason
        
        return response
    
    @classmethod
    def generate_status_response(cls, entity_name, status, detail=None):
        """Generate response for status questions."""
        if status.upper() in ["DOWN", "OFFLINE", "UNAVAILABLE"]:
            response = "⛔ {} is DOWN.".format(entity_name)
        elif status.upper() in ["CRITICAL"]:
            response = "⚠️ {} is in CRITICAL state.".format(entity_name)
        elif status.upper() in ["WARNING"]:
            response = "🔔 {} is in WARNING state.".format(entity_name)
        else:
            response = "✅ {} is {}.".format(entity_name, status)
        
        if detail:
            response += " " + detail
        
        return response
    
    @classmethod
    def generate_list_response(cls, items, entity_type="item"):
        """Generate response for list questions."""
        if not items:
            return "No {} found.".format(entity_type)
        
        count = len(items)
        response = "📋 **{} {} monitored:**\n\n".format(count, entity_type + ("s" if count != 1 else ""))
        
        for i, item in enumerate(items[:20], 1):
            response += "{}. {}\n".format(i, item)
        
        if count > 20:
            response += "\n... and {} more".format(count - 20)
        
        return response
    
    @classmethod
    def generate_yes_no_response(cls, answer, detail=None):
        """Generate response for yes/no questions."""
        if answer:
            response = "Yes."
        else:
            response = "No."
        
        if detail:
            response += " " + detail
        
        return response


class AnalyticalResponseGenerator(object):
    """
    Generates EXPLANATORY responses for analytical questions.
    
    Includes evidence and reasoning, but stays focused.
    """
    
    @classmethod
    def generate_root_cause_response(cls, target, root_cause, evidence, confidence):
        """Generate response for root cause questions."""
        lines = []
        
        # Lead with the answer
        if confidence == "HIGH":
            lines.append("**Root cause for {}:** {}".format(target, root_cause))
        elif confidence == "MEDIUM":
            lines.append("**Inferred root cause for {} (medium confidence):** {}".format(target, root_cause))
        else:
            lines.append("**Likely root cause for {} (needs investigation):** {}".format(target, root_cause))
        
        # Evidence (brief)
        if evidence:
            lines.append("")
            lines.append("**Evidence:**")
            for e in evidence[:3]:
                lines.append("• {}".format(e))
        
        return "\n".join(lines)
    
    @classmethod
    def generate_pattern_response(cls, pattern_type, description, data_points):
        """Generate response for pattern/trend questions."""
        lines = []
        
        lines.append("**Pattern:** {}".format(pattern_type))
        lines.append("")
        lines.append(description)
        
        if data_points:
            lines.append("")
            lines.append("**Key data:**")
            for point in data_points[:4]:
                lines.append("• {}".format(point))
        
        return "\n".join(lines)
    
    @classmethod
    def generate_risk_response(cls, risk_level, risk_factors, at_risk_entities=None):
        """Generate response for risk assessment questions."""
        lines = []
        
        # Risk level with emoji
        if risk_level == "CRITICAL":
            lines.append("🔴 **Risk Level: CRITICAL**")
        elif risk_level == "HIGH":
            lines.append("🟠 **Risk Level: HIGH**")
        elif risk_level in ["ELEVATED", "MEDIUM"]:
            lines.append("🟡 **Risk Level: ELEVATED**")
        else:
            lines.append("🟢 **Risk Level: MODERATE**")
        
        # Risk factors
        if risk_factors:
            lines.append("")
            lines.append("**Contributing factors:**")
            for factor in risk_factors[:4]:
                lines.append("• {}".format(factor))
        
        # At-risk entities
        if at_risk_entities:
            lines.append("")
            lines.append("**At-risk databases:** {}".format(", ".join(at_risk_entities[:5])))
        
        return "\n".join(lines)


class ActionResponseGenerator(object):
    """
    Generates PRESCRIPTIVE responses for action questions.
    
    Focuses on what to DO, with context.
    """
    
    @classmethod
    def generate_action_response(cls, root_cause, actions, urgency="MEDIUM", context=None):
        """Generate response for action/recommendation questions."""
        lines = []
        
        # Urgency indicator
        if urgency == "CRITICAL":
            lines.append("⚡ **IMMEDIATE ACTION REQUIRED**")
        elif urgency == "HIGH":
            lines.append("🔔 **High Priority Actions**")
        else:
            lines.append("📋 **Recommended Actions**")
        
        # Context (brief)
        if context:
            lines.append("")
            lines.append(context)
        
        # Actions
        if actions:
            lines.append("")
            for i, action in enumerate(actions[:5], 1):
                if isinstance(action, dict):
                    lines.append("{}. **{}:** {}".format(i, action.get("cause", ""), action.get("description", "")))
                    for step in action.get("steps", [])[:3]:
                        lines.append("   • {}".format(step))
                else:
                    lines.append("{}. {}".format(i, action))
        
        return "\n".join(lines)
    
    @classmethod
    def generate_fix_response(cls, issue, steps, expected_outcome=None):
        """Generate response for fix/resolve questions."""
        lines = []
        
        lines.append("**To fix {}:**".format(issue))
        lines.append("")
        
        for i, step in enumerate(steps[:6], 1):
            lines.append("{}. {}".format(i, step))
        
        if expected_outcome:
            lines.append("")
            lines.append("**Expected outcome:** {}".format(expected_outcome))
        
        return "\n".join(lines)


# Module-level instance for convenience
RESPONSE_ROUTER = IntentResponseRouter()
