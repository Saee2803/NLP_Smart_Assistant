# -*- coding: utf-8 -*-
# reasoning/dba_guardrails.py
"""
NLP-DRIVEN ORACLE OEM DATABASE ASSISTANT - 8 GUARDRAIL RULES
=============================================================

You operate ONLY on the alert data explicitly provided in this session.
You do NOT assume missing facts.
Assume user is a DBA / SRE peer. Be concise, technical, scoped, and precise.

================================================================================
RULE 1: CONTEXT & SCOPE RESOLUTION (MANDATORY)
================================================================================
You MUST maintain an explicit ACTIVE_DB_SCOPE at all times.

Rules:
- If user asks about a specific database (e.g. MIDEVSTB, MIDEVSTBN),
  lock ACTIVE_DB_SCOPE to that database.
- Short follow-up questions like:
  "Critical count?" / "Total for that DB?" / "This DB looks fine right?"
  MUST inherit the previous ACTIVE_DB_SCOPE.
- NEVER answer with environment-wide numbers
  unless user explicitly says: "environment", "overall", "all databases".

Before answering any numeric question:
- Re-verify: "Is this DB-scoped or Environment-scoped?"
- If ambiguous -> ask ONE clarification question.
- Never guess.

Violation prevention:
  [X] Do NOT reply "649,769 critical alerts" when ACTIVE_DB_SCOPE = MIDEVSTB.
  [OK] Correct answer must be DB-specific.

================================================================================
RULE 2: NUMERIC ANSWER PRECISION RULE
================================================================================
If user says: "Give only the number" / "Critical count?" / "Total alerts?"

Then:
- Respond with ONLY the number.
- No labels, no explanations, no confidence text.

Example:
  User: "How many CRITICAL alerts exist for MIDEVSTB?"
  Correct: 165837

================================================================================
RULE 3: PREDICTIVE & ROOT CAUSE GUARDRAILS
================================================================================
You are NOT allowed to state certainty unless proven.

FORBIDDEN phrases:
  [X] "Confirmed root cause"
  [X] "Will escalate"
  [X] "Guaranteed outage"
  [X] "HIGH confidence - computed"

REQUIRED phrasing:
  [OK] "Based on alert frequency patterns only"
  [OK] "Inference, not confirmation"
  [OK] "Medium confidence"
  [OK] "Requires validation via AWR / trace files / OEM metrics"

Root cause rule:
- ORA-600, ORA-12537, INTERNAL_ERROR are SYMPTOMS unless proven otherwise.
- You may rank them by frequency, NOT declare them final root cause.

================================================================================
RULE 4: UNIQUE INCIDENT / ISSUE COUNT RULE
================================================================================
You MUST NOT present exact incident counts unless incident IDs exist.

Forbidden:
  [X] "4 unique incidents"

Required:
  [OK] "~4 distinct alert patterns detected"
  [OK] "Approximate grouping based on message similarity"
  [OK] "Patterns != confirmed incidents"

Always add: "This is an approximation, not an incident count."

================================================================================
RULE 5: RISK & ESCALATION LANGUAGE
================================================================================
When asked: "Is this likely to escalate?" / "Will this cause outage?"

Use this structure:
- State current evidence
- State uncertainty
- State what data is missing

Example:
  "Based on sustained alert volume and repetition, there is elevated risk.
   However, without AWR/ASH and system metrics, outage likelihood cannot
   be confirmed."

================================================================================
RULE 6: EXECUTION & ACTION SAFETY
================================================================================
You CANNOT:
- Run SQL
- Restart databases
- Guarantee fixes

Always respond with:
  "I cannot execute changes. I can suggest safe investigation steps."

================================================================================
RULE 7: CONFIDENCE LABELING STANDARD
================================================================================
Default confidence = MEDIUM

Use HIGH only when:
  [OK] Direct OEM metric confirms
  [OK] Explicit DB down / confirmed failure

Otherwise:
  [OK] MEDIUM (pattern-based)
  [OK] LOW (insufficient data)

================================================================================
RULE 8: SHARED CONTEXT TONE
================================================================================
Assume user is a DBA / SRE peer.
Avoid generic chatbot tone.
Be concise, technical, scoped, and precise.

No textbook explanations. No fluff. Direct answers.
"""

import re
from enum import Enum, auto
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field


# =============================================================================
# FALLBACK RULE - LIMITED DATA RESPONSE
# =============================================================================

LIMITED_DATA_RESPONSE = "[WARNING] Limited Data: This information is not available in the current alert dataset."


# =============================================================================
# DBA-NATIVE TONE HELPER (HARD RULE 4)
# =============================================================================

class DBAToneEnforcer:
    """
    [HARD RULE 4] DBA-NATIVE TONE (STYLE FIX)
    
    Default assumption: User is a DBA who already understands Oracle basics.
    
    Style Rules:
    - No textbook explanations
    - No generic IT language
    - No motivational fluff
    - Direct, technical, calm
    
    [X] Instead of: "This indicates a potential problem that may impact services"
    [OK] Say: "Alert volume and repetition indicate an unresolved condition
              rather than transient noise."
    """
    
    # Generic IT phrases to avoid
    GENERIC_PHRASES = {
        "indicates a potential problem that may impact services":
            "indicates an unresolved condition rather than transient noise",
        "this could potentially cause issues":
            "this pattern warrants investigation",
        "there appears to be an issue":
            "the data shows",
        "you may want to consider":
            "recommended action",
        "it is recommended that you":
            "next step",
        "this is important because":
            "impact",
        "please note that":
            "note:",
        "I would suggest":
            "suggested action",
        "in order to":
            "to",
        "at this point in time":
            "currently",
        "going forward":
            "next",
        "leverage the":
            "use",
        "utilize":
            "use",
        "in terms of":
            "for",
        "with regards to":
            "regarding",
        "as per":
            "per",
    }
    
    # Textbook explanation patterns to remove
    TEXTBOOK_PATTERNS = [
        r"Oracle\s+(?:Database\s+)?is\s+a\s+(?:relational\s+)?database\b",
        r"ORA-\d+\s+(?:error\s+)?is\s+an?\s+(?:Oracle\s+)?error\s+that\s+(?:occurs|happens|indicates)",
        r"(?:This|The)\s+(?:error|alert)\s+(?:typically\s+)?(?:occurs|happens)\s+when\b",
        r"In\s+Oracle,?\s+(?:a|an|the)\s+\w+\s+(?:is|are)\s+(?:used|designed)\s+(?:to|for)\b",
    ]
    
    # Motivational fluff to remove
    FLUFF_PHRASES = [
        "I hope this helps",
        "Let me know if you need anything else",
        "Happy to help",
        "Great question",
        "Good catch",
        "You're on the right track",
        "This is a common issue",
        "Don't worry",
        "Rest assured",
    ]
    
    @classmethod
    def enforce_dba_tone(cls, response: str) -> str:
        """Convert generic/textbook language to DBA-native tone."""
        result = response
        
        # Replace generic phrases
        for generic, dba_style in cls.GENERIC_PHRASES.items():
            result = re.sub(
                re.escape(generic), 
                dba_style, 
                result, 
                flags=re.IGNORECASE
            )
        
        # Remove fluff phrases
        for fluff in cls.FLUFF_PHRASES:
            result = re.sub(
                re.escape(fluff) + r"[.!]?\s*",
                "",
                result,
                flags=re.IGNORECASE
            )
        
        return result.strip()
    
    @classmethod
    def check_tone_compliance(cls, response: str) -> Tuple[bool, List[str]]:
        """Check if response uses DBA-appropriate tone."""
        issues = []
        response_lower = response.lower()
        
        # Check for generic phrases
        for generic in cls.GENERIC_PHRASES.keys():
            if generic.lower() in response_lower:
                issues.append(f"Generic IT language: '{generic}'")
        
        # Check for fluff
        for fluff in cls.FLUFF_PHRASES:
            if fluff.lower() in response_lower:
                issues.append(f"Motivational fluff: '{fluff}'")
        
        # Check for textbook patterns
        for pattern in cls.TEXTBOOK_PATTERNS:
            if re.search(pattern, response, re.IGNORECASE):
                issues.append(f"Textbook explanation detected")
        
        return len(issues) == 0, issues


# =============================================================================
# SCOPE LEVELS (HARD RULE 1 - CONTEXT & SCOPE LOCK)
# =============================================================================

class ScopeLevel(Enum):
    """
    [HARD RULE 1] Active scope for the query.
    
    SCOPE HIERARCHY (Highest -> Lowest):
    1. DATABASE - Explicit DB name in current question
    2. CONTEXT - Database from active conversation context  
    3. ENVIRONMENT - Only if explicitly asked
    
    CRITICAL: Once scope is established, NEVER lose it unless user resets.
    """
    DATABASE = "DATABASE"       # Explicit DB name (highest priority)
    CONTEXT = "CONTEXT"         # From conversation context (second priority)
    ENVIRONMENT = "ENVIRONMENT" # Only if explicitly asked (lowest priority)
    UNCLEAR = "UNCLEAR"         # Needs ONE clarification question


# =============================================================================
# CONFIDENCE LEVELS (RULE 9 - MANDATORY)
# =============================================================================

class ConfidenceLevel(Enum):
    """
    [HARD RULE 2] Confidence Levels - MANDATORY for every answer.
    
    HIGH: Direct count, exact aggregation (backed by data)
    MEDIUM: Pattern inference, clustering, prediction
    LOW: Insufficient data, approximation
    
    Format in response: "Confidence: HIGH"
    """
    HIGH = "HIGH"       # Direct count, exact aggregation
    MEDIUM = "MEDIUM"   # Pattern inference, clustering
    LOW = "LOW"         # Insufficient data


# =============================================================================
# EXPLANATION MODES (RULE 8 - STRICT)
# =============================================================================

class ExplanationMode(Enum):
    """
    [HARD RULE 4] DBA-Native Tone Mode.
    
    Default: SENIOR_DBA (user is assumed to understand Oracle basics)
    Switch to MANAGER only when explicitly asked.
    
    Style Rules:
    - No textbook explanations
    - No generic IT language  
    - No motivational fluff
    - Direct, technical, calm
    """
    MANAGER = "MANAGER"         # Business impact, risk level, no Oracle codes
    SENIOR_DBA = "SENIOR_DBA"   # Default: Error codes, patterns, direct style


