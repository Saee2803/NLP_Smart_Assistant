# reasoning/self_audit_engine.py
"""
PHASE 11: SELF-AUDITING INTELLIGENCE ENGINE

A self-auditing, production-safe, senior DBA intelligence partner
who values correctness over speed and trust over verbosity.

CORE PRINCIPLES:
1. Self-audit every answer before responding
2. Detect and correct contradictions
3. Maintain consistency across conversation
4. Never fabricate, guess, or over-assume
5. Adapt tone strictly to data confidence
6. Learn from mistakes within session

INTEGRATES WITH: dba_guardrails.py for 7-guardrail enforcement
"""

import re
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

# Import the DBA Guardrails system (8 RULES)
try:
    from .dba_guardrails import (
        DBA_GUARDRAILS, AnswerMode, ScopeConstraint,
        apply_guardrails, get_answer_mode, is_strict_value_question,
        extract_scope, cannot_determine, format_safe_prediction,
        # 8 RULES Classes
        ScopeControlGuard,          # RULE 1: Context & Scope Resolution
        PredictiveReasoningSafety,  # RULE 3: Predictive & Root Cause Guardrails
        IncidentCountGuardrail,     # RULE 4: Unique Incident Count
        RiskEscalationLanguage,     # RULE 5: Risk & Escalation Language
        SafeActionBoundaries,       # RULE 6: Execution & Action Safety
        ConfidenceLabelingStandard, # RULE 7: Confidence Labeling Standard
        DBAToneEnforcer,            # RULE 8: Shared Context Tone
    )
    GUARDRAILS_AVAILABLE = True
except ImportError:
    GUARDRAILS_AVAILABLE = False


class TrustMode(Enum):
    """Trust modes for response generation."""
    NORMAL = "NORMAL"      # Full explanations, DBA reasoning
    STRICT = "STRICT"      # Minimal output, no inference (maps to STRICT_VALUE)
    SAFE = "SAFE"          # Cannot answer reliably
    
    @classmethod
    def from_answer_mode(cls, mode) -> 'TrustMode':
        """Convert AnswerMode to TrustMode."""
        if GUARDRAILS_AVAILABLE:
            if mode == AnswerMode.STRICT_VALUE:
                return cls.STRICT
        return cls.NORMAL


class ConfidenceLevel(Enum):
    """Data confidence levels."""
    EXACT = "EXACT"        # Direct from CSV/data
    PARTIAL = "PARTIAL"    # Pattern-based inference
    NONE = "NONE"          # No direct data


@dataclass
class ConversationFact:
    """A fact established in the conversation."""
    fact_type: str          # "count", "status", "database", "conclusion"
    key: str                # e.g., "MIDEVSTB:critical_count"
    value: Any              # The established value
    scope: str              # "primary", "standby", "environment"
    timestamp: datetime     # When established
    question: str           # Original question that established this
    confidence: ConfidenceLevel


@dataclass
class AuditResult:
    """Result of self-audit check."""
    passed: bool
    violations: List[str] = field(default_factory=list)
    corrections: List[str] = field(default_factory=list)
    trust_mode: TrustMode = TrustMode.NORMAL
    confidence: ConfidenceLevel = ConfidenceLevel.EXACT


