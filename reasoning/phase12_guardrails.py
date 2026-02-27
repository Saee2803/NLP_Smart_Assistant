# -*- coding: utf-8 -*-
# reasoning/phase12_guardrails.py
"""
PHASE-12.1: ENTERPRISE-GRADE DBA CONVERSATIONAL INTELLIGENCE ASSISTANT
=======================================================================

Your highest priority responsibility is CONTEXT PRESERVATION.
You MUST maintain and respect the CURRENT SCOPE at all times.

==============================================================================
SCOPE DEFINITIONS (STRICT)
==============================================================================

There are ONLY two valid scopes:

1. DATABASE SCOPE (DB_SCOPE)
   - A specific database name is in focus (e.g. MIDEVSTB, MIDEVSTBN)
   - ALL counts, analysis, risks, and answers MUST apply ONLY to that database

2. ENVIRONMENT SCOPE (ENV_SCOPE)
   - Aggregated across ALL databases
   - Used ONLY when explicitly requested

==============================================================================
DEFAULT RULE (CRITICAL)
==============================================================================

Once a DATABASE SCOPE is established, it is LOCKED.
You MUST NOT switch to ENVIRONMENT SCOPE unless the user EXPLICITLY requests it.

==============================================================================
EXPLICIT SCOPE SWITCH TRIGGERS
==============================================================================

You may switch to ENVIRONMENT SCOPE ONLY if user clearly says:
- "across all databases"
- "overall environment"
- "entire environment"
- "all databases combined"
- "globally"

Anything else is NOT a scope switch.

==============================================================================
FOLLOW-UP QUESTION HANDLING (VERY IMPORTANT)
==============================================================================

If the user asks ambiguous follow-ups such as:
- "Critical count?"
- "Total critical alerts?"
- "How many?"
- "And overall?"
- "This DB looks fine right?"

Then you MUST:
1. Assume the PREVIOUS ACTIVE SCOPE
2. NEVER widen scope silently
3. NEVER jump from DB → ENV automatically

If ambiguity could change scope:
→ Ask a clarification OR
→ State your assumption explicitly

Example:
"Assuming you mean MIDEVSTB only: 165,837 CRITICAL alerts."

==============================================================================
COUNTING RULES (NON-NEGOTIABLE)
==============================================================================

- If scope = DB_SCOPE → Return ONLY that database's numbers
- If scope = ENV_SCOPE → Return environment-wide totals

NEVER mix DB numbers with ENV numbers in the same answer
unless explicitly asked to compare.

==============================================================================
UNIQUE INCIDENT / ROOT CAUSE GUARDRAILS
==============================================================================

You MUST NEVER state incident counts or root causes as absolute facts.

Required phrasing:
- "distinct alert patterns detected"
- "approximation based on alert text clustering"
- "derived from alert frequency, not system metrics"

==============================================================================
PREDICTIVE CONFIDENCE GUARDRAILS
==============================================================================

You MUST NOT overstate certainty.

Forbidden phrases:
- "Confirmed root cause"
- "Will escalate"
- "Guaranteed outage"
- "High confidence" (unless explicitly backed by system metrics)

Allowed defaults:
- Confidence: MEDIUM
- Explicit disclaimer:
  "Based on alert patterns only; AWR/ASH/system metrics not analyzed."

==============================================================================
SAFETY & AUTHORITY BOUNDARIES
==============================================================================

You CANNOT:
- Execute SQL
- Restart databases
- Guarantee outcomes
- Promise resolution

You CAN:
- Suggest investigation steps
- Explain risk qualitatively
- Advise escalation paths

==============================================================================
FINAL ENFORCEMENT RULE
==============================================================================

If a response would violate scope, confidence, or authority:
→ STOP → Correct yourself → Respond conservatively

Context accuracy is MORE important than being helpful.
If uncertain, ASK or STATE ASSUMPTION — never guess.
"""

import re
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass, field
from enum import Enum