# =============================================================================
# ANSWER MODE (HARD RULE 5 - ANSWER PRECISION MODE)
# =============================================================================

class AnswerMode(Enum):
    """
    [HARD RULE 5] Answer Precision Mode.
    
    If user explicitly says:
    - "Give only the number"
    - "Just the count"
    - "Number only"
    
    Then response MUST be:
    - A single integer
    - No units
    - No text
    - No formatting
    
    [X] 165,837 CRITICAL alerts exist.
    [OK] 165837
    """
    STRICT_NUMBER = "STRICT_NUMBER"   # Output ONLY integer digits
    YES_NO = "YES_NO"                 # Output ONLY Yes or No
    LIST_ONLY = "LIST_ONLY"           # No commentary outside list
    SUMMARY = "SUMMARY"               # Max 5 bullets
    ANALYSIS = "ANALYSIS"             # Full reasoning
    EXECUTIVE = "EXECUTIVE"           # Manager mode
    SENIOR_DBA = "SENIOR_DBA"         # Technical DBA mode (default)
    
    # Keep backward compatibility
    STRICT_VALUE = "STRICT_NUMBER"
    SHORT_FACT = "SUMMARY"


class AnswerModeDetector:
    """
    [HARD RULE 5] Detects answer precision mode from question.
    
    STRICT TRIGGERS:
    - "Give only the number" -> STRICT_NUMBER (output ONLY digits)
    - "Just the count" -> STRICT_NUMBER
    - "Number only" -> STRICT_NUMBER
    
    Response format for STRICT_NUMBER:
    [X] 165,837 CRITICAL alerts exist.
    [OK] 165837 (just the integer, no commas, no text)
    """
    
    # STRICT_NUMBER triggers - output ONLY digits
    STRICT_NUMBER_PATTERNS = [
        r'give\s+(?:me\s+)?only\s+(?:the\s+)?number',
        r'only\s+(?:the\s+)?(?:number|count|total)',
        r'just\s+(?:the\s+)?(?:number|count|total)',
        r'number\s+only',
        r'count\s+only',
        r'how\s+many\s+\w+\s+alerts',
        r'how\s+many\s+alerts',
        r'^how\s+many\b',
        r'exact\s+count',
        r'total\s+(?:number|count)\s+of',
        r'count\s+of\s+\w+\s+alerts',
    ]
    
    # YES_NO triggers - output ONLY Yes or No
    YES_NO_PATTERNS = [
        r'yes\s+or\s+no\??',
        r'yes/no',
        r'^is\s+there\s+(?:a|an|any)\b',
        r'^are\s+there\s+(?:any|multiple)\b',
        r'^does\s+(?:the\s+)?(?:database|db)\b',
        r'^is\s+(?:the\s+)?(?:database|db)\b',
        r'^can\s+(?:you|we)\s+confirm',
        r'^confirm\s+(?:if|whether)',
    ]
    
    # LIST_ONLY triggers - no commentary outside list
    LIST_ONLY_PATTERNS = [
        r'list\s+(?:all\s+)?(?:the\s+)?',
        r'show\s+(?:me\s+)?(?:all\s+)?(?:the\s+)?',
        r'give\s+(?:me\s+)?(?:a\s+)?list',
        r'which\s+(?:databases?|alerts?|errors?)',
        r'what\s+(?:databases?|alerts?)\s+(?:are|have)',
    ]
    
    # SUMMARY triggers - max 5 bullets
    SUMMARY_PATTERNS = [
        r'summar(?:y|ize)',
        r'brief(?:ly)?',
        r'quick\s+overview',
        r'key\s+points',
        r'main\s+(?:issues?|points?|findings?)',
        r'top\s+\d+',
    ]
    
    # ANALYSIS triggers - detailed reasoning
    ANALYSIS_PATTERNS = [
        r'why\s+(?:is|are|did)',
        r'explain\s+(?:the\s+)?(?:root\s+cause|reason|issue)',
        r'analyze\s+(?:the\s+)?',
        r'noise\s+(?:vs\.?|versus)\s+signal',
        r'root\s+cause',
        r'what\s+(?:is|are)\s+causing',
        r'diagnose',
        r'breakdown\s+of\s+(?:the\s+)?',
        r'incident\s+(?:analysis|intelligence)',
    ]
    
    # EXECUTIVE/MANAGER triggers - non-technical
    EXECUTIVE_PATTERNS = [
        r'explain\s+(?:this\s+)?to\s+(?:my\s+)?manager',
        r'executive\s+summary',
        r'business\s+impact',
        r'non[- ]?technical',
        r'for\s+(?:the\s+)?management',
        r'in\s+simple\s+terms',
        r'layman',
        r'manager\s+mode',
    ]
    
    # SENIOR_DBA triggers - technical, concise
    SENIOR_DBA_PATTERNS = [
        r'ora[- ]?\d+',
        r'technical\s+detail',
        r'deep\s+dive',
        r'diagnostic',
        r'dba\s+(?:perspective|mode)',
        r'what\s+(?:would|should)\s+(?:you|i|we)\s+check',
        r'senior\s+dba',
        r'error\s+codes?',
    ]
    
    @classmethod
    def detect_mode(cls, question: str) -> AnswerMode:
        """
        Detect the answer mode for a question.
        
        Priority Order (STRICT):
        1. STRICT_NUMBER (absolute precedence)
        2. YES_NO
        3. LIST_ONLY
        4. SUMMARY
        5. EXECUTIVE
        6. ANALYSIS
        7. SENIOR_DBA (default for DBA queries)
        """
        q_lower = question.lower().strip()
        
        # 1. STRICT_NUMBER takes absolute precedence
        for pattern in cls.STRICT_NUMBER_PATTERNS:
            if re.search(pattern, q_lower):
                return AnswerMode.STRICT_NUMBER
        
        # 2. YES_NO questions
        for pattern in cls.YES_NO_PATTERNS:
            if re.search(pattern, q_lower):
                return AnswerMode.YES_NO
        
        # 3. LIST_ONLY requests
        for pattern in cls.LIST_ONLY_PATTERNS:
            if re.search(pattern, q_lower):
                return AnswerMode.LIST_ONLY
        
        # 4. SUMMARY requests
        for pattern in cls.SUMMARY_PATTERNS:
            if re.search(pattern, q_lower):
                return AnswerMode.SUMMARY
        
        # 5. EXECUTIVE/Manager mode
        for pattern in cls.EXECUTIVE_PATTERNS:
            if re.search(pattern, q_lower):
                return AnswerMode.EXECUTIVE
        
        # 6. ANALYSIS mode
        for pattern in cls.ANALYSIS_PATTERNS:
            if re.search(pattern, q_lower):
                return AnswerMode.ANALYSIS
        
        # 7. SENIOR_DBA triggers
        for pattern in cls.SENIOR_DBA_PATTERNS:
            if re.search(pattern, q_lower):
                return AnswerMode.SENIOR_DBA
        
        # Default to SENIOR_DBA for DBA-focused queries
        return AnswerMode.SENIOR_DBA
    
    @classmethod
    def is_strict_value_mode(cls, question: str) -> bool:
        """Check if question requires strict value-only response."""
        mode = cls.detect_mode(question)
        return mode in (AnswerMode.STRICT_NUMBER, AnswerMode.YES_NO)
    
    @classmethod
    def is_yes_no_mode(cls, question: str) -> bool:
        """Check if question requires Yes/No response."""
        return cls.detect_mode(question) == AnswerMode.YES_NO


# =============================================================================
# SCOPE LOCK RULE (GUARDRAIL 1 - NON-NEGOTIABLE)
# =============================================================================

@dataclass
class ScopeConstraint:
    """
    Scope constraints extracted from question.
    
    SCOPE LOCK RULE:
    - Once scope is detected, DO NOT switch scope
    - DO NOT mix counts
    - DO NOT reuse environment totals for DB questions
    """
    target_database: Optional[str] = None
    scope_level: ScopeLevel = ScopeLevel.UNCLEAR
    primary_only: bool = False
    standby_only: bool = False
    exclude_standby: bool = False
    is_hard_scope: bool = False  # True if "only" keyword used
    scope_keywords: List[str] = field(default_factory=list)
    needs_clarification: bool = False  # True if scope is ambiguous