class ConversationFactRegister:
    """
    Maintains facts established during the conversation.
    Used to detect contradictions and maintain consistency.
    """
    
    def __init__(self):
        self.facts: Dict[str, ConversationFact] = {}
        self.corrections: List[Tuple[str, str, str]] = []  # (key, old, new, reason)
        self._session_learnings: List[str] = []
    
    def register_fact(self, fact_type: str, key: str, value: Any, 
                     scope: str, question: str, 
                     confidence: ConfidenceLevel = ConfidenceLevel.EXACT):
        """Register a new fact from the conversation."""
        fact_key = f"{fact_type}:{key}:{scope}"
        
        self.facts[fact_key] = ConversationFact(
            fact_type=fact_type,
            key=key,
            value=value,
            scope=scope,
            timestamp=datetime.now(),
            question=question,
            confidence=confidence
        )
    
    def get_fact(self, fact_type: str, key: str, scope: str = None) -> Optional[ConversationFact]:
        """Retrieve a previously established fact."""
        if scope:
            fact_key = f"{fact_type}:{key}:{scope}"
            return self.facts.get(fact_key)
        
        # Search across all scopes
        for fk, fact in self.facts.items():
            if fk.startswith(f"{fact_type}:{key}:"):
                return fact
        return None
    
    def check_contradiction(self, fact_type: str, key: str, new_value: Any, 
                           scope: str) -> Tuple[bool, Optional[ConversationFact]]:
        """
        Check if new value contradicts an established fact.
        
        Returns:
            Tuple of (has_contradiction, existing_fact)
        """
        existing = self.get_fact(fact_type, key, scope)
        
        if existing is None:
            return False, None
        
        # Check for numeric contradiction (>5% difference for large numbers)
        if isinstance(existing.value, (int, float)) and isinstance(new_value, (int, float)):
            if existing.value == 0 and new_value == 0:
                return False, existing
            
            # Allow small variance for large numbers
            if existing.value > 1000:
                variance = abs(existing.value - new_value) / max(existing.value, 1)
                if variance > 0.05:  # More than 5% difference
                    return True, existing
            elif existing.value != new_value:
                return True, existing
        
        # Direct comparison for other types
        elif existing.value != new_value:
            return True, existing
        
        return False, existing
    
    def record_correction(self, key: str, old_value: str, new_value: str, reason: str):
        """Record a correction made during the session."""
        self.corrections.append((key, old_value, new_value, reason))
        self._session_learnings.append(f"Corrected {key}: {old_value} → {new_value} ({reason})")
    
    def add_learning(self, learning: str):
        """Add a session learning to avoid repeating mistakes."""
        self._session_learnings.append(learning)
    
    def get_learnings(self) -> List[str]:
        """Get all session learnings."""
        return self._session_learnings.copy()
    
    def reset(self):
        """Reset for new conversation."""
        self.facts.clear()
        self.corrections.clear()
        self._session_learnings.clear()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of registered facts."""
        return {
            "fact_count": len(self.facts),
            "corrections": len(self.corrections),
            "learnings": len(self._session_learnings),
            "facts": {k: {"value": v.value, "scope": v.scope} 
                     for k, v in self.facts.items()}
        }


class TrustModeDetector:
    """Detects which trust mode to use based on question context."""
    
    # Strict mode triggers - ENHANCED with STRICT_VALUE patterns
    STRICT_TRIGGERS = [
        r'give\s+(?:me\s+)?only\s+(?:the\s+)?number',
        r'exact\s+count',
        r'for\s+(?:the\s+)?audit',
        r'only\s+(?:the\s+)?(?:number|count|total)',
        r'number\s+only',
        r'just\s+(?:the\s+)?(?:number|count)',
        r'yes\s+or\s+no',
        r'yes/no',
        r'facts\s+only',
        r'how\s+many\s+[A-Z]+\s+alerts',  # "how many CRITICAL alerts"
        r'which\s+database',
        r'count\s+only',
    ]
    
    # Safe mode triggers (data uncertainty)
    SAFE_TRIGGERS = [
        r'what\s+will\s+happen',
        r'predict\s+(?:the\s+)?exact',
        r'guarantee',
        r'100%\s+(?:sure|certain)',
    ]
    
    @classmethod
    def detect_mode(cls, question: str, data_available: bool = True,
                   data_confidence: ConfidenceLevel = ConfidenceLevel.EXACT) -> TrustMode:
        """
        Detect appropriate trust mode for the question.
        
        Uses the DBA Guardrails AnswerMode if available, otherwise falls back
        to internal pattern matching.
        
        Args:
            question: User's question
            data_available: Whether relevant data exists
            data_confidence: Confidence level in available data
            
        Returns:
            Appropriate TrustMode
        """
        # Use DBA Guardrails if available (Guardrail #1: Answer Precision)
        if GUARDRAILS_AVAILABLE:
            answer_mode = get_answer_mode(question)
            if answer_mode == AnswerMode.STRICT_VALUE:
                return TrustMode.STRICT
        
        q_lower = question.lower()
        
        # Check for strict mode triggers
        for pattern in cls.STRICT_TRIGGERS:
            if re.search(pattern, q_lower):
                return TrustMode.STRICT
        
        # Check for safe mode triggers or data issues
        if not data_available:
            return TrustMode.SAFE
        
        if data_confidence == ConfidenceLevel.NONE:
            return TrustMode.SAFE
        
        for pattern in cls.SAFE_TRIGGERS:
            if re.search(pattern, q_lower):
                return TrustMode.SAFE
        
        return TrustMode.NORMAL


class ScopeValidator:
    """
    Validates that answers respect scope constraints.
    
    INTEGRATES: DBA Guardrails Scope Control (Guardrail #2)
    """
    
    # Primary vs Standby databases
    PRIMARY_INDICATORS = ['primary', 'main', 'prod', 'production']
    STANDBY_INDICATORS = ['standby', 'stbn', 'replica', 'dr', 'secondary']
    
    # Known primary-standby relationships for exact matching
    DB_RELATIONSHIPS = {
        "MIDEVSTB": "MIDEVSTBN",
        "PRODDB": "PRODDB_STANDBY",
        "FINDB": "FINDB_DR",
    }
    
    @classmethod
    def detect_scope(cls, question: str) -> str:
        """
        Detect requested scope from question.
        
        Uses DBA Guardrails if available for enhanced detection.
        """
        # Use DBA Guardrails for scope detection if available
        if GUARDRAILS_AVAILABLE:
            scope = extract_scope(question)
            if scope.primary_only:
                return "primary"
            if scope.standby_only:
                return "standby"
            if scope.target_database:
                # If a specific DB is mentioned, scope to that DB
                return "database"
        
        q_lower = question.lower()
        
        # Explicit scope indicators
        if any(ind in q_lower for ind in ['primary only', 'exclude standby', 
                                          'not standby', 'without standby']):
            return "primary"
        
        if any(ind in q_lower for ind in ['standby only', 'standby database',
                                          'only standby']):
            return "standby"
        
        # Database name patterns - EXACT matching (not substring)
        if re.search(r'\b[A-Z]+STB\b', question.upper()) and 'STBN' not in question.upper():
            return "primary"
        
        if re.search(r'\b[A-Z]+STBN\b', question.upper()):
            return "standby"
        
        return "environment"
    
    @classmethod
    def validate_scope(cls, answer: str, expected_scope: str, 
                       target_db: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Validate that answer respects scope constraints.
        
        Implements Guardrail #2: SCOPE CONTROL
        - If database name mentioned → DO NOT include environment totals
        - If "only" keyword used → treat as HARD FILTER
        - Data outside scope must be IGNORED completely
        
        Returns:
            Tuple of (is_valid, violation_reason)
        """
        answer_upper = answer.upper()
        
        # Primary-only scope should not mention standby data
        if expected_scope == "primary":
            if target_db:
                target_upper = target_db.upper()
                # Get the standby name for this database
                standby_name = cls.DB_RELATIONSHIPS.get(target_upper, f"{target_upper}N")
                
                if standby_name in answer_upper:
                    return False, f"Standby ({standby_name}) mentioned in primary-only scope"
            
            if any(ind in answer_upper for ind in ['STANDBY DATA', 'INCLUDING STANDBY']):
                return False, "Standby data referenced in primary-only scope"
        
        # Standby-only scope should not include primary totals
        if expected_scope == "standby":
            if "PRIMARY" in answer_upper and "NOT PRIMARY" not in answer_upper:
                return False, "Primary data referenced in standby-only scope"
        
        # Database-specific should not show environment totals (Guardrail #2 SCOPE CONTROL)
        if target_db and expected_scope not in ("environment",):
            # Check if answer is showing environment-wide data
            if "ENVIRONMENT" in answer_upper or "ALL DATABASES" in answer_upper:
                return False, f"Environment-wide data shown for {target_db}-specific query"
        
        return True, None
    
    @classmethod
    def extract_target_database(cls, question: str) -> Optional[str]:
        """Extract the target database from a question."""
        if GUARDRAILS_AVAILABLE:
            scope = extract_scope(question)
            return scope.target_database
        
        # Fallback extraction
        patterns = [
            r'for\s+([A-Z][A-Z0-9_]+(?:STB|STBN|DB)?)\b',
            r'on\s+([A-Z][A-Z0-9_]+(?:STB|STBN|DB)?)\b',
            r'\b([A-Z][A-Z0-9_]*(?:STB|STBN))\b',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, question.upper())
            if match:
                return match.group(1)
        
        return None


class SelfAuditEngine:
    """
    Main self-auditing engine for Phase 11.
    
    Performs mandatory self-audit before every response.
    """
    
    def __init__(self):
        self.fact_register = ConversationFactRegister()
        self.mode_detector = TrustModeDetector()
        self.scope_validator = ScopeValidator()
        self._current_mode = TrustMode.NORMAL
        self._audit_count = 0
        self._corrections_made = 0
    
    def audit_response(self, question: str, answer: str, 
                       data_used: List[Dict] = None,
                       extracted_values: Dict[str, Any] = None) -> AuditResult:
        """
        Perform mandatory self-audit on a response.
        
        MUST be called before returning ANY response.
        
        Args:
            question: Original user question
            answer: Generated answer
            data_used: List of data records used
            extracted_values: Key values extracted (counts, databases, etc.)
            
        Returns:
            AuditResult with pass/fail status and any corrections
        """
        self._audit_count += 1
        violations = []
        corrections = []
        
        extracted_values = extracted_values or {}
        data_used = data_used or []
        
        # =========================================
        # 1. QUESTION-ANSWER CONTRACT CHECK
        # =========================================
        trust_mode = self.mode_detector.detect_mode(question, len(data_used) > 0)
        self._current_mode = trust_mode
        
        if trust_mode == TrustMode.STRICT:
            # Check for contract violations
            contract_violations = self._check_strict_contract(question, answer)
            violations.extend(contract_violations)
        
        # =========================================
        # 2. DATA SCOPE VALIDATION
        # =========================================
        expected_scope = self.scope_validator.detect_scope(question)
        target_db = extracted_values.get("target_database")
        
        scope_valid, scope_violation = self.scope_validator.validate_scope(
            answer, expected_scope, target_db
        )
        if not scope_valid:
            violations.append(f"SCOPE_VIOLATION: {scope_violation}")
        
        # =========================================
        # 3. NUMERIC INTEGRITY CHECK
        # =========================================
        if "count" in extracted_values:
            count = extracted_values["count"]
            key = f"{target_db or 'environment'}:count"
            
            has_contradiction, existing = self.fact_register.check_contradiction(
                "count", key, count, expected_scope
            )
            
            if has_contradiction:
                # This is a potential contradiction
                old_val = existing.value if existing else "unknown"
                violations.append(
                    f"NUMERIC_CONTRADICTION: Previously stated {key}={old_val}, "
                    f"now showing {count}"
                )
                corrections.append(
                    f"Reconcile count difference: {old_val} vs {count}"
                )
        
        # =========================================
        # 4. CONFIDENCE LEVEL CHECK
        # =========================================
        data_confidence = self._assess_data_confidence(data_used)
        
        if data_confidence == ConfidenceLevel.NONE and trust_mode != TrustMode.SAFE:
            violations.append("CONFIDENCE_VIOLATION: No data but not in SAFE mode")
        
        # =========================================
        # 5. DETERMINE PASS/FAIL
        # =========================================
        passed = len(violations) == 0
        
        # Register facts if passed
        if passed and "count" in extracted_values:
            self.fact_register.register_fact(
                "count",
                f"{target_db or 'environment'}:count",
                extracted_values["count"],
                expected_scope,
                question,
                data_confidence
            )
        
        return AuditResult(
            passed=passed,
            violations=violations,
            corrections=corrections,
            trust_mode=trust_mode,
            confidence=data_confidence
        )
    
    def _check_strict_contract(self, question: str, answer: str) -> List[str]:
        """Check strict mode contract violations."""
        violations = []
        q_lower = question.lower()
        
        # "Give only the number" -> must be digits only
        if re.search(r'(?:give\s+)?(?:me\s+)?only\s+(?:the\s+)?number', q_lower):
            answer_clean = answer.strip()
            if not answer_clean.isdigit():
                violations.append(
                    f"CONTRACT_VIOLATION: 'Give only number' but answer is '{answer_clean[:50]}'"
                )
        
        # "Yes or No" -> must start with Yes or No
        if re.search(r'yes\s+or\s+no', q_lower):
            if not answer.strip().lower().startswith(('yes', 'no')):
                violations.append(
                    "CONTRACT_VIOLATION: 'Yes or No' question but answer doesn't start with Yes/No"
                )
        
        # Scope-specific queries
        if 'only' in q_lower:
            # Check for database-specific "only" patterns
            db_match = re.search(r'for\s+([A-Za-z0-9_]+)\s+only', q_lower)
            if db_match:
                target = db_match.group(1).upper()
                # Answer should focus on that database
                if target not in answer.upper():
                    violations.append(
                        f"CONTRACT_VIOLATION: Asked for '{target} only' but not in answer"
                    )
        
        return violations
    
    def _assess_data_confidence(self, data_used: List[Dict]) -> ConfidenceLevel:
        """Assess confidence level based on data used."""
        if not data_used:
            return ConfidenceLevel.NONE
        
        if len(data_used) > 0:
            return ConfidenceLevel.EXACT
        
        return ConfidenceLevel.PARTIAL
    
    def format_safe_mode_response(self, question: str, reason: str) -> str:
        """Format a SAFE mode response when we cannot answer reliably."""
        return (
            f"**I cannot answer this reliably with the available data.**\n\n"
            f"**Reason:** {reason}\n\n"
            f"A senior DBA would need additional information to provide "
            f"a trustworthy answer to this question."
        )
    
    def format_contradiction_note(self, old_value: Any, new_value: Any, 
                                   reason: str = None) -> str:
        """Format a note explaining a value difference."""
        note = (
            f"**Note:** Earlier we discussed a value of {old_value}. "
            f"This response shows {new_value}."
        )
        
        if reason:
            note += f" {reason}"
        else:
            note += " This difference may be due to scope or filter changes."
        
        return note
    
    def apply_confidence_tone(self, answer: str, 
                              confidence: ConfidenceLevel) -> str:
        """Apply appropriate tone based on confidence level."""
        if confidence == ConfidenceLevel.EXACT:
            # Confident tone - no changes needed
            return answer
        
        if confidence == ConfidenceLevel.PARTIAL:
            # Add caution prefix
            if not answer.startswith("Based on"):
                return f"**Based on available alert patterns:**\n\n{answer}"
            return answer
        
        if confidence == ConfidenceLevel.NONE:
            # Maximum caution
            return (
                f"**⚠️ Limited Confidence:**\n\n"
                f"{answer}\n\n"
                f"*Note: This assessment has limited data support. "
                f"Verify with direct system inspection.*"
            )
        
        return answer
    
    def record_correction(self, key: str, old_value: str, 
                          new_value: str, reason: str):
        """Record a correction made during the session."""
        self.fact_register.record_correction(key, old_value, new_value, reason)
        self._corrections_made += 1
    
    def add_session_learning(self, learning: str):
        """Add a learning to avoid repeating mistakes."""
        self.fact_register.add_learning(learning)
    
    def get_current_mode(self) -> TrustMode:
        """Get current trust mode."""
        return self._current_mode
    
    def get_stats(self) -> Dict[str, Any]:
        """Get audit statistics."""
        return {
            "audits_performed": self._audit_count,
            "corrections_made": self._corrections_made,
            "current_mode": self._current_mode.value,
            "facts_registered": len(self.fact_register.facts),
            "session_learnings": len(self.fact_register.get_learnings())
        }
    
    def reset(self):
        """Reset for new conversation."""
        self.fact_register.reset()
        self._current_mode = TrustMode.NORMAL
        # Keep audit count and corrections for session stats


# Singleton instance
SELF_AUDIT = SelfAuditEngine()


# =========================================
# RESPONSE WRAPPER WITH FULL 8 RULES GUARDRAILS
# =========================================

def audit_before_respond(question: str, answer: str, 
                         data_used: List[Dict] = None,
                         extracted_values: Dict[str, Any] = None) -> Tuple[str, AuditResult]:
    """
    Apply all 8 RULES and self-audit to a response.
    
    8 RULES APPLIED:
    1. CONTEXT & SCOPE RESOLUTION - Maintain ACTIVE_DB_SCOPE
    2. NUMERIC ANSWER PRECISION - Number-only when asked
    3. PREDICTIVE & ROOT CAUSE GUARDRAILS - No certainty claims
    4. UNIQUE INCIDENT COUNT - Use approximate language
    5. RISK & ESCALATION LANGUAGE - Structure: evidence + uncertainty + missing data
    6. EXECUTION & ACTION SAFETY - Cannot execute changes
    7. CONFIDENCE LABELING - Default MEDIUM, HIGH only with proof
    8. SHARED CONTEXT TONE - DBA peer, concise, technical
    
    Args:
        question: User question
        answer: Generated answer
        data_used: Data records used
        extracted_values: Extracted values (counts, dbs, etc.)
        
    Returns:
        Tuple of (final_answer, audit_result)
    """
    final_answer = answer
    corrections_applied = []
    
    # ===================================================
    # RULE 6: EXECUTION & ACTION SAFETY (Check First)
    # ===================================================
    if GUARDRAILS_AVAILABLE and SafeActionBoundaries.needs_action_refusal(question):
        refusal_response = SafeActionBoundaries.get_safe_response(question)
        audit_result = AuditResult(
            passed=True,
            violations=[],
            corrections=["Applied RULE 6: Execution & Action Safety"],
            trust_mode=TrustMode.SAFE,
            confidence=ConfidenceLevel.EXACT
        )
        return refusal_response, audit_result
    
    # ===================================================
    # RULE 2: NUMERIC ANSWER PRECISION
    # ===================================================
    if GUARDRAILS_AVAILABLE:
        # First, apply DBA Guardrails if available
        final_answer, guardrail_result = apply_guardrails(question, answer, data_used)
        
        # If guardrails made corrections, use corrected answer
        if guardrail_result.corrected_response:
            answer = guardrail_result.corrected_response
        
        # Convert guardrail result to audit result format
        if guardrail_result.mode == AnswerMode.STRICT_VALUE:
            # For STRICT_VALUE mode, return only the value (RULE 2)
            numbers = re.findall(r'\d+', answer.replace(',', ''))
            if numbers:
                # Return the most significant number
                final_answer = max(numbers, key=int)
                audit_result = AuditResult(
                    passed=True,
                    violations=[],
                    corrections=["Applied RULE 2: Numeric Answer Precision"],
                    trust_mode=TrustMode.STRICT,
                    confidence=ConfidenceLevel.EXACT if data_used else ConfidenceLevel.NONE
                )
                return final_answer, audit_result
    
    # ===================================================
    # RULE 8: SHARED CONTEXT TONE (DBA Peer)
    # ===================================================
    if GUARDRAILS_AVAILABLE:
        final_answer = DBAToneEnforcer.enforce_dba_tone(final_answer)
        corrections_applied.append("RULE 8: Shared Context Tone")
    
    # ===================================================
    # RULE 4: UNIQUE INCIDENT COUNT
    # ===================================================
    if GUARDRAILS_AVAILABLE:
        is_compliant, violations = IncidentCountGuardrail.check_incident_count_language(final_answer)
        if not is_compliant:
            final_answer = IncidentCountGuardrail.fix_incident_language(final_answer)
            corrections_applied.append("RULE 4: Unique Incident Count")
    
    # ===================================================
    # RULE 3: PREDICTIVE & ROOT CAUSE GUARDRAILS
    # ===================================================
    if GUARDRAILS_AVAILABLE:
        is_safe, pred_violations = PredictiveReasoningSafety.check_prediction_safety(final_answer)
        if not is_safe:
            final_answer = PredictiveReasoningSafety.sanitize_prediction(final_answer)
            corrections_applied.append("RULE 3: Predictive Guardrails")
    
    # ===================================================
    # RULE 5: RISK & ESCALATION LANGUAGE
    # ===================================================
    if GUARDRAILS_AVAILABLE and RiskEscalationLanguage.is_escalation_question(question):
        is_compliant, risk_violations = RiskEscalationLanguage.check_risk_language(final_answer)
        if not is_compliant:
            corrections_applied.append("RULE 5: Risk Language")
    
    # ===================================================
    # RULE 7: CONFIDENCE LABELING STANDARD
    # ===================================================
    if GUARDRAILS_AVAILABLE:
        is_compliant, conf_violations = ConfidenceLabelingStandard.check_confidence_claims(final_answer)
        if not is_compliant:
            corrections_applied.append("RULE 7: Confidence Labeling")
    
    # Continue with standard self-audit
    audit = SELF_AUDIT.audit_response(question, answer, data_used, extracted_values)
    
    if audit.passed:
        # Apply confidence-appropriate tone
        final_answer = SELF_AUDIT.apply_confidence_tone(final_answer, audit.confidence)
        return final_answer, audit
    
    # Handle failures based on trust mode
    if audit.trust_mode == TrustMode.SAFE:
        # FALLBACK RULE: NO-DATA HANDLING
        if GUARDRAILS_AVAILABLE:
            safe_answer = cannot_determine(
                audit.violations[0] if audit.violations else "Insufficient data",
                "Additional database metrics or live connection"
            )
        else:
            safe_answer = SELF_AUDIT.format_safe_mode_response(
                question, 
                audit.violations[0] if audit.violations else "Insufficient data"
            )
        return safe_answer, audit
    
    # For STRICT mode violations, try to correct
    if audit.trust_mode == TrustMode.STRICT:
        # HARD RULE 5: ANSWER PRECISION - extract just the number
        numbers = re.findall(r'\d+', answer.replace(',', ''))
        if numbers:
            # Return the most significant number
            final_answer = max(numbers, key=int)
            return final_answer, audit
    
    # Return original with warning (minimal, per DBA-Native tone)
    warning = (
        f"**Note:** *{'; '.join(audit.violations[:2])}*\n\n"
        f"{final_answer}"
    )
    return warning, audit


def apply_full_guardrails(question: str, answer: str,
                          data_used: List[Dict] = None) -> str:
    """
    Apply all DBA Guardrails and return the final answer.
    
    This is the simplest entry point for guardrail enforcement.
    
    Args:
        question: User question
        answer: Generated answer
        data_used: Data records used
        
    Returns:
        Final answer with all guardrails applied
    """
    final_answer, _ = audit_before_respond(question, answer, data_used)
    return final_answer