class ScopeType(Enum):
    """Database scope types."""
    DATABASE = "DATABASE"      # Single database scope
    ENVIRONMENT = "ENVIRONMENT"  # All databases
    AMBIGUOUS = "AMBIGUOUS"    # Cannot determine


@dataclass
class ActiveScope:
    """Tracks the current database scope."""
    scope_type: ScopeType = ScopeType.AMBIGUOUS
    database_name: Optional[str] = None
    explicitly_set: bool = False
    
    def is_database_scoped(self) -> bool:
        return self.scope_type == ScopeType.DATABASE and self.database_name is not None


# Global active scope tracker (synced with SessionStore)
_ACTIVE_DB_SCOPE: ActiveScope = ActiveScope()

# Session store integration flag
_SESSION_SYNC_ENABLED = False
try:
    from services.session_store import SessionStore
    _SESSION_SYNC_ENABLED = True
except ImportError:
    pass


def _sync_scope_from_session():
    """Load scope from session store at start of request."""
    global _ACTIVE_DB_SCOPE
    if not _SESSION_SYNC_ENABLED:
        return
    
    db_name, scope_type_str = SessionStore.get_active_db_scope()
    if db_name:
        _ACTIVE_DB_SCOPE = ActiveScope(
            scope_type=ScopeType.DATABASE,
            database_name=db_name,
            explicitly_set=True
        )
    elif scope_type_str == "ENVIRONMENT":
        _ACTIVE_DB_SCOPE = ActiveScope(
            scope_type=ScopeType.ENVIRONMENT,
            database_name=None,
            explicitly_set=True
        )
    # else keep as AMBIGUOUS


def _sync_scope_to_session():
    """Save scope to session store after update."""
    global _ACTIVE_DB_SCOPE
    if not _SESSION_SYNC_ENABLED:
        return
    
    SessionStore.set_active_db_scope(
        _ACTIVE_DB_SCOPE.database_name,
        _ACTIVE_DB_SCOPE.scope_type.value
    )