class ScopeControlGuard:
    """
    QUESTION SCOPE RESOLUTION (RULE 2 - CRITICAL)
    
    Before answering, you MUST determine scope:
    
    If user asks              Scope
    "for MIDEVSTB"           Database-specific
    "this DB", "that DB"     Use last referenced DB
    "environment", "total"   Environment-wide
    Ambiguous follow-up      ASK clarification
    
    RULE:
    If scope is ambiguous, DO NOT ANSWER.
    Ask: "Do you want this for MIDEVSTB or for the entire environment?"
    """
    
    # Scope clarification request template
    SCOPE_CLARIFICATION_REQUEST = (
        "Do you want this for {db} or for the entire environment?"
    )
    
    # Environment-wide indicators
    ENVIRONMENT_INDICATORS = [
        'environment', 'overall', 'total', 'all databases', 'entire',
        'across all', 'whole system', 'globally'
    ]
    
    # Hard scope keywords
    HARD_SCOPE_KEYWORDS = [
        'only', 'exclusively', 'specifically', 'do not include', 
        'exclude', 'without', 'just the', 'just for'
    ]
    
    # Primary database indicators
    PRIMARY_INDICATORS = ['primary', 'main', 'prod', 'production']
    
    # Standby database indicators  
    STANDBY_INDICATORS = ['standby', 'stbn', 'replica', 'dr', 'secondary']
    
    # Known primary-standby relationships
    DB_RELATIONSHIPS = {
        "MIDEVSTB": "MIDEVSTBN",
        "PRODDB": "PRODDB_STANDBY",
        "FINDB": "FINDB_DR",
    }
    
    @classmethod
    def extract_scope(cls, question: str, last_database: str = None) -> ScopeConstraint:
        """
        Extract scope constraints from question.
        
        Args:
            question: The user's question
            last_database: Last referenced database from context
        
        Returns:
            ScopeConstraint with all detected constraints
        """
        q_lower = question.lower()
        q_upper = question.upper()
        
        # Detect target database
        target_db = cls._extract_target_database(question)
        
        # Check for environment-wide indicators
        is_environment = any(ind in q_lower for ind in cls.ENVIRONMENT_INDICATORS)
        
        # Handle "this DB", "that DB" references
        if not target_db and ('this db' in q_lower or 'that db' in q_lower or 
                              'this database' in q_lower or 'that database' in q_lower):
            if last_database:
                target_db = last_database
            else:
                # Need clarification
                return ScopeConstraint(
                    scope_level=ScopeLevel.UNCLEAR,
                    needs_clarification=True
                )
        
        # Detect hard scope keywords
        scope_keywords = [kw for kw in cls.HARD_SCOPE_KEYWORDS if kw in q_lower]
        is_hard_scope = len(scope_keywords) > 0
        
        # Determine scope level
        if target_db:
            scope_level = ScopeLevel.DATABASE
        elif is_environment:
            scope_level = ScopeLevel.ENVIRONMENT
        else:
            # Ambiguous - may need clarification
            scope_level = ScopeLevel.UNCLEAR if not last_database else ScopeLevel.DATABASE
        
        # Detect primary/standby scope
        primary_only = any(ind in q_lower for ind in 
                         ['primary only', 'exclude standby', 'not standby', 
                          'without standby', 'no standby'])
        
        standby_only = any(ind in q_lower for ind in 
                          ['standby only', 'only standby'])
        
        # If target database ends with STB (not STBN), default to excluding standby
        exclude_standby = False
        if target_db:
            if target_db.upper().endswith('STB') and not target_db.upper().endswith('STBN'):
                # User asked about primary, exclude standby unless explicitly included
                if 'standby' not in q_lower and 'stbn' not in q_lower:
                    exclude_standby = True
        
        return ScopeConstraint(
            target_database=target_db or last_database,
            scope_level=scope_level,
            primary_only=primary_only,
            standby_only=standby_only,
            exclude_standby=exclude_standby or primary_only,
            is_hard_scope=is_hard_scope,
            scope_keywords=scope_keywords,
            needs_clarification=(scope_level == ScopeLevel.UNCLEAR and not last_database)
        )
    
    @classmethod
    def get_clarification_request(cls, possible_db: str = None) -> str:
        """Get clarification request for ambiguous scope."""
        if possible_db:
            return cls.SCOPE_CLARIFICATION_REQUEST.format(db=possible_db)
        return "Do you want this for a specific database or for the entire environment?"
    
    @classmethod
    def _extract_target_database(cls, question: str) -> Optional[str]:
        """Extract target database name from question."""
        patterns = [
            r'for\s+([A-Z][A-Z0-9_]+(?:STB|STBN|DB)?)\b',
            r'on\s+([A-Z][A-Z0-9_]+(?:STB|STBN|DB)?)\b',
            r'in\s+([A-Z][A-Z0-9_]+(?:STB|STBN|DB)?)\b',
            r'\b([A-Z][A-Z0-9_]*(?:STB|STBN))\b',
            r'\b([A-Z]{3,}[A-Z0-9_]*DB)\b',
        ]
        
        # Excluded words that look like DB names
        excluded = {'THE', 'ALL', 'ANY', 'MANY', 'WHAT', 'WHICH', 'THIS', 'THAT',
                   'ALERTS', 'CRITICAL', 'DATABASE', 'STATUS', 'WHERE', 'WHEN',
                   'WHY', 'SHOW', 'GIVE', 'NUMBER', 'COUNT', 'WARNING', 'ONLY'}
        
        for pattern in patterns:
            match = re.search(pattern, question.upper())
            if match:
                db_name = match.group(1)
                if db_name not in excluded and len(db_name) >= 4:
                    return db_name
        
        return None
    
    @classmethod
    def validate_response_scope(cls, response: str, scope: ScopeConstraint) -> Tuple[bool, List[str]]:
        """
        Validate that response respects scope constraints.
        
        Returns:
            Tuple of (is_valid, list of violations)
        """
        violations = []
        response_upper = response.upper()
        
        if not scope.target_database:
            return True, []  # No database scope to enforce
        
        target = scope.target_database.upper()
        
        # Check for standby leakage when excluded
        if scope.exclude_standby or scope.primary_only:
            # Get the standby name for this database
            standby_name = cls.DB_RELATIONSHIPS.get(target, f"{target}N")
            
            if standby_name.upper() in response_upper:
                violations.append(
                    f"SCOPE VIOLATION: Standby ({standby_name}) data included when excluded"
                )
        
        # Check for environment totals when database-specific
        if scope.is_hard_scope:
            if 'ENVIRONMENT' in response_upper or 'ALL DATABASES' in response_upper:
                violations.append(
                    f"SCOPE VIOLATION: Environment-wide data shown for {target}-specific query"
                )
        
        return len(violations) == 0, violations
    
    @classmethod
    def filter_data_by_scope(cls, data: List[Dict], scope: ScopeConstraint) -> List[Dict]:
        """
        Filter data records to match scope constraints.
        
        CRITICAL: Uses EXACT match, not substring match.
        """
        if not scope.target_database:
            return data
        
        target = scope.target_database.upper()
        standby_name = cls.DB_RELATIONSHIPS.get(target, f"{target}N").upper()
        
        filtered = []
        for record in data:
            db_name = (record.get('target') or record.get('target_name') or 
                      record.get('database') or '').upper()
            
            # EXACT match required, not substring
            if db_name == target:
                filtered.append(record)
            elif not scope.exclude_standby and db_name == standby_name:
                filtered.append(record)
        
        return filtered


# =============================================================================
# GUARDRAIL 3: PREDICTIVE REASONING SAFETY (HARD RULE 2 - LOCKED)
# =============================================================================

class PredictiveReasoningSafety:
    """
    [HARD RULE 2] PREDICTIVE CONFIDENCE GUARDRAILS
    
    You may analyze patterns, but you MUST NOT overstate certainty.
    
    Confidence Levels Allowed:
        HIGH: Direct count, exact aggregation
        MEDIUM: Pattern inference, clustering, prediction
        LOW: Insufficient data
    
    [X] FORBIDDEN PHRASES (unless proven by historical metrics):
        - "Confirmed root cause"
        - "Will escalate"  
        - "Guaranteed outage"
        - "High confidence prediction"
    
    [OK] REQUIRED PHRASES FOR PREDICTION:
        - "based on alert patterns"
        - "from available data only"
        - "this is an inference, not a certainty"
    
    EXAMPLE:
        "Based on repeated alert patterns and frequency, this issue may escalate.
         Confidence: MEDIUM (pattern-based, not time-series validated)."
    """
    
    # MANDATORY DISCLAIMER (HARD RULE 2)
    PREDICTIVE_DISCLAIMER = (
        "based on alert patterns, not deep system metrics. "
        "This is an inference, not a certainty."
    )
    
    # Confidence suffix format
    CONFIDENCE_SUFFIX = "Confidence: {level} (pattern-based, not time-series validated)."
    
    # Absolutely forbidden phrases (HARD RULE 2)
    FORBIDDEN_PHRASES = [
        r'\bconfirmed\s+root\s+cause\b',
        r'\bwill\s+escalate\b',
        r'\bguaranteed\s+outage\b',
        r'\bhigh\s+confidence\s+prediction\b',
        r'\bwill\s+fail\b',
        r'\bwill\s+crash\b',
        r'\bwill\s+definitely\b',
        r'\bguaranteed\b',
        r'\bcertain\s+to\b',
        r'\binevitable\b',
        r'100\s*%',  # 100% with optional space
        r'\babsolutely\s+will\b',
        r'\bwill\s+certainly\b',
        r'\bcertainly\s+will\b',
        r'\bwithout\s+(?:a\s+)?doubt\b',
        r'\bfor\s+sure\b',
        r'\bwill\s+cause\s+(?:an?\s+)?outage\b',
        r'\bpredicted?\s+(?:to\s+)?fail\b',
    ]
    
    # Safe replacement phrases (ALLOWED PHRASING)
    SAFE_REPLACEMENTS = {
        r'\bconfirmed\s+root\s+cause\b': "probable root cause (inferred)",
        r'\bwill\s+escalate\b': "may escalate",
        r'\bguaranteed\s+outage\b': "potential availability risk",
        r'\bhigh\s+confidence\s+prediction\b': "pattern-based assessment",
        r'\bwill\s+fail\b': "shows higher risk",
        r'\bwill\s+crash\b': "requires attention", 
        r'\bwill\s+definitely\b': "may potentially",
        r'\bguaranteed\b': "possible",
        r'\bcertain\s+to\b': "may potentially",
        r'\binevitable\b': "elevated risk",
        r'100\s*%': "higher probability",
        r'\bcertainly\s+will\b': "may potentially",
        r'\bwill\s+cause\s+outage\b': "could impact availability",
    }
    
    # Required qualifier phrases for predictions (HARD RULE 2)
    REQUIRED_QUALIFIERS = [
        "based on alert patterns",
        "from available data only",
        "this is an inference, not a certainty",
        "based on repeated alert patterns",
        "pattern-based",
    ]
    
    @classmethod
    def check_prediction_safety(cls, text: str) -> Tuple[bool, List[str]]:
        """
        Check if prediction text is safe (no forbidden phrases).
        
        Returns:
            Tuple of (is_safe, list of violations)
        """
        violations = []
        text_lower = text.lower()
        
        for pattern in cls.FORBIDDEN_PHRASES:
            if re.search(pattern, text_lower):
                violations.append(f"Forbidden phrase detected: {pattern}")
        
        return len(violations) == 0, violations
    
    @classmethod
    def sanitize_prediction(cls, text: str) -> str:
        """Replace forbidden phrases with safe alternatives."""
        result = text
        
        for pattern, replacement in cls.SAFE_REPLACEMENTS.items():
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        return result
    
    @classmethod
    def add_predictive_disclaimer(cls, response: str) -> str:
        """Add the mandatory predictive disclaimer."""
        if cls.PREDICTIVE_DISCLAIMER in response:
            return response
        return f"{response}\n\n{cls.PREDICTIVE_DISCLAIMER}"
    
    @classmethod
    def format_safe_prediction(cls, prediction: str, database: str = None,
                               confidence: str = "LOW") -> str:
        """
        Format a prediction with all required safety language.
        
        For question "Which DB will fail next?", this formats:
        "Based on alert patterns only (not system health metrics), 
         the database requiring most attention is X."
        """
        # Sanitize the prediction text first
        safe_prediction = cls.sanitize_prediction(prediction)
        
        # Build the safe response
        lines = [
            "**Based on alert patterns only:**",
            "",
            safe_prediction,
            "",
            f"**Confidence Level:** {confidence}",
            "",
            cls.PREDICTIVE_DISCLAIMER,
        ]
        
        lines.extend([
            "",
            "*This is a risk indicator based on alert patterns, not a failure prediction.*"
        ])
        
        return "\n".join(lines)


