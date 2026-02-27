# nlp_engine/oem_intent_engine.py
"""
OEM Intelligence Intent Engine

CRITICAL FIX: Properly classify user intents with UNIQUE reasoning paths.
Each intent type MUST produce different analysis and response.

Python 3.6 compatible.
"""

import re


class OEMIntentEngine:
    """
    Advanced intent classification specifically for OEM database monitoring.
    Ensures UNIQUE reasoning paths for different question types.
    
    INTENT ROUTING GATE (MANDATORY):
    - ENTITY_COUNT / ENTITY_LIST intents bypass alert analysis pipeline
    - These return DIRECT factual answers from inventory/metadata
    """
    
    # Intent constants
    INTENT_FACTUAL = "FACTUAL"
    INTENT_ROOT_CAUSE = "ROOT_CAUSE"
    INTENT_FREQUENCY = "FREQUENCY_PATTERN"
    INTENT_TIME_BASED = "TIME_BASED"
    INTENT_PREDICTIVE = "PREDICTIVE"
    INTENT_RECOMMENDATION = "RECOMMENDATION"
    INTENT_HEALTH = "HEALTH_STATUS"
    INTENT_COMPARISON = "COMPARISON"
    INTENT_STANDBY_DATAGUARD = "STANDBY_DATAGUARD"
    INTENT_TABLESPACE = "TABLESPACE"
    INTENT_RISK_POSTURE = "RISK_POSTURE"
    INTENT_UNKNOWN = "UNKNOWN"
    
    # NEW: Inventory/Metadata intents (bypass alert analysis)
    INTENT_ENTITY_COUNT = "ENTITY_COUNT"
    INTENT_ENTITY_LIST = "ENTITY_LIST"
    
    # =====================================================
    # QUESTION TYPE CLASSIFICATION (MANDATORY FIRST STEP)
    # =====================================================
    # Every question MUST be classified into ONE of these types:
    #   FACTUAL    - which, how many, is it, list
    #   ANALYTICAL - why, pattern, trend, comparison
    #   ACTION     - what should, how to fix, remediation
    #
    # Response format MUST match question type:
    #   FACT       → Short, direct answer ONLY
    #   ANALYSIS   → Explanation with evidence
    #   ACTION     → Steps and recommendations
    # MUST match IntentResponseRouter constants
    # =====================================================
    QUESTION_TYPE_FACTUAL = "FACT"      # Match IntentResponseRouter.TYPE_FACT
    QUESTION_TYPE_ANALYTICAL = "ANALYSIS"  # Match IntentResponseRouter.TYPE_ANALYSIS
    QUESTION_TYPE_ACTION = "ACTION"
    
    # =====================================================
    # INTENT ACTION ELIGIBILITY - CRITICAL BEHAVIOR RULE
    # =====================================================
    # This mapping determines which intents should include action recommendations.
    # 
    # RULE: Actions should ONLY appear for:
    #   1. RISK/FAILURE/INCIDENT intents (user needs to ACT)
    #   2. EXPLICIT ACTION REQUEST intents (user asked "what to do")
    #
    # Actions should NOT appear for:
    #   - FACTUAL queries (just reporting data)
    #   - DESCRIPTIVE/ANALYTICAL queries (summarizing state)
    #   - LIST/COUNT queries (inventory questions)
    #
    # A human expert DBA would NOT prescribe "what to do" for:
    #   "How many databases are down?" → Just answer the count
    #   "Which database has most errors?" → Just name it
    #   "What ORA codes are occurring?" → Just list them
    # =====================================================
    INTENTS_WITH_ACTIONS = {
        # ACTION type - user needs steps
        "RECOMMENDATION": True,      # Explicit action request
        
        # These are ANALYTICAL but may include actions if explicitly asked
        "ROOT_CAUSE": False,         # Why question → explanation only unless "what to do"
        "PREDICTIVE": False,         # Risk prediction → info only unless action asked
        "RISK_POSTURE": False,       # Risk assessment → info only
        "STANDBY_DATAGUARD": False,  # DG issues → list findings only
        "TABLESPACE": False,         # Space issues → list findings only
        
        # FACTUAL - no action section ever
        "FACTUAL": False,            # Just answering what was asked
        "HEALTH_STATUS": False,      # Reporting current state
        "FREQUENCY_PATTERN": False,  # Describing patterns
        "TIME_BASED": False,         # Temporal analysis
        "COMPARISON": False,         # Comparing entities
        "ENTITY_COUNT": False,       # Inventory count
        "ENTITY_LIST": False,        # Inventory list
        "UNKNOWN": False,            # Uncertain intent
    }
    
    # =====================================================
    # RESPONSE FORMAT BY QUESTION TYPE
    # =====================================================
    # FACTUAL   → use_short_format = True (no template)
    # ANALYTICAL → use_structured_format = True (explanation)
    # ACTION    → use_action_format = True (steps)
    # =====================================================
    FACTUAL_INTENTS = {
        "FACTUAL", "HEALTH_STATUS", "ENTITY_COUNT", "ENTITY_LIST",
        "TIME_BASED", "FREQUENCY_PATTERN"
    }
    
    ANALYTICAL_INTENTS = {
        "ROOT_CAUSE", "PREDICTIVE", "RISK_POSTURE", "COMPARISON",
        "STANDBY_DATAGUARD", "TABLESPACE"
    }
    
    ACTION_INTENTS = {
        "RECOMMENDATION"
    }
    
    @classmethod
    def get_question_type(cls, intent):
        """
        Get the question type for an intent.
        
        Returns:
            str: FACTUAL, ANALYTICAL, or ACTION
        """
        if intent in cls.ACTION_INTENTS:
            return cls.QUESTION_TYPE_ACTION
        elif intent in cls.ANALYTICAL_INTENTS:
            return cls.QUESTION_TYPE_ANALYTICAL
        else:
            return cls.QUESTION_TYPE_FACTUAL
    
    @classmethod
    def get_question_type_from_text(cls, question, intent=None):
        """
        PRODUCTION: Get question type directly from question text.
        
        This OVERRIDES intent-based type inference when specific patterns match.
        Ensures factual questions get factual responses regardless of intent.
        
        Args:
            question: The user's question text
            intent: Optional classified intent for fallback
            
        Returns:
            str: FACTUAL, ANALYTICAL, or ACTION
        """
        try:
            from nlp_engine.intent_response_router import IntentResponseRouter
            return IntentResponseRouter.get_question_type(question, intent)
        except ImportError:
            # Fallback to intent-based
            if intent:
                return cls.get_question_type(intent)
            return cls.QUESTION_TYPE_FACTUAL
    
    @classmethod
    def should_use_short_format(cls, intent, question=None):
        """
        Determine if response should be short and direct (no template).
        
        FACTUAL questions get SHORT answers:
        - "Which database is critical?" → "MIDEVSTBN is in CRITICAL state."
        - "How many alerts?" → "649,787 alerts total."
        
        PRODUCTION: Uses question text for better accuracy.
        """
        # If question provided, use text-based detection
        if question:
            question_type = cls.get_question_type_from_text(question, intent)
            return question_type == cls.QUESTION_TYPE_FACTUAL
        
        return intent in cls.FACTUAL_INTENTS
    
    @classmethod
    def should_include_actions(cls, intent, question=None):
        """
        Determine if an intent type should include action recommendations.
        
        CRITICAL RULE: Only ACTION question type gets actions.
        
        PRODUCTION: Uses question text for better accuracy.
        Actions should ONLY appear when:
        1. User explicitly asks "what should I do", "how to fix", etc.
        2. NOT for factual or analytical questions
        
        Args:
            intent: The classified intent string
            question: Optional question text for pattern-based detection
            
        Returns:
            bool: True if actions should be included, False otherwise
        """
        # If question provided, use text-based detection
        if question:
            try:
                from nlp_engine.intent_response_router import IntentResponseRouter
                return IntentResponseRouter.should_include_actions(question, intent)
            except ImportError:
                pass
        
        return cls.INTENTS_WITH_ACTIONS.get(intent, False)
    
    @classmethod
    def should_include_root_cause(cls, intent, question=None):
        """
        Determine if response should include root cause analysis.
        
        CRITICAL RULE: Root cause belongs ONLY to:
        - Incidents, failures, instability
        - "Why" questions
        - Risk/prediction questions
        
        NEVER attach root cause to:
        - Inventory questions
        - Count questions  
        - List questions
        - Hour/time factual questions
        
        Args:
            intent: The classified intent string
            question: Optional question text for pattern-based detection
            
        Returns:
            bool: True if root cause should be included, False otherwise
        """
        # If question provided, use text-based detection
        if question:
            try:
                from nlp_engine.intent_response_router import IntentResponseRouter
                return IntentResponseRouter.should_include_root_cause(question, intent)
            except ImportError:
                pass
        
        # Intent-based fallback
        return intent in cls.ANALYTICAL_INTENTS or intent == "RECOMMENDATION"
    
    def __init__(self):
        """Initialize intent engine with patterns."""
        self._init_patterns()
    
    def _init_patterns(self):
        """Initialize intent patterns."""
        self.INTENT_PATTERNS = {
            # =====================================================
            # ENTITY/INVENTORY INTENTS (HIGHEST PRIORITY - BYPASS ALERT ANALYSIS)
            # These return DIRECT factual answers, NO alert/time/RCA logic
            # =====================================================
            "ENTITY_COUNT": {
                "keywords": ["how many", "count", "total", "number of"],
                "question_patterns": [
                    r"how\s+many\s+(servers?|databases?|hosts?|targets?|instances?)",
                    r"count\s+of\s+(servers?|databases?|hosts?|targets?)",
                    r"total\s+(servers?|databases?|hosts?|targets?)",
                    r"number\s+of\s+(servers?|databases?|hosts?|targets?|dbs?)",
                    r"how\s+many\s+(are|do)\s+(we\s+)?(have|monitor|manage)",
                    r"(servers?|databases?|hosts?)\s+(are|do)\s+(we\s+)?(have|monitor)"
                ],
                "priority": 200,  # HIGHEST - must be checked first
                "requires_target": False,
                "bypass_alert_analysis": True
            },
            "ENTITY_LIST": {
                "keywords": ["list", "show all", "what are", "which", "all databases", "all servers"],
                "question_patterns": [
                    r"list\s+(all\s+)?(the\s+)?(servers?|databases?|hosts?|targets?|dbs?)",
                    r"show\s+(me\s+)?(all\s+)?(the\s+)?(servers?|databases?|hosts?|targets?)",
                    r"what\s+(are|is)\s+(the\s+)?(servers?|databases?|hosts?|targets?)",
                    r"which\s+(servers?|databases?|hosts?|targets?)\s+(are|do)\s+(we\s+)?(have|monitor)",
                    r"all\s+(monitored\s+)?(servers?|databases?|hosts?|targets?)",
                    r"give\s+(me\s+)?(a\s+)?list\s+of"
                ],
                "priority": 199,  # Second highest
                "requires_target": False,
                "bypass_alert_analysis": True
            },
            # =====================================================
            # ALERT ANALYSIS INTENTS (require full reasoning pipeline)
            # =====================================================
            "STANDBY_DATAGUARD": {
                "keywords": ["standby", "data guard", "dataguard", "apply lag", "lag beyond", "transport lag", "mrp", "redo apply", "errors on standby", "standby database"],
                "question_patterns": [
                    "standby",
                    "data.*guard",
                    "apply.*lag",
                    "redo.*ship",
                    "errors?.*standby",
                    "standby.*errors?",
                    "lag.*beyond.*threshold"
                ],
                "priority": 100,
                "requires_target": False
            },
            "TABLESPACE": {
                "keywords": ["tablespace", "tablespaces", "space full", "storage full", "disk full", "close to full", "space issue"],
                "question_patterns": [
                    "tablespace.*full",
                    "which.*tablespace",
                    "space.*issue",
                    "storage.*full",
                    "close\\s+to\\s+full",
                    "tablespace.*close"
                ],
                "priority": 95,
                "requires_target": False
            },
            "TIME_BASED": {
                "keywords": ["between", "during", "after midnight", "before", "morning", "night", "hour", "am", "pm"],
                "question_patterns": [
                    "at\\s+\\d+\\s*(am|pm)",
                    "between\\s+\\d+.*and\\s+\\d+",
                    "after\\s+midnight",
                    "during\\s+(night|day|morning|evening)",
                    "show\\s+alerts?\\s+between",
                    "alerts?\\s+between",
                    "occurring\\s+after",
                    "which\\s+hour.*highest"
                ],
                "priority": 90,
                "requires_target": False
            },
            "ROOT_CAUSE": {
                "keywords": ["why", "reason", "cause", "caused", "due to", "because", "root cause", "repeatedly", "occurring"],
                "question_patterns": [
                    "why\\s+(does|did|is|was|do|are)",
                    "what\\s+(caused|causes)",
                    "reason\\s+for",
                    "root.*cause",
                    "why.*repeatedly",
                    "why.*down",
                    "why.*fail",
                    "why.*stop",
                    "why.*occurring",
                    "why.*most.*alerts?"
                ],
                "priority": 85,
                "requires_target": False
            },
            "PREDICTIVE": {
                "keywords": ["will", "next", "predict", "forecast", "likely", "going to", "expected", "fail next"],
                "question_patterns": [
                    "will\\s+(it|this|the)",
                    "(most\\s+)?likely\\s+to\\s+fail",
                    "going\\s+to\\s+(fail|crash|stop)",
                    "predict",
                    "next\\s+failure",
                    "expected\\s+to",
                    "fail\\s+next",
                    "which.*likely.*fail"
                ],
                "priority": 80,
                "requires_target": False
            },
            "FREQUENCY_PATTERN": {
                # CRITICAL FIX: REMOVED "how many" and "count" - these belong to FACT_COUNT
                # FREQUENCY is about PATTERNS and TIME, not COUNTS
                "keywords": ["often", "frequent", "recurring", "repeatedly", "pattern", "highest frequency", "peak hour", "which hour"],
                "question_patterns": [
                    "how\\s+often",
                    "how\\s+frequent",
                    "(keeps?|keep)\\s+(failing|crashing|stopping)",
                    "repeatedly",
                    "recurring",
                    "pattern",
                    "highest.*frequency",
                    "which.*hour.*highest",
                    "peak.*hour",
                    "what.*hour"
                ],
                "priority": 75,
                "requires_target": False
            },
            "RECOMMENDATION": {
                "keywords": ["fix", "action", "should", "recommend", "solution", "resolve", "what to do", "immediate action", "taken for"],
                "question_patterns": [
                    "(what|how)\\s+(to|should)\\s+(fix|do|resolve)",
                    "recommend",
                    "action.*take",
                    "immediate\\s+action",
                    "solution",
                    "actions?.*should.*be.*taken",
                    "what.*should.*be.*taken"
                ],
                "priority": 70,
                "requires_target": False
            },
            "RISK_POSTURE": {
                "keywords": ["risk", "posture", "overall", "environment", "risky"],
                "question_patterns": [
                    "risk\\s+posture",
                    "overall\\s+risk",
                    "environment.*risk",
                    "how\\s+risky"
                ],
                "priority": 68,
                "requires_target": False
            },
            "HEALTH_STATUS": {
                "keywords": ["health", "status", "state", "condition", "stable", "down right now", "up", "critical", "are any", "currently"],
                "question_patterns": [
                    "(what|how)\\s+is.*status",
                    "health\\s+of",
                    "is.*down",
                    "is.*up",
                    "currently.*(in\\s+)?critical",
                    "are\\s+any.*down",
                    "databases?\\s+down",
                    "down\\s+right\\s+now"
                ],
                "priority": 65,
                "requires_target": False
            },
            "COMPARISON": {
                "keywords": ["compare", "vs", "versus", "difference", "better", "worse", "than"],
                "question_patterns": [
                    "compare",
                    "\\bvs\\b",
                    "versus",
                    "difference\\s+between"
                ],
                "priority": 60,
                "requires_target": False
            },
            "FACTUAL": {
                "keywords": ["which", "what", "how many", "list", "show", "count", "most", "affected", "errors", "occurring"],
                "question_patterns": [
                    "which\\s+(database|db)",
                    "what\\s+(errors?|alerts?)",
                    "how\\s+many",
                    "list\\s+(all|the)",
                    "show\\s+(me|all)",
                    "most\\s+affected",
                    "what.*errors?.*occurring",
                    "errors?.*occurring"
                ],
                "priority": 50,
                "requires_target": False
            }
        }
    
    def classify(self, question):
        """
        Classify question into a specific intent with extracted entities.
        
        INTENT ROUTING GATE (MANDATORY FIRST STEP):
        - ENTITY_COUNT / ENTITY_LIST are checked FIRST
        - If matched, bypass ALL alert analysis logic
        - Return direct factual answers from inventory/metadata
        
        Returns:
            dict with intent, confidence, entities, sub_intent, raw_question,
                  bypass_alert_analysis (bool)
        """
        q_lower = question.lower().strip()
        
        # =====================================================
        # INTENT ROUTING GATE - CHECK ENTITY INTENTS FIRST
        # These MUST be checked before any alert-based intents
        # =====================================================
        entity_result = self._check_entity_intent(q_lower, question)
        if entity_result:
            return entity_result
        
        # =====================================================
        # HARD COUNT GUARD (ABSOLUTE RULE - HIGHEST PRIORITY)
        # =====================================================
        # If question contains "how many", "total", "count", "number of":
        #   → FORCE FACTUAL intent with FACT_COUNT sub_intent
        #   → NEVER route to FREQUENCY_PATTERN or TIME analysis
        #   → Response MUST be a NUMBER only
        # This rule is ABSOLUTE and OVERRIDES all other classification.
        # =====================================================
        count_guard_keywords = ["how many", "total", "count", "number of"]
        is_count_question = any(kw in q_lower for kw in count_guard_keywords)
        
        # Exception: "which hour" or "peak hour" questions are TIME, not COUNT
        is_time_question = any(kw in q_lower for kw in ["which hour", "what hour", "peak hour", "highest hour"])
        
        if is_count_question and not is_time_question:
            # HARD COUNT GUARD ACTIVATED - route to FACTUAL with FACT_COUNT
            entities = self._extract_entities(question, q_lower)
            return {
                "intent": self.INTENT_FACTUAL,
                "confidence": 0.95,
                "entities": entities,
                "sub_intent": "FACT_COUNT",  # CRITICAL: Forces count-only response
                "all_scores": [{"intent": "FACTUAL", "score": 20.0, "priority": 999, "requires_target": False}],
                "raw_question": question,
                "bypass_time_analysis": True,  # Signal to skip time/frequency logic
                "force_count_response": True   # Signal to use count formatter
            }
        
        # =====================================================
        # STANDBY/DATA GUARD OVERRIDE (CRITICAL FIX)
        # If question mentions standby/dataguard keywords, MUST route to STANDBY_DATAGUARD
        # NEVER let FACTUAL intent steal standby questions
        # =====================================================
        standby_keywords = ["standby", "data guard", "dataguard", "apply lag", "transport lag", 
                           "mrp", "redo apply", "redo ship", "lag beyond"]
        if any(kw in q_lower for kw in standby_keywords):
            primary_intent = self.INTENT_STANDBY_DATAGUARD
            confidence = 0.95
            entities = self._extract_entities(question, q_lower)
            sub_intent = self._detect_sub_intent(q_lower, primary_intent)
            return {
                "intent": primary_intent,
                "confidence": confidence,
                "entities": entities,
                "sub_intent": sub_intent,
                "all_scores": [{"intent": "STANDBY_DATAGUARD", "score": 15.0, "priority": 100, "requires_target": False}],
                "raw_question": question
            }
        
        # =====================================================
        # TABLESPACE OVERRIDE (CRITICAL FIX)
        # If question mentions tablespace keywords, MUST route to TABLESPACE
        # =====================================================
        tablespace_keywords = ["tablespace", "tablespaces", "space full", "storage full", 
                              "disk full", "close to full", "running out of space"]
        if any(kw in q_lower for kw in tablespace_keywords):
            primary_intent = self.INTENT_TABLESPACE
            confidence = 0.95
            entities = self._extract_entities(question, q_lower)
            sub_intent = self._detect_sub_intent(q_lower, primary_intent)
            return {
                "intent": primary_intent,
                "confidence": confidence,
                "entities": entities,
                "sub_intent": sub_intent,
                "all_scores": [{"intent": "TABLESPACE", "score": 15.0, "priority": 95, "requires_target": False}],
                "raw_question": question
            }
        
        # =====================================================
        # SPECIAL OVERRIDES - semantic intent detection
        # These patterns MUST map to specific intents regardless of score
        # =====================================================
        
        # CRITICAL/WARNING state → HEALTH_STATUS
        if any(x in q_lower for x in ["critical state", "critical status", "in critical", 
                                       "warning state", "warning status", "down right now",
                                       "is down", "is up", "currently in"]):
            primary_intent = self.INTENT_HEALTH
            confidence = 0.90
            entities = self._extract_entities(question, q_lower)
            sub_intent = self._detect_sub_intent(q_lower, primary_intent)
            return {
                "intent": primary_intent,
                "confidence": confidence,
                "entities": entities,
                "sub_intent": sub_intent,
                "all_scores": [{"intent": "HEALTH_STATUS", "score": 10.0, "priority": 65}],
                "raw_question": question
            }
        
        # ROOT CAUSE - why questions
        if any(x in q_lower for x in ["why is", "why does", "root cause", "what caused", 
                                       "reason for", "why are there"]):
            primary_intent = self.INTENT_ROOT_CAUSE
            confidence = 0.90
            entities = self._extract_entities(question, q_lower)
            sub_intent = self._detect_sub_intent(q_lower, primary_intent)
            return {
                "intent": primary_intent,
                "confidence": confidence,
                "entities": entities,
                "sub_intent": sub_intent,
                "all_scores": [{"intent": "ROOT_CAUSE", "score": 10.0, "priority": 90}],
                "raw_question": question
            }
        
        # TIME_BASED - time-specific questions
        if any(x in q_lower for x in ["after midnight", "before midnight", "at night",
                                       "during day", "morning", "afternoon", "peak hour",
                                       "what time", "when do", "between", "after 6pm",
                                       "business hours", "overnight"]):
            primary_intent = self.INTENT_TIME_BASED
            confidence = 0.90
            entities = self._extract_entities(question, q_lower)
            sub_intent = self._detect_sub_intent(q_lower, primary_intent)
            return {
                "intent": primary_intent,
                "confidence": confidence,
                "entities": entities,
                "sub_intent": sub_intent,
                "all_scores": [{"intent": "TIME_BASED", "score": 10.0, "priority": 78}],
                "raw_question": question
            }
        
        # PREDICTIVE - prediction questions
        if any(x in q_lower for x in ["will fail", "likely to fail", "predict", "forecast",
                                       "going to have issues", "at risk", "risk assessment",
                                       "will there be", "expected to"]):
            primary_intent = self.INTENT_PREDICTIVE
            confidence = 0.90
            entities = self._extract_entities(question, q_lower)
            sub_intent = self._detect_sub_intent(q_lower, primary_intent)
            return {
                "intent": primary_intent,
                "confidence": confidence,
                "entities": entities,
                "sub_intent": sub_intent,
                "all_scores": [{"intent": "PREDICTIVE", "score": 10.0, "priority": 75}],
                "raw_question": question
            }
        
        # RECOMMENDATION - what to do questions
        if any(x in q_lower for x in ["what should i do", "how do i fix", "how to resolve",
                                       "recommend", "action", "steps to", "remediate",
                                       "fix for", "solution for"]):
            primary_intent = self.INTENT_RECOMMENDATION
            confidence = 0.90
            entities = self._extract_entities(question, q_lower)
            sub_intent = self._detect_sub_intent(q_lower, primary_intent)
            return {
                "intent": primary_intent,
                "confidence": confidence,
                "entities": entities,
                "sub_intent": sub_intent,
                "all_scores": [{"intent": "RECOMMENDATION", "score": 10.0, "priority": 72}],
                "raw_question": question
            }
        
        # Score all intents
        scored_intents = []
        for intent_name, config in self.INTENT_PATTERNS.items():
            score = self._score_intent(q_lower, config)
            if score > 0:
                scored_intents.append({
                    "intent": intent_name,
                    "score": score,
                    "priority": config["priority"],
                    "requires_target": config["requires_target"]
                })
        
        # Sort by score, then by priority
        scored_intents.sort(key=lambda x: (x["score"], x["priority"]), reverse=True)
        
        # Get best match
        if scored_intents:
            best = scored_intents[0]
            primary_intent = best["intent"]
            confidence = min(0.95, best["score"] / 3.0)
        else:
            primary_intent = self.INTENT_UNKNOWN
            confidence = 0.2
        
        # Extract entities
        entities = self._extract_entities(question, q_lower)
        
        # Determine sub-intent for compound questions
        sub_intent = self._detect_sub_intent(q_lower, primary_intent)
        
        return {
            "intent": primary_intent,
            "confidence": confidence,
            "entities": entities,
            "sub_intent": sub_intent,
            "all_scores": scored_intents[:3],
            "raw_question": question
        }
    
    def _score_intent(self, question, config):
        """Score how well question matches intent."""
        score = 0
        
        # Keyword matching
        for keyword in config["keywords"]:
            if keyword in question:
                score += 1.0
        
        # Pattern matching (more precise)
        for pattern in config["question_patterns"]:
            try:
                if re.search(pattern, question, re.IGNORECASE):
                    score += 2.0
            except re.error:
                pass
        
        return score
    
    # =====================================================
    # INTENT ROUTING GATE - ENTITY INTENT DETECTION
    # =====================================================
    def _check_entity_intent(self, q_lower, question):
        """
        MANDATORY FIRST CHECK: Detect ENTITY_COUNT or ENTITY_LIST intents.
        
        These intents MUST:
        - Return DIRECT factual answers from inventory/metadata
        - BYPASS all alert analysis, time analysis, root cause, prediction logic
        - NOT reuse previous alert context
        
        Examples:
        - "How many servers in OEM?" → ENTITY_COUNT
        - "List all databases" → ENTITY_LIST
        - "How many databases are monitored?" → ENTITY_COUNT
        
        Returns:
            Classification dict if entity intent detected, None otherwise
        """
        # Entity type keywords to detect
        entity_keywords = [
            "server", "servers", "database", "databases", "db", "dbs",
            "host", "hosts", "target", "targets", "instance", "instances",
            "monitored", "monitoring", "oem", "managed"
        ]
        
        # Check if question contains entity-related keywords
        has_entity_keyword = any(kw in q_lower for kw in entity_keywords)
        if not has_entity_keyword:
            return None
        
        # =====================================================
        # ENTITY_COUNT DETECTION
        # =====================================================
        count_patterns = [
            r"how\s+many\s+(servers?|databases?|hosts?|targets?|instances?|dbs?)",
            r"count\s+(of\s+)?(servers?|databases?|hosts?|targets?)",
            r"total\s+(number\s+of\s+)?(servers?|databases?|hosts?|targets?)",
            r"number\s+of\s+(servers?|databases?|hosts?|targets?|dbs?)",
            r"how\s+many\s+(are|do)\s+(we\s+)?(have|monitor|manage)",
            r"(servers?|databases?|hosts?)\s+(are|do)\s+(we\s+)?(have|monitor)",
            r"how\s+many.*monitored",
            r"how\s+many.*in\s+oem",
            r"total.*databases?",
            r"count.*databases?"
        ]
        
        for pattern in count_patterns:
            try:
                if re.search(pattern, q_lower, re.IGNORECASE):
                    # Determine entity type
                    entity_type = self._extract_entity_type(q_lower)
                    return {
                        "intent": self.INTENT_ENTITY_COUNT,
                        "confidence": 0.95,
                        "entities": {"entity_type": entity_type},
                        "sub_intent": None,
                        "all_scores": [{"intent": "ENTITY_COUNT", "score": 10.0, "priority": 200}],
                        "raw_question": question,
                        "bypass_alert_analysis": True  # CRITICAL FLAG
                    }
            except re.error:
                pass
        
        # =====================================================
        # ENTITY_LIST DETECTION
        # =====================================================
        list_patterns = [
            r"list\s+(all\s+)?(the\s+)?(servers?|databases?|hosts?|targets?|dbs?)",
            r"show\s+(me\s+)?(all\s+)?(the\s+)?(servers?|databases?|hosts?|targets?)",
            r"what\s+(are|is)\s+(the\s+)?(servers?|databases?|hosts?|targets?)",
            r"which\s+(servers?|databases?|hosts?|targets?)\s+(are|do)\s+(we\s+)?(have|monitor)",
            r"all\s+(monitored\s+)?(servers?|databases?|hosts?|targets?)",
            r"give\s+(me\s+)?(a\s+)?list",
            r"names?\s+of\s+(all\s+)?(servers?|databases?|hosts?|targets?)",
            r"list.*databases?",
            r"show.*databases?"
        ]
        
        for pattern in list_patterns:
            try:
                if re.search(pattern, q_lower, re.IGNORECASE):
                    entity_type = self._extract_entity_type(q_lower)
                    return {
                        "intent": self.INTENT_ENTITY_LIST,
                        "confidence": 0.95,
                        "entities": {"entity_type": entity_type},
                        "sub_intent": None,
                        "all_scores": [{"intent": "ENTITY_LIST", "score": 10.0, "priority": 199}],
                        "raw_question": question,
                        "bypass_alert_analysis": True  # CRITICAL FLAG
                    }
            except re.error:
                pass
        
        return None
    
    def _extract_entity_type(self, q_lower):
        """Extract the type of entity being asked about."""
        if any(x in q_lower for x in ["server", "servers", "host", "hosts"]):
            return "SERVER"
        elif any(x in q_lower for x in ["database", "databases", "db", "dbs", "instance", "instances"]):
            return "DATABASE"
        elif any(x in q_lower for x in ["target", "targets"]):
            return "TARGET"
        else:
            return "DATABASE"  # Default to database

    def _detect_sub_intent(self, question, primary_intent):
        """Detect secondary intent for compound questions."""
        sub_intents = []
        
        # Time-based sub-intent
        time_words = ["midnight", "night", "am", "pm", "hour"]
        has_time = False
        for t in time_words:
            if t in question:
                has_time = True
                break
        if has_time and primary_intent != "TIME_BASED":
            sub_intents.append("TIME_CONTEXT")
        
        # Frequency sub-intent
        freq_words = ["often", "repeatedly", "many times"]
        has_freq = False
        for f in freq_words:
            if f in question:
                has_freq = True
                break
        if has_freq and primary_intent != "FREQUENCY_PATTERN":
            sub_intents.append("FREQUENCY_CONTEXT")
        
        return sub_intents[0] if sub_intents else None
    
    def _extract_entities(self, question, q_lower):
        """Extract all relevant entities from question."""
        entities = {}
        
        # Extract target database
        target = self._extract_target(question)
        if target:
            entities["target"] = target
        
        # Extract time range
        time_range = self._extract_time_range(q_lower)
        if time_range:
            entities["time_range"] = time_range
        
        # Extract severity filter
        severity = self._extract_severity(q_lower)
        if severity:
            entities["severity"] = severity
        
        # Extract metric type
        metric = self._extract_metric_type(q_lower)
        if metric:
            entities["metric_type"] = metric
        
        # Extract ORA code if mentioned
        ora_code = self._extract_ora_code(question)
        if ora_code:
            entities["ora_code"] = ora_code
        
        return entities
    
    def _extract_target(self, question):
        """Extract database/target name."""
        tokens = re.findall(r'[A-Z][A-Z0-9_]{2,}', question)
        # Extended exclude list to avoid capturing keywords as targets
        exclude = {
            "OEM", "ORA", "CPU", "RAM", "SGA", "PGA", "DBA", "SQL", "XML", "CSV", 
            "THE", "AND", "FOR", "WHY", "HOW", "WHAT", "WHICH", "WHEN", "WHERE",
            "CRITICAL", "WARNING", "ERROR", "INTERNAL", "SEVERE", "INFO",
            "DATA", "GUARD", "STANDBY", "PRIMARY", "TABLESPACE", "STORAGE",
            "MIDNIGHT", "NIGHT", "MORNING", "EVENING", "TODAY", "YESTERDAY"
        }
        
        for token in tokens:
            if token not in exclude:
                return token
        
        return None
    
    def _extract_time_range(self, question):
        """Extract time range from question."""
        # Pattern: "between X AM and Y AM"
        between_match = re.search(
            r'between\s+(\d{1,2})\s*(am|pm)?\s*and\s+(\d{1,2})\s*(am|pm)?',
            question, re.IGNORECASE
        )
        if between_match:
            start_hour = int(between_match.group(1))
            end_hour = int(between_match.group(3))
            start_meridiem = between_match.group(2) or between_match.group(4) or "am"
            end_meridiem = between_match.group(4) or between_match.group(2) or "am"
            
            if start_meridiem and "pm" in start_meridiem.lower() and start_hour != 12:
                start_hour += 12
            if end_meridiem and "pm" in end_meridiem.lower() and end_hour != 12:
                end_hour += 12
            if start_meridiem and "am" in start_meridiem.lower() and start_hour == 12:
                start_hour = 0
            if end_meridiem and "am" in end_meridiem.lower() and end_hour == 12:
                end_hour = 0
            
            return {"type": "RANGE", "start_hour": start_hour, "end_hour": end_hour}
        
        # Pattern: "at X AM"
        at_match = re.search(r'at\s+(\d{1,2})\s*(am|pm)', question, re.IGNORECASE)
        if at_match:
            hour = int(at_match.group(1))
            meridiem = at_match.group(2)
            if meridiem and "pm" in meridiem.lower() and hour != 12:
                hour += 12
            if meridiem and "am" in meridiem.lower() and hour == 12:
                hour = 0
            return {"type": "SPECIFIC_HOUR", "hour": hour}
        
        # Pattern: "after midnight"
        if "after midnight" in question:
            return {"type": "RANGE", "start_hour": 0, "end_hour": 6}
        
        # Pattern: "night" / "nightly"
        if "night" in question or "nightly" in question:
            return {"type": "RANGE", "start_hour": 22, "end_hour": 6}
        
        return None
    
    def _extract_severity(self, question):
        """Extract severity level from question."""
        if "critical" in question:
            return "CRITICAL"
        if "warning" in question:
            return "WARNING"
        if "high" in question:
            return "HIGH"
        return None
    
    def _extract_metric_type(self, question):
        """Extract metric type being asked about."""
        metric_keywords = {
            "CPU": ["cpu", "processor", "utilization"],
            "MEMORY": ["memory", "heap", "pga", "sga", "ram"],
            "DISK": ["disk", "storage", "tablespace", "io"],
            "NETWORK": ["network", "connectivity", "timeout"],
            "REDO": ["redo", "redo log", "archive"],
            "UNDO": ["undo", "rollback"]
        }
        
        for metric, keywords in metric_keywords.items():
            for kw in keywords:
                if kw in question:
                    return metric
        
        return None
    
    def _extract_ora_code(self, question):
        """Extract ORA error code if mentioned."""
        match = re.search(r'ORA[-\s]?(\d{3,5})', question, re.IGNORECASE)
        if match:
            return "ORA-{0}".format(match.group(1))
        return None