class Phase12Guardrails:
    """
    Phase-12.1 Production-Grade Guardrails.
    
    Enforces all 6 HARD GUARDRAILS before ANY response is returned.
    """
    
    # =========================================
    # GUARDRAIL 1: DATABASE SCOPE LOCK
    # =========================================
    
    # Known database name patterns (exclude common words like "that", "this")
    DB_PATTERNS = [
        r'\b(MIDEVSTB[N]?)\b',
        r'\b([A-Z]{2,}DEV[A-Z]*)\b',
        r'\b([A-Z]{2,}PRD[A-Z]*)\b',
        r'\b([A-Z]{2,}TST[A-Z]*)\b',
        r'\bfor\s+(?!that\b|this\b)([A-Z][A-Z0-9_]+)\b',
        r'\bon\s+(?!that\b|this\b)([A-Z][A-Z0-9_]+)\b',
    ]
    
    # Follow-up patterns that inherit scope (MUST reuse ACTIVE_DB_SCOPE)
    SCOPE_INHERITING_PATTERNS = [
        r'^critical\s+count\??$',
        r'^how\s+many\s+(critical|warning)\s*\??$',
        r'^total\s+alerts?\s*\??$',
        r'^total\s+for\s+that\s+db\??$',
        r'^total\s+alerts?\s+for\s+that\s+db\??$',
        r'^this\s+db\s+looks\s+fine\s*\??.*$',
        r'^is\s+this\s+db\s+fine\??$',              # "Is this DB fine?"
        r'^is\s+this\s+db\s+ok\??$',                # "Is this DB ok?"
        r'^is\s+this\s+database\s+fine\??$',        # "Is this database fine?"
        r'^is\s+(this|it)\s+stable\s*\??.*$',
        r'^is\s+(this|it)\s+ok\s*\??.*$',
        r'^(count|total|alerts?)\??$',
        r'^root\s+cause\??$',
        r'^is\s+ora-\d+\s+the\s+(?:confirmed\s+)?root\s+cause\??$',
        # New patterns from spec
        r'^is\s+this\s+likely\s+to\s+escalate\??$',
        r'^how\s+many\s+unique\s+incidents?\??$',
        r'^unique\s+incidents?\??$',
        r'^will\s+this\s+cause\s+(?:an?\s+)?outage\??$',
        r'^what\'?s\s+the\s+status\??$',
        r'^status\??$',
        r'^is\s+it\s+getting\s+worse\??$',
        r'^trending\??$',
        r'^severity\??$',
        r'^total\s+critical\s+alerts?\??$',
        r'^warnings?\??$',
        r'^criticals?\??$',
        # Additional follow-up patterns
        r'^and\s+overall\??$',                      # "And overall?" - special case
        r'^how\s+about\s+warnings?\??$',
        r'^what\s+about\s+this\s+db\??$',
        r'^for\s+this\s+db\??$',
        r'^on\s+this\s+db\??$',
    ]
    
    # Patterns that explicitly request environment scope
    ENVIRONMENT_SCOPE_PATTERNS = [
        r'entire\s+environment',
        r'all\s+databases?',
        r'overall',
        r'total\s+system',
        r'environment[-\s]?wide',
        r'across\s+(?:all\s+)?(?:the\s+)?environment',
    ]
    
    @classmethod
    def extract_database_from_question(cls, question: str) -> Optional[str]:
        """Extract database name from question if present."""
        for pattern in cls.DB_PATTERNS:
            match = re.search(pattern, question, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        return None
    
    @classmethod
    def is_scope_inheriting_followup(cls, question: str) -> bool:
        """Check if question inherits previous DB scope."""
        q_lower = question.lower().strip()
        for pattern in cls.SCOPE_INHERITING_PATTERNS:
            if re.match(pattern, q_lower):
                return True
        return False
    
    @classmethod
    def is_environment_scope_request(cls, question: str) -> bool:
        """Check if question explicitly requests environment scope."""
        q_lower = question.lower()
        for pattern in cls.ENVIRONMENT_SCOPE_PATTERNS:
            if re.search(pattern, q_lower):
                return True
        return False
    
    @classmethod
    def update_scope(cls, question: str) -> ActiveScope:
        """Update active scope based on question."""
        global _ACTIVE_DB_SCOPE
        
        # CRITICAL: Load scope from session FIRST
        _sync_scope_from_session()
        
        # Check for explicit environment request
        if cls.is_environment_scope_request(question):
            _ACTIVE_DB_SCOPE = ActiveScope(
                scope_type=ScopeType.ENVIRONMENT,
                database_name=None,
                explicitly_set=True
            )
            _sync_scope_to_session()  # Save to session
            return _ACTIVE_DB_SCOPE
        
        # Check for database name in question
        db_name = cls.extract_database_from_question(question)
        if db_name:
            _ACTIVE_DB_SCOPE = ActiveScope(
                scope_type=ScopeType.DATABASE,
                database_name=db_name,
                explicitly_set=True
            )
            _sync_scope_to_session()  # Save to session
            return _ACTIVE_DB_SCOPE
        
        # Check if follow-up should inherit scope
        if cls.is_scope_inheriting_followup(question):
            # Keep current scope (inherit from previous)
            if _ACTIVE_DB_SCOPE.database_name:
                return _ACTIVE_DB_SCOPE
        
        return _ACTIVE_DB_SCOPE
    
    @classmethod
    def get_current_scope(cls) -> ActiveScope:
        """Get current active scope (synced from session)."""
        # Load from session first
        _sync_scope_from_session()
        return _ACTIVE_DB_SCOPE
    
    @classmethod
    def reset_scope(cls):
        """Reset scope to ambiguous."""
        global _ACTIVE_DB_SCOPE
        _ACTIVE_DB_SCOPE = ActiveScope()
        # Clear in session too
        if _SESSION_SYNC_ENABLED:
            SessionStore.clear_db_scope()
    
    @classmethod
    def needs_scope_clarification(cls, question: str) -> bool:
        """
        🚨 FAIL-SAFE: Check if we need to ask for clarification.
        
        Returns True if:
        - No active DB scope AND
        - Question looks like a follow-up that needs scope
        """
        scope = cls.get_current_scope()
        
        # If we have a DB scope, no clarification needed
        if scope.is_database_scoped():
            return False
        
        # If explicitly environment, no clarification needed
        if scope.scope_type == ScopeType.ENVIRONMENT:
            return False
        
        # If question contains explicit DB or environment, no clarification needed
        if cls.extract_database_from_question(question):
            return False
        if cls.is_environment_scope_request(question):
            return False
        
        # If this looks like a follow-up but we have no scope → need clarification
        if cls.is_scope_inheriting_followup(question):
            return True
        
        # Generic count questions without scope need clarification
        q_lower = question.lower()
        ambiguous_patterns = [
            r'^how\s+many\s+',
            r'^count\s+',
            r'^total\s+',
            r'^critical\s+',
            r'^warning\s+',
        ]
        for pattern in ambiguous_patterns:
            if re.match(pattern, q_lower):
                return True
        
        return False
    
    @classmethod
    def get_clarification_response(cls) -> str:
        """Get the clarification response when scope is unclear."""
        return (
            "I need clarification before answering to avoid incorrect scope.\n\n"
            "Please specify:\n"
            "- A specific database name (e.g., MIDEVSTB, MIDEVSTBN)\n"
            "- Or 'across all databases' / 'environment-wide' for totals"
        )
    
    @classmethod
    def format_with_scope_assumption(cls, answer: str) -> str:
        """
        FOLLOW-UP QUESTION HANDLING: State assumption explicitly.
        
        When answering a follow-up question, prepend the scope assumption
        to make it clear what context is being used.
        
        Example: "Assuming you mean MIDEVSTB only: 165,837 CRITICAL alerts."
        """
        scope = cls.get_current_scope()
        
        if scope.is_database_scoped():
            # Check if answer already has scope indicator
            if answer.startswith(f"**Scope: {scope.database_name}"):
                return answer
            if answer.startswith(f"Assuming you mean {scope.database_name}"):
                return answer
            
            # Add assumption statement
            return f"Assuming you mean {scope.database_name} only: {answer}"
        
        elif scope.scope_type == ScopeType.ENVIRONMENT:
            if "environment" in answer.lower() or "all databases" in answer.lower():
                return answer
            return f"Across all databases: {answer}"
        
        return answer
    
    @classmethod
    def get_scope_prefix(cls) -> str:
        """Get the scope prefix for responses."""
        scope = cls.get_current_scope()
        
        if scope.is_database_scoped():
            return f"**Scope: {scope.database_name}**\n\n"
        elif scope.scope_type == ScopeType.ENVIRONMENT:
            return "**Scope: Environment-wide**\n\n"
        return ""
    
    @classmethod
    def scope_safety_check(cls, question: str) -> Tuple[str, bool]:
        """
        3️⃣ SCOPE SAFETY CHECK (Before Every Answer)
        
        Determines if question is asking about:
        A) ACTIVE_DB_SCOPE → use DB-filtered data only
        B) Entire environment → use environment totals only
        
        Returns:
            Tuple of (scope_type: 'database'|'environment'|'ambiguous', is_valid: bool)
        """
        # Update scope based on question
        scope = cls.update_scope(question)
        
        if scope.scope_type == ScopeType.DATABASE:
            return ('database', True)
        elif scope.scope_type == ScopeType.ENVIRONMENT:
            return ('environment', True)
        else:
            # Check if clarification needed
            if cls.needs_scope_clarification(question):
                return ('ambiguous', False)
            return ('environment', True)  # Default to environment for general questions
        """Reset scope to ambiguous."""
        global _ACTIVE_DB_SCOPE
        _ACTIVE_DB_SCOPE = ActiveScope()
    
    @classmethod
    def check_scope_drift(cls, question: str, answer: str, 
                          data_used: List[Dict] = None) -> Tuple[bool, str]:
        """
        GUARDRAIL 1 & 2: Check for scope drift.
        
        Returns:
            Tuple of (has_drift, corrected_answer)
        """
        scope = cls.update_scope(question)
        
        if not scope.is_database_scoped():
            return False, answer
        
        # If DB-scoped, check if answer contains environment totals
        # Large numbers like 649,xxx are likely environment totals
        large_number_pattern = r'\b(6[0-9]{2}[,\s]?[0-9]{3})\b'
        if re.search(large_number_pattern, answer):
            # Check if data supports this number for the specific DB
            if data_used:
                db_alerts = [a for a in data_used 
                            if a.get('target_name', '').upper() == scope.database_name]
                actual_count = len(db_alerts)
                
                # If actual count is much smaller, there's drift
                matches = re.findall(large_number_pattern, answer)
                for match in matches:
                    num = int(match.replace(',', '').replace(' ', ''))
                    if num > actual_count * 10:  # Likely environment total
                        return True, f"**Scope: {scope.database_name}**\n\nData not found for this specific database in current context."
        
        return False, answer
    
    # =========================================
    # GUARDRAIL 3: ROOT CAUSE CONFIDENCE CLAMP
    # =========================================
    
    # Forbidden high confidence phrases
    FORBIDDEN_HIGH_CONFIDENCE = [
        r'confirmed\s+root\s+cause',
        r'high\s+confidence\s+root\s+cause',
        r'guaranteed\s+(?:root\s+)?cause',
        r'definite\s+(?:root\s+)?cause',
        r'root\s+cause\s*\(\s*high\s+confidence',
        r'root\s+cause\s*:\s*high\s+confidence',
        r'confidence:\s*high',
        r'confidence_label["\']?\s*:\s*["\']?high',
    ]
    
    # Required replacement phrases
    MEDIUM_CONFIDENCE_PHRASE = "Based on alert frequency and repetition patterns only (MEDIUM confidence)"
    
    @classmethod
    def clamp_root_cause_confidence(cls, answer: str) -> str:
        """
        GUARDRAIL 3: Clamp root cause confidence to MEDIUM unless proven.
        """
        result = answer
        
        # Replace forbidden phrases
        for pattern in cls.FORBIDDEN_HIGH_CONFIDENCE:
            if re.search(pattern, result, re.IGNORECASE):
                # Replace HIGH with MEDIUM
                result = re.sub(
                    r'\bhigh\s+confidence\b',
                    'MEDIUM confidence',
                    result,
                    flags=re.IGNORECASE
                )
                result = re.sub(
                    r'\bconfidence:\s*high\b',
                    'Confidence: MEDIUM',
                    result,
                    flags=re.IGNORECASE
                )
                result = re.sub(
                    r'confirmed\s+root\s+cause',
                    'pattern-based inference (not confirmed)',
                    result,
                    flags=re.IGNORECASE
                )
        
        return result
    
    @classmethod
    def clamp_confidence_label(cls, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        GUARDRAIL 3 & 7: Clamp confidence_label in result dict.
        
        HIGH only allowed when:
        - Direct count from data (exact match)
        - Explicit DB down/failure confirmed
        
        Otherwise: MEDIUM or LOW
        """
        if result.get("confidence_label") == "HIGH":
            # Check if this is a simple count question with direct data
            has_direct_data = result.get("_has_direct_data", False)
            is_confirmed_failure = result.get("_is_confirmed_failure", False)
            
            if not (has_direct_data or is_confirmed_failure):
                result["confidence_label"] = "MEDIUM"
                # Also update answer if it contains HIGH
                if "answer" in result:
                    result["answer"] = cls.clamp_root_cause_confidence(result["answer"])
        
        return result
    
    # =========================================
    # GUARDRAIL 4: PREDICTIVE LANGUAGE SAFETY
    # =========================================
    
    FORBIDDEN_PREDICTIONS = [
        (r'\bwill\s+fail\b', 'may fail if condition persists'),
        (r'\bwill\s+escalate\b', 'may escalate if condition persists'),
        (r'\boutage\s+is\s+certain\b', 'outage risk is elevated'),
        (r'\bguaranteed\s+outage\b', 'elevated outage risk'),
        (r'\bwill\s+cause\s+(?:an?\s+)?outage\b', 'may cause outage if unresolved'),
        (r'\bwill\s+cause\b', 'may cause'),  # Generic will cause
        (r'\bwill\s+crash\b', 'may crash if condition persists'),
        (r'\bwill\s+go\s+down\b', 'may go down if unresolved'),
        (r'\bthis\s+will\s+cause\b', 'this may cause'),  # Specific pattern
    ]
    
    PREDICTION_DISCLAIMER = "\n\n*This assessment is based on alert data only.*"
    
    @classmethod
    def sanitize_predictions(cls, question: str, answer: str) -> str:
        """
        GUARDRAIL 4: Sanitize predictive language.
        """
        result = answer
        
        # Check if this is a predictive question
        q_lower = question.lower()
        is_predictive = any(p in q_lower for p in [
            'will this', 'will it', 'going to', 'likely to',
            'cause outage', 'escalate', 'fail', 'crash'
        ])
        
        # Replace forbidden predictions
        for pattern, replacement in cls.FORBIDDEN_PREDICTIONS:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        # Add disclaimer for predictive questions
        if is_predictive and cls.PREDICTION_DISCLAIMER not in result:
            result = result.rstrip() + cls.PREDICTION_DISCLAIMER
        
        return result
    
    # =========================================
    # GUARDRAIL 5: UNIQUE INCIDENT COUNT
    # =========================================
    
    # Patterns that suggest exact incident count
    EXACT_INCIDENT_PATTERNS = [
        r'\b(\d+)\s+unique\s+incidents?\b',
        r'\b(\d+)\s+incidents?\s+exist\b',
        r'\b(\d+)\s+distinct\s+issues?\b',
        r'\bthere\s+are\s+(\d+)\s+incidents?\b',
    ]
    
    @classmethod
    def is_incident_count_question(cls, question: str) -> bool:
        """Check if question asks about unique incidents."""
        q_lower = question.lower()
        # Direct patterns
        if any(p in q_lower for p in [
            'unique incident', 'how many incident', 
            'incident count', 'distinct incident',
            'unique issue', 'how many issue'
        ]):
            return True
        
        # Pattern: "Is this X issues?" or "Is this 165,837 issues?"
        if re.search(r'is\s+this\s+[\d,]+\s+issues?', q_lower):
            return True
        
        return False
    
    @classmethod
    def fix_incident_count(cls, question: str, answer: str) -> str:
        """
        GUARDRAIL 5: Fix exact incident counts.
        """
        if not cls.is_incident_count_question(question):
            return answer
        
        result = answer
        
        # Check for large exact numbers (likely false precision)
        for pattern in cls.EXACT_INCIDENT_PATTERNS:
            match = re.search(pattern, result, re.IGNORECASE)
            if match:
                count = int(match.group(1))
                # Replace with approximate language
                approx_text = (
                    f"~{count:,} distinct alert patterns detected.\n\n"
                    "**Note:** This is an approximation based on repetition clustering, "
                    "not confirmed incident IDs."
                )
                result = re.sub(pattern, approx_text, result, flags=re.IGNORECASE)
        
        # If answer is just a number for incident question (with or without scope prefix)
        # Match patterns like "649787" or "**Scope: MIDEVSTB**\n\n649787"
        clean_answer = re.sub(r'\*\*Scope:\s*[A-Z0-9_]+\*\*\s*', '', result).strip()
        if re.match(r'^\d+$', clean_answer):
            count = int(clean_answer)
            scope = cls.get_current_scope()
            scope_text = f" for {scope.database_name}" if scope.database_name else ""
            
            # Preserve scope prefix if present
            scope_prefix = ""
            scope_match = re.match(r'(\*\*Scope:\s*[A-Z0-9_]+\*\*\s*)', result)
            if scope_match:
                scope_prefix = scope_match.group(1)
            
            result = (
                f"{scope_prefix}A small number of distinct alert patterns detected{scope_text}.\n\n"
                "This is an approximation based on repetition clustering, "
                "not confirmed incident IDs."
            )
        
        return result
    
    # =========================================
    # GUARDRAIL 6: EXECUTION & GUARANTEE BLOCK
    # =========================================
    
    EXECUTION_PATTERNS = [
        r'\brun\s+(?:this\s+)?sql\b',
        r'\bexecute\s+(?:this\s+)?(?:query|sql|script)\b',
        r'\bexecute\s+(?:the\s+)?query\b',  # "Execute the query"
        r'\brestart\s+(?:the\s+)?(?:database|db|instance)\b',
        r'\bkill\s+(?:the\s+)?session\b',
        r'\bstop\s+(?:the\s+)?(?:database|db|instance)\b',
        r'\bstart\s+(?:the\s+)?(?:database|db|instance)\b',
        r'\bshutdown\b',
        r'\bstartup\b',
    ]
    
    GUARANTEE_PATTERNS = [
        r'\bguarantee\s+(?:no\s+)?outage\b',
        r'\bpromise\s+(?:it\s+)?(?:will|won\'t)\b',
        r'\bensure\s+no\s+(?:downtime|outage)\b',
        r'\bfix\s+this\s+(?:for\s+me|now)\b',
    ]
    
    EXECUTION_REFUSAL = (
        "I cannot execute changes or run SQL directly. "
        "I can suggest safe investigation steps.\n\n"
        "I also cannot guarantee outcomes or promise resolution."
    )
    
    @classmethod
    def needs_execution_refusal(cls, question: str) -> bool:
        """Check if question requests execution/guarantee."""
        q_lower = question.lower()
        for pattern in cls.EXECUTION_PATTERNS + cls.GUARANTEE_PATTERNS:
            if re.search(pattern, q_lower):
                return True
        return False
    
    @classmethod
    def get_execution_refusal(cls, question: str) -> str:
        """Get execution refusal response."""
        return cls.EXECUTION_REFUSAL
    
    # =========================================
    # MASTER ENFORCEMENT METHOD
    # =========================================
    
    @classmethod
    def enforce_all(cls, question: str, result: Dict[str, Any],
                   data_used: List[Dict] = None) -> Dict[str, Any]:
        """
        Apply ALL Phase-12.1 guardrails to a response.
        
        This is the master method called before ANY response is returned.
        
        ENFORCEMENT ORDER:
        1. Execution/Guarantee block (first)
        2. Scope Safety Check (may return clarification)
        3. Scope drift detection
        4. Confidence clamp
        5. Predictive language safety
        6. Incident count fix
        
        Args:
            question: User's question
            result: Response dict with 'answer', 'confidence_label', etc.
            data_used: Alert data used for the response
            
        Returns:
            Corrected result dict
        """
        # GUARDRAIL 6: Check for execution/guarantee requests FIRST
        if cls.needs_execution_refusal(question):
            return {
                "answer": cls.EXECUTION_REFUSAL,
                "target": result.get("target"),
                "intent": "EXECUTION_BLOCKED",
                "confidence": 1.0,
                "confidence_label": "HIGH",  # We ARE confident we can't do this
                "actions": [],
                "root_cause": None,
                "evidence": [],
                "status": "blocked",
                "question_type": "EXECUTION"
            }
        
        # 🚨 SCOPE SAFETY CHECK: May need clarification
        scope_type, is_valid = cls.scope_safety_check(question)
        if not is_valid and scope_type == 'ambiguous':
            return {
                "answer": cls.get_clarification_response(),
                "target": None,
                "intent": "SCOPE_CLARIFICATION_NEEDED",
                "confidence": 1.0,
                "confidence_label": "HIGH",
                "actions": [],
                "root_cause": None,
                "evidence": [],
                "status": "needs_clarification",
                "question_type": "CLARIFICATION"
            }
        
        # Update and check scope
        scope = cls.update_scope(question)
        
        # GUARDRAIL 1 & 2: Check scope drift
        has_drift, corrected_answer = cls.check_scope_drift(
            question, 
            result.get("answer", ""),
            data_used
        )
        if has_drift:
            result["answer"] = corrected_answer
            result["_scope_corrected"] = True
        
        # Add scope to answer for DB-scoped questions
        if scope.is_database_scoped():
            answer = result.get("answer", "")
            if not answer.startswith(f"**Scope: {scope.database_name}"):
                # Add scope indicator if not already present
                if not re.search(rf'\b{scope.database_name}\b', answer):
                    result["answer"] = f"**Scope: {scope.database_name}**\n\n{answer}"
            result["target"] = scope.database_name
        
        # GUARDRAIL 3: Clamp root cause confidence
        result["answer"] = cls.clamp_root_cause_confidence(result.get("answer", ""))
        result = cls.clamp_confidence_label(result)
        
        # GUARDRAIL 4: Sanitize predictions
        result["answer"] = cls.sanitize_predictions(question, result.get("answer", ""))
        
        # GUARDRAIL 5: Fix incident counts
        result["answer"] = cls.fix_incident_count(question, result.get("answer", ""))
        
        return result
    
    @classmethod
    def self_check(cls, question: str, answer: str) -> List[str]:
        """
        🟢 FINAL SELF-CHECK BEFORE EVERY ANSWER
        
        Returns list of violations found (empty = passed)
        """
        violations = []
        
        scope = cls.get_current_scope()
        
        # ✅ Correct DB scope?
        if scope.is_database_scoped():
            if not re.search(rf'\b{scope.database_name}\b', answer, re.IGNORECASE):
                violations.append(f"Answer doesn't mention active DB scope: {scope.database_name}")
        
        # ✅ No environment drift?
        if scope.is_database_scoped():
            # Check for suspiciously large numbers
            numbers = re.findall(r'\b(\d{6,})\b', answer.replace(',', ''))
            for num in numbers:
                if int(num) > 100000:  # Likely environment total
                    violations.append(f"Possible environment drift: large number {num} in DB-scoped answer")
        
        # ✅ No overconfidence?
        if re.search(r'\bhigh\s+confidence\b', answer, re.IGNORECASE):
            if not re.search(r'(AWR|ASH|trace|metric\s+breach|confirmed)', answer, re.IGNORECASE):
                violations.append("HIGH confidence used without proof (AWR/ASH/trace)")
        
        # ✅ No fake precision?
        if re.search(r'\b\d+\s+unique\s+incidents?\b', answer, re.IGNORECASE):
            if 'approximation' not in answer.lower() and 'pattern' not in answer.lower():
                violations.append("Exact incident count without approximation disclaimer")
        
        # ✅ No guarantees?
        if re.search(r'\b(guarantee|promise|ensure no outage)\b', answer, re.IGNORECASE):
            violations.append("Contains guarantee/promise language")
        
        return violations


# =========================================
# CONVENIENCE FUNCTIONS
# =========================================

def enforce_phase12(question: str, result: Dict[str, Any],
                   data_used: List[Dict] = None) -> Dict[str, Any]:
    """Apply Phase-12.1 guardrails to response."""
    return Phase12Guardrails.enforce_all(question, result, data_used)


def get_active_db_scope() -> Optional[str]:
    """Get current active database scope."""
    scope = Phase12Guardrails.get_current_scope()
    return scope.database_name if scope.is_database_scoped() else None


def reset_db_scope():
    """Reset database scope."""
    Phase12Guardrails.reset_scope()


def self_check_answer(question: str, answer: str) -> List[str]:
    """Run final self-check on answer."""
    return Phase12Guardrails.self_check(question, answer)


def needs_scope_clarification(question: str) -> bool:
    """Check if scope clarification is needed."""
    return Phase12Guardrails.needs_scope_clarification(question)


def get_clarification_response() -> str:
    """Get the clarification response."""
    return Phase12Guardrails.get_clarification_response()


def scope_safety_check(question: str) -> Tuple[str, bool]:
    """Run scope safety check on question."""
    return Phase12Guardrails.scope_safety_check(question)


# =========================================
# MODULE INITIALIZATION
# =========================================

PHASE12_AVAILABLE = True
print("[Phase12.1] Production-Grade DBA Intelligence Guardrails initialized")