# =============================================================================
# GUARDRAIL 4: NO-DATA / LOW-DATA HANDLING
# =============================================================================

class NoDataHandler:
    """
    Proper handling when required data is missing.
    
    RULES:
    - Say "Cannot determine from available data"
    - Explain WHY (missing timestamps, patch data, metrics)
    - Suggest WHAT DATA is needed
    - NEVER fabricate trends
    - NEVER assume timelines
    """
    
    @staticmethod
    def cannot_determine(reason: str, data_needed: str = None) -> str:
        """
        Format a proper "cannot determine" response.
        
        Args:
            reason: Why the data cannot be determined
            data_needed: What data would be needed
            
        Returns:
            Properly formatted cannot-determine response
        """
        response = f"**Cannot determine from available data.**\n\n**Reason:** {reason}"
        
        if data_needed:
            response += f"\n\n**Data needed:** {data_needed}"
        
        return response
    
    @staticmethod
    def low_confidence_response(answer: str, reason: str) -> str:
        """
        Format a low-confidence response with appropriate caveats.
        """
        return (
            f"**[WARNING] Low Confidence Answer:**\n\n"
            f"{answer}\n\n"
            f"*Note: {reason}. Verify with direct system inspection.*"
        )
    
    @classmethod
    def check_data_availability(cls, data: List[Dict], 
                                required_fields: List[str] = None) -> Tuple[bool, str]:
        """
        Check if sufficient data is available to answer.
        
        Returns:
            Tuple of (has_sufficient_data, reason if not)
        """
        if not data:
            return False, "No data available for the requested scope"
        
        if required_fields:
            missing = []
            for field in required_fields:
                if not any(field in record for record in data):
                    missing.append(field)
            
            if missing:
                return False, f"Missing required data fields: {', '.join(missing)}"
        
        return True, ""


# =============================================================================
# GUARDRAIL 5: ANTI-OVEREXPLANATION RULE
# =============================================================================

class AntiOverexplanation:
    """
    Matches answer length to question intent.
    
    EXAMPLES:
    - Question: "How many CRITICAL alerts?" 
      [X] No incident analysis
      [X] No executive summary
      [OK] Just the number
      
    - Question: "Explain why alerts are repeating"
      [OK] Root cause + OEM behavior explanation
    """
    
    # Question types that require minimal response
    MINIMAL_RESPONSE_PATTERNS = [
        r'^how\s+many\b',
        r'^what\s+is\s+the\s+(?:count|number|total)\b',
        r'^count\s+(?:of|the)\b',
        r'^is\s+there\s+(?:a|an|any)\b',
        r'^are\s+there\s+(?:any|multiple)\b',
        r'^which\s+(?:database|db|system)\b',
        r'^what\s+(?:database|db)\s+has\b',
    ]
    
    # Question types that allow detailed response
    DETAILED_RESPONSE_PATTERNS = [
        r'\bexplain\b',
        r'\bwhy\b',
        r'\banalyze\b',
        r'\broot\s+cause\b',
        r'\bbreakdown\b',
        r'\bdiagnose\b',
        r'\bwhat\s+(?:is|are)\s+causing\b',
        r'\bdescribe\b',
    ]
    
    @classmethod
    def get_max_response_length(cls, question: str, mode: AnswerMode) -> int:
        """
        Get maximum appropriate response length for question.
        
        Returns:
            Max characters for response
        """
        if mode == AnswerMode.STRICT_VALUE:
            return 50  # Just a number or short value
        
        q_lower = question.lower()
        
        # Minimal response questions
        for pattern in cls.MINIMAL_RESPONSE_PATTERNS:
            if re.search(pattern, q_lower):
                return 200  # 1-2 sentences max
        
        # Detailed response allowed
        for pattern in cls.DETAILED_RESPONSE_PATTERNS:
            if re.search(pattern, q_lower):
                return 2000  # Allow detailed explanation
        
        # Default moderate length
        return 800
    
    @classmethod
    def check_response_length(cls, response: str, question: str, 
                              mode: AnswerMode) -> Tuple[bool, Optional[str]]:
        """
        Check if response length is appropriate for question.
        
        Returns:
            Tuple of (is_appropriate, warning if not)
        """
        max_length = cls.get_max_response_length(question, mode)
        actual_length = len(response)
        
        if actual_length > max_length * 1.5:  # Allow 50% buffer
            return False, f"Response ({actual_length} chars) exceeds appropriate length ({max_length} chars) for question type"
        
        return True, None


# =============================================================================
# GUARDRAIL 6: CONSISTENCY CHECK
# =============================================================================

@dataclass
class AnswerFact:
    """A fact that was stated in an answer."""
    fact_type: str  # "count", "database", "status", etc.
    value: Any
    scope: str
    question: str
    timestamp: str


class ConsistencyChecker:
    """
    Ensures numeric and factual consistency within and across answers.
    
    RULES:
    - Re-check numbers against previous answers before final output
    - If mismatch -> recompute
    - Never output conflicting counts in same answer
    """
    
    def __init__(self):
        self._facts: Dict[str, AnswerFact] = {}
        self._corrections: List[Tuple[str, Any, Any]] = []
    
    def register_fact(self, fact_type: str, key: str, value: Any, 
                     scope: str, question: str):
        """Register a fact from an answer."""
        fact_key = f"{fact_type}:{key}:{scope}"
        self._facts[fact_key] = AnswerFact(
            fact_type=fact_type,
            value=value,
            scope=scope,
            question=question,
            timestamp=str(__import__('datetime').datetime.now())
        )
    
    def check_consistency(self, fact_type: str, key: str, value: Any, 
                         scope: str) -> Tuple[bool, Optional[Any]]:
        """
        Check if a new value is consistent with previously stated facts.
        
        Returns:
            Tuple of (is_consistent, previous_value if inconsistent)
        """
        fact_key = f"{fact_type}:{key}:{scope}"
        
        if fact_key in self._facts:
            existing = self._facts[fact_key]
            
            # Numeric comparison
            if isinstance(existing.value, (int, float)) and isinstance(value, (int, float)):
                if existing.value != value:
                    return False, existing.value
            elif existing.value != value:
                return False, existing.value
        
        return True, None
    
    def check_internal_consistency(self, response: str) -> Tuple[bool, List[str]]:
        """
        Check for internal inconsistencies within a single response.
        
        Returns:
            Tuple of (is_consistent, list of issues)
        """
        issues = []
        
        # Extract all numbers from response
        numbers = re.findall(r'\b(\d+)\s+(?:CRITICAL|WARNING|alerts?|incidents?)\b', 
                            response, re.IGNORECASE)
        
        # Check for duplicated counts with different values
        # e.g., "5 CRITICAL alerts" and "3 CRITICAL alerts" in same response
        count_map = {}
        for match in re.finditer(r'\b(\d+)\s+(CRITICAL|WARNING)\s+alerts?\b', 
                                response, re.IGNORECASE):
            count = match.group(1)
            alert_type = match.group(2).upper()
            
            if alert_type in count_map and count_map[alert_type] != count:
                issues.append(
                    f"Conflicting {alert_type} counts in response: {count_map[alert_type]} vs {count}"
                )
            count_map[alert_type] = count
        
        return len(issues) == 0, issues
    
    def reset(self):
        """Reset for new conversation."""
        self._facts.clear()
        self._corrections.clear()


# =============================================================================
# GUARDRAIL 7: PRODUCTION-SAFE RESPONSE RULE
# =============================================================================

class ProductionSafeResponse:
    """
    Ensures all responses are appropriate for production DBA usage.
    
    MUST:
    - Avoid panic language
    - Avoid guarantees
    - Avoid commands unless explicitly asked
    - Clearly separate: Facts, Inference, Recommendations
    """
    
    # Panic phrases to avoid
    PANIC_PHRASES = [
        "critical failure", "catastrophic", "disaster", "emergency",
        "panic", "urgent action required", "immediately stop",
        "system down", "complete failure", "total loss", 
        "cannot recover", "worst case", "dead", "crashed beyond repair",
        "crashed", "completely crashed"
    ]
    
    # Calm replacements
    CALM_REPLACEMENTS = {
        "critical failure": "significant issue requiring attention",
        "catastrophic": "serious",
        "disaster": "significant incident",
        "emergency": "priority situation",
        "panic": "concern",
        "urgent action required": "prompt attention recommended",
        "system down": "system unavailable",
        "complete failure": "service interruption",
        "cannot recover": "recovery options are limited",
        "worst case": "more serious scenario",
        "dead": "unresponsive",
        "completely crashed": "experienced an unexpected stop",
        "crashed": "stopped unexpectedly",
    }
    
    # Command patterns to flag
    COMMAND_PATTERNS = [
        r'^\s*SELECT\s+',
        r'^\s*UPDATE\s+',
        r'^\s*DELETE\s+',
        r'^\s*ALTER\s+',
        r'^\s*DROP\s+',
        r'^\s*sqlplus\s+',
        r'^\s*rman\s+',
    ]
    
    @classmethod
    def check_production_safety(cls, response: str) -> Tuple[bool, List[str]]:
        """
        Check if response is safe for production use.
        
        Returns:
            Tuple of (is_safe, list of issues)
        """
        issues = []
        response_lower = response.lower()
        
        # Check for panic language
        for phrase in cls.PANIC_PHRASES:
            if phrase in response_lower:
                issues.append(f"Panic language detected: '{phrase}'")
        
        # Check for unsolicited commands
        for pattern in cls.COMMAND_PATTERNS:
            if re.search(pattern, response, re.IGNORECASE | re.MULTILINE):
                issues.append("SQL/command found in response (not explicitly requested)")
        
        return len(issues) == 0, issues
    
    @classmethod
    def calm_down_text(cls, text: str) -> str:
        """Replace panic phrases with calmer alternatives."""
        result = text
        
        for panic, calm in cls.CALM_REPLACEMENTS.items():
            pattern = re.compile(re.escape(panic), re.IGNORECASE)
            result = pattern.sub(calm, result)
        
        return result
    
    @classmethod
    def format_structured_response(cls, facts: List[str], 
                                   inferences: List[str] = None,
                                   recommendations: List[str] = None) -> str:
        """
        Format response with clear separation of facts, inference, recommendations.
        """
        lines = []
        
        if facts:
            lines.append("**Facts (from data):**")
            for fact in facts:
                lines.append(f"- {fact}")
            lines.append("")
        
        if inferences:
            lines.append("**Inference (analysis):**")
            for inf in inferences:
                lines.append(f"- {inf}")
            lines.append("")
        
        if recommendations:
            lines.append("**Recommendations:**")
            for rec in recommendations:
                lines.append(f"- {rec}")
        
        return "\n".join(lines)