class IntentAnalyzer:
    """
    Analyzes what specific information is needed based on intent.
    """
    
    @staticmethod
    def get_analysis_requirements(intent, entities):
        """
        Return what data/analysis is needed for this intent.
        """
        requirements = {
            "data_needed": [],
            "analysis_type": [],
            "response_format": "",
            "drill_down_required": False
        }
        
        if intent == OEMIntentEngine.INTENT_FACTUAL:
            requirements["data_needed"] = ["alert_counts", "database_list", "severity_summary"]
            requirements["analysis_type"] = ["aggregation", "filtering"]
            requirements["response_format"] = "LIST_OR_COUNT"
            requirements["drill_down_required"] = False
        
        elif intent == OEMIntentEngine.INTENT_ROOT_CAUSE:
            requirements["data_needed"] = ["alerts_detail", "ora_codes", "message_analysis"]
            requirements["analysis_type"] = ["ora_code_extraction", "context_analysis"]
            requirements["response_format"] = "ROOT_CAUSE_ANALYSIS"
            requirements["drill_down_required"] = True
        
        elif intent == OEMIntentEngine.INTENT_TIME_BASED:
            requirements["data_needed"] = ["alerts_by_time", "hourly_distribution"]
            requirements["analysis_type"] = ["temporal_filtering", "time_aggregation"]
            requirements["response_format"] = "TIME_ANALYSIS"
            requirements["drill_down_required"] = True
        
        elif intent == OEMIntentEngine.INTENT_FREQUENCY:
            requirements["data_needed"] = ["alert_counts", "patterns"]
            requirements["analysis_type"] = ["frequency_calculation"]
            requirements["response_format"] = "FREQUENCY_REPORT"
            requirements["drill_down_required"] = True
        
        elif intent == OEMIntentEngine.INTENT_PREDICTIVE:
            requirements["data_needed"] = ["historical_patterns", "failure_probability"]
            requirements["analysis_type"] = ["prediction_model", "risk_scoring"]
            requirements["response_format"] = "PREDICTION_REPORT"
            requirements["drill_down_required"] = False
        
        elif intent == OEMIntentEngine.INTENT_RECOMMENDATION:
            requirements["data_needed"] = ["root_cause", "historical_fixes"]
            requirements["analysis_type"] = ["root_cause_first", "action_mapping"]
            requirements["response_format"] = "ACTION_PLAN"
            requirements["drill_down_required"] = True
        
        elif intent == OEMIntentEngine.INTENT_HEALTH:
            requirements["data_needed"] = ["current_alerts", "recent_incidents"]
            requirements["analysis_type"] = ["status_check", "severity_assessment"]
            requirements["response_format"] = "STATUS_REPORT"
            requirements["drill_down_required"] = False
        
        elif intent == OEMIntentEngine.INTENT_STANDBY_DATAGUARD:
            requirements["data_needed"] = ["standby_alerts", "dataguard_metrics"]
            requirements["analysis_type"] = ["dataguard_specific_filter"]
            requirements["response_format"] = "DATAGUARD_REPORT"
            requirements["drill_down_required"] = True
        
        elif intent == OEMIntentEngine.INTENT_TABLESPACE:
            requirements["data_needed"] = ["tablespace_alerts", "storage_metrics"]
            requirements["analysis_type"] = ["tablespace_filter"]
            requirements["response_format"] = "TABLESPACE_REPORT"
            requirements["drill_down_required"] = True
        
        elif intent == OEMIntentEngine.INTENT_RISK_POSTURE:
            requirements["data_needed"] = ["all_alerts", "all_databases"]
            requirements["analysis_type"] = ["environment_wide_assessment"]
            requirements["response_format"] = "RISK_POSTURE_REPORT"
            requirements["drill_down_required"] = False
        
        else:
            requirements["data_needed"] = ["basic_summary"]
            requirements["analysis_type"] = ["general_summary"]
            requirements["response_format"] = "GENERAL"
            requirements["drill_down_required"] = False
        
        return requirements