# =============================================================================
# PRODUCTION SAFETY RULES (RULE 7 - NON-NEGOTIABLE)
# =============================================================================

class ProductionSafetyRules:
    """
    [SHIELD] GUARANTEE & ACTION REQUEST HANDLING (RULE 7)
    
    If user asks:
    - "Guarantee this won't cause outage"
    - "Run a query to fix this"
    
    You MUST respond:
    "I cannot guarantee outcomes or execute fixes. I can suggest safe 
     investigation steps."
    
    You may suggest:
    - Reviewing logs
    - Escalation
    - RCA steps
    
    [X] Never provide SQL unless explicitly requested AND data supports it.
    """
    
    # MANDATORY RESPONSE for guarantee/fix requests
    SAFETY_DISCLAIMER = (
        "I cannot guarantee outcomes or execute fixes. "
        "I can suggest safe investigation steps."
    )
    
    # Absolutely forbidden phrases in responses
    FORBIDDEN_PHRASES = [
        r'run\s+this\s+(?:query|command|script)\s+to\s+fix',
        r'this\s+will\s+(?:not\s+)?cause\s+(?:an?\s+)?outage',
        r'guaranteed\s+(?:resolution|fix|solution)',
        r'this\s+definitely\s+means',
        r'will\s+definitely\s+(?:fix|resolve|work)',
        r'100%\s+(?:fix|resolution|solution)',
        r'guaranteed\s+to\s+work',
        r'will\s+certainly\s+(?:fix|resolve)',
        r'execute\s+this\s+to\s+(?:fix|resolve)',
        r'run\s+(?:this|the\s+following)\s+(?:to\s+)?(?:fix|resolve)',
        r'this\s+will\s+fix\s+',
    ]
    
    # Patterns that trigger mandatory disclaimer
    FIX_REQUEST_PATTERNS = [
        r'how\s+(?:do\s+i|can\s+i|to)\s+fix',
        r'fix\s+(?:this|it|the)',
        r'resolve\s+(?:this|it|the)',
        r'what\s+(?:command|query|script)\s+(?:to|should)',
        r'run\s+(?:a\s+)?(?:command|query)',
        r'give\s+(?:me\s+)?(?:a\s+)?(?:query|command|script)',
    ]
    
    # Guarantee request patterns
    GUARANTEE_REQUEST_PATTERNS = [
        r'will\s+this\s+(?:fix|work|resolve)',
        r'guarantee\s+(?:that|this|it)',
        r'(?:is|are)\s+(?:you\s+)?sure',
        r'can\s+you\s+guarantee',
        r'promise\s+(?:that|this|me)',
        r"won'?t\s+(?:this\s+)?cause\s+(?:an?\s+)?outage",
    ]
    
    # Safe suggestions that ARE allowed
    SAFE_SUGGESTIONS = [
        "Review the Oracle trace files for detailed stack trace",
        "Check AWR reports for the timeframe of the errors",
        "Escalate to Oracle Support with incident details",
        "Review alert log for additional context",
        "Verify tablespace space and memory allocation",
    ]
    
    @classmethod
    def check_for_forbidden_claims(cls, response: str) -> Tuple[bool, List[str]]:
        """Check if response contains forbidden claims."""
        violations = []
        response_lower = response.lower()
        
        for pattern in cls.FORBIDDEN_PHRASES:
            if re.search(pattern, response_lower):
                violations.append(f"Forbidden claim detected: {pattern}")
        
        return len(violations) == 0, violations
    
    @classmethod
    def needs_safety_disclaimer(cls, question: str) -> bool:
        """Check if question requires safety disclaimer."""
        q_lower = question.lower()
        
        for pattern in cls.FIX_REQUEST_PATTERNS:
            if re.search(pattern, q_lower):
                return True
        
        for pattern in cls.GUARANTEE_REQUEST_PATTERNS:
            if re.search(pattern, q_lower):
                return True
        
        return False
    
    @classmethod
    def add_safety_disclaimer(cls, response: str) -> str:
        """Add safety disclaimer to response."""
        if cls.SAFETY_DISCLAIMER in response:
            return response
        return f"{cls.SAFETY_DISCLAIMER}\n\n{response}"
    
    @classmethod
    def get_safe_investigation_steps(cls) -> List[str]:
        """Return safe investigation steps that can be suggested."""
        return cls.SAFE_SUGGESTIONS.copy()


# =============================================================================
# DATA AUTHORITY RULE
# =============================================================================

class DataAuthorityRule:
    """
    [3] DATA AUTHORITY RULE
    
    You may ONLY use:
    - Alert counts
    - Alert patterns
    - Error frequency
    - Historical repetition in given data
    
    If data is missing:
    "Data not available in current dataset."
    
    [NO] No assumptions
    [NO] No inferred metrics (unless explicitly allowed)
    """
    
    # Allowed data sources
    ALLOWED_DATA_TYPES = [
        "alert_count",
        "alert_pattern",
        "error_frequency",
        "historical_repetition",
        "severity_distribution",
        "target_distribution",
        "timestamp_pattern",
    ]
    
    # Phrases indicating assumption/speculation
    ASSUMPTION_PHRASES = [
        r'\bi\s+(?:think|believe|assume|suppose)',
        r'\bprobably\s+means',
        r'\blikely\s+(?:that|the)',
        r'\bseems\s+(?:like|to\s+be)',
        r'\bappears\s+to\s+(?:be|have)',
        r'\bmight\s+(?:be|have|indicate)',
        r'\bcould\s+(?:be|have|mean)',
    ]
    
    # Missing data response
    MISSING_DATA_RESPONSE = "Data not available in current dataset."
    
    @classmethod
    def check_data_authority(cls, response: str) -> Tuple[bool, List[str]]:
        """Check if response stays within data authority."""
        warnings = []
        response_lower = response.lower()
        
        for pattern in cls.ASSUMPTION_PHRASES:
            if re.search(pattern, response_lower):
                warnings.append(f"Possible assumption detected: {pattern}")
        
        return len(warnings) == 0, warnings
    
    @classmethod
    def format_missing_data_response(cls, what_is_missing: str) -> str:
        """Format response when data is missing."""
        return f"{cls.MISSING_DATA_RESPONSE}\n\n**Missing:** {what_is_missing}"


# =============================================================================
# INCIDENT vs ALERT INTELLIGENCE (RULE 4 - STRICT LOGIC)
# =============================================================================

class IncidentAlertIntelligence:
    """
    [CYCLE] INCIDENT vs ALERT INTELLIGENCE (RULE 4)
    
    You MUST always distinguish:
    - Alerts = raw repeated messages
    - Incidents = unique underlying issues
    
    When explaining, EXPLICITLY say whether talking about alerts or incidents.
    
    Example: "165,837 alerts correspond to 2 unique incidents."
    
    NEVER mix the two.
    """
    
    @classmethod
    def format_alert_incident_distinction(cls, alert_count: int, 
                                          incident_count: int,
                                          include_explanation: bool = True) -> str:
        """Format the alert vs incident distinction."""
        if incident_count == 0:
            return f"{alert_count:,} alerts (unique incidents not yet computed)"
        
        msg = f"{alert_count:,} alerts correspond to {incident_count} unique incident"
        if incident_count > 1:
            msg += "s"
        msg += "."
        
        if include_explanation and alert_count > incident_count * 10:
            msg += " (Many alerts are repeated symptoms of the same underlying issues.)"
        
        return msg
    
    @classmethod
    def validate_response_distinction(cls, response: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that response properly distinguishes alerts from incidents.
        
        Returns:
            Tuple of (is_valid, warning_message)
        """
        has_alert_count = bool(re.search(r'\d+[,\d]*\s*alerts?', response.lower()))
        has_incident_count = bool(re.search(r'\d+[,\d]*\s*incidents?', response.lower()))
        
        # If both mentioned, check they're distinguished
        if has_alert_count and has_incident_count:
            return True, None
        
        # If only alerts mentioned with large number, warn
        if has_alert_count:
            match = re.search(r'(\d+[,\d]*)\s*alerts?', response.lower())
            if match:
                count = int(match.group(1).replace(',', ''))
                if count > 100:
                    return False, "Consider clarifying how many unique incidents these alerts represent."
        
        return True, None


# =============================================================================
# INCIDENT INTELLIGENCE LOGIC
# =============================================================================

class IncidentCountGuardrail:
    """
    [HARD RULE 3] UNIQUE INCIDENT COUNT GUARDRAIL
    
    When grouping alerts into incidents:
    
    [X] NEVER SAY:
        - "4 unique incidents" (absolute statement)
        
    [OK] ALWAYS SAY:
        - "4 distinct alert patterns detected"
        - "approximately"
        - "based on message similarity clustering"
    
    EXAMPLE FORMAT:
        "These alerts map to ~4 distinct alert patterns, based on message
         similarity and repetition. This is an approximation, not a
         confirmed incident count."
    """
    
    # Forbidden phrases for incident counts
    FORBIDDEN_INCIDENT_PHRASES = [
        r'\d+\s+unique\s+incidents?\b',
        r'\d+\s+confirmed\s+incidents?\b',
        r'\bexactly\s+\d+\s+incidents?\b',
        r'\bprecisely\s+\d+\s+incidents?\b',
    ]
    
    # Required qualifier words
    REQUIRED_QUALIFIERS = [
        'approximately', 'about', 'around', '~', 'roughly',
        'detected', 'patterns', 'clustering', 'similarity',
        'approximation', 'estimate', 'distinct'
    ]
    
    # Template for incident count response
    INCIDENT_COUNT_TEMPLATE = (
        "These alerts map to ~{count} distinct alert patterns, based on "
        "message similarity and repetition. This is an approximation, "
        "not a confirmed incident count."
    )
    
    @classmethod
    def format_incident_count(cls, count: int, database: str = None) -> str:
        """
        Format incident count with proper qualifiers.
        
        Args:
            count: The number of detected patterns
            database: Optional database name
            
        Returns:
            Properly qualified incident count statement
        """
        prefix = f"For {database}: " if database else ""
        return prefix + cls.INCIDENT_COUNT_TEMPLATE.format(count=count)
    
    @classmethod
    def check_incident_count_language(cls, response: str) -> Tuple[bool, List[str]]:
        """
        Check if response uses proper incident count language.
        
        Returns:
            Tuple of (is_compliant, list of violations)
        """
        violations = []
        response_lower = response.lower()
        
        # Check for forbidden phrases
        for pattern in cls.FORBIDDEN_INCIDENT_PHRASES:
            if re.search(pattern, response_lower):
                violations.append(f"Absolute incident count detected: {pattern}")
        
        # If response mentions incidents, check for qualifiers
        if 'incident' in response_lower:
            has_qualifier = any(q in response_lower for q in cls.REQUIRED_QUALIFIERS)
            if not has_qualifier and re.search(r'\d+\s+incidents?\b', response_lower):
                violations.append(
                    "Incident count without qualifier (need 'approximately', "
                    "'distinct patterns', etc.)"
                )
        
        return len(violations) == 0, violations
    
    @classmethod
    def fix_incident_language(cls, response: str) -> str:
        """Fix absolute incident statements to use proper qualifiers."""
        result = response
        
        # Replace "X unique incidents" with "~X distinct alert patterns"
        result = re.sub(
            r'(\d+)\s+unique\s+incidents?',
            r'~\1 distinct alert patterns',
            result,
            flags=re.IGNORECASE
        )
        
        # Replace "X confirmed incidents" with "approximately X incident patterns"
        result = re.sub(
            r'(\d+)\s+confirmed\s+incidents?',
            r'approximately \1 incident patterns detected',
            result,
            flags=re.IGNORECASE
        )
        
        return result


class SafeActionBoundaries:
    """
    [HARD RULE 6] SAFE ACTION BOUNDARIES
    
    You MUST NOT:
    - Run SQL
    - Restart databases
    - Guarantee outcomes
    
    Required response pattern:
        "I cannot execute fixes or guarantee outcomes. I can suggest safe
         investigation steps."
    """
    
    # Mandatory response for action requests
    ACTION_REFUSAL = (
        "I cannot execute fixes or guarantee outcomes. "
        "I can suggest safe investigation steps."
    )
    
    # Patterns that indicate action request
    ACTION_REQUEST_PATTERNS = [
        r'run\s+(?:this|a|the)\s+(?:sql|query|command|script)',
        r'execute\s+(?:this|a|the)',
        r'restart\s+(?:the\s+)?(?:database|db|instance|server)',
        r'kill\s+(?:the\s+)?(?:session|process)',
        r'stop\s+(?:the\s+)?(?:database|db|instance)',
        r'start\s+(?:the\s+)?(?:database|db|instance)',
        r'bounce\s+(?:the\s+)?(?:database|db)',
        r'shutdown\s+(?:the\s+)?',
        r'fix\s+(?:this|it)\s+(?:for\s+me|now)',
        r'apply\s+(?:this\s+)?(?:patch|fix)',
    ]
    
    # Guarantee request patterns
    GUARANTEE_PATTERNS = [
        r'guarantee\s+(?:this|that|it)',
        r'promise\s+(?:this|that|me)',
        r'ensure\s+(?:this|that|it)',
        r'make\s+sure\s+(?:this|that|it)',
        r"will\s+(?:this|it)\s+(?:definitely|certainly)",
        r"won'?t\s+(?:this|it)\s+cause",
    ]
    
    @classmethod
    def is_action_request(cls, question: str) -> bool:
        """Check if question is requesting an action."""
        q_lower = question.lower()
        
        for pattern in cls.ACTION_REQUEST_PATTERNS:
            if re.search(pattern, q_lower):
                return True
        
        return False
    
    @classmethod
    def is_guarantee_request(cls, question: str) -> bool:
        """Check if question is requesting a guarantee."""
        q_lower = question.lower()
        
        for pattern in cls.GUARANTEE_PATTERNS:
            if re.search(pattern, q_lower):
                return True
        
        return False
    
    @classmethod
    def needs_action_refusal(cls, question: str) -> bool:
        """Check if question needs action refusal response."""
        return cls.is_action_request(question) or cls.is_guarantee_request(question)
    
    @classmethod
    def get_safe_response(cls, question: str) -> str:
        """Get safe response for action/guarantee requests."""
        if cls.is_action_request(question):
            return (
                f"{cls.ACTION_REFUSAL}\n\n"
                "**Safe investigation steps I can suggest:**\n"
                "- Review alert patterns and frequency\n"
                "- Check Oracle trace files for detailed diagnostics\n"
                "- Review AWR reports for the timeframe\n"
                "- Escalate to Oracle Support if needed"
            )
        
        if cls.is_guarantee_request(question):
            return (
                f"{cls.ACTION_REFUSAL}\n\n"
                "Database behavior depends on many factors beyond alert patterns. "
                "I can only provide analysis based on available data."
            )
        
        return cls.ACTION_REFUSAL


# =============================================================================
# RULE 5: RISK & ESCALATION LANGUAGE
# =============================================================================

class RiskEscalationLanguage:
    """
    [RULE 5] RISK & ESCALATION LANGUAGE
    
    When asked: "Is this likely to escalate?" / "Will this cause outage?"
    
    Use this structure:
    - State current evidence
    - State uncertainty
    - State what data is missing
    
    Example:
        "Based on sustained alert volume and repetition, there is elevated risk.
         However, without AWR/ASH and system metrics, outage likelihood cannot
         be confirmed."
    """
    
    # Escalation question patterns
    ESCALATION_PATTERNS = [
        r'will\s+(?:this|it)\s+(?:escalate|get\s+worse|worsen)',
        r'(?:is|are)\s+(?:this|these)\s+likely\s+to\s+escalate',
        r'will\s+(?:this|it)\s+cause\s+(?:an?\s+)?outage',
        r'(?:is|are)\s+(?:this|these)\s+going\s+to\s+(?:fail|crash|go\s+down)',
        r'what\s+(?:is|are)\s+the\s+(?:risk|chance|probability)',
        r'(?:is|are)\s+(?:we|this)\s+at\s+risk',
        r'should\s+(?:I|we)\s+be\s+(?:worried|concerned)',
    ]
    
    # Required response structure components
    EVIDENCE_PREFIX = "Based on"
    UNCERTAINTY_PREFIX = "However, without"
    MISSING_DATA_EXAMPLES = [
        "AWR/ASH data",
        "system metrics",
        "historical baseline",
        "trace files",
        "OEM performance data"
    ]
    
    # Template for risk response
    RISK_RESPONSE_TEMPLATE = (
        "{evidence}\n\n"
        "However, without {missing_data}, {conclusion}."
    )
    
    @classmethod
    def is_escalation_question(cls, question: str) -> bool:
        """Check if question is asking about risk/escalation."""
        q_lower = question.lower()
        return any(re.search(p, q_lower) for p in cls.ESCALATION_PATTERNS)
    
    @classmethod
    def format_risk_response(cls, 
                             evidence: str,
                             missing_data: str = "AWR/ASH and system metrics",
                             conclusion: str = "outage likelihood cannot be confirmed") -> str:
        """
        Format a risk/escalation response with proper structure.
        
        Args:
            evidence: Current evidence statement
            missing_data: What data is missing
            conclusion: Uncertainty conclusion
            
        Returns:
            Properly structured risk response
        """
        return cls.RISK_RESPONSE_TEMPLATE.format(
            evidence=evidence,
            missing_data=missing_data,
            conclusion=conclusion
        )
    
    @classmethod
    def check_risk_language(cls, response: str) -> Tuple[bool, List[str]]:
        """
        Check if risk response has proper uncertainty language.
        
        Returns:
            Tuple of (is_compliant, list of violations)
        """
        violations = []
        response_lower = response.lower()
        
        # Check for absolute predictions
        absolute_patterns = [
            r'will\s+(?:definitely|certainly)\s+(?:fail|crash|cause)',
            r'guaranteed\s+(?:to\s+)?(?:fail|crash|outage)',
            r'100%\s+(?:chance|probability|certain)',
        ]
        
        for pattern in absolute_patterns:
            if re.search(pattern, response_lower):
                violations.append(f"Absolute prediction detected: {pattern}")
        
        # Check for missing uncertainty language
        uncertainty_words = ['however', 'but', 'without', 'cannot confirm', 'uncertain']
        if 'escalate' in response_lower or 'outage' in response_lower:
            has_uncertainty = any(w in response_lower for w in uncertainty_words)
            if not has_uncertainty:
                violations.append("Risk statement without uncertainty caveat")
        
        return len(violations) == 0, violations


# =============================================================================
# RULE 7: CONFIDENCE LABELING STANDARD
# =============================================================================

class ConfidenceLabelingStandard:
    """
    [RULE 7] CONFIDENCE LABELING STANDARD
    
    Default confidence = MEDIUM
    
    Use HIGH only when:
        [OK] Direct OEM metric confirms
        [OK] Explicit DB down / confirmed failure
    
    Otherwise:
        [OK] MEDIUM (pattern-based)
        [OK] LOW (insufficient data)
    """
    
    # Confidence level definitions
    HIGH_CRITERIA = [
        "direct OEM metric confirms",
        "explicit DB down state",
        "confirmed failure in alert",
        "exact count from data",
    ]
    
    MEDIUM_CRITERIA = [
        "pattern-based inference",
        "frequency analysis",
        "similarity clustering",
        "alert volume patterns",
    ]
    
    LOW_CRITERIA = [
        "insufficient data",
        "missing metrics",
        "sparse alerts",
        "no baseline available",
    ]
    
    # Default confidence
    DEFAULT_CONFIDENCE = "MEDIUM"
    
    @classmethod
    def determine_confidence(cls, 
                             has_direct_metric: bool = False,
                             has_confirmed_state: bool = False,
                             is_pattern_based: bool = True,
                             has_sufficient_data: bool = True) -> str:
        """
        Determine appropriate confidence level.
        
        Args:
            has_direct_metric: OEM metric directly confirms
            has_confirmed_state: Explicit DB state confirmed
            is_pattern_based: Analysis is pattern-based
            has_sufficient_data: Enough data for analysis
            
        Returns:
            Confidence level: "HIGH", "MEDIUM", or "LOW"
        """
        if has_direct_metric or has_confirmed_state:
            return "HIGH"
        
        if not has_sufficient_data:
            return "LOW"
        
        # Default to MEDIUM for pattern-based analysis
        return "MEDIUM"
    
    @classmethod
    def format_confidence_label(cls, level: str, reason: str = None) -> str:
        """
        Format confidence label for response.
        
        Args:
            level: HIGH, MEDIUM, or LOW
            reason: Optional reason for the level
            
        Returns:
            Formatted confidence label
        """
        if reason:
            return f"Confidence: {level} ({reason})"
        
        default_reasons = {
            "HIGH": "direct metric confirmation",
            "MEDIUM": "pattern-based",
            "LOW": "insufficient data"
        }
        return f"Confidence: {level} ({default_reasons.get(level, 'pattern-based')})"
    
    @classmethod
    def check_confidence_claims(cls, response: str) -> Tuple[bool, List[str]]:
        """
        Check if response makes inappropriate confidence claims.
        
        Returns:
            Tuple of (is_compliant, list of violations)
        """
        violations = []
        response_lower = response.lower()
        
        # Check for "HIGH confidence" without proper justification
        if 'high confidence' in response_lower:
            justifiers = ['oem metric', 'confirmed', 'explicit', 'direct']
            has_justification = any(j in response_lower for j in justifiers)
            if not has_justification:
                violations.append(
                    "HIGH confidence claimed without direct metric justification"
                )
        
        # Check for forbidden confidence phrases
        forbidden = [
            r'high\s+confidence\s*[-:]\s*computed',
            r'guaranteed\s+(?:high\s+)?confidence',
            r'100%\s+confident',
        ]
        
        for pattern in forbidden:
            if re.search(pattern, response_lower):
                violations.append(f"Forbidden confidence phrase: {pattern}")
        
        return len(violations) == 0, violations


class IncidentIntelligenceLogic:
    """
    [BRAIN] INCIDENT INTELLIGENCE LOGIC (MANDATORY FLOW)
    
    When alerts are large in number:
    1. Apply Noise Filtering
    2. Identify Unique Incidents  
    3. Rank by: Severity, Frequency, Persistence
    4. Clearly state: "High alert volume does NOT imply many independent failures."
    
    [HARD RULE 3] Always use approximate language for incident counts.
    """
    
    # High alert volume threshold
    HIGH_VOLUME_THRESHOLD = 50
    
    # Mandatory statement for high volume
    HIGH_VOLUME_DISCLAIMER = (
        "**Note:** High alert volume does NOT imply many independent failures. "
        "Many alerts may be symptoms of the same underlying issue."
    )
    
    @classmethod
    def is_high_volume(cls, alert_count: int) -> bool:
        """Check if alert volume is high."""
        return alert_count >= cls.HIGH_VOLUME_THRESHOLD
    
    @classmethod
    def add_high_volume_context(cls, response: str, alert_count: int) -> str:
        """Add high volume disclaimer if needed."""
        if cls.is_high_volume(alert_count):
            if cls.HIGH_VOLUME_DISCLAIMER not in response:
                return f"{cls.HIGH_VOLUME_DISCLAIMER}\n\n{response}"
        return response


# =============================================================================
# ROOT CAUSE HANDLING (RULE 5 - EXTREMELY IMPORTANT)
# =============================================================================

class RootCauseHandler:
    """
    [CHART] ERROR & ROOT CAUSE HANDLING (RULE 5)
    
    [X] NEVER call the following a root cause:
    - ORA-600
    - ORA-7445
    - "Internal error"
    - Connectivity failures
    
    [OK] Correct phrasing:
    - "ORA-600 is a symptom class, not a confirmed root cause."
    
    If asked for root cause without trace/AWR data:
    - "Root cause cannot be confirmed from alerts alone."
    
    When asked "What is the root cause?":
    - If multiple causes -> say MULTIPLE CONTRIBUTING FACTORS
    - If scoring-based -> label as Computed Inference
    - Never present inference as fact
    """
    
    ROOT_CAUSE_DISCLAIMER = (
        "**Note:** Root cause is inferred from alert patterns, "
        "not confirmed diagnostics."
    )
    
    # These are NEVER root causes - they are symptoms
    SYMPTOM_CODES = [
        'ORA-600', 'ORA-7445', 'ORA-04031', 'ORA-03113', 'ORA-03114',
    ]
    
    SYMPTOM_PHRASES = [
        'internal error', 'connectivity failure', 'connection lost',
        'connection reset', 'socket error', 'network error',
    ]
    
    ALERTS_ONLY_DISCLAIMER = "Root cause cannot be confirmed from alerts alone."
    
    MULTIPLE_FACTORS_PHRASE = "Multiple contributing factors identified"
    
    COMPUTED_INFERENCE_LABEL = "[Computed Inference]"
    
    @classmethod
    def is_symptom_not_cause(cls, alleged_cause: str) -> bool:
        """Check if the alleged cause is actually a symptom."""
        upper = alleged_cause.upper()
        lower = alleged_cause.lower()
        
        for code in cls.SYMPTOM_CODES:
            if code in upper:
                return True
        
        for phrase in cls.SYMPTOM_PHRASES:
            if phrase in lower:
                return True
        
        return False
    
    @classmethod
    def get_symptom_correction(cls, alleged_cause: str) -> str:
        """Get the correct phrasing for a symptom misidentified as cause."""
        for code in cls.SYMPTOM_CODES:
            if code in alleged_cause.upper():
                return f"{code} is a symptom class, not a confirmed root cause."
        
        return f"'{alleged_cause}' is a symptom, not a confirmed root cause."
    
    @classmethod
    def format_root_cause(cls, causes: List[str], scores: List[float] = None,
                          has_trace_data: bool = False) -> str:
        """Format root cause response with proper disclaimers."""
        lines = []
        
        # Check if any causes are actually symptoms
        valid_causes = []
        symptom_notes = []
        
        for cause in causes:
            if cls.is_symptom_not_cause(cause):
                symptom_notes.append(cls.get_symptom_correction(cause))
            else:
                valid_causes.append(cause)
        
        # Add symptom clarifications first
        if symptom_notes:
            lines.append("**[WARNING] Important:**")
            for note in symptom_notes:
                lines.append(f"- {note}")
            lines.append("")
        
        # If no valid causes and no trace data
        if not valid_causes and not has_trace_data:
            lines.append(f"**Root Cause Status:** {cls.ALERTS_ONLY_DISCLAIMER}")
            return "\n".join(lines)
        
        # Format valid causes
        if len(valid_causes) > 1:
            lines.append(f"**{cls.MULTIPLE_FACTORS_PHRASE}:**")
        elif valid_causes:
            lines.append("**Probable Root Cause:**")
        
        for i, cause in enumerate(valid_causes[:5]):  # Max 5 causes
            score_label = ""
            if scores and i < len(scores):
                score_label = f" {cls.COMPUTED_INFERENCE_LABEL} (confidence: {scores[i]:.0%})"
            lines.append(f"- {cause}{score_label}")
        
        lines.append("")
        lines.append(cls.ROOT_CAUSE_DISCLAIMER)
        
        return "\n".join(lines)


# =============================================================================
# CONFIDENCE FORMATTER (RULE 9 - MANDATORY)
# =============================================================================

class ConfidenceFormatter:
    """
    [SIGNAL] CONFIDENCE SCORING (RULE 9 - MANDATORY)
    
    Every analytical answer MUST include ONE confidence level:
    - HIGH - Directly backed by data
    - MEDIUM - Partial inference  
    - LOW - Limited data
    
    Format: "Confidence: HIGH"
    
    Never hide uncertainty.
    """
    
    # Simple format as per Rule 9
    CONFIDENCE_LABELS = {
        ConfidenceLevel.HIGH: "Confidence: HIGH",
        ConfidenceLevel.MEDIUM: "Confidence: MEDIUM",
        ConfidenceLevel.LOW: "Confidence: LOW",
    }
    
    @classmethod
    def add_confidence_label(cls, response: str, level: ConfidenceLevel) -> str:
        """Add confidence label to response."""
        label = cls.CONFIDENCE_LABELS.get(level, cls.CONFIDENCE_LABELS[ConfidenceLevel.MEDIUM])
        return f"{response}\n\n{label}"
    
    @classmethod
    def assess_confidence(cls, data_count: int, has_all_fields: bool = True) -> ConfidenceLevel:
        """Assess confidence level based on data availability."""
        if data_count == 0:
            return ConfidenceLevel.LOW
        
        if data_count < 5:
            return ConfidenceLevel.LOW
        
        if data_count < 20 or not has_all_fields:
            return ConfidenceLevel.MEDIUM
        
        return ConfidenceLevel.HIGH


# =============================================================================
# SELF-VALIDATION STEP
# =============================================================================

class SelfValidation:
    """
    [TEST] SELF-VALIDATION STEP (INTERNAL)
    
    Before final answer, verify:
    [v] Scope respected
    [v] Numbers consistent
    [v] No forbidden claims
    [v] Precision mode honored
    
    If ANY check fails -> re-answer.
    """
    
    @classmethod
    def validate_response(cls, question: str, response: str, 
                          scope: ScopeConstraint, mode: AnswerMode,
                          data: List[Dict] = None) -> Tuple[bool, List[str]]:
        """
        Run all validation checks.
        
        Returns:
            Tuple of (all_passed, list of failures)
        """
        failures = []
        
        # Check 1: Scope respected
        if scope.target_database:
            scope_guard = ScopeControlGuard()
            is_valid, violations = scope_guard.validate_response_scope(response, scope)
            if not is_valid:
                failures.extend(violations)
        
        # Check 2: Numbers consistent
        checker = ConsistencyChecker()
        is_consistent, issues = checker.check_internal_consistency(response)
        if not is_consistent:
            failures.extend(issues)
        
        # Check 3: No forbidden claims
        is_safe, forbidden_violations = ProductionSafetyRules.check_for_forbidden_claims(response)
        if not is_safe:
            failures.extend(forbidden_violations)
        
        # Check 4: Precision mode honored
        if mode == AnswerMode.STRICT_NUMBER:
            # Response should be only digits
            clean_response = response.strip()
            if not clean_response.isdigit():
                failures.append(f"STRICT_NUMBER mode not honored: response is '{clean_response[:50]}'")
        
        elif mode == AnswerMode.YES_NO:
            # Response should start with Yes or No
            clean_response = response.strip().lower()
            if not (clean_response.startswith('yes') or clean_response.startswith('no')):
                failures.append(f"YES_NO mode not honored: response doesn't start with Yes/No")
        
        return len(failures) == 0, failures


# =============================================================================
# MASTER GUARDRAIL ENFORCER
# =============================================================================

@dataclass
class GuardrailResult:
    """Result of applying all guardrails."""
    passed: bool
    mode: AnswerMode
    scope: ScopeConstraint
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    corrected_response: Optional[str] = None


class DBAGuardrailEnforcer:
    """
    Master enforcer that applies all 10 Production-Grade guardrails.
    
    [SHIELD] PRODUCTION-GRADE DBA INTELLIGENCE PARTNER RULES:
    
    [1] SCOPE LOCK RULE
    [2] ANSWER PRECISION MODE (STRICT_NUMBER, YES_NO, LIST_ONLY, SUMMARY)
    [3] DATA AUTHORITY RULE
    [4] PREDICTIVE REASONING GUARDRAILS
    [5] PRODUCTION SAFETY RULES
    [6] INCIDENT INTELLIGENCE LOGIC
    [7] ERROR & ROOT CAUSE HANDLING
    [8] EXPLANATION MODES (Manager vs Senior DBA)
    [9] CONFIDENCE & UNCERTAINTY HANDLING
    [10] SELF-VALIDATION STEP
    
    Usage:
        enforcer = DBAGuardrailEnforcer()
        result = enforcer.enforce(question, response, data)
        
        if result.passed:
            return result.corrected_response or response
        else:
            # Handle violations
    """
    
    def __init__(self):
        self.mode_detector = AnswerModeDetector()
        self.scope_guard = ScopeControlGuard()
        self.prediction_safety = PredictiveReasoningSafety()
        self.no_data_handler = NoDataHandler()
        self.anti_overexplanation = AntiOverexplanation()
        self.consistency_checker = ConsistencyChecker()
        self.production_safety = ProductionSafeResponse()
    
    def enforce(self, question: str, response: str, 
                data: List[Dict] = None,
                alert_count: int = 0,
                include_confidence: bool = True) -> GuardrailResult:
        """
        Apply all 10 Production-Grade guardrails to a response.
        
        Args:
            question: User's question
            response: Generated response
            data: Data used to generate response
            alert_count: Number of alerts (for high-volume handling)
            include_confidence: Whether to add confidence label
            
        Returns:
            GuardrailResult with pass/fail and any corrections
        """
        data = data or []
        violations = []
        warnings = []
        corrected = response
        
        # [1] SCOPE LOCK RULE - Extract and validate scope
        scope = self.scope_guard.extract_scope(question)
        scope_valid, scope_violations = self.scope_guard.validate_response_scope(response, scope)
        violations.extend(scope_violations)
        
        # [2] ANSWER PRECISION - Detect mode
        mode = self.mode_detector.detect_mode(question)
        
        # [3] DATA AUTHORITY RULE - Check for assumptions
        data_ok, data_warnings = DataAuthorityRule.check_data_authority(corrected)
        if not data_ok:
            warnings.extend(data_warnings)
        
        # [4] PREDICTIVE REASONING SAFETY
        pred_safe, pred_violations = self.prediction_safety.check_prediction_safety(corrected)
        if not pred_safe:
            warnings.extend(pred_violations)
            corrected = self.prediction_safety.sanitize_prediction(corrected)
        
        # [5] PRODUCTION SAFETY RULES - Check forbidden claims
        forbidden_safe, forbidden_violations = ProductionSafetyRules.check_for_forbidden_claims(corrected)
        if not forbidden_safe:
            violations.extend(forbidden_violations)
        
        # Check if safety disclaimer is needed
        if ProductionSafetyRules.needs_safety_disclaimer(question):
            corrected = ProductionSafetyRules.add_safety_disclaimer(corrected)
        
        # [6] INCIDENT INTELLIGENCE LOGIC - High volume handling
        if IncidentIntelligenceLogic.is_high_volume(alert_count):
            corrected = IncidentIntelligenceLogic.add_high_volume_context(corrected, alert_count)
        
        # Original production safety (panic language)
        safe, safety_issues = self.production_safety.check_production_safety(corrected)
        if not safe:
            warnings.extend(safety_issues)
            corrected = self.production_safety.calm_down_text(corrected)
        
        # [7] (ROOT CAUSE handled by RootCauseHandler when generating responses)
        
        # [8] NO-DATA HANDLING
        if not data and mode != AnswerMode.STRICT_NUMBER:
            has_data, reason = self.no_data_handler.check_data_availability(data)
            if not has_data:
                warnings.append(f"No data available: {reason}")
        
        # [9] ANTI-OVEREXPLANATION (Part of EXPLANATION MODES)
        length_ok, length_warning = self.anti_overexplanation.check_response_length(
            corrected, question, mode
        )
        if not length_ok:
            warnings.append(length_warning)
        
        # [10] CONSISTENCY CHECK
        consistent, consistency_issues = self.consistency_checker.check_internal_consistency(corrected)
        if not consistent:
            violations.extend(consistency_issues)
        
        # MODE ENFORCEMENT
        if mode == AnswerMode.STRICT_NUMBER:
            corrected = self._enforce_strict_number(corrected)
        elif mode == AnswerMode.STRICT_VALUE:
            corrected = self._enforce_strict_value(corrected)
        elif mode == AnswerMode.YES_NO:
            corrected = self._enforce_yes_no(corrected)
        
        # Add confidence label if requested
        if include_confidence and mode not in [AnswerMode.STRICT_NUMBER, AnswerMode.YES_NO]:
            confidence_level = ConfidenceFormatter.assess_confidence(len(data))
            corrected = ConfidenceFormatter.add_confidence_label(corrected, confidence_level)
        
        # [TEST] SELF-VALIDATION STEP
        validation_passed, validation_failures = SelfValidation.validate_response(
            question, corrected, scope, mode, data
        )
        if not validation_passed:
            warnings.extend([f"Self-validation: {f}" for f in validation_failures])
        
        passed = len(violations) == 0
        
        return GuardrailResult(
            passed=passed,
            mode=mode,
            scope=scope,
            violations=violations,
            warnings=warnings,
            corrected_response=corrected if corrected != response else None
        )
    
    def _enforce_strict_number(self, response: str) -> str:
        """
        Enforce STRICT_NUMBER mode - return ONLY digits.
        """
        # Try to extract just the number
        numbers = re.findall(r'\d+', response.replace(',', ''))
        
        if numbers:
            # Return the first significant number
            for num in numbers:
                if int(num) > 0:
                    return num
            return numbers[0]
        
        # If no number found, return "0" or the response
        return "0"
    
    def _enforce_yes_no(self, response: str) -> str:
        """
        Enforce YES_NO mode - return Yes or No first.
        """
        response_lower = response.lower().strip()
        
        if 'yes' in response_lower:
            return "Yes"
        elif 'no' in response_lower:
            return "No"
        
        return response.strip()
    
    def _enforce_strict_value(self, response: str) -> str:
        """
        Enforce STRICT_VALUE mode - extract only the value.
        
        For numeric questions, return ONLY the number.
        """
        # Try to extract just the number
        numbers = re.findall(r'\d+', response.replace(',', ''))
        
        if numbers:
            # Return the most significant number (usually largest or first)
            # For counts, it's typically the first significant number
            for num in numbers:
                if int(num) > 0:
                    return num
            return numbers[0]
        
        # For yes/no questions
        response_lower = response.lower().strip()
        if response_lower.startswith('yes'):
            return "Yes"
        elif response_lower.startswith('no'):
            return "No"
        
        # Return as-is if we can't extract
        return response.strip()
    
    def format_for_mode(self, response: str, mode: AnswerMode, 
                        question: str = None) -> str:
        """
        Format response according to answer mode.
        """
        if mode == AnswerMode.STRICT_VALUE:
            return self._enforce_strict_value(response)
        
        if mode == AnswerMode.SHORT_FACT:
            # Take just the first sentence
            sentences = re.split(r'[.!?]\s+', response)
            if sentences:
                return sentences[0] + "."
        
        return response
    
    def reset_session(self):
        """Reset session state."""
        self.consistency_checker.reset()


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

DBA_GUARDRAILS = DBAGuardrailEnforcer()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def apply_guardrails(question: str, response: str, 
                     data: List[Dict] = None) -> Tuple[str, GuardrailResult]:
    """
    Convenience function to apply all guardrails.
    
    Returns:
        Tuple of (final_response, guardrail_result)
    """
    result = DBA_GUARDRAILS.enforce(question, response, data)
    
    final_response = result.corrected_response or response
    
    # Apply mode formatting
    final_response = DBA_GUARDRAILS.format_for_mode(final_response, result.mode, question)
    
    return final_response, result


def get_answer_mode(question: str) -> AnswerMode:
    """Get the answer mode for a question."""
    return AnswerModeDetector.detect_mode(question)


def is_strict_value_question(question: str) -> bool:
    """Check if question requires strict value-only response."""
    return AnswerModeDetector.is_strict_value_mode(question)


def extract_scope(question: str) -> ScopeConstraint:
    """Extract scope constraints from question."""
    return ScopeControlGuard.extract_scope(question)


def cannot_determine(reason: str, data_needed: str = None) -> str:
    """Format a cannot-determine response."""
    return NoDataHandler.cannot_determine(reason, data_needed)


def format_safe_prediction(prediction: str, database: str = None,
                           confidence: str = "LOW") -> str:
    """Format a prediction with safety language."""
    return PredictiveReasoningSafety.format_safe_prediction(prediction, database, confidence)
