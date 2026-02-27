# services/intelligence_service.py
"""
==============================================================
INTELLIGENCE SERVICE (WIRING LAYER)
==============================================================

This service:
1. Orchestrates the reasoning pipeline
2. Ensures actions are ALWAYS present (FOR ELIGIBLE INTENTS ONLY)
3. Updates session memory after each analysis
4. Returns enhanced response structure

PRODUCTION ENHANCEMENT (v2.0):
- Integrated with ProductionIntelligenceOrchestrator
- Root cause NEVER Unknown (fallback inference)
- Actions NEVER empty FOR ELIGIBLE INTENTS (risk-based fallback)
- DOWN vs CRITICAL properly separated
- Session memory tracks across all requests

INTENT-BASED ACTION FILTERING (v2.1):
- Actions only included for RISK/FAILURE/INCIDENT intents
- FACTUAL/DESCRIPTIVE intents do NOT get action recommendations
- Matches expert human DBA behavior

CONVERSATIONAL INTELLIGENCE (v2.3):
- Detects follow-up queries (LIMIT, REFERENCE, FILTER)
- Uses session context for intelligent responses
- Resolves "this database", "show me 20", "only critical"
- Provides clarification when context is missing

DBA INTELLIGENCE (v3.0):
- Uses DBAIntelligenceFormatter for enterprise-grade responses
- 5 layers of DBA intelligence in all responses
- Human-like, contextual, actionable responses

Python 3.6.8 compatible.
"""

import re
from data_engine.global_cache import GLOBAL_DATA, SYSTEM_READY
from services.session_store import SessionStore

# INCIDENT INTELLIGENCE ENGINE IMPORT
try:
    from reasoning.incident_intelligence_engine import (
        IncidentIntelligenceEngine,
        INCIDENT_INTELLIGENCE_ENGINE
    )
    INCIDENT_ENGINE_AVAILABLE = True
except ImportError:
    INCIDENT_ENGINE_AVAILABLE = False
    print("[WARNING] Incident Intelligence Engine not available")

# DBA INTELLIGENCE FORMATTER IMPORT (legacy)
try:
    from reasoning.dba_intelligence_formatter import (
        DBAIntelligenceFormatter,
        get_dba_formatter
    )
    DBA_FORMATTER_AVAILABLE = True
except ImportError:
    DBA_FORMATTER_AVAILABLE = False
    print("[WARNING] DBA Intelligence Formatter not available")

# INTENT ENGINE IMPORT for action eligibility check
try:
    from nlp_engine.oem_intent_engine import OEMIntentEngine
    INTENT_ENGINE_AVAILABLE = True
except ImportError:
    INTENT_ENGINE_AVAILABLE = False

# INTENT RESPONSE ROUTER for question type detection
try:
    from nlp_engine.intent_response_router import IntentResponseRouter
    ROUTER_AVAILABLE = True
except ImportError:
    ROUTER_AVAILABLE = False

# PRODUCTION INTELLIGENCE IMPORT
try:
    from incident_engine.production_intelligence_engine import (
        PRODUCTION_INTELLIGENCE,
        ORACodeMappingEngine,
        RootCauseFallbackEngine,
        ActionFallbackEngine,
        DownVsCriticalEngine,
        SessionMemoryEngine
    )
    PRODUCTION_ENGINE_AVAILABLE = True
except ImportError:
    PRODUCTION_ENGINE_AVAILABLE = False

# PHASE 7: ENTERPRISE TRUST ENGINE IMPORT
try:
    from reasoning.enterprise_trust_engine import (
        ENTERPRISE_TRUST,
        TrustedAnswer
    )
    from reasoning.db_scope_guard import DB_SCOPE_GUARD
    from reasoning.answer_confidence_engine import ANSWER_CONFIDENCE
    from reasoning.language_guardrails import LANGUAGE_GUARDRAILS
    PHASE7_TRUST_AVAILABLE = True
except ImportError:
    PHASE7_TRUST_AVAILABLE = False
    print("[WARNING] Phase 7 Enterprise Trust Engine not available")

# PHASE 8: DATA AWARENESS LAYER
try:
    from reasoning.data_awareness_layer import (
        DATA_AWARENESS,
        TEMPORAL_INTELLIGENCE,
        BASELINE_COMPARISON,
        RELATIONSHIP_GRAPH,
        STATE_EXPLAINER
    )
    DATA_AWARENESS_AVAILABLE = True
except ImportError:
    DATA_AWARENESS_AVAILABLE = False
    print("[WARNING] Data Awareness Layer not available")

# PHASE 9: INCIDENT COMMANDER (Autonomous DBA)
try:
    from reasoning.incident_commander import INCIDENT_COMMANDER
    INCIDENT_COMMANDER_AVAILABLE = True
except ImportError:
    INCIDENT_COMMANDER_AVAILABLE = False
    print("[WARNING] Incident Commander not available")

# PHASE 10: ANSWER CONTRACTS (Enterprise-grade validation)
try:
    from reasoning.answer_contracts import (
        ANSWER_CONTRACTS,
        AnswerContract,
        ContractType,
        Audience,
        ConfidenceLevel,
        AnswerContractValidator
    )
    ANSWER_CONTRACTS_AVAILABLE = True
except ImportError:
    ANSWER_CONTRACTS_AVAILABLE = False
    print("[WARNING] Answer Contracts not available")

# PHASE 11: SELF-AUDITING INTELLIGENCE
try:
    from reasoning.self_audit_engine import (
        SELF_AUDIT,
        TrustMode,
        ConfidenceLevel as AuditConfidence,
        audit_before_respond,
        apply_full_guardrails
    )
    SELF_AUDIT_AVAILABLE = True
except ImportError:
    SELF_AUDIT_AVAILABLE = False
    print("[WARNING] Self-Audit Engine not available")

# PHASE-12.1: PRODUCTION-GRADE DBA INTELLIGENCE GUARDRAILS
try:
    from reasoning.phase12_guardrails import (
        Phase12Guardrails,
        enforce_phase12,
        get_active_db_scope,
        reset_db_scope,
        self_check_answer,
        PHASE12_AVAILABLE
    )
except ImportError:
    PHASE12_AVAILABLE = False
    print("[WARNING] Phase-12.1 Guardrails not available")

# DBA GUARDRAILS (8 RULES - Oracle OEM Assistant)
try:
    from reasoning.dba_guardrails import (
        DBA_GUARDRAILS,
        apply_guardrails,
        get_answer_mode,
        is_strict_value_question,
        extract_scope,
        AnswerMode,
        # 8 RULES Classes
        ScopeControlGuard,          # RULE 1: Context & Scope Resolution
        PredictiveReasoningSafety,  # RULE 3: Predictive & Root Cause Guardrails
        IncidentCountGuardrail,     # RULE 4: Unique Incident Count
        RiskEscalationLanguage,     # RULE 5: Risk & Escalation Language
        SafeActionBoundaries,       # RULE 6: Execution & Action Safety
        ConfidenceLabelingStandard, # RULE 7: Confidence Labeling Standard
        DBAToneEnforcer,            # RULE 8: Shared Context Tone
        ConfidenceLevel as GuardrailConfidence,
    )
    DBA_GUARDRAILS_AVAILABLE = True
except ImportError:
    DBA_GUARDRAILS_AVAILABLE = False
    print("[WARNING] DBA Guardrails not available")


class IntelligenceService:
    """
    Central intelligence service for OEM analysis.
    
    Wires together:
    - OEMReasoningPipeline (logic layer)
    - ProductionIntelligenceOrchestrator (industry-grade enhancements)
    - SessionStore (memory layer)
    - Response formatting (API layer)
    - DBAIntelligenceFormatter (enterprise-grade DBA responses)
    
    PRODUCTION FIXES (v2.2):
    - Strict intent-based data isolation
    - STANDBY_DATAGUARD uses ONLY dataguard alerts
    - Session context RESET per question (no leakage)
    - Formatter isolation by question type
    
    CONVERSATIONAL INTELLIGENCE (v2.3):
    - Follow-up detection before pipeline processing
    - Context-aware response generation
    - Smart clarification fallbacks
    
    DBA INTELLIGENCE (v3.0):
    - All responses enhanced with DBA context
    - Incident reasoning (duplicates vs unique)
    - Human-like, non-robotic responses
    """
    
    def __init__(self):
        self._pipeline = None
        self._production_engine_used = False
        # CRITICAL: Track formatter context per-request (NOT cached)
        self._current_formatter_context = None
        
        # INCIDENT INTELLIGENCE ENGINE - Enterprise DBA Intelligence
        self._incident_engine = None
        if INCIDENT_ENGINE_AVAILABLE:
            try:
                self._incident_engine = INCIDENT_INTELLIGENCE_ENGINE
            except Exception:
                pass
        
        # DBA Intelligence Formatter for enterprise-grade responses (legacy fallback)
        self._dba_formatter = None
        if DBA_FORMATTER_AVAILABLE:
            try:
                self._dba_formatter = get_dba_formatter()
            except Exception:
                pass
    
    @property
    def pipeline(self):
        """Lazy-load the reasoning pipeline."""
        if self._pipeline is None:
            from nlp_engine.oem_reasoning_pipeline import OEMReasoningPipeline
            self._pipeline = OEMReasoningPipeline()
        return self._pipeline
    
    def _reset_formatter_context(self):
        """
        CRITICAL FIX: Reset formatter context for each new question.
        Prevents root cause/action leakage between questions.
        """
        self._current_formatter_context = {
            "root_cause": None,
            "actions": [],
            "confidence": None,
            "evidence": []
        }
        # Also reset SessionStore's per-question context
        SessionStore.reset_question_context()
    
    # =====================================================
    # CRITICAL FIX: Strict DB Matching Helper
    # Prevents MIDEVSTB from matching MIDEVSTBN
    # =====================================================
    def _filter_alerts_by_db_strict(self, alerts, db_name):
        """
        Filter alerts for a specific database using EXACT match.
        
        CRITICAL: Previously used 'db_upper in target' which caused
        MIDEVSTB to match MIDEVSTBN. Now uses EXACT match only.
        
        Handles targets like:
        - "MIDEVSTB" -> matches MIDEVSTB
        - "MIDEVSTB:listener" -> extract DB name, matches MIDEVSTB
        - "MIDEVSTBN:cpu" -> extract DB name, matches MIDEVSTBN (NOT MIDEVSTB)
        
        Args:
            alerts: List of alerts
            db_name: Database name to filter for
            
        Returns:
            List of alerts for exactly this database
        """
        db_upper = db_name.upper().strip()
        
        def extract_db_name(target_str):
            """Extract DB name from target like 'MIDEVSTB:listener' -> 'MIDEVSTB'"""
            if not target_str:
                return ""
            target_upper = target_str.upper().strip()
            # If has colon, take the part before it
            if ':' in target_upper:
                return target_upper.split(':')[0]
            return target_upper
        
        def is_exact_match(alert):
            target = alert.get("target_name") or alert.get("target") or ""
            target_db = extract_db_name(target)
            return target_db == db_upper
        
        return [a for a in alerts if is_exact_match(a)]
    
    # =====================================================
    # STRICT OUTPUT MODE: "Give only the number"
    # =====================================================
    def _is_strict_number_mode(self, question):
        """
        Detect if user wants ONLY a number, no explanation.
        
        Patterns:
        - "give only the number"
        - "just the number"
        - "only number"
        - "number only"
        """
        q_lower = question.lower()
        patterns = [
            r'(?:give\s+)?(?:me\s+)?only\s+(?:the\s+)?number',
            r'just\s+(?:the\s+)?number',
            r'number\s+only',
            r'only\s+(?:a\s+)?number'
        ]
        return any(re.search(p, q_lower) for p in patterns)
    
    # =====================================================
    # PHASE 7: ENTERPRISE TRUST WRAPPER
    # Apply trust processing to any response
    # =====================================================
    def _apply_phase7(self, response, question, alerts=None):
        """
        Apply Phase 7 Enterprise Trust processing to any response.
        
        This ensures ALL responses go through:
        - Trust scoring
        - Scope validation
        - Confidence calibration
        - Language guardrails
        - PHASE 10: Answer Contract Enforcement
        - PHASE 11: Self-Audit Intelligence
        
        Args:
            response: The response dict to enhance
            question: Original user question
            alerts: Optional alerts used (for scope validation)
            
        Returns:
            Enhanced response with phase7 metadata
        """
        # =====================================================
        # PHASE 11: SELF-AUDIT + DBA GUARDRAILS (7 Guardrails)
        # Audit BEFORE returning any response
        # =====================================================
        if SELF_AUDIT_AVAILABLE:
            try:
                # Extract values for fact registration
                extracted_values = {}
                if response.get("result_count") is not None:
                    extracted_values["count"] = response.get("result_count")
                if response.get("target"):
                    extracted_values["target_database"] = response.get("target")
                
                # Use audit_before_respond which includes ALL 7 DBA Guardrails
                original_answer = response.get("answer", "")
                audited_answer, audit_result = audit_before_respond(
                    question=question,
                    answer=original_answer,
                    data_used=alerts or [],
                    extracted_values=extracted_values
                )
                
                # Store audit metadata
                response["self_audit"] = {
                    "passed": audit_result.passed,
                    "trust_mode": audit_result.trust_mode.value,
                    "confidence": audit_result.confidence.value,
                    "violations": audit_result.violations[:3] if audit_result.violations else [],
                    "corrections": audit_result.corrections[:2] if audit_result.corrections else [],
                    "dba_guardrails_applied": DBA_GUARDRAILS_AVAILABLE
                }
                
                # Use the guardrail-processed answer
                response["answer"] = audited_answer
                    
            except Exception as e:
                response["self_audit"] = {"error": str(e)}
        
        # =====================================================
        # PHASE 10: ANSWER CONTRACT ENFORCEMENT
        # Validate response against its contract FIRST
        # =====================================================
        if ANSWER_CONTRACTS_AVAILABLE:
            try:
                contract = ANSWER_CONTRACTS.build_contract(question)
                original_answer = response.get("answer", "")
                
                # Enforce contract
                validated_answer, is_valid, violation = ANSWER_CONTRACTS.enforce(
                    original_answer, 
                    contract
                )
                
                # Update response with validated answer
                response["answer"] = validated_answer
                
                # Add contract metadata
                response["answer_contract"] = {
                    "type": contract.contract_type.value,
                    "audience": contract.audience.value,
                    "is_valid": is_valid,
                    "violation": violation,
                    "numeric_only": contract.numeric_only,
                    "target_database": contract.target_database,
                }
                
                # If numeric-only mode, skip further processing
                if contract.numeric_only:
                    response["phase7"] = {"phase7_processed": False, "reason": "numeric_only_mode"}
                    return response
                    
            except Exception as e:
                response["answer_contract"] = {"error": str(e)}
        
        if not PHASE7_TRUST_AVAILABLE:
            response["phase7"] = {"phase7_processed": False}
            return response
        
        try:
            q_lower = question.lower()
            
            # Determine answer type
            if "how many" in q_lower or response.get("result_count", 0) > 0:
                answer_type = "count"
            elif "predict" in q_lower or "will" in q_lower:
                answer_type = "prediction"
            elif response.get("root_cause"):
                answer_type = "root_cause"
            else:
                answer_type = "general"
            
            # Get target for scope validation
            target = response.get("target")
            
            # Get alerts for scope validation
            target_alerts = alerts or []
            if target and target_alerts:
                filtered, _ = DB_SCOPE_GUARD.filter_alerts_strict(target_alerts, target)
                target_alerts = filtered
            
            # Process through trust engine
            trusted = ENTERPRISE_TRUST.process_answer(
                question=question,
                raw_answer=response.get("answer", ""),
                answer_type=answer_type,
                target_database=target,
                alerts_used=target_alerts[:100]
            )
            
            # Apply sanitized answer
            response["answer"] = trusted.answer
            
            # Update confidence from Phase 7
            response["confidence"] = trusted.confidence.score
            response["confidence_label"] = trusted.confidence.level.value
            
            # Add Phase 7 metadata
            response["phase7"] = {
                "trust_score": trusted.trust_score,
                "scope_valid": trusted.scope_valid.is_valid,
                "quality_passed": trusted.quality_check.passed,
                "phase7_processed": True
            }
        except Exception as e:
            response["phase7"] = {"phase7_processed": False, "error": str(e)}
        
        return response
    
    # =====================================================
    # CONVERSATIONAL INTELLIGENCE - FOLLOW-UP DETECTION
    # =====================================================
    
    def _classify_question_intent(self, question):
        """
        Classify the INTENT TYPE of a question.
        
        CRITICAL: This determines if a question is truly NEW or a follow-up.
        
        Returns:
            tuple: (intent_type, sub_type, detected_entity)
            
        Intent types:
            FACT_COUNT        → how many, total, count
            FACT_TIME         → peak hour, when, time
            FACT_ENTITY       → which database, which tablespace
            FACT_DISTRIBUTION → breakdown, top N, most frequent
            STATUS            → down, critical, healthy, running
            ANALYSIS          → why, root cause, reason
            PREDICTION        → likely to fail, will fail
            ACTION            → what should DBA do
            STANDBY           → standby, data guard, apply lag
            TABLESPACE        → tablespace, space, full
        """
        q_lower = question.lower().strip()
        q_upper = question.upper()
        
        # Extract any database entity mentioned
        detected_entity = None
        db_patterns = [
            r'\b([A-Z][A-Z0-9_]{2,}(?:STB|STBN|DB|PRD|DEV|TST))\b',
            r'(?:for|about|on)\s+([A-Z][A-Z0-9_]{3,})\b'
        ]
        for pattern in db_patterns:
            match = re.search(pattern, q_upper)
            if match:
                potential = match.group(1)
                excluded = {"THE", "FOR", "AND", "WITH", "SHOW", "THIS", "THAT", 
                           "FROM", "ONLY", "ALERTS", "CRITICAL", "DATABASE", "STATUS",
                           "WHAT", "WHICH", "WHERE", "WHEN", "WHY", "HOW"}
                if potential not in excluded and len(potential) >= 4:
                    detected_entity = potential
                    break
        
        # ACTION: what should DBA do
        if any(p in q_lower for p in ["what should", "what can", "what action", "recommend", "suggestion", "dba do"]):
            return ("ACTION", None, detected_entity)
        
        # STATUS: down, critical, healthy
        if any(p in q_lower for p in ["down", "offline", "unavailable", "is it down", "are.*down"]):
            return ("STATUS", "DOWN", detected_entity)
        if any(p in q_lower for p in ["critical", "is.*critical", "are.*critical"]):
            return ("STATUS", "CRITICAL", detected_entity)
        if any(p in q_lower for p in ["healthy", "running", "up", "status"]):
            return ("STATUS", "HEALTH", detected_entity)
        
        # ANALYSIS: why, root cause
        if any(p in q_lower for p in ["why", "root cause", "reason", "cause of", "explain"]):
            return ("ANALYSIS", None, detected_entity)
        
        # PREDICTION: likely to fail
        if any(p in q_lower for p in ["predict", "likely to fail", "will fail", "going to fail", "at risk", "most likely"]):
            return ("PREDICTION", None, detected_entity)
        
        # FACT_COUNT: how many, total, count
        if any(p in q_lower for p in ["how many", "count", "total", "number of"]):
            return ("FACT_COUNT", None, detected_entity)
        
        # FACT_TIME: peak hour, when
        if any(p in q_lower for p in ["peak hour", "which hour", "what hour", "when", "time", "busiest"]):
            return ("FACT_TIME", None, detected_entity)
        
        # TABLESPACE: tablespace issues
        if any(p in q_lower for p in ["tablespace", "space", "full", "storage"]):
            return ("TABLESPACE", None, detected_entity)
        
        # STANDBY: standby/dataguard issues
        if any(p in q_lower for p in ["standby", "data guard", "dataguard", "apply lag", "transport", "replica", "dr "]):
            return ("STANDBY", None, detected_entity)
        
        # FACT_DISTRIBUTION: breakdown, top, most
        if any(p in q_lower for p in ["breakdown", "distribution", "top ", "most ", "frequent", "which database"]):
            return ("FACT_DISTRIBUTION", None, detected_entity)
        
        # FACT_ENTITY: specific entity query
        if detected_entity:
            return ("FACT_ENTITY", None, detected_entity)
        
        # Default to generic FACT
        return ("FACT", None, detected_entity)
    
    def _is_obvious_followup(self, question):
        """
        Check if this is OBVIOUSLY a follow-up (before context reset check).
        
        These patterns are unambiguously follow-ups and should NEVER reset context:
        - "ok show me 20"
        - "only critical"
        - "top 10"
        - "more"
        - "show me more"
        - "only the errors"
        """
        q_lower = question.lower().strip()
        
        # Obvious follow-up patterns - these NEVER reset context
        obvious_followup_patterns = [
            r"^ok\b",                          # "ok show me 20", "ok just 5"
            r"^only\b",                        # "only critical", "only errors"
            r"^just\b",                        # "just the critical ones"
            r"^top \d+",                       # "top 10", "top 5"
            r"^show me \d+",                   # "show me 20"
            r"^give me \d+",                   # "give me 10"
            r"^\d+ more",                      # "10 more"
            r"^more\b",                        # "more", "more results"
            r"^less\b",                        # "less"
            r"^first \d+",                     # "first 10"
            r"^last \d+",                      # "last 5"
            r"^limit",                         # "limit to 10"
            r"^filter",                        # "filter by critical"
            r"^sort",                          # "sort by time"
            r"^group",                         # "group by severity"
            r"^what about those",              # reference to previous
            r"^and those",                     # continuation
            r"^same",                          # "same database", "same for"
            r"^this ",                         # "this database", "this one"
            r"^these ",                        # "these alerts"
            r"^that ",                         # "that database"
            r"^those ",                        # "those errors"
        ]
        
        for pattern in obvious_followup_patterns:
            if re.search(pattern, q_lower):
                return True
        
        # Short questions with just numbers are follow-ups
        if re.match(r'^(\d+)$', q_lower):  # Just "10" or "20"
            return True
        
        # "show me X" where X is a number is a follow-up
        if re.match(r'^show\s+me\s+\d+$', q_lower):
            return True
        
        return False
    
    def _should_reset_context(self, question):
        """
        Determine if context should be RESET for this question.
        
        CRITICAL: A question is NEW (requires context reset) if:
        1. Intent type CHANGES (e.g., STANDBY → FACT_COUNT)
        2. New database entity is mentioned that differs from context
        3. Explicit fresh question patterns are detected
        
        BUT FIRST: Check if this is an obvious follow-up!
        
        Returns:
            bool: True if context should be reset
        """
        # FIRST: Check if this is an obvious follow-up - NEVER reset for these
        if self._is_obvious_followup(question):
            return False
        
        # Classify the incoming question
        new_intent, new_subtype, new_entity = self._classify_question_intent(question)
        
        # Get current context
        context = SessionStore.get_conversation_context()
        
        # If no prior context, no need to reset
        if not context.get("has_context"):
            return False
        
        old_topic = context.get("topic", "")
        old_alert_type = context.get("alert_type", "")
        old_databases = context.get("databases", [])
        
        # Map old topic to intent type for comparison
        old_intent = None
        if old_topic == "STANDBY_ALERTS" or old_alert_type == "dataguard":
            old_intent = "STANDBY"
        elif old_topic == "TABLESPACE_ALERTS" or old_alert_type == "tablespace":
            old_intent = "TABLESPACE"
        elif old_topic == "CRITICAL_ALERTS":
            old_intent = "STATUS"
        elif old_topic:
            old_intent = "FACT"
        
        # RULE 1: Intent type change = NEW question
        if old_intent and new_intent != old_intent:
            # Check if this is a significant intent change
            significant_changes = [
                ("STANDBY", "FACT_COUNT"),
                ("STANDBY", "FACT_TIME"),
                ("STANDBY", "STATUS"),
                ("STANDBY", "ANALYSIS"),
                ("TABLESPACE", "FACT_COUNT"),
                ("TABLESPACE", "FACT_TIME"),
                ("TABLESPACE", "STATUS"),
                ("FACT_COUNT", "FACT_TIME"),
                ("FACT_TIME", "FACT_COUNT"),
                ("STATUS", "FACT_COUNT"),
                ("STATUS", "FACT_TIME"),
                ("ANALYSIS", "FACT_COUNT"),
                ("ANALYSIS", "FACT_TIME"),
                ("FACT", "STANDBY"),
                ("FACT", "TABLESPACE"),
            ]
            if (old_intent, new_intent) in significant_changes or (new_intent, old_intent) in significant_changes:
                return True
        
        # RULE 2: New entity that differs from context
        if new_entity and old_databases:
            if new_entity.upper() not in [db.upper() for db in old_databases]:
                # Only reset if this is a standalone entity question, not a filter within scope
                q_lower = question.lower()
                # Don't reset if user says "show me alerts for X" (could be filtering within scope)
                # DO reset if user says "what about X", "how is X", "is X down"
                if any(p in q_lower for p in ["what about", "how is", "how about", "status of"]):
                    return True
                # Check for "is X down" pattern
                if re.search(r'\bis\s+\w+\s+down\b', q_lower):
                    return True
        
        # RULE 3: Explicit fresh question indicators
        q_lower = question.lower()
        fresh_indicators = [
            r"^how many\b",
            r"^which hour\b",
            r"^what is the peak\b",
            r"^are any databases\b",
            r"^is any database\b",
            r"^what errors\b",
            r"^why does\b",
            r"^what should\b",
        ]
        for pattern in fresh_indicators:
            if re.search(pattern, q_lower):
                return True
        
        return False
    
    def _detect_followup_type(self, question):
        """
        Detect if this is a follow-up query and what type.
        
        Types:
        - LIMIT: "show me 20", "top 10", "only 5"
        - REFERENCE: "this database", "same one", "these alerts"
        - FILTER: "only critical", "just errors"
        - ENTITY_SPECIFIC: "show me alerts for DBNAME"
        
        Returns:
            tuple: (is_followup, followup_type, extracted_value)
        """
        q_lower = question.lower().strip()
        q_upper = question.upper()
        
        # Check for explicit database name FIRST (takes priority)
        # Pattern: Database names are typically uppercase with STB/STBN/DB/PRD/DEV suffix
        db_patterns = [
            r'\b([A-Z][A-Z0-9_]{2,}(?:STB|STBN|DB|PRD|DEV|TST))\b',  # Standard suffixes
            r'(?:for|about|on)\s+([A-Z][A-Z0-9_]{3,})\b',            # "for DBNAME"
            r'\balerts?\s+(?:for|on|from)\s+([A-Z][A-Z0-9_]{3,})\b'  # "alerts for DBNAME"
        ]
        
        for pattern in db_patterns:
            db_match = re.search(pattern, q_upper)
            if db_match:
                potential_db = db_match.group(1)
                # Exclude common English words that might match
                excluded = {"THE", "FOR", "AND", "WITH", "SHOW", "THIS", "THAT", 
                           "FROM", "ONLY", "ALERTS", "CRITICAL", "DATABASE", "STATUS"}
                if potential_db not in excluded and len(potential_db) >= 4:
                    # Verify it looks like a database name
                    alerts = GLOBAL_DATA.get("alerts", [])
                    if alerts:
                        # CRITICAL FIX: Check more alerts and use PARTIAL matching
                        # First 200 alerts may not contain all database names
                        # Also use partial match for names like MIDEVSTB/MIDEVSTBN
                        for a in alerts[:2000]:  # Check first 2000 alerts
                            if a:
                                t = (a.get("target_name") or a.get("target") or "").upper()
                                # CRITICAL FIX: Use partial matching
                                if t == potential_db or potential_db in t or t in potential_db:
                                    return (True, "ENTITY_SPECIFIC", potential_db)
                    else:
                        # No alerts loaded, but pattern looks like a DB name
                        if any(suf in potential_db for suf in ["STB", "STBN", "DB", "PRD", "DEV"]):
                            return (True, "ENTITY_SPECIFIC", potential_db)
        
        # LIMIT patterns: "show me 20", "top 10", "only 5"
        # CRITICAL FIX: Also check for severity word in same query
        # e.g., "ok show me 18 warning" → LIMIT_FILTER with (18, "WARNING")
        limit_patterns = [
            r"show\s+(?:me\s+)?(\d+)",
            r"(?:top|first|last)\s+(\d+)",
            r"only\s+(\d+)",
            r"(\d+)\s+(?:alerts?|issues?|errors?)",
            r"give\s+(?:me\s+)?(\d+)"
        ]
        for pattern in limit_patterns:
            match = re.search(pattern, q_lower)
            if match:
                try:
                    limit = int(match.group(1))
                    print("[FOLLOWUP DEBUG] Matched LIMIT pattern, limit={}".format(limit))
                    # CRITICAL FIX: Check if there's ALSO a severity filter in the query
                    # FIX: Include plural forms (warnings, criticals, errors)
                    severity_match = re.search(r'\b(critical|criticals|warning|warnings|info|high|error|errors)\b', q_lower)
                    if severity_match:
                        severity_word = severity_match.group(1).lower().rstrip('s')  # Normalize plurals
                        severity_map = {"critical": "CRITICAL", "high": "CRITICAL",
                                       "error": "CRITICAL", "warning": "WARNING", "info": "INFO"}
                        severity = severity_map.get(severity_word, None)
                        print("[FOLLOWUP DEBUG] Also found severity={}, returning LIMIT_FILTER".format(severity))
                        # Return combined LIMIT_FILTER with tuple of (limit, severity)
                        return (True, "LIMIT_FILTER", (limit, severity))
                    print("[FOLLOWUP DEBUG] No severity found, returning LIMIT")
                    return (True, "LIMIT", limit)
                except (ValueError, IndexError):
                    pass
        
        # Also check word numbers
        word_nums = {"five": 5, "ten": 10, "twenty": 20, "thirty": 30, "fifty": 50}
        for word, num in word_nums.items():
            if word in q_lower and ("show" in q_lower or "top" in q_lower or "list" in q_lower):
                return (True, "LIMIT", num)
        
        # REFERENCE patterns: "this database", "same one", "these databases"
        ref_patterns = [
            r"\b(?:this|that|these|those)\s+(?:database|db|server|alert|one|issue)s?",
            r"\bsame\s+(?:database|db|one|alert)s?",
            r"\bfor\s+(?:this|that|these|those|it|them)\b",
            r"\bthe\s+same\b",
            r"\bthese\s+(?:ones?|alerts?|issues?|databases?)?\b",
            r"\bthose\s+(?:ones?|alerts?|issues?|databases?)?\b",
            r"\bfor\s+them\b"
        ]
        for pattern in ref_patterns:
            if re.search(pattern, q_lower):
                return (True, "REFERENCE", None)
        
        # CONTINUATION patterns: "ok", "show more", "next", "continue"
        # These require prior context to make sense
        context = SessionStore.get_conversation_context()
        if context.get("has_context"):
            continuation_patterns = [
                r"^ok\b",
                r"^yes\b",
                r"^sure\b",
                r"\bshow\s+more\b",
                r"\bmore\s+(?:alerts?|details?|info)?\b",
                r"\bnext\b",
                r"\bcontinue\b"
            ]
            for pattern in continuation_patterns:
                if re.search(pattern, q_lower):
                    return (True, "CONTINUATION", None)
        
        # FILTER patterns: "only critical", "just errors"
        # FIX: Include plural forms (warnings, criticals, errors)
        filter_patterns = [
            (r"\bonly\s+(critical|criticals|high|error|errors|warning|warnings|info)", "severity"),
            (r"\bjust\s+(critical|criticals|high|error|errors|warning|warnings)", "severity"),
            (r"(critical|criticals|high|warning|warnings)\s+(?:only|ones?)", "severity"),
        ]
        for pattern, filter_type in filter_patterns:
            match = re.search(pattern, q_lower)
            if match:
                severity_word = match.group(1).lower().rstrip('s')  # Normalize plurals
                severity_map = {"critical": "CRITICAL", "high": "CRITICAL", 
                              "error": "CRITICAL", "warning": "WARNING", "info": "INFO"}
                severity = severity_map.get(severity_word, "CRITICAL")
                return (True, "FILTER", severity)
        
        # =====================================================
        # SHORTHAND patterns: Short questions that inherit scope
        # "Critical count?", "Total alerts?", "Status?", "Is it fine?"
        # =====================================================
        shorthand_patterns = [
            (r"^critical\s+count\??$", "CRITICAL"),
            (r"^warning\s+count\??$", "WARNING"),
            (r"^total\s+(?:count|alerts?)?\??$", None),
            (r"^count\??$", None),
            (r"^status\??$", None),
            (r"^is\s+(?:this|it)\s+(?:db\s+)?(?:fine|ok|stable)\??$", None),
            (r"^(?:this|that)\s+db\s+(?:fine|ok|stable|looks?\s+fine)\??$", None),
            (r"^root\s+cause\??$", None),
            (r"^what\s+(?:is|was)\s+the\s+root\s+cause\??$", None),
        ]
        for pattern, severity in shorthand_patterns:
            if re.match(pattern, q_lower):
                if severity:
                    return (True, "FILTER", severity)
                else:
                    return (True, "SHORTHAND", None)
        
        return (False, None, None)
    
    def _handle_followup(self, question, followup_type, extracted_value, alerts):
        """
        Handle follow-up queries using session context.
        
        CRITICAL FIX v2: When user explicitly mentions a database name with "show alerts for X",
        this should be treated as a NEW query, not a follow-up within existing scope.
        
        Returns:
            dict with answer and metadata, or None if can't handle
        """
        context = SessionStore.get_conversation_context()
        q_lower = question.lower()
        
        # ENTITY_SPECIFIC: User specified a database name
        if followup_type == "ENTITY_SPECIFIC":
            db_name = extracted_value
            
            # =====================================================
            # CRITICAL FIX v2: Check if this is an EXPLICIT DB query
            # Pattern: "show me alerts for X", "alerts for X", "X status"
            # These should RESET context and start fresh for the new DB
            # =====================================================
            is_explicit_db_query = any(p in q_lower for p in [
                "show me alerts for",
                "show alerts for", 
                "alerts for",
                "show me {} ".format(db_name.lower()),
                "show me {0} alerts".format(db_name.lower()),
                "{0} status".format(db_name.lower()),
                "{0} alerts".format(db_name.lower())
            ])
            
            # Also check if DB name is DIFFERENT from current context
            current_target = context.get("last_target", "").upper() if context.get("last_target") else ""
            db_is_different = db_name.upper() != current_target
            
            if is_explicit_db_query or db_is_different:
                # This is a NEW query for a specific DB - reset context
                # Don't carry over standby/tablespace filters from previous conversation
                SessionStore.set_conversation_context(
                    topic=None,
                    alert_type=None,
                    severity=None,
                    displayed_count=0,
                    result_count=0,
                    has_context=False
                )
                return self._generate_db_specific_answer(question, db_name, alerts, {})
            
            # Same DB mentioned again within existing scope - filter within scope
            if context.get("has_context"):
                return self._handle_entity_within_scope(question, db_name, alerts, context)
            else:
                return self._generate_db_specific_answer(question, db_name, alerts, context)
        
        # For other follow-ups, we need prior context
        if not context.get("has_context"):
            return self._get_clarification_response(followup_type)
        
        if followup_type == "LIMIT":
            return self._handle_limit_followup(question, extracted_value, alerts, context)
        
        # CRITICAL FIX: Handle combined LIMIT + FILTER (e.g., "ok show me 18 warning")
        elif followup_type == "LIMIT_FILTER":
            limit, severity = extracted_value
            return self._handle_limit_filter_followup(question, limit, severity, alerts, context)
        
        elif followup_type == "REFERENCE":
            return self._handle_reference_followup(question, alerts, context)
        
        elif followup_type == "FILTER":
            return self._handle_filter_followup(question, extracted_value, alerts, context)
        
        elif followup_type == "CONTINUATION":
            return self._handle_continuation_followup(question, alerts, context)
        
        # =====================================================
        # SHORTHAND: "Critical count?", "Status?", "Is it fine?"
        # These inherit the last_target from context
        # =====================================================
        elif followup_type == "SHORTHAND":
            return self._handle_shorthand_followup(question, alerts, context)
        
        return None
    
    def _handle_entity_within_scope(self, question, db_name, alerts, context):
        """
        Handle database entity mentioned within an active scope.
        
        CRITICAL: This NARROWS the scope, it does NOT reset to global.
        
        Example flow:
            "show me standby issues" → context: topic=STANDBY_ALERTS
            "show me alerts for MIDDEVSTB" → filter STANDBY alerts for MIDDEVSTB only
        
        Args:
            question: User's question
            db_name: Database name extracted from question
            alerts: All alerts
            context: Current conversation context
            
        Returns:
            dict with scoped, filtered answer
        """
        db_upper = db_name.upper()
        topic = context.get("topic", "alerts")
        alert_type = context.get("alert_type")
        severity_filter = context.get("severity")
        
        # Step 1: Start with alerts for this database
        # CRITICAL FIX: Use STRICT matching to prevent MIDEVSTB matching MIDEVSTBN
        db_alerts = self._filter_alerts_by_db_strict(alerts, db_name)
        
        # Step 2: Apply the ACTIVE SCOPE filter (this is the critical fix)
        if alert_type == "dataguard":
            dg_keywords = ["standby", "data guard", "dataguard", "apply", "transport", "mrp", "redo", "ora-16"]
            db_alerts = [a for a in db_alerts if 
                        any(kw in (a.get("message") or a.get("msg_text") or "").lower() for kw in dg_keywords) or
                        any(kw in (a.get("issue_type") or "").lower() for kw in ["standby", "dataguard"])]
        elif alert_type == "tablespace":
            ts_keywords = ["tablespace", "space", "full", "extent", "ora-1654", "ora-1653"]
            db_alerts = [a for a in db_alerts if 
                        any(kw in (a.get("message") or a.get("msg_text") or "").lower() for kw in ts_keywords)]
        
        # Step 3: Apply severity filter if active
        # CRITICAL FIX: Case-insensitive comparison
        if severity_filter:
            severity_upper = severity_filter.upper()
            db_alerts = [a for a in db_alerts if 
                        (a.get("severity") or a.get("alert_state") or "").upper() == severity_upper]
        
        # Build scoped answer
        scope_label = self._get_scope_label(topic, alert_type)
        
        if not db_alerts:
            # IMPORTANT: Return "no X alerts for Y" NOT global summary
            return {
                "answer": "No {0} found for database **{1}**.".format(scope_label, db_name),
                "target": db_name,
                "intent": "FACT_SCOPED",
                "confidence": 0.9,
                "question_type": "FACT"
            }
        
        # Count by severity - CRITICAL FIX: Normalize to UPPERCASE
        severity_counts = {}
        for a in db_alerts:
            sev = (a.get("severity") or a.get("alert_state") or "UNKNOWN").upper()
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        
        # Build answer
        answer = "**{0}** for **{1}**: **{2}** alert(s)".format(
            scope_label.title(), db_name, len(db_alerts))
        
        if severity_counts:
            sev_parts = []
            for sev in ["CRITICAL", "WARNING", "INFO"]:
                if sev in severity_counts:
                    sev_parts.append("{0} {1}".format(severity_counts[sev], sev))
            if sev_parts:
                answer += " ({0})".format(", ".join(sev_parts))
        
        answer += ".\n\n"
        
        # Show top alerts (limit to 10)
        top_alerts = db_alerts[:10]
        if top_alerts:
            answer += "**Top Issues:**\n"
            for i, alert in enumerate(top_alerts, 1):
                msg = alert.get("message") or alert.get("msg_text") or "Unknown issue"
                if len(msg) > 100:
                    msg = msg[:97] + "..."
                sev = alert.get("severity", "")
                answer += "{0}. [{1}] {2}\n".format(i, sev, msg)
        
        # Update context - NARROW the scope to this database
        SessionStore.set_conversation_context(
            databases=[db_name],
            result_count=len(db_alerts)
        )
        SessionStore.update(last_target=db_name)
        
        return {
            "answer": answer.strip(),
            "target": db_name,
            "intent": "FACT_SCOPED",
            "confidence": 0.9,
            "question_type": "FACT"
        }
    
    def _get_scope_label(self, topic, alert_type):
        """Get human-readable label for the current scope."""
        if alert_type == "dataguard":
            return "standby/Data Guard alerts"
        elif alert_type == "tablespace":
            return "tablespace alerts"
        elif topic:
            return topic.replace("_", " ").lower()
        return "alerts"
    
    def _handle_continuation_followup(self, question, alerts, context):
        """Handle CONTINUATION follow-ups: ok, show more, next."""
        # Get alerts based on last context with default limit
        filtered_alerts = self._filter_alerts_by_context(alerts, context)
        
        if not filtered_alerts:
            return {
                "answer": "No more alerts found matching previous criteria.",
                "target": context.get("last_target"),
                "confidence": 0.5
            }
        
        # CRITICAL FIX: Use displayed_count (actual alerts shown to user) not result_count
        # displayed_count tracks how many alerts user has actually SEEN
        displayed_count = context.get("displayed_count", 0)
        limit = 10
        start = min(displayed_count, len(filtered_alerts))
        end = min(start + limit, len(filtered_alerts))
        
        # CRITICAL FIX: Only show "seen all" if user has actually scrolled through alerts
        # Not just because we counted them
        if start >= len(filtered_alerts) and displayed_count > 0:
            return {
                "answer": "You've seen all {0} alerts matching this criteria.".format(len(filtered_alerts)),
                "target": context.get("last_target"),
                "confidence": 0.9,
                "question_type": "FACT"
            }
        
        batch = filtered_alerts[start:end]
        topic = context.get("topic", "alerts")
        answer = self._format_alert_list(batch, topic, len(batch), len(filtered_alerts))
        answer += "\n\n(Showing {0}-{1} of {2})".format(start + 1, end, len(filtered_alerts))
        
        # Update context with new displayed count (actual alerts shown to user)
        SessionStore.set_conversation_context(displayed_count=end, result_count=len(filtered_alerts))
        
        return {
            "answer": answer,
            "target": context.get("last_target"),
            "intent": "FACT_LIST",
            "confidence": 0.85,
            "question_type": "FACT"
        }
    
    def _handle_limit_followup(self, question, limit, alerts, context):
        """Handle LIMIT follow-ups: show me 20, top 10."""
        # Get alerts based on last context
        filtered_alerts = self._filter_alerts_by_context(alerts, context)
        
        if not filtered_alerts:
            return {
                "answer": "No alerts found matching previous criteria.",
                "target": context.get("last_target"),
                "confidence": 0.5,
                "question_type": "FACT"
            }
        
        # Limit the results
        limited = filtered_alerts[:limit]
        
        # Build answer
        topic = context.get("topic", "alerts")
        answer = self._format_alert_list(limited, topic, limit, len(filtered_alerts))
        
        # CRITICAL FIX: Update displayed_count for pagination tracking
        SessionStore.set_conversation_context(
            displayed_count=len(limited),
            result_count=len(filtered_alerts)
        )
        
        return {
            "answer": answer,
            "target": context.get("last_target"),
            "intent": "FACT_LIST",
            "confidence": 0.85,
            "question_type": "FACT"
        }
    
    def _handle_limit_filter_followup(self, question, limit, severity, alerts, context):
        """
        Handle combined LIMIT + FILTER follow-ups: "ok show me 18 warning"
        
        This handles queries where user specifies BOTH a count AND a severity filter.
        
        Args:
            question: User's question
            limit: Number of alerts to show
            severity: Severity filter (CRITICAL, WARNING, INFO)
            alerts: All alerts
            context: Conversation context
            
        Returns:
            dict with filtered and limited answer
        """
        # DEBUG: Log context and parameters
        print("[LIMIT_FILTER DEBUG] limit:", limit, "severity:", severity)
        print("[LIMIT_FILTER DEBUG] context.last_target:", context.get("last_target"))
        print("[LIMIT_FILTER DEBUG] context.has_context:", context.get("has_context"))
        print("[LIMIT_FILTER DEBUG] total alerts available:", len(alerts) if alerts else 0)
        
        # CRITICAL FIX: Use _filter_alerts_by_context_no_severity when severity is specified
        # This prevents double-filtering and allows proper severity switching
        filtered_alerts = self._filter_alerts_by_context_no_severity(alerts, context)
        print("[LIMIT_FILTER DEBUG] after context filter:", len(filtered_alerts) if filtered_alerts else 0)
        
        # Apply severity filter - CRITICAL FIX: Case-insensitive comparison
        if severity:
            severity_upper = severity.upper()
            filtered_alerts = [a for a in filtered_alerts if 
                              (a.get("severity") or a.get("alert_state") or "").upper() == severity_upper]
            print("[LIMIT_FILTER DEBUG] after severity filter:", len(filtered_alerts) if filtered_alerts else 0)
        
        if not filtered_alerts:
            print("[LIMIT_FILTER DEBUG] NO ALERTS FOUND! Returning error message")
            return {
                "answer": "No **{0}** alerts found matching previous criteria.".format(severity),
                "target": context.get("last_target"),
                "confidence": 0.7,
                "question_type": "FACT"
            }
        
        # Limit the results
        limited = filtered_alerts[:limit]
        
        # Build answer with severity label
        topic = "{0} {1}".format(severity, context.get("topic", "alerts")).strip()
        answer = self._format_alert_list(limited, topic, limit, len(filtered_alerts))
        
        # CRITICAL FIX: Update displayed_count properly for pagination
        SessionStore.set_conversation_context(
            severity=severity, 
            displayed_count=len(limited),
            result_count=len(filtered_alerts)
        )
        
        return {
            "answer": answer,
            "target": context.get("last_target"),
            "intent": "FACT_LIST",
            "confidence": 0.9,
            "question_type": "FACT"
        }
    
    def _handle_reference_followup(self, question, alerts, context):
        """Handle REFERENCE follow-ups: this database, same one, these databases."""
        q_lower = question.lower()
        
        # Check if user is asking about MULTIPLE databases ("these databases")
        is_plural = any(p in q_lower for p in ["these", "those", "them", "all"])
        
        if is_plural:
            # Return alerts for ALL databases from context
            dbs = context.get("databases", [])
            if not dbs:
                return self._get_clarification_response("REFERENCE")
            
            return self._generate_multi_db_answer(question, dbs, alerts, context)
        
        # Single database reference
        target = context.get("last_target")
        if not target:
            # Try to get from last_databases
            dbs = context.get("databases", [])
            if dbs:
                target = dbs[0]
        
        # PHASE-12.1: Try to get from scope if still no target
        if not target and PHASE12_AVAILABLE:
            scope = Phase12Guardrails.get_current_scope()
            if scope.is_database_scoped():
                target = scope.database_name
        
        if not target:
            return self._get_clarification_response("REFERENCE")
        
        # Check if this is a QUALITATIVE health question
        is_health_question = any(w in q_lower for w in ["fine", "ok", "okay", "healthy", "stable", "status"])
        if is_health_question:
            return self._generate_health_assessment(question, target, alerts, context)
        
        return self._generate_db_specific_answer(question, target, alerts, context)
    
    def _handle_shorthand_followup(self, question, alerts, context):
        """
        Handle SHORTHAND follow-ups: "Critical count?", "Status?", "Is it fine?"
        
        These inherit the last_target from context and answer about that database.
        """
        q_lower = question.lower()
        
        # Get target from context
        target = context.get("last_target")
        if not target:
            # Try Phase-12.1 scope
            if PHASE12_AVAILABLE:
                scope = Phase12Guardrails.get_current_scope()
                if scope.is_database_scoped():
                    target = scope.database_name
        
        if not target:
            return self._get_clarification_response("SHORTHAND")
        
        # Filter alerts for this target
        db_alerts = self._filter_alerts_by_db_strict(alerts, target)
        
        # Determine what the user is asking
        if "count" in q_lower or "total" in q_lower or "how many" in q_lower:
            # Count question - detect severity
            if "critical" in q_lower:
                severity_alerts = [a for a in db_alerts if (a.get("severity") or "").upper() == "CRITICAL"]
                count = len(severity_alerts)
                answer = str(count)
            elif "warning" in q_lower:
                severity_alerts = [a for a in db_alerts if (a.get("severity") or "").upper() == "WARNING"]
                count = len(severity_alerts)
                answer = str(count)
            else:
                count = len(db_alerts)
                answer = str(count)
            
            return {
                "answer": answer,
                "target": target,
                "intent": "FACT",
                "confidence": 1.0,
                "confidence_label": "HIGH",
                "question_type": "FACT",
                "_has_direct_data": True
            }
        
        elif "status" in q_lower or "fine" in q_lower or "ok" in q_lower or "stable" in q_lower or "healthy" in q_lower:
            # Qualitative health question - return ASSESSMENT, not counts
            return self._generate_health_assessment(question, target, alerts, context)
        
        elif "root cause" in q_lower or "cause" in q_lower:
            # Root cause question for this DB
            return self._generate_db_specific_answer(question, target, alerts, context)
        
        # Default - generate DB answer
        return self._generate_db_specific_answer(question, target, alerts, context)
    
    def _generate_health_assessment(self, question, db_name, alerts, context):
        """
        Generate qualitative health assessment for a database.
        
        For questions like "Is this DB fine?", "Is it healthy?", "Status?"
        Returns: Assessment + Risk Level + Action (NOT just counts)
        """
        db_upper = db_name.upper()
        
        # Filter alerts for this database
        db_alerts = [a for a in alerts if 
                    (a.get("target_name") or a.get("target") or "").upper() == db_upper]
        
        # Count by severity
        critical_count = sum(1 for a in db_alerts if (a.get("severity") or "").upper() == "CRITICAL")
        warning_count = sum(1 for a in db_alerts if (a.get("severity") or "").upper() == "WARNING")
        total = len(db_alerts)
        
        # Determine health status based on thresholds
        if critical_count == 0 and warning_count < 10:
            status = "HEALTHY"
            risk = "LOW"
            verdict = "Yes"
            assessment = f"**{db_name}** appears to be operating normally."
            action = "Continue routine monitoring."
        elif critical_count < 10:
            status = "WARNING"
            risk = "MEDIUM"
            verdict = "Needs attention"
            assessment = f"**{db_name}** has minor issues that should be addressed."
            action = "Review warning alerts and address root causes."
        elif critical_count < 100:
            status = "DEGRADED"
            risk = "HIGH"
            verdict = "No"
            assessment = f"**{db_name}** is experiencing significant issues."
            action = "Prioritize investigation of critical alerts."
        else:
            status = "UNHEALTHY"
            risk = "CRITICAL"
            verdict = "No"
            assessment = f"**{db_name}** is NOT fine."
            action = "Immediate DBA investigation required."
        
        # Build qualitative answer
        answer = f"**{verdict}** — {assessment}\n\n"
        
        if critical_count > 0:
            answer += f"This database has **{critical_count:,}** critical alerts"
            if critical_count > 100:
                answer += ", which is far above normal operating levels.\n"
            else:
                answer += ".\n"
        
        if warning_count > 0:
            answer += f"Additionally, there are **{warning_count:,}** warning alerts.\n"
        
        answer += f"\n**Assessment:**\n"
        answer += f"- Status: **{status}**\n"
        answer += f"- Risk Level: **{risk}**\n"
        answer += f"- Action: {action}"
        
        return {
            "answer": answer.strip(),
            "target": db_name,
            "intent": "ANALYSIS",
            "confidence": 0.95,
            "confidence_label": "HIGH",
            "question_type": "ANALYSIS",
            "_has_direct_data": True
        }
    
    def _generate_multi_db_answer(self, question, db_list, alerts, context):
        """Generate answer for multiple databases from context."""
        db_uppers = [db.upper() for db in db_list]
        
        # Filter alerts for these databases
        multi_db_alerts = [a for a in alerts if 
                         (a.get("target_name") or a.get("target") or "").upper() in db_uppers]
        
        if not multi_db_alerts:
            return {
                "answer": "No alerts found for databases: {0}".format(", ".join(db_list)),
                "target": None,
                "confidence": 0.7
            }
        
        # Also apply alert_type filter from context
        alert_type = context.get("alert_type")
        if alert_type == "dataguard":
            dg_keywords = ["standby", "data guard", "dataguard", "apply", "transport", "mrp", "redo"]
            multi_db_alerts = [a for a in multi_db_alerts if 
                             any(kw in (a.get("message") or a.get("msg_text") or "").lower() for kw in dg_keywords)]
        
        # Count by database
        db_counts = {}
        for a in multi_db_alerts:
            db = (a.get("target_name") or a.get("target") or "Unknown").upper()
            db_counts[db] = db_counts.get(db, 0) + 1
        
        # Build answer
        total = len(multi_db_alerts)
        topic = context.get("topic", "alerts").replace("_", " ").title()
        
        answer = "**{0}** for **{1}** databases:\n\n".format(topic, len(db_list))
        
        for db in db_list:
            db_upper = db.upper()
            count = db_counts.get(db_upper, 0)
            answer += "- **{0}**: {1} alerts\n".format(db, count)
        
        answer += "\n**Total**: {0} alerts".format(total)
        
        # Show top issues
        shown = min(10, total)
        if shown > 0:
            answer += "\n\n**Top Issues:**\n"
            for i, alert in enumerate(multi_db_alerts[:shown], 1):
                db = alert.get("target_name") or alert.get("target") or "Unknown"
                msg = alert.get("message") or alert.get("msg_text") or ""
                if len(msg) > 80:
                    msg = msg[:77] + "..."
                sev = alert.get("severity", "")
                answer += "{0}. [{1}] **{2}**: {3}\n".format(i, sev, db, msg)
        
        # Update context
        SessionStore.set_conversation_context(
            result_count=total,
            databases=db_list
        )
        
        return {
            "answer": answer.strip(),
            "target": db_list[0] if len(db_list) == 1 else None,
            "intent": "FACT_LIST",
            "confidence": 0.85,
            "question_type": "FACT"
        }
    
    def _handle_filter_followup(self, question, severity, alerts, context):
        """Handle FILTER follow-ups: only critical, just errors, critical count?."""
        q_lower = question.lower()
        
        # =====================================================
        # CRITICAL FIX: Check if this is a COUNT question
        # "Critical count?" → return just the number
        # =====================================================
        is_count_question = "count" in q_lower or "how many" in q_lower or "total" in q_lower
        
        # CRITICAL FIX: Check if severity is CHANGING from previous context
        # If so, this is a NEW filtered view - reset displayed_count
        previous_severity = context.get("severity")
        severity_changed = previous_severity and previous_severity != severity
        
        # Get target from context or Phase12 scope
        target = context.get("last_target")
        if not target and PHASE12_AVAILABLE:
            scope = Phase12Guardrails.get_current_scope()
            if scope.is_database_scoped():
                target = scope.database_name
        
        # Filter by target first
        if target:
            filtered_alerts = self._filter_alerts_by_db_strict(alerts, target)
        else:
            filtered_alerts = alerts
        
        # Apply severity filter - CRITICAL FIX: Case-insensitive comparison
        if severity:
            severity_upper = severity.upper()
            filtered_alerts = [a for a in filtered_alerts if 
                              (a.get("severity") or a.get("alert_state") or "").upper() == severity_upper]
        
        if not filtered_alerts:
            if is_count_question:
                return {
                    "answer": "0",
                    "target": target,
                    "confidence": 1.0,
                    "confidence_label": "HIGH",
                    "question_type": "FACT",
                    "_has_direct_data": True
                }
            return {
                "answer": "No **{0}** alerts found matching previous criteria.".format(severity),
                "target": target,
                "confidence": 0.7,
                "question_type": "FACT"
            }
        
        # =====================================================
        # COUNT question → return just the number
        # =====================================================
        if is_count_question:
            count = len(filtered_alerts)
            return {
                "answer": str(count),
                "target": target,
                "intent": "FACT",
                "confidence": 1.0,
                "confidence_label": "HIGH",
                "question_type": "FACT",
                "_has_direct_data": True
            }
        
        # Build answer - show first 20 alerts
        topic = "{0} {1}".format(severity, context.get("topic", "alerts"))
        answer = self._format_alert_list(filtered_alerts[:20], topic, 20, len(filtered_alerts))
        
        # CRITICAL FIX: Reset displayed_count when severity changes
        # This is a NEW filtered view, user hasn't seen these alerts yet
        SessionStore.set_conversation_context(
            severity=severity, 
            displayed_count=min(20, len(filtered_alerts)),  # User will see first 20
            result_count=len(filtered_alerts)
        )
        
        return {
            "answer": answer,
            "target": target,
            "intent": "FACT_LIST",
            "confidence": 0.85,
            "question_type": "FACT"
        }
    
    def _handle_direct_severity_query(self, question, severity, alerts):
        """
        Handle direct severity filter queries WITHOUT prior context.
        
        Examples:
        - "show only warnings" → Filter all alerts by WARNING
        - "show all critical alerts" → Filter all alerts by CRITICAL
        - "show alerts excluding warning" → Filter all alerts by CRITICAL
        
        Args:
            question: User's question
            severity: Target severity (WARNING, CRITICAL, etc.)
            alerts: All alerts
            
        Returns:
            dict with answer and metadata
        """
        severity_upper = severity.upper()
        
        # Filter alerts by severity
        filtered_alerts = [a for a in alerts if 
                         (a.get("severity") or a.get("alert_state") or "").upper() == severity_upper]
        
        count = len(filtered_alerts)
        
        if count == 0:
            return {
                "answer": f"No **{severity_upper}** alerts found.",
                "target": None,
                "intent": "FACT",
                "confidence": 0.9,
                "confidence_label": "HIGH",
                "actions": [],
                "root_cause": None,
                "evidence": [],
                "session_context": SessionStore.get_context_summary(),
                "status": "success",
                "question_type": "FACT"
            }
        
        # Count by database
        db_counts = {}
        for a in filtered_alerts:
            db = (a.get("target_name") or a.get("target") or "UNKNOWN").upper()
            db_counts[db] = db_counts.get(db, 0) + 1
        
        # Build answer
        answer = f"**{count:,}** {severity_upper} alert(s)"
        if db_counts:
            db_list = sorted(db_counts.items(), key=lambda x: -x[1])[:5]
            db_str = ", ".join([f"{db}: {cnt:,}" for db, cnt in db_list])
            answer += f" across **{len(db_counts)}** database(s).\n\n**Distribution:** {db_str}"
        else:
            answer += "."
        
        # Update context
        SessionStore.set_conversation_context(
            severity=severity_upper,
            result_count=count,
            displayed_count=min(20, count),
            has_context=True
        )
        
        return {
            "answer": answer,
            "target": None,
            "intent": "FACT",
            "confidence": 0.95,
            "confidence_label": "HIGH",
            "actions": [],
            "root_cause": None,
            "evidence": [],
            "session_context": SessionStore.get_context_summary(),
            "status": "success",
            "question_type": "FACT"
        }
    
    def _handle_severity_count_query(self, question, severity, alerts):
        """
        Handle "how many warning/critical alerts" type queries.
        
        Uses INCIDENT INTELLIGENCE ENGINE for enterprise DBA responses.
        
        Args:
            question: User's question
            severity: Target severity (WARNING, CRITICAL)
            alerts: All alerts
            
        Returns:
            dict with count answer and incident intelligence
        """
        severity_upper = severity.upper()
        
        # Count alerts by severity
        severity_alerts = [a for a in alerts if 
                         (a.get("severity") or a.get("alert_state") or "").upper() == severity_upper]
        count = len(severity_alerts)
        
        # Use INCIDENT INTELLIGENCE ENGINE (preferred)
        if self._incident_engine:
            intent_data = {"severity": severity_upper}
            answer = self._incident_engine.analyze_and_respond(
                severity_alerts, 
                "COUNT", 
                intent_data
            )
        # Fallback to DBA Intelligence Formatter
        elif self._dba_formatter:
            data = {
                "count": count,
                "severity": severity_upper,
                "alerts": severity_alerts[:100]
            }
            answer = self._dba_formatter.format_response(data, "COUNT", {"severity": severity_upper})
            if severity_upper == "CRITICAL" and count > 100:
                answer = self._dba_formatter.add_dba_guidance(answer, severity=severity_upper, alert_count=count)
        else:
            # Fallback with DBA-friendly style
            if count == 0:
                answer = f"There are no {severity_upper.lower()} alerts — this is typically a positive indicator."
            elif count > 10000:
                answer = f"There are **{count:,}** {severity_upper.lower()} alerts across all databases, which is significantly higher than normal."
            else:
                answer = f"There are **{count:,}** {severity_upper.lower()} alerts across all monitored databases."
        
        response = {
            "answer": answer,
            "target": None,
            "intent": "FACT",
            "confidence": 0.95,
            "confidence_label": "HIGH",
            "actions": [],
            "root_cause": None,
            "evidence": [],
            "session_context": SessionStore.get_context_summary(),
            "status": "success",
            "question_type": "FACT"
        }
        
        # PHASE 7: Apply trust processing
        return self._apply_phase7(response, question, severity_alerts)
    
    # =====================================================
    # ISSUE 1 HANDLER: DB-specific severity count
    # "how many critical alerts for MIDEVSTB"
    # =====================================================
    def _handle_db_severity_count(self, db_name, severity, alerts, question=""):
        """
        Handle "how many critical alerts for MIDEVSTB" type queries.
        
        CRITICAL FIX: Uses STRICT DB matching to prevent MIDEVSTB from matching MIDEVSTBN.
        CRITICAL FIX: Supports "give only the number" strict output mode.
        
        Args:
            db_name: Database name (e.g., MIDEVSTB)
            severity: Severity filter (CRITICAL, WARNING)
            alerts: All alerts
            question: Original question (for strict output mode detection)
            
        Returns:
            dict with DB-specific severity count and incident intelligence
        """
        db_upper = db_name.upper()
        severity_upper = severity.upper()
        
        # CRITICAL FIX: Use STRICT DB matching (exact match only)
        db_alerts = self._filter_alerts_by_db_strict(alerts, db_name)
        
        # Count by severity
        severity_alerts = [a for a in db_alerts if 
                         (a.get("severity") or a.get("alert_state") or "").upper() == severity_upper]
        count = len(severity_alerts)
        
        # CRITICAL FIX: Check for strict number mode
        if question and self._is_strict_number_mode(question):
            # Return ONLY the number, nothing else
            answer = str(count)
            response = {
                "answer": answer,
                "target": db_name,
                "intent": "FACT",
                "confidence": 0.99,
                "confidence_label": "HIGH",
                "actions": [],
                "root_cause": None,
                "evidence": [],
                "session_context": SessionStore.get_context_summary(),
                "status": "success",
                "question_type": "FACT"
            }
            return self._apply_phase7(response, question, severity_alerts)
        
        # Use INCIDENT INTELLIGENCE ENGINE (preferred)
        if self._incident_engine:
            intent_data = {"database": db_name, "severity": severity_upper}
            answer = self._incident_engine.analyze_and_respond(
                severity_alerts, 
                "COUNT", 
                intent_data
            )
        # Fallback to DBA Intelligence Formatter
        elif self._dba_formatter:
            data = {
                "count": count,
                "database": db_name,
                "severity": severity_upper,
                "alerts": severity_alerts[:100]
            }
            answer = self._dba_formatter.format_response(data, "COUNT", {"database": db_name, "severity": severity_upper})
            if severity_upper == "CRITICAL" and count > 10:
                answer = self._dba_formatter.add_dba_guidance(answer, severity=severity_upper, alert_count=count)
        else:
            # Basic fallback
            if count == 0:
                answer = f"**{db_name}** has no {severity_upper.lower()} alerts — this is typically a healthy indicator."
            elif count > 10000:
                answer = f"Yes — **{db_name}** currently has **{count:,}** {severity_upper.lower()} alerts, which is significantly higher than normal and likely requires immediate investigation."
            elif count > 100:
                answer = f"**{db_name}** has **{count:,}** {severity_upper.lower()} alerts. This warrants review by a DBA."
            else:
                answer = f"**{db_name}** has **{count:,}** {severity_upper.lower()} alert(s)."
        
        # Update context
        SessionStore.set_conversation_context(
            databases=[db_name],
            severity=severity_upper,
            result_count=count,
            last_target=db_name,
            has_context=True
        )
        
        response = {
            "answer": answer,
            "target": db_name,
            "intent": "FACT",
            "confidence": 0.95,
            "confidence_label": "HIGH",
            "actions": [],
            "root_cause": None,
            "evidence": [],
            "session_context": SessionStore.get_context_summary(),
            "status": "success",
            "question_type": "FACT"
        }
        
        # PHASE 7: Apply trust processing
        return self._apply_phase7(response, f"how many {severity} alerts for {db_name}", severity_alerts)
    
    # =====================================================
    # ISSUE 2 HANDLER: List alerts for DB
    # "list critical alerts for MIDEVSTB"
    # =====================================================
    def _handle_list_alerts_for_db(self, db_name, severity, alerts, limit=20):
        """
        Handle "list critical alerts for MIDEVSTB" type queries.
        Returns actual list of alerts, not just summary.
        
        Args:
            db_name: Database name
            severity: Severity filter (optional)
            alerts: All alerts
            limit: Max alerts to show (default 20)
            
        Returns:
            dict with alert list
        """
        db_upper = db_name.upper()
        
        # CRITICAL FIX: Use STRICT matching to prevent MIDEVSTB matching MIDEVSTBN
        db_alerts = self._filter_alerts_by_db_strict(alerts, db_name)
        
        # Apply severity filter if specified
        if severity and severity != "all":
            severity_upper = severity.upper()
            db_alerts = [a for a in db_alerts if 
                        (a.get("severity") or a.get("alert_state") or "").upper() == severity_upper]
        
        total = len(db_alerts)
        
        if total == 0:
            sev_text = f" {severity.upper()}" if severity and severity != "all" else ""
            return {
                "answer": f"No{sev_text} alerts found for **{db_name}**.",
                "target": db_name,
                "intent": "FACT",
                "confidence": 0.9,
                "confidence_label": "HIGH",
                "actions": [],
                "root_cause": None,
                "evidence": [],
                "session_context": SessionStore.get_context_summary(),
                "status": "success",
                "question_type": "FACT"
            }
        
        # Build list response
        sev_label = f"{severity.upper()} " if severity and severity != "all" else ""
        answer = f"**{total:,}** {sev_label}alert(s) for **{db_name}**:\n\n"
        
        shown = db_alerts[:limit]
        for i, alert in enumerate(shown, 1):
            msg = alert.get("message") or alert.get("msg_text") or "Unknown issue"
            if len(msg) > 100:
                msg = msg[:97] + "..."
            sev = (alert.get("severity") or alert.get("alert_state") or "").upper()
            timestamp = alert.get("occurred") or alert.get("timestamp") or ""
            if timestamp:
                answer += f"{i}. [{sev}] {msg} ({timestamp})\n"
            else:
                answer += f"{i}. [{sev}] {msg}\n"
        
        if total > limit:
            answer += f"\n*(Showing {limit} of {total:,}. Ask for 'next 20' or 'show more' to see more)*"
        
        # Update context
        SessionStore.set_conversation_context(
            databases=[db_name],
            severity=severity.upper() if severity else None,
            result_count=total,
            displayed_count=min(limit, total),
            last_target=db_name,
            has_context=True
        )
        
        return {
            "answer": answer.strip(),
            "target": db_name,
            "intent": "FACT_LIST",
            "confidence": 0.95,
            "confidence_label": "HIGH",
            "actions": [],
            "root_cause": None,
            "evidence": [],
            "session_context": SessionStore.get_context_summary(),
            "status": "success",
            "question_type": "FACT"
        }
    
    # =====================================================
    # ISSUE 3 HANDLER: First N alerts
    # "show first 5 critical alerts"
    # =====================================================
    def _handle_first_n_alerts(self, limit, severity, db_name, alerts):
        """
        Handle "show first 5 critical alerts" type queries.
        
        Args:
            limit: Number of alerts to show
            severity: Severity filter (optional)
            db_name: Database filter (optional)
            alerts: All alerts
            
        Returns:
            dict with first N alerts
        """
        filtered = alerts
        
        # Apply database filter if specified
        if db_name:
            # CRITICAL FIX: Use STRICT matching to prevent MIDEVSTB matching MIDEVSTBN
            filtered = self._filter_alerts_by_db_strict(filtered, db_name)
        
        # Apply severity filter if specified
        if severity:
            severity_upper = severity.upper()
            filtered = [a for a in filtered if 
                       (a.get("severity") or a.get("alert_state") or "").upper() == severity_upper]
        
        total = len(filtered)
        
        if total == 0:
            parts = []
            if severity:
                parts.append(severity.upper())
            if db_name:
                parts.append(f"for {db_name}")
            filter_desc = " ".join(parts) if parts else ""
            return {
                "answer": f"No {filter_desc} alerts found.".strip(),
                "target": db_name,
                "intent": "FACT",
                "confidence": 0.9,
                "confidence_label": "HIGH",
                "actions": [],
                "root_cause": None,
                "evidence": [],
                "session_context": SessionStore.get_context_summary(),
                "status": "success",
                "question_type": "FACT"
            }
        
        # Get first N alerts
        shown = filtered[:limit]
        
        # Build response
        sev_label = f"{severity.upper()} " if severity else ""
        db_label = f" for **{db_name}**" if db_name else ""
        answer = f"**First {len(shown)}** {sev_label}alert(s){db_label} (out of {total:,}):\n\n"
        
        for i, alert in enumerate(shown, 1):
            msg = alert.get("message") or alert.get("msg_text") or "Unknown issue"
            if len(msg) > 100:
                msg = msg[:97] + "..."
            sev = (alert.get("severity") or alert.get("alert_state") or "").upper()
            db = (alert.get("target_name") or alert.get("target") or "").upper()
            answer += f"{i}. [{sev}] **{db}**: {msg}\n"
        
        # Update context
        SessionStore.set_conversation_context(
            databases=[db_name] if db_name else [],
            severity=severity.upper() if severity else None,
            result_count=total,
            displayed_count=len(shown),
            last_target=db_name,
            has_context=True
        )
        
        return {
            "answer": answer.strip(),
            "target": db_name,
            "intent": "FACT_LIST",
            "confidence": 0.95,
            "confidence_label": "HIGH",
            "actions": [],
            "root_cause": None,
            "evidence": [],
            "session_context": SessionStore.get_context_summary(),
            "status": "success",
            "question_type": "FACT"
        }
    
    # =====================================================
    # ISSUE 4 HANDLER: Range-based pagination
    # "show alerts from 21 to 30"
    # =====================================================
    def _handle_range_alerts(self, start_idx, end_idx, db_name, alerts):
        """
        Handle "show alerts from 21 to 30" type queries.
        
        Args:
            start_idx: Starting index (1-based)
            end_idx: Ending index (1-based, inclusive)
            db_name: Database filter (optional)
            alerts: All alerts
            
        Returns:
            dict with range of alerts
        """
        filtered = alerts
        
        # Apply database filter if specified
        if db_name:
            # CRITICAL FIX: Use STRICT matching to prevent MIDEVSTB matching MIDEVSTBN
            filtered = self._filter_alerts_by_db_strict(filtered, db_name)
        
        total = len(filtered)
        
        # Convert to 0-based indices
        start_0 = max(0, start_idx - 1)  # Convert 1-based to 0-based
        end_0 = min(total, end_idx)      # end_idx is inclusive, so don't subtract 1
        
        if start_0 >= total:
            return {
                "answer": f"Only **{total:,}** alerts available. Cannot show range {start_idx}-{end_idx}.",
                "target": db_name,
                "intent": "FACT",
                "confidence": 0.9,
                "confidence_label": "HIGH",
                "actions": [],
                "root_cause": None,
                "evidence": [],
                "session_context": SessionStore.get_context_summary(),
                "status": "success",
                "question_type": "FACT"
            }
        
        # Get range of alerts
        shown = filtered[start_0:end_0]
        
        if not shown:
            return {
                "answer": f"No alerts found in range {start_idx}-{end_idx}.",
                "target": db_name,
                "intent": "FACT",
                "confidence": 0.7,
                "confidence_label": "MEDIUM",
                "actions": [],
                "root_cause": None,
                "evidence": [],
                "session_context": SessionStore.get_context_summary(),
                "status": "success",
                "question_type": "FACT"
            }
        
        # Build response
        db_label = f" for **{db_name}**" if db_name else ""
        answer = f"**Alerts {start_idx}-{start_0 + len(shown)}**{db_label} (of {total:,} total):\n\n"
        
        for i, alert in enumerate(shown, start_idx):
            msg = alert.get("message") or alert.get("msg_text") or "Unknown issue"
            if len(msg) > 100:
                msg = msg[:97] + "..."
            sev = (alert.get("severity") or alert.get("alert_state") or "").upper()
            db = (alert.get("target_name") or alert.get("target") or "").upper()
            answer += f"{i}. [{sev}] **{db}**: {msg}\n"
        
        # Update context
        SessionStore.set_conversation_context(
            databases=[db_name] if db_name else [],
            result_count=total,
            displayed_count=end_0,
            last_target=db_name,
            has_context=True
        )
        
        return {
            "answer": answer.strip(),
            "target": db_name,
            "intent": "FACT_LIST",
            "confidence": 0.95,
            "confidence_label": "HIGH",
            "actions": [],
            "root_cause": None,
            "evidence": [],
            "session_context": SessionStore.get_context_summary(),
            "status": "success",
            "question_type": "FACT"
        }
    
    # =====================================================
    # ISSUE 5 HANDLER: Database comparison
    # "compare alerts between MIDEVSTB and MIDEVSTBN"
    # =====================================================
    def _handle_db_comparison(self, db1, db2, alerts):
        """
        Handle "compare alerts between MIDEVSTB and MIDEVSTBN" type queries.
        
        Args:
            db1: First database name
            db2: Second database name
            alerts: All alerts
            
        Returns:
            dict with comparison table
        """
        def get_db_stats(db_name, all_alerts):
            # CRITICAL FIX: Use STRICT matching to prevent MIDEVSTB matching MIDEVSTBN
            db_alerts = self._filter_alerts_by_db_strict(all_alerts, db_name)
            
            # Count by severity
            severity_counts = {}
            for a in db_alerts:
                sev = (a.get("severity") or a.get("alert_state") or "UNKNOWN").upper()
                severity_counts[sev] = severity_counts.get(sev, 0) + 1
            
            return {
                "total": len(db_alerts),
                "critical": severity_counts.get("CRITICAL", 0),
                "warning": severity_counts.get("WARNING", 0),
                "info": severity_counts.get("INFO", 0)
            }
        
        stats1 = get_db_stats(db1, alerts)
        stats2 = get_db_stats(db2, alerts)
        
        # Build comparison table
        answer = f"**Alert Comparison: {db1} vs {db2}**\n\n"
        answer += f"| Metric | {db1} | {db2} |\n"
        answer += "|--------|-------|-------|\n"
        answer += f"| **Total Alerts** | {stats1['total']:,} | {stats2['total']:,} |\n"
        answer += f"| CRITICAL | {stats1['critical']:,} | {stats2['critical']:,} |\n"
        answer += f"| WARNING | {stats1['warning']:,} | {stats2['warning']:,} |\n"
        answer += f"| INFO | {stats1['info']:,} | {stats2['info']:,} |\n"
        
        # Add insight
        diff = abs(stats1['total'] - stats2['total'])
        if stats1['total'] > stats2['total']:
            answer += f"\n**{db1}** has **{diff:,}** more alerts than **{db2}**."
        elif stats2['total'] > stats1['total']:
            answer += f"\n**{db2}** has **{diff:,}** more alerts than **{db1}**."
        else:
            answer += f"\nBoth databases have the same number of alerts."
        
        return {
            "answer": answer,
            "target": None,
            "intent": "FACT_COMPARISON",
            "confidence": 0.95,
            "confidence_label": "HIGH",
            "actions": [],
            "root_cause": None,
            "evidence": [],
            "session_context": SessionStore.get_context_summary(),
            "status": "success",
            "question_type": "FACT"
        }
    
    # =====================================================
    # ISSUE 6 HANDLER: Standby alert count
    # "how many standby alerts"
    # =====================================================
    def _handle_standby_count(self, alerts):
        """
        Handle "how many standby alerts" type queries.
        
        Args:
            alerts: All alerts
            
        Returns:
            dict with standby alert count
        """
        # Keywords that indicate standby/dataguard alerts
        dg_keywords = [
            "standby", "data guard", "dataguard", "apply lag", 
            "transport lag", "mrp", "redo apply", "ora-16", 
            "physical standby", "dr ", "replica", "apply rate"
        ]
        
        # Filter standby alerts
        standby_alerts = [a for a in alerts if 
                        any(kw in (a.get("message") or a.get("msg_text") or "").lower() for kw in dg_keywords) or
                        any(kw in (a.get("issue_type") or "").lower() for kw in ["standby", "dataguard", "data guard"])]
        
        count = len(standby_alerts)
        
        if count == 0:
            answer = "No standby/Data Guard alerts found."
        else:
            # Count by database
            db_counts = {}
            for a in standby_alerts:
                db = (a.get("target_name") or a.get("target") or "UNKNOWN").upper()
                db_counts[db] = db_counts.get(db, 0) + 1
            
            # Count by severity
            severity_counts = {}
            for a in standby_alerts:
                sev = (a.get("severity") or a.get("alert_state") or "UNKNOWN").upper()
                severity_counts[sev] = severity_counts.get(sev, 0) + 1
            
            answer = f"**{count:,}** standby/Data Guard alert(s)"
            
            if severity_counts:
                sev_parts = []
                for sev in ["CRITICAL", "WARNING", "INFO"]:
                    if sev in severity_counts:
                        sev_parts.append(f"{severity_counts[sev]:,} {sev}")
                if sev_parts:
                    answer += f" ({', '.join(sev_parts)})"
            
            answer += f" across **{len(db_counts)}** database(s)."
            
            # Show top affected databases
            if db_counts:
                top_dbs = sorted(db_counts.items(), key=lambda x: -x[1])[:5]
                answer += "\n\n**Top Affected:**\n"
                for db, cnt in top_dbs:
                    answer += f"- **{db}**: {cnt:,} alerts\n"
        
        # Update context
        SessionStore.set_conversation_context(
            topic="STANDBY_ALERTS",
            alert_type="dataguard",
            result_count=count,
            has_context=True
        )
        
        response = {
            "answer": answer.strip(),
            "target": None,
            "intent": "FACT",
            "confidence": 0.95,
            "confidence_label": "HIGH",
            "actions": [],
            "root_cause": None,
            "evidence": [],
            "session_context": SessionStore.get_context_summary(),
            "status": "success",
            "question_type": "FACT"
        }
        
        # PHASE 7: Apply trust processing
        return self._apply_phase7(response, "how many standby alerts", standby_alerts)

    # =====================================================
    # NEW HANDLER: "give me ONLY the count of CRITICAL"
    # =====================================================
    def _handle_only_count(self, severity, db_name, alerts):
        """Return ONLY the count number for a severity (optionally for a DB)."""
        filtered = alerts
        
        # Filter by database if specified
        if db_name:
            # CRITICAL FIX: Use STRICT matching to prevent MIDEVSTB matching MIDEVSTBN
            filtered = self._filter_alerts_by_db_strict(filtered, db_name)
        
        # Filter by severity
        severity_upper = severity.upper()
        count = sum(1 for a in filtered if 
                   (a.get("severity") or a.get("alert_state") or "").upper() == severity_upper)
        
        # Return JUST the count
        if db_name:
            answer = f"**{count:,}** {severity_upper} alerts for {db_name}."
        else:
            answer = f"**{count:,}** {severity_upper} alerts."
        
        return {
            "answer": answer,
            "target": db_name,
            "intent": "FACT",
            "confidence": 0.95,
            "confidence_label": "HIGH",
            "actions": [],
            "root_cause": None,
            "evidence": [],
            "session_context": SessionStore.get_context_summary(),
            "status": "success",
            "question_type": "FACT"
        }

    # =====================================================
    # NEW HANDLER: "show CRITICAL alerts 11 to 20 for DB"
    # =====================================================
    def _handle_severity_range_alerts(self, start_idx, end_idx, severity, db_name, alerts):
        """Handle range pagination with severity filter."""
        db_upper = db_name.upper()
        severity_upper = severity.upper()
        
        # CRITICAL FIX: Use STRICT matching to prevent MIDEVSTB matching MIDEVSTBN
        db_alerts = self._filter_alerts_by_db_strict(alerts, db_name)
        
        # Filter by severity
        filtered = [a for a in db_alerts if 
                   (a.get("severity") or a.get("alert_state") or "").upper() == severity_upper]
        
        total = len(filtered)
        
        # Convert to 0-based indices
        start_0 = max(0, start_idx - 1)
        end_0 = min(total, end_idx)
        
        if start_0 >= total:
            return {
                "answer": f"Only **{total:,}** {severity_upper} alerts for {db_name}. Cannot show range {start_idx}-{end_idx}.",
                "target": db_name,
                "intent": "FACT",
                "confidence": 0.9,
                "confidence_label": "HIGH",
                "actions": [],
                "root_cause": None,
                "evidence": [],
                "session_context": SessionStore.get_context_summary(),
                "status": "success",
                "question_type": "FACT"
            }
        
        shown = filtered[start_0:end_0]
        
        answer = f"**{severity_upper} Alerts {start_idx}-{start_0 + len(shown)}** for **{db_name}** (of {total:,} total):\n\n"
        
        for i, alert in enumerate(shown, start_idx):
            msg = alert.get("message") or alert.get("msg_text") or "Unknown issue"
            if len(msg) > 100:
                msg = msg[:97] + "..."
            answer += f"{i}. [{severity_upper}] {msg}\n"
        
        return {
            "answer": answer.strip(),
            "target": db_name,
            "intent": "FACT_LIST",
            "confidence": 0.95,
            "confidence_label": "HIGH",
            "actions": [],
            "root_cause": None,
            "evidence": [],
            "session_context": SessionStore.get_context_summary(),
            "status": "success",
            "question_type": "FACT"
        }

    # =====================================================
    # NEW HANDLER: "compare total vs critical alerts"
    # =====================================================
    def _handle_total_vs_severity_comparison(self, alerts):
        """Compare total vs critical/warning alerts for all databases."""
        # Group by database
        db_stats = {}
        for a in alerts:
            db = (a.get("target_name") or a.get("target") or "UNKNOWN").upper()
            if db not in db_stats:
                db_stats[db] = {"total": 0, "critical": 0, "warning": 0, "info": 0}
            db_stats[db]["total"] += 1
            sev = (a.get("severity") or a.get("alert_state") or "").upper()
            if sev == "CRITICAL":
                db_stats[db]["critical"] += 1
            elif sev == "WARNING":
                db_stats[db]["warning"] += 1
            else:
                db_stats[db]["info"] += 1
        
        # Build comparison table
        answer = "**Alert Comparison: TOTAL vs CRITICAL**\n\n"
        answer += "| Database | TOTAL | CRITICAL | WARNING | INFO |\n"
        answer += "|----------|-------|----------|---------|------|\n"
        
        for db, stats in sorted(db_stats.items()):
            answer += f"| **{db}** | {stats['total']:,} | {stats['critical']:,} | {stats['warning']:,} | {stats['info']:,} |\n"
        
        # Totals
        total_all = sum(s["total"] for s in db_stats.values())
        critical_all = sum(s["critical"] for s in db_stats.values())
        warning_all = sum(s["warning"] for s in db_stats.values())
        info_all = sum(s["info"] for s in db_stats.values())
        
        answer += f"| **TOTAL** | {total_all:,} | {critical_all:,} | {warning_all:,} | {info_all:,} |\n"
        
        # Add insight
        critical_pct = (critical_all / total_all * 100) if total_all > 0 else 0
        answer += f"\n**{critical_pct:.1f}%** of all alerts are CRITICAL."
        
        return {
            "answer": answer,
            "target": None,
            "intent": "FACT_COMPARISON",
            "confidence": 0.95,
            "confidence_label": "HIGH",
            "actions": [],
            "root_cause": None,
            "evidence": [],
            "session_context": SessionStore.get_context_summary(),
            "status": "success",
            "question_type": "FACT"
        }

    # =====================================================
    # NEW HANDLER: "show standby alerts summary only"
    # =====================================================
    def _handle_standby_summary(self, alerts):
        """Show standby alerts summary (count + db name only)."""
        dg_keywords = [
            "standby", "data guard", "dataguard", "apply lag", 
            "transport lag", "mrp", "redo apply", "ora-16", 
            "physical standby", "dr ", "replica", "apply rate"
        ]
        
        # Filter standby alerts
        standby_alerts = [a for a in alerts if 
                        any(kw in (a.get("message") or a.get("msg_text") or "").lower() for kw in dg_keywords) or
                        any(kw in (a.get("issue_type") or "").lower() for kw in ["standby", "dataguard", "data guard"])]
        
        count = len(standby_alerts)
        
        # Count by database
        db_counts = {}
        for a in standby_alerts:
            db = (a.get("target_name") or a.get("target") or "UNKNOWN").upper()
            db_counts[db] = db_counts.get(db, 0) + 1
        
        if count == 0:
            answer = "No standby alerts found."
        else:
            answer = f"**Standby Alerts Summary:**\n\n"
            answer += f"**Total:** {count:,} alerts\n\n"
            answer += "| Database | Count |\n"
            answer += "|----------|-------|\n"
            for db, cnt in sorted(db_counts.items(), key=lambda x: -x[1]):
                answer += f"| **{db}** | {cnt:,} |\n"
        
        return {
            "answer": answer.strip(),
            "target": None,
            "intent": "FACT",
            "confidence": 0.95,
            "confidence_label": "HIGH",
            "actions": [],
            "root_cause": None,
            "evidence": [],
            "session_context": SessionStore.get_context_summary(),
            "status": "success",
            "question_type": "FACT"
        }

    # =====================================================
    # NEW HANDLER: "group alerts by error code"
    # =====================================================
    def _handle_group_by_error_code(self, alerts):
        """Group alerts by ORA error code."""
        import re
        
        # Extract ORA codes
        ora_counts = {}
        no_ora = 0
        
        for a in alerts:
            msg = a.get("message") or a.get("msg_text") or ""
            # Match ORA-XXXXX patterns
            ora_matches = re.findall(r'ORA-\d+', msg.upper())
            if ora_matches:
                for ora in ora_matches:
                    ora_counts[ora] = ora_counts.get(ora, 0) + 1
            else:
                no_ora += 1
        
        # Build answer
        answer = f"**Alerts Grouped by Error Code:**\n\n"
        
        if ora_counts:
            answer += "| Error Code | Count |\n"
            answer += "|------------|-------|\n"
            
            # Sort by count descending, show top 20
            for ora, cnt in sorted(ora_counts.items(), key=lambda x: -x[1])[:20]:
                answer += f"| {ora} | {cnt:,} |\n"
            
            if len(ora_counts) > 20:
                answer += f"\n*(Showing top 20 of {len(ora_counts)} error codes)*\n"
        
        if no_ora > 0:
            answer += f"\n**Alerts without ORA code:** {no_ora:,}"
        
        return {
            "answer": answer.strip(),
            "target": None,
            "intent": "FACT",
            "confidence": 0.95,
            "confidence_label": "HIGH",
            "actions": [],
            "root_cause": None,
            "evidence": [],
            "session_context": SessionStore.get_context_summary(),
            "status": "success",
            "question_type": "FACT"
        }

    # =====================================================
    # NEW HANDLER: "top 3 alert types per database"
    # =====================================================
    def _handle_top_alert_types_per_db(self, limit, alerts):
        """Show top N alert types for each database."""
        import re
        
        # Group by database and extract alert types (ORA codes or issue types)
        db_types = {}
        
        for a in alerts:
            db = (a.get("target_name") or a.get("target") or "UNKNOWN").upper()
            if db not in db_types:
                db_types[db] = {}
            
            # Try to extract ORA code or use issue_type
            msg = a.get("message") or a.get("msg_text") or ""
            ora_match = re.search(r'ORA-\d+', msg.upper())
            
            if ora_match:
                alert_type = ora_match.group(0)
            else:
                alert_type = a.get("issue_type") or "Other"
            
            db_types[db][alert_type] = db_types[db].get(alert_type, 0) + 1
        
        # Build answer
        answer = f"**Top {limit} Alert Types per Database:**\n\n"
        
        for db in sorted(db_types.keys()):
            types = db_types[db]
            top_types = sorted(types.items(), key=lambda x: -x[1])[:limit]
            
            answer += f"**{db}:**\n"
            for i, (alert_type, cnt) in enumerate(top_types, 1):
                answer += f"  {i}. {alert_type}: {cnt:,}\n"
            answer += "\n"
        
        return {
            "answer": answer.strip(),
            "target": None,
            "intent": "FACT",
            "confidence": 0.95,
            "confidence_label": "HIGH",
            "actions": [],
            "root_cause": None,
            "evidence": [],
            "session_context": SessionStore.get_context_summary(),
            "status": "success",
            "question_type": "FACT"
        }

    def _filter_alerts_by_context_no_severity(self, alerts, context):
        """Filter alerts by context but WITHOUT applying severity filter.
        Used when severity is about to change."""
        filtered = alerts
        
        # Filter by alert type (dataguard, tablespace, etc.)
        alert_type = context.get("alert_type")
        if alert_type == "dataguard":
            dg_keywords = ["standby", "data guard", "dataguard", "apply", "transport", "mrp", "redo", "ora-16"]
            filtered = [a for a in filtered if 
                       any(kw in (a.get("message") or a.get("msg_text") or "").lower() for kw in dg_keywords) or
                       any(kw in (a.get("issue_type") or "").lower() for kw in ["standby", "dataguard"])]
        elif alert_type == "tablespace":
            ts_keywords = ["tablespace", "space", "full", "extent", "ora-1654", "ora-1653"]
            filtered = [a for a in filtered if 
                       any(kw in (a.get("message") or a.get("msg_text") or "").lower() for kw in ts_keywords)]
        
        # Filter by target if specified - STRICT EXACT MATCHING
        target = context.get("last_target")
        if target:
            target_upper = target.upper()
            filtered = [a for a in filtered if 
                       (a.get("target_name") or a.get("target") or "").upper() == target_upper]
        
        # NOTE: Deliberately NOT filtering by severity here
        return filtered
    
    def _generate_db_specific_answer(self, question, db_name, alerts, context):
        """Generate answer for a specific database."""
        db_upper = db_name.upper()
        
        # Filter alerts for this database - STRICT EXACT MATCHING
        db_alerts = [a for a in alerts if 
                    (a.get("target_name") or a.get("target") or "").upper() == db_upper]
        
        if not db_alerts:
            return {
                "answer": "No alerts found for database **{0}**.".format(db_name),
                "target": db_name,
                "confidence": 0.9
            }
        
        # Check if also filtering by alert type from context
        alert_type = context.get("alert_type") if context else None
        if alert_type == "dataguard":
            dg_keywords = ["standby", "data guard", "dataguard", "apply", "transport", "mrp", "redo"]
            db_alerts = [a for a in db_alerts if 
                        any(kw in (a.get("message") or a.get("msg_text") or "").lower() for kw in dg_keywords)]
        
        # Count by severity - CRITICAL FIX: Normalize severity to UPPERCASE
        severity_counts = {}
        for a in db_alerts:
            sev = (a.get("severity") or a.get("alert_state") or "UNKNOWN").upper()
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        
        # Build answer - SUMMARY ONLY (no alert list)
        answer = "**{0:,}** alert(s) for **{1}**".format(len(db_alerts), db_name)
        
        if severity_counts:
            sev_parts = []
            for sev in ["CRITICAL", "WARNING", "INFO"]:
                if sev in severity_counts:
                    sev_parts.append("{0:,} {1}".format(severity_counts[sev], sev))
            if sev_parts:
                answer += " ({0})".format(", ".join(sev_parts))
        
        answer += "."
        
        # NO alert list for summary - user can ask "show me 10" for details
        
        # Update context - CRITICAL: Set all context in one call for consistency
        SessionStore.set_conversation_context(
            topic="{0}_ALERTS".format(db_name),
            result_count=len(db_alerts),
            displayed_count=0,  # User hasn't scrolled yet
            databases=[db_name],
            last_target=db_name,  # CRITICAL: Must set last_target here
            severity=None,        # No severity filter yet
            alert_type=None       # No alert type filter
        )
        SessionStore.update(last_target=db_name)
        
        return {
            "answer": answer.strip(),
            "target": db_name,
            "intent": "FACT_ENTITY",
            "confidence": 0.9,
            "question_type": "FACT"
        }
    
    def _filter_alerts_by_context(self, alerts, context):
        """Filter alerts based on conversation context."""
        filtered = alerts
        
        # Filter by alert type (dataguard, tablespace, etc.)
        alert_type = context.get("alert_type")
        if alert_type == "dataguard":
            dg_keywords = ["standby", "data guard", "dataguard", "apply", "transport", "mrp", "redo", "ora-16"]
            filtered = [a for a in filtered if 
                       any(kw in (a.get("message") or a.get("msg_text") or "").lower() for kw in dg_keywords) or
                       any(kw in (a.get("issue_type") or "").lower() for kw in ["standby", "dataguard"])]
        elif alert_type == "tablespace":
            ts_keywords = ["tablespace", "space", "full", "extent", "ora-1654", "ora-1653"]
            filtered = [a for a in filtered if 
                       any(kw in (a.get("message") or a.get("msg_text") or "").lower() for kw in ts_keywords)]
        
        # Filter by target if specified - STRICT EXACT MATCHING
        target = context.get("last_target")
        if target:
            target_upper = target.upper()
            filtered = [a for a in filtered if 
                       (a.get("target_name") or a.get("target") or "").upper() == target_upper]
        
        # Filter by severity if specified
        # CRITICAL FIX: Case-insensitive comparison (data has 'Critical', 'Warning')
        severity = context.get("severity")
        if severity:
            severity_upper = severity.upper()
            filtered = [a for a in filtered if 
                       (a.get("severity") or a.get("alert_state") or "").upper() == severity_upper]
        
        return filtered
    
    def _format_alert_list(self, alerts, topic, limit, total):
        """Format a list of alerts into a readable answer."""
        if not alerts:
            return "No alerts found."
        
        answer = "**{0}** (showing {1} of {2}):\n\n".format(
            topic.replace("_", " ").title(),
            min(len(alerts), limit),
            total
        )
        
        for i, alert in enumerate(alerts[:limit], 1):
            target = alert.get("target_name") or alert.get("target") or "Unknown"
            msg = alert.get("message") or alert.get("msg_text") or ""
            severity = alert.get("severity", "")
            
            if len(msg) > 80:
                msg = msg[:77] + "..."
            
            answer += "{0}. [{1}] **{2}**: {3}\n".format(i, severity, target, msg)
        
        return answer.strip()
    
    def _enhance_with_dba_intelligence(self, result, alerts=None):
        """
        Enhance response with DBA Intelligence formatting.
        
        Applies 5 layers of DBA intelligence:
        1. Factual accuracy (already in result)
        2. Incident reasoning (detect duplicates)
        3. Contextual explanation (severity context)
        4. Human-like response style
        5. Actionable guidance
        
        Args:
            result: The response dict with 'answer' field
            alerts: Optional list of alerts for pattern analysis
            
        Returns:
            Enhanced result dict
        """
        if not self._dba_formatter or not result:
            return result
        
        answer = result.get("answer", "")
        if not answer:
            return result
        
        # Extract metadata for intelligence enhancement
        target = result.get("target")
        severity = None
        count = 0
        question_type = result.get("question_type", "FACT")
        
        # Try to extract severity and count from answer or context
        context = SessionStore.get_conversation_context()
        severity = context.get("severity")
        count = context.get("result_count", 0)
        
        # For COUNT-type questions, enhance the answer format
        if question_type == "FACT" and count > 0:
            # Check if this is a high-volume situation
            if count > 10000 and alerts:
                # Analyze incident patterns
                pattern = self._dba_formatter._analyze_incident_patterns(alerts)
                explanation = self._dba_formatter._explain_incident_reasoning(pattern)
                if explanation and explanation not in answer:
                    answer = answer.rstrip(".") + ".\n\n" + explanation
            
            # Add severity context for critical alerts
            if severity and severity.upper() == "CRITICAL" and count > 10:
                severity_ctx = self._dba_formatter._assess_severity_context(count, severity, target)
                if severity_ctx.get("assessment") == "immediate_investigation":
                    if "higher than normal" not in answer.lower() and "investigation" not in answer.lower():
                        answer += "\n\nThis is significantly higher than normal and likely requires immediate investigation."
        
        # Add DBA guidance for ACTION-type questions
        if question_type == "ACTION" and severity:
            answer = self._dba_formatter.add_dba_guidance(
                answer,
                severity=severity,
                alert_count=count,
                include_guidance=True
            )
        
        result["answer"] = answer
        return result
    
    def _get_clarification_response(self, followup_type):
        """Return clarification when context is missing."""
        # Use DBA formatter for clarification if available
        if self._dba_formatter:
            if followup_type == "LIMIT":
                return {
                    "answer": (
                        "I'd like to show you a specific number of items, but I need more context.\n\n"
                        "Could you specify what you'd like to see?\n"
                        "- Standby/Data Guard alerts\n"
                        "- Critical alerts for a specific database\n"
                        "- Alerts for a specific database (e.g., MIDEVSTBN)"
                    ),
                    "intent": "CLARIFICATION",
                    "confidence": 0.5
                }
            elif followup_type == "REFERENCE":
                return {
                    "answer": (
                        "I'm not sure which database you're referring to.\n\n"
                        "Please specify a database name, for example:\n"
                        "- 'show alerts for MIDEVSTBN'\n"
                        "- 'how many critical alerts for MIDEVSTB?'"
                    ),
                    "intent": "CLARIFICATION",
                    "confidence": 0.5
                }
            elif followup_type == "FILTER":
                return {
                    "answer": (
                        "I can filter results, but I need to know what to filter.\n\n"
                        "Try asking about:\n"
                        "- Standby issues\n"
                        "- Alerts for a specific database\n"
                        "Then I can apply severity filters."
                    ),
                    "intent": "CLARIFICATION",
                    "confidence": 0.5
                }
            elif followup_type == "SHORTHAND":
                return {
                    "answer": (
                        "I need clarification before answering to avoid incorrect scope.\n\n"
                        "Please specify:\n"
                        "- A specific database name (e.g., MIDEVSTB, MIDEVSTBN)\n"
                        "- Or 'across all databases' / 'environment-wide' for totals"
                    ),
                    "intent": "CLARIFICATION",
                    "confidence": 0.5
                }
            
            return {
                "answer": "Could you please provide more details about what you'd like to see?",
                "intent": "CLARIFICATION",
                "confidence": 0.5
            }
        
        # Fallback to original clarification responses
        if followup_type == "LIMIT":
            return {
                "answer": ("I'd like to show you a specific number of items, but I need more context.\n\n"
                          "What would you like to see?\n"
                          "- Standby/Data Guard alerts\n"
                          "- Critical alerts\n"
                          "- Alerts for a specific database (e.g., MIDEVSTBN)"),
                "intent": "CLARIFICATION",
                "confidence": 0.5
            }
        elif followup_type == "REFERENCE":
            return {
                "answer": ("I'm not sure which database you're referring to.\n\n"
                          "Please specify a database name, for example:\n"
                          "- 'show alerts for MIDEVSTBN'\n"
                          "- 'MIDEVSTB status'"),
                "intent": "CLARIFICATION",
                "confidence": 0.5
            }
        elif followup_type == "FILTER":
            return {
                "answer": ("I can filter results, but I need to know what to filter.\n\n"
                          "Try asking about:\n"
                          "- Standby issues\n"
                          "- Alerts for a specific database\n"
                          "Then I can apply severity filters."),
                "intent": "CLARIFICATION",
                "confidence": 0.5
            }
        
        return {
            "answer": "Could you please provide more details about what you'd like to see?",
            "intent": "CLARIFICATION",
            "confidence": 0.5
        }
    
    # =====================================================
    # PHASE 8: DATA AWARENESS HANDLERS
    # Handle queries that need special data awareness
    # =====================================================
    
    def _handle_relationship_query(self, target_db, alerts):
        """Handle 'Are these related to MIDEVSTB?' queries."""
        if not DATA_AWARENESS_AVAILABLE:
            return None
        
        # Get relationship info
        rel_info = RELATIONSHIP_GRAPH.get_relationship(target_db)
        
        # Get alert counts for related databases
        target_upper = target_db.upper()
        target_alerts = [a for a in alerts if 
                        target_upper in (a.get("target_name") or a.get("target") or "").upper()]
        target_count = len(target_alerts)
        
        # Check for standby
        if rel_info.get("is_primary"):
            standbys = rel_info.get("related_databases", [])
            if standbys:
                standby = standbys[0]
                standby_alerts = [a for a in alerts if 
                                 standby in (a.get("target_name") or a.get("target") or "").upper()]
                standby_count = len(standby_alerts)
                
                explanation = RELATIONSHIP_GRAPH.explain_standby_alert_propagation(
                    target_db, standby, target_count, standby_count
                )
                
                answer = (
                    f"**Yes, related.** {standby} is the standby database of {target_db}.\n\n"
                    f"{explanation}\n\n"
                    f"Primary instability on {target_db} can propagate to standby alerts on {standby}."
                )
            else:
                answer = f"**{target_db}** has {target_count:,} alerts. No known standby databases detected."
        elif rel_info.get("is_standby"):
            primary = rel_info.get("primary_database")
            if primary:
                primary_alerts = [a for a in alerts if 
                                 primary in (a.get("target_name") or a.get("target") or "").upper()]
                primary_count = len(primary_alerts)
                
                answer = (
                    f"**Yes, related.** {target_db} is the STANDBY of {primary} (primary).\n\n"
                    f"- **{primary}** (primary): {primary_count:,} alerts\n"
                    f"- **{target_db}** (standby): {target_count:,} alerts\n\n"
                    f"Issues on the standby often indicate problems propagating from the primary."
                )
            else:
                answer = f"**{target_db}** appears to be a standby database with {target_count:,} alerts."
        else:
            answer = f"**{target_db}** has {target_count:,} alerts. Relationship to other databases not determined."
        
        return {
            "answer": answer,
            "target": target_db,
            "intent": "FACT",
            "confidence": 0.85,
            "confidence_label": "HIGH",
            "actions": [],
            "root_cause": None,
            "evidence": [],
            "session_context": SessionStore.get_context_summary(),
            "status": "success",
            "question_type": "FACT"
        }
    
    def _handle_normality_query(self, db_name, alerts):
        """Handle 'Is this alert volume normal?' queries."""
        if not DATA_AWARENESS_AVAILABLE:
            return None
        
        if db_name:
            # CRITICAL FIX: Use STRICT matching to prevent MIDEVSTB matching MIDEVSTBN
            db_alerts = self._filter_alerts_by_db_strict(alerts, db_name)
            count = len(db_alerts)
            
            # Count by severity
            critical_count = sum(1 for a in db_alerts if 
                                (a.get("severity") or "").upper() == "CRITICAL")
            
            assessment = BASELINE_COMPARISON.assess_volume_normality(
                db_name, count, severity=None
            )
            critical_assessment = BASELINE_COMPARISON.assess_volume_normality(
                db_name, critical_count, severity="CRITICAL"
            )
            
            answer = (
                f"**{db_name}** Alert Volume Assessment:\n\n"
                f"**Total Alerts:** {count:,} — {assessment['status']}\n"
                f"{assessment['explanation']}\n\n"
                f"**Critical Alerts:** {critical_count:,} — {critical_assessment['status']}\n"
                f"{critical_assessment['explanation']}\n\n"
                f"**Recommendation:** {assessment['recommendation']}"
            )
        else:
            total_count = len(alerts)
            critical_count = sum(1 for a in alerts if 
                                (a.get("severity") or "").upper() == "CRITICAL")
            
            answer = (
                f"**Environment Alert Volume:**\n\n"
                f"- Total Alerts: **{total_count:,}**\n"
                f"- Critical Alerts: **{critical_count:,}**\n\n"
                f"This is **significantly elevated**. Normal baseline is ~50-200 critical alerts per database.\n\n"
                f"**Assessment:** NOT NORMAL — immediate investigation recommended."
            )
        
        return {
            "answer": answer,
            "target": db_name,
            "intent": "FACT",
            "confidence": 0.8,
            "confidence_label": "MEDIUM",
            "actions": [],
            "root_cause": None,
            "evidence": [],
            "session_context": SessionStore.get_context_summary(),
            "status": "success",
            "question_type": "FACT"
        }
    
    def _handle_temporal_query(self, time_filter, alerts):
        """Handle 'alerts from yesterday' queries."""
        if not DATA_AWARENESS_AVAILABLE:
            return None
        
        filtered, description, success = TEMPORAL_INTELLIGENCE.filter_by_time(alerts, time_filter)
        
        if not success:
            answer = (
                f"**Alerts for '{time_filter}':**\n\n"
                f"⚠️ Precise time filtering may not be available. "
                f"Alert timestamps in the dataset may not support '{time_filter}' filtering.\n\n"
                f"**Total alerts in dataset:** {len(alerts):,}"
            )
        else:
            count = len(filtered)
            if count == 0:
                answer = f"**No alerts found** for '{time_filter}'.\n\nTotal alerts in dataset: {len(alerts):,}"
            else:
                # Get severity breakdown
                critical = sum(1 for a in filtered if (a.get("severity") or "").upper() == "CRITICAL")
                warning = sum(1 for a in filtered if (a.get("severity") or "").upper() == "WARNING")
                
                answer = (
                    f"**{description}:** {count:,} alerts\n\n"
                    f"- Critical: {critical:,}\n"
                    f"- Warning: {warning:,}\n\n"
                )
                
                # Top databases
                db_counts = {}
                for a in filtered:
                    db = (a.get("target_name") or a.get("target") or "UNKNOWN").upper()
                    db_counts[db] = db_counts.get(db, 0) + 1
                
                if db_counts:
                    top_dbs = sorted(db_counts.items(), key=lambda x: -x[1])[:3]
                    answer += "**Top Databases:**\n"
                    for db, cnt in top_dbs:
                        answer += f"- {db}: {cnt:,}\n"
        
        return {
            "answer": answer,
            "target": None,
            "intent": "FACT",
            "confidence": 0.7 if success else 0.5,
            "confidence_label": "MEDIUM" if success else "LOW",
            "actions": [],
            "root_cause": None,
            "evidence": [],
            "session_context": SessionStore.get_context_summary(),
            "status": "success",
            "question_type": "FACT"
        }
    
    def _handle_repetition_query(self, db_name, alerts):
        """Handle 'Why are warnings repeated?' queries."""
        if not DATA_AWARENESS_AVAILABLE:
            return None
        
        if db_name:
            # CRITICAL FIX: Use STRICT matching to prevent MIDEVSTB matching MIDEVSTBN
            db_alerts = self._filter_alerts_by_db_strict(alerts, db_name)
        else:
            db_alerts = alerts
        
        explanation_info = STATE_EXPLAINER.explain_repeated_alerts(db_alerts, db_name)
        
        answer = (
            f"**Why alerts are repeating" + (f" for {db_name}**:\n\n" if db_name else "**:\n\n") +
            f"{explanation_info.get('explanation', 'Unable to determine cause.')}\n\n"
        )
        
        if explanation_info.get('recommendation'):
            answer += f"**Recommendation:** {explanation_info['recommendation']}"
        
        return {
            "answer": answer,
            "target": db_name,
            "intent": "ANALYSIS",
            "confidence": 0.8,
            "confidence_label": "MEDIUM",
            "actions": [],
            "root_cause": explanation_info.get('primary_state'),
            "evidence": [],
            "session_context": SessionStore.get_context_summary(),
            "status": "success",
            "question_type": "ANALYSIS"
        }
    
    def _handle_worried_query(self, alerts):
        """Handle 'Should I be worried?' queries."""
        total = len(alerts)
        critical = sum(1 for a in alerts if (a.get("severity") or "").upper() == "CRITICAL")
        
        # Count unique databases
        dbs = set()
        for a in alerts:
            db = (a.get("target_name") or a.get("target") or "").upper()
            if db:
                dbs.add(db)
        
        # Determine worry level
        if critical > 100000:
            worry_level = "YES — IMMEDIATE ATTENTION NEEDED"
            explanation = (
                f"You have **{critical:,}** critical alerts across **{len(dbs)}** databases. "
                f"This is significantly above normal thresholds."
            )
            recommendation = (
                "1. Identify the top database with most critical alerts\n"
                "2. Review the dominant error type (likely ORA-600 or connectivity issues)\n"
                "3. Engage on-call DBA immediately for databases showing internal errors"
            )
        elif critical > 10000:
            worry_level = "YES — ELEVATED CONCERN"
            explanation = f"**{critical:,}** critical alerts warrant investigation."
            recommendation = "Review top databases and error patterns. Prioritize ORA-600 errors."
        elif critical > 1000:
            worry_level = "MODERATE — MONITOR CLOSELY"
            explanation = f"**{critical:,}** critical alerts are above baseline but not emergency level."
            recommendation = "Monitor trends. Investigate if count increases."
        else:
            worry_level = "LOW — SITUATION APPEARS STABLE"
            explanation = f"**{critical:,}** critical alerts is within normal operational range."
            recommendation = "Continue normal monitoring."
        
        answer = (
            f"**{worry_level}**\n\n"
            f"{explanation}\n\n"
            f"**Recommendation:**\n{recommendation}"
        )
        
        return {
            "answer": answer,
            "target": None,
            "intent": "ANALYSIS",
            "confidence": 0.85,
            "confidence_label": "HIGH",
            "actions": [],
            "root_cause": None,
            "evidence": [],
            "session_context": SessionStore.get_context_summary(),
            "status": "success",
            "question_type": "ANALYSIS"
        }
    
    def _handle_failure_prediction_query(self, alerts):
        """Handle 'Which database is most likely to fail?' queries."""
        # Count alerts per database
        db_counts = {}
        db_critical = {}
        for a in alerts:
            db = (a.get("target_name") or a.get("target") or "UNKNOWN").upper()
            db_counts[db] = db_counts.get(db, 0) + 1
            if (a.get("severity") or "").upper() == "CRITICAL":
                db_critical[db] = db_critical.get(db, 0) + 1
        
        if not db_critical:
            return {
                "answer": "No critical alerts detected — no databases currently at high risk of failure.",
                "target": None,
                "intent": "PREDICTION",
                "confidence": 0.7,
                "confidence_label": "MEDIUM",
                "actions": [],
                "status": "success"
            }
        
        # Find highest risk database
        most_critical_db = max(db_critical.items(), key=lambda x: x[1])
        db_name, crit_count = most_critical_db
        total_count = db_counts.get(db_name, 0)
        
        # Check for ORA-600 errors (internal errors = high failure risk)
        db_alerts = [a for a in alerts if 
                    (a.get("target_name") or a.get("target") or "").upper() == db_name]
        ora600_count = sum(1 for a in db_alerts if 
                         "ora-600" in (a.get("message") or a.get("msg_text") or "").lower() or
                         "ora 600" in (a.get("message") or a.get("msg_text") or "").lower())
        
        risk_factors = []
        if crit_count > 100000:
            risk_factors.append(f"Extremely high critical alert count ({crit_count:,})")
        if ora600_count > 0:
            risk_factors.append(f"ORA-600 internal errors detected ({ora600_count:,})")
        
        answer = (
            f"**Most at-risk database: {db_name}**\n\n"
            f"- Total Alerts: {total_count:,}\n"
            f"- Critical Alerts: {crit_count:,}\n"
            f"- ORA-600 Errors: {ora600_count:,}\n\n"
            f"**Risk Factors:**\n"
        )
        
        if risk_factors:
            for rf in risk_factors:
                answer += f"- {rf}\n"
        else:
            answer += "- High alert volume relative to other databases\n"
        
        answer += (
            f"\n**⚠️ Confidence Note:** This is based on alert volume, not deep system metrics. "
            f"For accurate failure prediction, review AWR/ASH data and system logs."
        )
        
        return {
            "answer": answer,
            "target": db_name,
            "intent": "PREDICTION",
            "confidence": 0.6,
            "confidence_label": "MEDIUM",
            "actions": ["Review " + db_name + " alert log", "Check ORA-600 trace files"],
            "root_cause": None,
            "evidence": [],
            "session_context": SessionStore.get_context_summary(),
            "status": "success",
            "question_type": "PREDICTION"
        }
    
    def _handle_ignore_consequences_query(self, alerts):
        """Handle 'What happens if we ignore these alerts?' queries."""
        total = len(alerts)
        critical = sum(1 for a in alerts if (a.get("severity") or "").upper() == "CRITICAL")
        
        # Check for dangerous patterns
        ora600_count = sum(1 for a in alerts if 
                         "ora-600" in (a.get("message") or a.get("msg_text") or "").lower())
        connectivity = sum(1 for a in alerts if 
                          "failed to connect" in (a.get("message") or a.get("msg_text") or "").lower())
        
        consequences = []
        if ora600_count > 0:
            consequences.append(f"**ORA-600 errors ({ora600_count:,})**: Can lead to database crash or data corruption if unaddressed")
        if connectivity > 0:
            consequences.append(f"**Connectivity failures ({connectivity:,})**: Applications may lose database access")
        if critical > 10000:
            consequences.append(f"**High critical volume ({critical:,})**: System degradation likely")
        
        if not consequences:
            answer = (
                "**Consequence of ignoring alerts:**\n\n"
                "Current alerts appear to be low-risk. However, continued monitoring is recommended.\n\n"
                "**General risk of ignoring alerts:** Undetected issues can escalate to outages."
            )
        else:
            answer = (
                "**Consequence of ignoring these alerts:**\n\n" +
                "\n".join(f"- {c}" for c in consequences) +
                "\n\n**Recommendation:** Address ORA-600 errors and connectivity issues first. "
                "These have the highest impact on system stability."
            )
        
        return {
            "answer": answer,
            "target": None,
            "intent": "ANALYSIS",
            "confidence": 0.8,
            "confidence_label": "MEDIUM",
            "actions": [],
            "root_cause": None,
            "evidence": [],
            "session_context": SessionStore.get_context_summary(),
            "status": "success",
            "question_type": "ANALYSIS"
        }
    
    def _handle_evidence_query(self, alerts):
        """Handle 'What evidence supports this being CRITICAL?' queries."""
        critical = sum(1 for a in alerts if (a.get("severity") or "").upper() == "CRITICAL")
        total = len(alerts)
        
        # Count ORA-600
        ora600_count = sum(1 for a in alerts if 
                         "ora-600" in (a.get("message") or a.get("msg_text") or "").lower())
        
        # Count unique databases affected
        dbs = set()
        for a in alerts:
            if (a.get("severity") or "").upper() == "CRITICAL":
                db = (a.get("target_name") or a.get("target") or "").upper()
                if db:
                    dbs.add(db)
        
        evidence_points = [
            f"**{critical:,}** critical alerts out of {total:,} total ({critical*100//total if total else 0}%)",
            f"**{len(dbs)}** database(s) affected by critical alerts",
        ]
        
        if ora600_count > 0:
            evidence_points.append(f"**{ora600_count:,}** ORA-600 internal errors (severe)")
        
        answer = (
            "**Evidence supporting CRITICAL risk assessment:**\n\n" +
            "\n".join(f"- {e}" for e in evidence_points) +
            "\n\n**Conclusion:** Alert volume and severity distribution support a CRITICAL risk posture."
        )
        
        return {
            "answer": answer,
            "target": None,
            "intent": "ANALYSIS",
            "confidence": 0.9,
            "confidence_label": "HIGH",
            "actions": [],
            "root_cause": None,
            "evidence": evidence_points,
            "session_context": SessionStore.get_context_summary(),
            "status": "success",
            "question_type": "ANALYSIS"
        }
    
    def _handle_manager_explanation(self, alerts):
        """
        Handle 'Explain this to a manager' queries.
        
        CRITICAL: Manager mode must be:
        - Business language (no ORA codes, no technical terms)
        - 5-6 simple bullets
        - Focus on: business impact, risk, downtime, SLA
        - Actionable recommendation
        """
        total = len(alerts)
        critical = sum(1 for a in alerts if (a.get("severity") or "").upper() == "CRITICAL")
        warning = total - critical
        
        # Top database
        db_counts = {}
        for a in alerts:
            db = (a.get("target_name") or a.get("target") or "UNKNOWN").upper()
            db_counts[db] = db_counts.get(db, 0) + 1
        
        top_db = max(db_counts.items(), key=lambda x: x[1]) if db_counts else ("Unknown", 0)
        num_dbs = len(db_counts)
        
        # Risk assessment based on critical count
        if critical > 100000:
            risk_level = "CRITICAL"
            risk_desc = "Service outage risk is HIGH"
            urgency = "Immediate action required"
        elif critical > 10000:
            risk_level = "HIGH"
            risk_desc = "Service degradation likely"
            urgency = "Action required within 24 hours"
        elif critical > 1000:
            risk_level = "MEDIUM"
            risk_desc = "Potential service impact"
            urgency = "Review within 48 hours"
        else:
            risk_level = "LOW"
            risk_desc = "Minimal impact expected"
            urgency = "Monitor and address as time permits"
        
        answer = (
            "**Executive Summary:**\n\n"
            f"**Current Situation:**\n"
            f"- {num_dbs} database(s) are experiencing issues\n"
            f"- **{critical:,}** require immediate attention\n"
            f"- **{top_db[0]}** is the most affected system\n\n"
            f"**Business Risk:** {risk_level}\n"
            f"- {risk_desc}\n"
            f"- Applications depending on these databases may be impacted\n"
            f"- Without action, this could affect service availability\n\n"
            f"**Recommended Action:**\n"
            f"- {urgency}\n"
            f"- Database team is aware and investigating\n"
            f"- Priority: Focus on {top_db[0]} first"
        )
        
        return {
            "answer": answer,
            "target": None,
            "intent": "ANALYSIS",
            "confidence": 0.85,
            "confidence_label": "HIGH",
            "actions": [],
            "root_cause": None,
            "evidence": [],
            "session_context": SessionStore.get_context_summary(),
            "status": "success",
            "question_type": "ANALYSIS"
        }
    
    def _handle_dba_explanation_query(self, alerts):
        """Handle 'Explain like talking to senior DBA' queries.
        
        STYLE: Speak like an experienced colleague, not a report.
        Use conversational DBA language, not formal documentation.
        
        SCOPE AWARE: If we have a locked scope (MIDEVSTB), explain THAT database.
        """
        # PHASE-12.1: Check if we have a scoped database
        target_db = None
        if PHASE12_AVAILABLE:
            scope = Phase12Guardrails.get_current_scope()
            if scope.is_database_scoped():
                target_db = scope.database_name
        
        # If no scope, check session context
        if not target_db:
            context = SessionStore.get_conversation_context()
            target_db = context.get("last_target")
        
        # If we have a target, filter alerts to that database
        if target_db:
            target_upper = target_db.upper()
            filtered_alerts = [a for a in alerts if 
                              (a.get("target_name") or a.get("target") or "").upper() == target_upper]
            if filtered_alerts:
                alerts = filtered_alerts
        
        total = len(alerts)
        critical = sum(1 for a in alerts if (a.get("severity") or "").upper() == "CRITICAL")
        warning = total - critical
        
        # Count error types
        ora600_count = sum(1 for a in alerts if 
                         "ora-600" in (a.get("message") or a.get("msg_text") or "").lower())
        ora12537_count = sum(1 for a in alerts if 
                         "ora-12537" in (a.get("message") or a.get("msg_text") or "").lower())
        
        # Top databases
        db_critical = {}
        for a in alerts:
            if (a.get("severity") or "").upper() == "CRITICAL":
                target = a.get("target_name") or a.get("target") or "UNKNOWN"
                if ':' in target:
                    db = target.split(':')[0].upper()
                else:
                    db = target.upper()
                db_critical[db] = db_critical.get(db, 0) + 1
        
        top_dbs = sorted(db_critical.items(), key=lambda x: -x[1])[:2]
        top_db = top_dbs[0][0] if top_dbs else (target_db or "UNKNOWN")
        top_db_count = top_dbs[0][1] if top_dbs else 0
        
        # Build conversational response
        if target_db:
            answer = f"**Alright, here's the situation with {target_db}:**\n\n"
        else:
            answer = "**Alright, here's what I'm seeing:**\n\n"
        
        # Opening assessment
        if critical > 100000:
            answer += f"We've got a serious situation — **{critical:,}** critical alerts"
            if target_db:
                answer += f" on **{target_db}**. "
            else:
                answer += " across the environment. "
        elif critical > 10000:
            answer += f"There's a significant volume — **{critical:,}** critical alerts"
            if target_db:
                answer += f" on **{target_db}**. "
            else:
                answer += ". "
        else:
            answer += f"Currently looking at **{critical:,}** critical alerts"
            if target_db:
                answer += f" on **{target_db}**. "
            else:
                answer += ". "
        
        # Top database callout
        if top_dbs:
            answer += f"**{top_db}** is taking the brunt of it with {top_db_count:,} criticals.\n\n"
        
        # Error pattern analysis
        if ora600_count > 0:
            answer += (
                f"🔴 **ORA-600s detected** ({ora600_count:,} occurrences) — these are internal errors. "
                f"You'll want to pull trace files from `$ORACLE_BASE/diag/rdbms/{top_db.lower()}/trace/`. "
                f"Look for the first occurrence, get the arguments, and cross-reference with MOS.\n\n"
            )
        
        if ora12537_count > 0:
            answer += (
                f"⚠️ **ORA-12537 TNS connection issues** ({ora12537_count:,}) — likely network or listener problems. "
                f"Check `lsnrctl status`, verify network connectivity, and look for firewall issues.\n\n"
            )
        
        # What I'd do
        answer += "**What I'd do first:**\n"
        if ora600_count > 0:
            answer += f"1. SSH to {top_db}, check alert log for the ORA-600 stack trace\n"
            answer += "2. Run `adrci` → `show incident` → grab incident package\n"
        else:
            answer += f"1. Check alert log on {top_db} for patterns\n"
            answer += "2. Look at AWR for the last hour\n"
        
        if len(top_dbs) > 1:
            answer += f"3. After that, look at {top_dbs[1][0]} — it's next in line\n"
        else:
            answer += "3. Cross-check with app team for any recent deployments\n"
        
        return {
            "answer": answer,
            "target": target_db or top_db,
            "intent": "ANALYSIS",
            "confidence": 0.9,
            "confidence_label": "HIGH",
            "actions": ["Review trace files", "Check V$DIAG_INFO", "Search MOS"],
            "root_cause": "ORA-600 internal errors" if ora600_count > 0 else None,
            "evidence": [],
            "session_context": SessionStore.get_context_summary(),
            "status": "success",
            "question_type": "ANALYSIS"
        }
    
    def _handle_issue_count_query(self, alerts):
        """
        Handle 'Is this one issue or many?' queries.
        
        Returns a clear, human explanation of whether alerts are clustered
        around few issues or spread across many.
        """
        total = len(alerts)
        
        # Count unique error patterns
        error_patterns = {}
        for a in alerts:
            msg = (a.get("message") or a.get("msg_text") or "")[:100]
            import re
            # Fix ORA code extraction
            ora_match = re.search(r'ora-?(\d+)', msg.lower())
            if ora_match:
                key = f"ORA-{ora_match.group(1)}"
            else:
                # Use first significant word or issue_type
                issue_type = a.get("issue_type")
                if issue_type:
                    key = issue_type.upper()
                else:
                    key = msg[:30] if msg else "UNKNOWN"
            error_patterns[key] = error_patterns.get(key, 0) + 1
        
        unique_patterns = len(error_patterns)
        top_patterns = sorted(error_patterns.items(), key=lambda x: -x[1])[:5]
        top_error = top_patterns[0] if top_patterns else ("UNKNOWN", 0)
        top_concentration = (top_error[1] * 100 // total) if total > 0 else 0
        
        # Determine the assessment
        if unique_patterns <= 3 and top_concentration > 40:
            # Few patterns, high concentration = likely ONE root cause
            answer = (
                f"**This looks like ONE major issue (or closely related issues).**\n\n"
                f"Out of {total:,} alerts, I'm seeing only **{unique_patterns}** distinct error patterns. "
                f"The top error alone accounts for **{top_concentration}%** of all alerts.\n\n"
                f"**The main culprit:** {top_error[0]} ({top_error[1]:,} occurrences)\n\n"
                f"This pattern suggests a single root cause generating cascading alerts. "
                f"Fix the primary issue and alert volume should drop significantly."
            )
        elif unique_patterns <= 5:
            # Few patterns = handful of issues
            answer = (
                f"**A handful of distinct issues (not just one).**\n\n"
                f"I count **{unique_patterns}** unique error patterns across {total:,} alerts.\n\n"
                f"**Top issues:**\n"
            )
            for pattern, count in top_patterns[:5]:
                pct = count * 100 // total
                answer += f"- **{pattern}**: {count:,} ({pct}%)\n"
            answer += f"\nYou'll need to address each of these, but start with the top one."
        else:
            # Many patterns = systemic/widespread
            answer = (
                f"**This is MANY different issues, not one.**\n\n"
                f"Found **{unique_patterns}** unique error patterns across {total:,} alerts. "
                f"This indicates either systemic problems or multiple unrelated failures happening together.\n\n"
                f"**Top patterns (showing 5 of {unique_patterns}):**\n"
            )
            for pattern, count in top_patterns[:5]:
                pct = count * 100 // total
                answer += f"- **{pattern}**: {count:,} ({pct}%)\n"
            answer += f"\nRecommend triaging by database first, then addressing errors per-DB."
        
        return {
            "answer": answer,
            "target": None,
            "intent": "ANALYSIS",
            "confidence": 0.85,
            "confidence_label": "HIGH",
            "actions": [],
            "root_cause": None,
            "evidence": [],
            "session_context": SessionStore.get_context_summary(),
            "status": "success",
            "question_type": "ANALYSIS"
        }
    
    def _handle_most_error_query(self, alerts):
        """Handle 'Which error is causing most alerts?' queries."""
        # Count by error code/type
        error_counts = {}
        for a in alerts:
            msg = (a.get("message") or a.get("msg_text") or "").lower()
            
            # Extract ORA code
            import re
            ora_match = re.search(r'ora-?(\d+)', msg)
            if ora_match:
                # Fix: Ensure proper ORA-XXXXX format (no double dash)
                key = f"ORA-{ora_match.group(1)}"
            else:
                # Use issue_type if available
                issue_type = a.get("issue_type") or "UNKNOWN"
                key = issue_type.upper()
            
            error_counts[key] = error_counts.get(key, 0) + 1
        
        if not error_counts:
            return {
                "answer": "Unable to determine dominant error type from available data.",
                "intent": "FACT",
                "confidence": 0.5
            }
        
        # Find top error
        top_error = max(error_counts.items(), key=lambda x: x[1])
        total = len(alerts)
        
        top_errors = sorted(error_counts.items(), key=lambda x: -x[1])[:5]
        
        answer = (
            f"**Top Error: {top_error[0]}** ({top_error[1]:,} occurrences, "
            f"{top_error[1]*100//total}% of all alerts)\n\n"
            f"**Error Distribution:**\n"
        )
        for err, cnt in top_errors:
            pct = cnt * 100 // total
            answer += f"- **{err}**: {cnt:,} ({pct}%)\n"
        
        # Add context for known errors
        if "ORA-600" in top_error[0]:
            answer += (
                f"\n**About ORA-600:**\n"
                f"Internal error — indicates Oracle kernel issue. "
                f"Check trace files for arguments, search MOS for specific error."
            )
        
        return {
            "answer": answer,
            "target": None,
            "intent": "FACT",
            "confidence": 0.9,
            "confidence_label": "HIGH",
            "actions": [],
            "root_cause": top_error[0],
            "evidence": [],
            "session_context": SessionStore.get_context_summary(),
            "status": "success",
            "question_type": "FACT"
        }
    
    # =====================================================
    # PHASE 9: INCIDENT COMMANDER HANDLERS
    # Autonomous DBA Incident Command Mode
    # =====================================================
    
    def _handle_incident_status_query(self, alerts):
        """
        Handle incident status queries.
        
        Patterns:
        - "What is the incident status?"
        - "Give me a sitrep"
        - "What's happening?"
        - "Status report"
        """
        if not INCIDENT_COMMANDER_AVAILABLE:
            return None
        
        assessment = INCIDENT_COMMANDER.assess_production_state(alerts)
        answer = INCIDENT_COMMANDER.format_incident_response(assessment, audience="DBA")
        
        incident = assessment.get("incident_status", {})
        
        return {
            "answer": answer,
            "target": None,
            "intent": "ANALYSIS",
            "confidence": 0.95,
            "confidence_label": "HIGH",
            "actions": assessment.get("actions", {}).get("do_now", []),
            "root_cause": None,
            "evidence": [],
            "session_context": SessionStore.get_context_summary(),
            "status": "success",
            "question_type": "INCIDENT_COMMAND",
            "incident_severity": incident.get("severity"),
            "incident_status": incident.get("status")
        }
    
    def _handle_priority_query(self, alerts):
        """
        Handle priority/triage queries.
        
        Patterns:
        - "What's the top priority?"
        - "What should I focus on?"
        - "Prioritize the issues"
        - "What's P1?"
        """
        if not INCIDENT_COMMANDER_AVAILABLE:
            return None
        
        assessment = INCIDENT_COMMANDER.assess_production_state(alerts)
        priorities = assessment.get("priorities", [])
        
        if not priorities:
            answer = "No prioritized issues detected. Production appears stable."
        else:
            p1 = next((p for p in priorities if p["priority"] == "P1"), None)
            
            if p1:
                answer = (
                    f"🔥 **TOP PRIORITY (P1): {p1['database']}**\n\n"
                    f"- **{p1['critical_count']:,}** critical alerts\n"
                    f"- Reason: {p1['reason']}\n"
                    f"- Action: {p1['action']}\n\n"
                )
                
                # Add P2/P3 summary
                p2_count = len([p for p in priorities if p["priority"] == "P2"])
                p3_count = len([p for p in priorities if p["priority"] == "P3"])
                
                if p2_count > 0 or p3_count > 0:
                    answer += f"**Also tracking:** {p2_count} P2 issues, {p3_count} P3 issues"
            else:
                answer = "No P1 issues identified. Reviewing P2/P3 items:\n\n"
                for p in priorities[:3]:
                    answer += f"- **{p['priority']}**: {p['database']} ({p['critical_count']:,} critical)\n"
        
        return {
            "answer": answer,
            "target": None,
            "intent": "ANALYSIS",
            "confidence": 0.9,
            "confidence_label": "HIGH",
            "actions": [],
            "root_cause": None,
            "evidence": [],
            "session_context": SessionStore.get_context_summary(),
            "status": "success",
            "question_type": "INCIDENT_COMMAND"
        }
    
    def _handle_next_action_query(self, alerts):
        """
        Handle "what should I do?" queries.
        
        Patterns:
        - "What should I do now?"
        - "What's the next step?"
        - "What action should I take?"
        - "Guide me"
        """
        if not INCIDENT_COMMANDER_AVAILABLE:
            return None
        
        assessment = INCIDENT_COMMANDER.assess_production_state(alerts)
        actions = assessment.get("actions", {})
        
        do_now = actions.get("do_now", [])
        can_wait = actions.get("can_wait", [])
        do_not_touch = actions.get("do_not_touch", [])
        
        answer = "**▶️ ACTION GUIDANCE**\n\n"
        
        if do_now:
            answer += "**DO NOW:**\n"
            for action in do_now:
                answer += f"  ✓ {action}\n"
            answer += "\n"
        
        if can_wait:
            answer += "**CAN WAIT:**\n"
            for action in can_wait[:3]:
                answer += f"  ○ {action}\n"
            answer += "\n"
        
        if do_not_touch:
            answer += "**DO NOT TOUCH:**\n"
            for action in do_not_touch:
                answer += f"  ✗ {action}\n"
        
        return {
            "answer": answer,
            "target": None,
            "intent": "ACTION",
            "confidence": 0.85,
            "confidence_label": "HIGH",
            "actions": do_now,
            "root_cause": None,
            "evidence": [],
            "session_context": SessionStore.get_context_summary(),
            "status": "success",
            "question_type": "INCIDENT_COMMAND"
        }
    
    def _handle_escalation_query(self, alerts):
        """
        Handle escalation queries.
        
        Patterns:
        - "Should I escalate?"
        - "Do I need to call someone?"
        - "Who should I notify?"
        """
        if not INCIDENT_COMMANDER_AVAILABLE:
            return None
        
        assessment = INCIDENT_COMMANDER.assess_production_state(alerts)
        escalation = assessment.get("escalation", {})
        incident = assessment.get("incident_status", {})
        
        if escalation.get("needed"):
            targets = ", ".join(escalation.get("targets", []))
            answer = (
                f"📣 **ESCALATION REQUIRED**\n\n"
                f"**Incident Status:** {incident.get('status', 'UNKNOWN')}\n"
                f"**Critical Alerts:** {assessment.get('critical_count', 0):,}\n\n"
                f"**Notify:** {targets}\n\n"
                f"**Reason:** {escalation.get('reason', 'Active incident requires oversight')}\n\n"
                f"**What to say:**\n"
                f"\"We have an active database incident affecting {incident.get('database_count', 0)} "
                f"database(s) with {assessment.get('critical_count', 0):,} critical alerts. "
                f"Immediate attention required.\""
            )
        else:
            answer = (
                f"📋 **ESCALATION NOT REQUIRED AT THIS TIME**\n\n"
                f"- Incident Status: {incident.get('status', 'NORMAL')}\n"
                f"- Critical Alerts: {assessment.get('critical_count', 0):,}\n\n"
                f"Continue monitoring. Escalate if situation degrades."
            )
        
        return {
            "answer": answer,
            "target": None,
            "intent": "ANALYSIS",
            "confidence": 0.9,
            "confidence_label": "HIGH",
            "actions": [],
            "root_cause": None,
            "evidence": [],
            "session_context": SessionStore.get_context_summary(),
            "status": "success",
            "question_type": "INCIDENT_COMMAND"
        }
    
    def _handle_prediction_query(self, alerts):
        """
        Handle prediction queries (SAFE MODE).
        
        Patterns:
        - "What's likely to fail next?"
        - "What should I watch for?"
        - "Predict the next issue"
        """
        if not INCIDENT_COMMANDER_AVAILABLE:
            return None
        
        assessment = INCIDENT_COMMANDER.assess_production_state(alerts)
        predictions = assessment.get("predictions", [])
        
        if not predictions:
            answer = (
                "**🔮 PREDICTION (Safe Mode)**\n\n"
                "No imminent escalation patterns detected based on current data.\n"
                "Continue standard monitoring."
            )
        else:
            answer = "**🔮 LIKELY NEXT RISKS**\n\n"
            for pred in predictions:
                answer += (
                    f"**{pred.get('subsystem', 'UNKNOWN')}**\n"
                    f"- Prediction: {pred['prediction']}\n"
                    f"- Confidence: {pred['confidence']}\n"
                    f"- Evidence: {pred['evidence']}\n\n"
                )
            
            answer += (
                "⚠️ *Note: These are risk indicators, not guarantees. "
                "Monitor the above areas closely.*"
            )
        
        return {
            "answer": answer,
            "target": None,
            "intent": "PREDICTION",
            "confidence": 0.6,  # Lower confidence for predictions
            "confidence_label": "MEDIUM",
            "actions": [],
            "root_cause": None,
            "evidence": [],
            "session_context": SessionStore.get_context_summary(),
            "status": "success",
            "question_type": "INCIDENT_COMMAND"
        }
    
    def _handle_blast_radius_query(self, alerts):
        """
        Handle blast radius queries.
        
        Patterns:
        - "What's the blast radius?"
        - "How widespread is this?"
        - "How many systems affected?"
        """
        if not INCIDENT_COMMANDER_AVAILABLE:
            return None
        
        assessment = INCIDENT_COMMANDER.assess_production_state(alerts)
        db_breakdown = assessment.get("db_breakdown", {})
        subsystems = assessment.get("subsystem_status", {})
        
        affected_dbs = len([db for db, stats in db_breakdown.items() 
                          if stats.get("CRITICAL", 0) > 0])
        total_dbs = len(db_breakdown)
        affected_subsystems = len(subsystems)
        
        answer = (
            f"**💥 BLAST RADIUS ASSESSMENT**\n\n"
            f"**Databases Affected:** {affected_dbs} of {total_dbs}\n"
            f"**Subsystems Impacted:** {affected_subsystems}\n\n"
            f"**Database Breakdown:**\n"
        )
        
        for db, stats in sorted(db_breakdown.items(), 
                                key=lambda x: x[1].get("CRITICAL", 0), 
                                reverse=True)[:5]:
            status = "🔴" if stats.get("CRITICAL", 0) > 1000 else "🟠" if stats.get("CRITICAL", 0) > 0 else "🟢"
            answer += f"{status} **{db}**: {stats.get('CRITICAL', 0):,} critical\n"
        
        if subsystems:
            answer += f"\n**Subsystem Status:**\n"
            for name, status in subsystems.items():
                icon = "🔴" if status["status"] == "CRITICAL" else "🟠"
                answer += f"{icon} **{name}**: {status['critical']} critical alerts\n"
        
        return {
            "answer": answer,
            "target": None,
            "intent": "ANALYSIS",
            "confidence": 0.9,
            "confidence_label": "HIGH",
            "actions": [],
            "root_cause": None,
            "evidence": [],
            "session_context": SessionStore.get_context_summary(),
            "status": "success",
            "question_type": "INCIDENT_COMMAND"
        }
    
    # =====================================================
    # MAIN ANALYSIS METHOD
    # =====================================================
    
    def analyze(self, question):
        """
        Main analysis entry point.
        
        CRITICAL: This method:
        1. Detects follow-up queries FIRST
        2. Processes through reasoning pipeline if not follow-up
        3. Updates session context for future follow-ups
        4. Returns enhanced response with session context
        
        CONVERSATIONAL FLOW:
        User: "show standby issues" → Standard processing
        User: "show me 20" → Follow-up LIMIT (uses standby context)
        User: "only critical" → Follow-up FILTER (uses standby context)
        
        Args:
            question: User's natural language question
        
        Returns:
            Dict with answer and metadata
        """
        # =====================================================
        # CRITICAL FIX: Reset formatter context for EACH question
        # Prevents root cause/action leakage between questions
        # =====================================================
        self._reset_formatter_context()
        
        # =====================================================
        # PHASE-12.1: Update scope FIRST (before any processing)
        # This ensures scope is available for follow-up detection
        # =====================================================
        if PHASE12_AVAILABLE:
            Phase12Guardrails.update_scope(question)
        
        # Check system readiness
        if not SYSTEM_READY.get("ready", False):
            return {
                "answer": "System is initializing. Please wait...",
                "status": "initializing",
                "actions": [],
                "confidence": 0
            }
        
        # Check data availability
        alerts = GLOBAL_DATA.get("alerts", [])
        if not alerts:
            return {
                "answer": "OEM alert data is not available.",
                "status": "no_data",
                "actions": [],
                "confidence": 0
            }
        
        try:
            # =====================================================
            # PRIORITY PATTERN HANDLING (BEFORE FOLLOWUP DETECTION)
            # Handle specific patterns that should NOT be treated as followups
            # These patterns have explicit syntax that should be matched directly
            # =====================================================
            import re
            q_lower = question.lower()
            
            # =====================================================
            # DATA AWARENESS CHECK (PHASE 8)
            # Check if we have data needed to answer this question
            # =====================================================
            if DATA_AWARENESS_AVAILABLE:
                data_check = DATA_AWARENESS.check_data_availability(question, alerts)
                if not data_check.has_data and data_check.missing_fields:
                    # Generate safe response for missing data
                    missing_field = data_check.missing_fields[0]
                    safe_response = DATA_AWARENESS.get_safe_response_for_missing_data(question, missing_field)
                    return {
                        "answer": f"{data_check.safe_answer_prefix}\n\n{safe_response}",
                        "target": None,
                        "intent": "FACT",
                        "confidence": 0.3,
                        "confidence_label": "LOW",
                        "actions": [],
                        "root_cause": None,
                        "evidence": [],
                        "session_context": SessionStore.get_context_summary(),
                        "status": "success",
                        "question_type": "FACT",
                        "data_limitation": True
                    }
            
            # =====================================================
            # PHASE 9: INCIDENT COMMANDER PATTERNS
            # Autonomous DBA Incident Command Mode
            # =====================================================
            if INCIDENT_COMMANDER_AVAILABLE:
                # Incident Status / Sitrep queries
                if re.search(r'(?:incident\s+)?status|sitrep|what\'?s\s+happening|situation\s+report|current\s+state', q_lower):
                    result = self._handle_incident_status_query(alerts)
                    if result:
                        return self._apply_phase7(result, question, alerts)
                
                # Priority / Triage queries
                if re.search(r'(?:top\s+)?priorit|what\s+should\s+i\s+focus|triage|what\'?s\s+p1|most\s+urgent', q_lower):
                    result = self._handle_priority_query(alerts)
                    if result:
                        return self._apply_phase7(result, question, alerts)
                
                # Next Action queries
                if re.search(r'what\s+should\s+i\s+do|next\s+step|guide\s+me|what\s+action|what\s+now', q_lower):
                    result = self._handle_next_action_query(alerts)
                    if result:
                        return self._apply_phase7(result, question, alerts)
                
                # Escalation queries
                if re.search(r'escalat|should\s+i\s+call|notify|who\s+should\s+i\s+tell', q_lower):
                    result = self._handle_escalation_query(alerts)
                    if result:
                        return self._apply_phase7(result, question, alerts)
                
                # Prediction queries
                if re.search(r'predict|what\s+(?:will|might)\s+fail|next\s+risk|watch\s+for|what\'?s\s+coming', q_lower):
                    result = self._handle_prediction_query(alerts)
                    if result:
                        return self._apply_phase7(result, question, alerts)
                
                # Blast radius queries
                if re.search(r'blast\s+radius|how\s+widespread|how\s+many\s+(?:systems?|dbs?|databases?)\s+affected|scope\s+of\s+(?:impact|incident)', q_lower):
                    result = self._handle_blast_radius_query(alerts)
                    if result:
                        return self._apply_phase7(result, question, alerts)
            
            # =====================================================
            # AUDIENCE-SPECIFIC EXPLANATIONS (HIGH PRIORITY)
            # Must be checked early to avoid fallback handling
            # =====================================================
            
            # DBA EXPLANATION: "Explain like talking to senior DBA"
            # Simplified pattern to catch variations like "you are" vs "you're"
            if re.search(r'explain\s+.*senior\s+dba|like\s+.*senior\s+dba|as\s+a\s+dba', q_lower):
                result = self._handle_dba_explanation_query(alerts)
                if result:
                    return self._apply_phase7(result, question, alerts)
            
            # MANAGER EXPLANATION: "Explain this to a manager"
            if re.search(r'explain\s+(?:this\s+)?(?:to\s+)?(?:a\s+)?manager|for\s+(?:my\s+)?manager|executive\s+summary', q_lower):
                result = self._handle_manager_explanation(alerts)
                if result:
                    return self._apply_phase7(result, question, alerts)
            
            # =====================================================
            # RELATIONSHIP QUERIES: "Are these related to MIDEVSTB?"
            # =====================================================
            related_match = re.search(
                r'(?:are\s+)?(?:these|they|this)\s+related\s+to\s+([A-Za-z0-9_]+)',
                q_lower
            )
            if related_match and DATA_AWARENESS_AVAILABLE:
                target_db = related_match.group(1).upper()
                result = self._handle_relationship_query(target_db, alerts)
                if result:
                    return result
            
            # =====================================================
            # NORMALITY QUERIES: "Is this alert volume normal?"
            # =====================================================
            normal_match = re.search(
                r'(?:is\s+)?(?:this|the)\s+(?:alert\s+)?(?:volume|count|number)\s+normal(?:\s+for\s+([A-Za-z0-9_]+))?',
                q_lower
            )
            if normal_match and DATA_AWARENESS_AVAILABLE:
                db_name = normal_match.group(1).upper() if normal_match.group(1) else None
                result = self._handle_normality_query(db_name, alerts)
                if result:
                    return result
            
            # =====================================================
            # TEMPORAL QUERIES: "alerts from yesterday", "today's alerts"
            # =====================================================
            temporal_match = re.search(
                r'(?:show|how)?\s*(?:me\s+)?(?:alerts?\s+)?(?:from\s+)?(yesterday|today|last\s+hour|last\s+24\s+hours|this\s+week)(?:\s+only)?',
                q_lower
            )
            if temporal_match and DATA_AWARENESS_AVAILABLE:
                time_filter = temporal_match.group(1)
                result = self._handle_temporal_query(time_filter, alerts)
                if result:
                    return result
            
            # =====================================================
            # REPETITION QUERIES: "Why are warnings repeated?"
            # =====================================================
            repeat_match = re.search(
                r'why\s+(?:are\s+)?(?:([A-Za-z0-9_]+)\s+)?(?:warnings?|alerts?)\s+(?:repeated|repeating|duplicated)',
                q_lower
            )
            if repeat_match and DATA_AWARENESS_AVAILABLE:
                db_name = repeat_match.group(1).upper() if repeat_match.group(1) else None
                result = self._handle_repetition_query(db_name, alerts)
                if result:
                    return result
            
            # =====================================================
            # WORRIED QUERIES: "Should I be worried?"
            # =====================================================
            worried_match = re.search(
                r'should\s+i\s+(?:be\s+)?(?:worried|concerned)(?:\s+(?:right\s+)?now)?',
                q_lower
            )
            if worried_match:
                result = self._handle_worried_query(alerts)
                if result:
                    return result
            
            # =====================================================
            # FAILURE PREDICTION: "Which database is most likely to fail?"
            # =====================================================
            fail_predict_match = re.search(
                r'which\s+(?:database|db)\s+(?:is\s+)?(?:most\s+)?(?:likely\s+to\s+fail|will\s+fail\s*(?:next)?|at\s+risk)',
                q_lower
            )
            if fail_predict_match:
                result = self._handle_failure_prediction_query(alerts)
                if result:
                    return result
            
            # =====================================================
            # IGNORE CONSEQUENCES: "What happens if we ignore these?"
            # =====================================================
            ignore_match = re.search(
                r'(?:what\s+(?:happens|will\s+happen)|consequence)\s+(?:of\s+)?(?:if\s+)?(?:we\s+)?ignor(?:e|ing)\s*(?:these|this|the)?\s*(?:alerts?)?',
                q_lower
            )
            if ignore_match:
                result = self._handle_ignore_consequences_query(alerts)
                if result:
                    return result
            
            # =====================================================
            # EVIDENCE QUERIES: "What evidence supports this?"
            # =====================================================
            evidence_match = re.search(
                r'what\s+evidence\s+supports?\s+(?:this|the|being)',
                q_lower
            )
            if evidence_match:
                result = self._handle_evidence_query(alerts)
                if result:
                    return result
            
            # =====================================================
            # MANAGER EXPLANATION: "Explain this to a manager"
            # =====================================================
            manager_match = re.search(
                r'explain\s+(?:this\s+)?(?:to\s+)?(?:a\s+)?manager',
                q_lower
            )
            if manager_match:
                result = self._handle_manager_explanation(alerts)
                if result:
                    return result
            
            # =====================================================
            # DBA EXPLANATION: "Explain like talking to senior DBA"
            # =====================================================
            dba_explain_match = re.search(
                r'explain\s+.*senior\s+dba|like\s+.*senior\s+dba|as\s+a\s+dba',
                q_lower
            )
            if dba_explain_match:
                result = self._handle_dba_explanation_query(alerts)
                if result:
                    return result
            
            # =====================================================
            # ONE BIG ISSUE OR MANY: "Is this one issue or many?"
            # =====================================================
            issue_count_match = re.search(
                r'(?:is\s+)?(?:this|these|it)\s+(?:one\s+)?(?:big\s+)?issue\s+or\s+many|one\s+big\s+issue\s+or\s+many|one\s+issue\s+or\s+many\s+issues',
                q_lower
            )
            if issue_count_match:
                result = self._handle_issue_count_query(alerts)
                if result:
                    return result
            
            # =====================================================
            # WHICH ERROR CAUSING MOST: "Which error is causing most alerts?"
            # =====================================================
            most_error_match = re.search(
                r'which\s+error\s+(?:is\s+)?(?:causing|responsible\s+for)\s+(?:the\s+)?most(?:\s+alerts?)?',
                q_lower
            )
            if most_error_match:
                result = self._handle_most_error_query(alerts)
                if result:
                    return result
            
            # =====================================================
            # NEW FIX: "give me ONLY the count of CRITICAL alerts for MIDEVSTB"
            # Returns JUST the count number
            # =====================================================
            only_count_match = re.search(
                r'(?:give\s+me\s+)?only\s+(?:the\s+)?count\s+(?:of\s+)?(critical|warning|warnings?)\s*(?:alerts?)?\s*(?:for|on|in)?\s*([A-Za-z0-9_]+)?',
                q_lower
            )
            if only_count_match:
                severity = only_count_match.group(1).lower().rstrip('s')
                db_name = only_count_match.group(2).upper() if only_count_match.group(2) else None
                target_severity = "CRITICAL" if severity == "critical" else "WARNING"
                result = self._handle_only_count(target_severity, db_name, alerts)
                if result:
                    return result
            
            # =====================================================
            # NEW FIX: "show CRITICAL alerts 11 to 20 for MIDEVSTBN"
            # Range with severity filter
            # =====================================================
            severity_range_match = re.search(
                r'(?:show|list|display)\s+(?:me\s+)?(critical|warning|warnings?)\s+alerts?\s+(\d+)\s+(?:to|-)\s+(\d+)\s+(?:for|on|in)\s+([A-Za-z0-9_]+)',
                q_lower
            )
            if severity_range_match:
                severity = severity_range_match.group(1).lower().rstrip('s')
                start_idx = int(severity_range_match.group(2))
                end_idx = int(severity_range_match.group(3))
                db_name = severity_range_match.group(4).upper()
                target_severity = "CRITICAL" if severity == "critical" else "WARNING"
                result = self._handle_severity_range_alerts(start_idx, end_idx, target_severity, db_name, alerts)
                if result:
                    return result
            
            # =====================================================
            # NEW FIX: "compare total vs critical alerts for both databases"
            # Compare metrics (total vs critical)
            # =====================================================
            compare_metrics_match = re.search(
                r'compare\s+(total|all)\s+(?:vs|versus|and)\s+(critical|warning)\s+(?:alerts?)?\s*(?:for\s+)?(?:both\s+)?(?:databases?)?',
                q_lower
            )
            if compare_metrics_match:
                result = self._handle_total_vs_severity_comparison(alerts)
                if result:
                    return result
            
            # =====================================================
            # NEW FIX: "show standby alerts summary only (count + db name)"
            # =====================================================
            standby_summary_match = re.search(
                r'(?:show\s+)?standby\s+alerts?\s+summary\s+only',
                q_lower
            )
            if standby_summary_match:
                result = self._handle_standby_summary(alerts)
                if result:
                    return result
            
            # =====================================================
            # NEW FIX: "group alerts by error code"
            # =====================================================
            group_by_error_match = re.search(
                r'group\s+(?:alerts?\s+)?by\s+(?:error\s+)?(?:code|ora)',
                q_lower
            )
            if group_by_error_match:
                result = self._handle_group_by_error_code(alerts)
                if result:
                    return result
            
            # =====================================================
            # NEW FIX: "top 3 alert types per database"
            # =====================================================
            top_types_match = re.search(
                r'top\s+(\d+)\s+(?:alert\s+)?types?\s+(?:per|for\s+each|by)\s+(?:database|db)',
                q_lower
            )
            if top_types_match:
                limit = int(top_types_match.group(1))
                result = self._handle_top_alert_types_per_db(limit, alerts)
                if result:
                    return result
            
            # ISSUE 1: "how many critical alerts for MIDEVSTB" - DB-specific severity count
            db_severity_match = re.search(
                r'how\s+many\s+(critical|warning|warnings?)\s+alerts?\s+(?:for|on|in|exist\s+for)\s+([A-Za-z0-9_]+)',
                q_lower
            )
            if db_severity_match:
                severity = db_severity_match.group(1).lower().rstrip('s')
                db_name = db_severity_match.group(2).upper()
                target_severity = "CRITICAL" if severity == "critical" else "WARNING"
                result = self._handle_db_severity_count(db_name, target_severity, alerts, question)
                if result:
                    return result
            
            # ISSUE 2: "list critical alerts for MIDEVSTB" - List alerts (not summary)
            list_alerts_match = re.search(
                r'list\s+(critical|warning|warnings?|all)?\s*alerts?\s+(?:for|on|in)\s+([A-Za-z0-9_]+)',
                q_lower
            )
            if list_alerts_match:
                severity = (list_alerts_match.group(1) or "").lower().rstrip('s')
                db_name = list_alerts_match.group(2).upper()
                result = self._handle_list_alerts_for_db(db_name, severity, alerts)
                if result:
                    return result
            
            # ISSUE 3: "show first 5 critical alerts for MIDEVSTB" - First N pagination
            first_n_match = re.search(
                r'(?:show|list|display)\s+(?:me\s+)?(?:the\s+)?first\s+(\d+)\s+(critical|warning|warnings?)?\s*alerts?(?:\s+(?:for|on|in)\s+([A-Za-z0-9_]+))?',
                q_lower
            )
            if first_n_match:
                limit = int(first_n_match.group(1))
                severity = (first_n_match.group(2) or "").lower().rstrip('s') if first_n_match.group(2) else None
                db_name = first_n_match.group(3).upper() if first_n_match.group(3) else None
                result = self._handle_first_n_alerts(limit, severity, db_name, alerts)
                if result:
                    return result
            
            # ISSUE 4: "show alerts from 21 to 30" - Range pagination
            range_match = re.search(
                r'(?:show|list|display)\s+(?:me\s+)?alerts?\s+(?:from\s+)?(\d+)\s+(?:to|-)\s+(\d+)(?:\s+(?:for|on|in)\s+([A-Za-z0-9_]+))?',
                q_lower
            )
            if range_match:
                start_idx = int(range_match.group(1))
                end_idx = int(range_match.group(2))
                db_name = range_match.group(3).upper() if range_match.group(3) else None
                result = self._handle_range_alerts(start_idx, end_idx, db_name, alerts)
                if result:
                    return result
            
            # ISSUE 5: "compare alerts between MIDEVSTB and MIDEVSTBN" - DB comparison
            compare_match = re.search(
                r'compare\s+(?:alerts?\s+)?(?:between\s+)?([A-Za-z0-9_]+)\s+(?:and|vs|versus|with)\s+([A-Za-z0-9_]+)',
                q_lower
            )
            if compare_match:
                db1 = compare_match.group(1).upper()
                db2 = compare_match.group(2).upper()
                result = self._handle_db_comparison(db1, db2, alerts)
                if result:
                    return result
            
            # ISSUE 6: "how many standby alerts" - Standby alert count
            standby_count_match = re.search(
                r'how\s+many\s+(standby|dataguard|data\s*guard)\s*(?:alerts?)?',
                q_lower
            )
            if standby_count_match:
                result = self._handle_standby_count(alerts)
                if result:
                    return result
            
            # =====================================================
            # CRITICAL: CHECK IF CONTEXT SHOULD BE RESET FIRST
            # This must happen BEFORE follow-up detection
            # A question is NEW if it changes intent type or entity
            # =====================================================
            if self._should_reset_context(question):
                # This is a NEW question - reset conversation context
                SessionStore.set_conversation_context(
                    topic=None,
                    alert_type=None,
                    severity=None,
                    databases=[],
                    result_count=0,
                    has_context=False
                )
            
            # =====================================================
            # CONVERSATIONAL INTELLIGENCE: Detect follow-ups
            # Only apply if context wasn't just reset
            # =====================================================
            is_followup, followup_type, extracted_value = self._detect_followup_type(question)
            
            # CRITICAL FIX: ENTITY_SPECIFIC queries should ALWAYS go through follow-up handler
            # They set up context for future follow-ups even if current context is empty
            # Other follow-up types (LIMIT, FILTER, etc.) require prior context
            context = SessionStore.get_conversation_context()
            should_handle_as_followup = False
            
            if is_followup and followup_type:
                if followup_type == "ENTITY_SPECIFIC":
                    # ENTITY_SPECIFIC always handled - sets up context for future
                    should_handle_as_followup = True
                elif context.get("has_context"):
                    # Other types need prior context
                    should_handle_as_followup = True
            
            if should_handle_as_followup:
                followup_result = self._handle_followup(question, followup_type, extracted_value, alerts)
                if followup_result and followup_result.get("answer"):
                    # Return follow-up response directly
                    return {
                        "answer": followup_result.get("answer"),
                        "target": followup_result.get("target"),
                        "intent": followup_result.get("intent", "FOLLOWUP"),
                        "confidence": followup_result.get("confidence", 0.8),
                        "confidence_label": "HIGH" if followup_result.get("confidence", 0) > 0.7 else "MEDIUM",
                        "actions": [],
                        "root_cause": None,
                        "evidence": [],
                        "session_context": SessionStore.get_context_summary(),
                        "status": "success",
                        "question_type": followup_result.get("question_type", "FACT")
                    }
            
            # =====================================================
            # DIRECT SEVERITY QUERY HANDLING (NEW)
            # Handle "show only warnings", "show all critical alerts" etc.
            # as standalone queries WITHOUT requiring prior context
            # =====================================================
            if is_followup and followup_type == "FILTER" and not context.get("has_context"):
                # This is a direct severity filter query - handle it directly
                severity = extracted_value
                if severity:
                    result = self._handle_direct_severity_query(question, severity, alerts)
                    if result:
                        return result
            
            # Also check for "excluding" patterns (e.g., "show alerts excluding warning")
            q_lower = question.lower()
            # Also check for "excluding" patterns (e.g., "show alerts excluding warning")
            import re  # Ensure re is available in this scope
            q_lower = question.lower()
            excluding_match = re.search(r'exclud(?:e|ing)\s+(warning|warnings?|critical)', q_lower)
            if excluding_match:
                excluded = excluding_match.group(1).lower().rstrip('s')
                # Invert: excluding warning = show critical, excluding critical = show warning
                target_severity = "CRITICAL" if excluded == "warning" else "WARNING"
                result = self._handle_direct_severity_query(question, target_severity, alerts)
                if result:
                    return result
            
            # Check for "show all critical/warning alerts" pattern
            all_severity_match = re.search(r'(?:show|list|display)\s+(?:me\s+)?(?:all\s+)?(critical|warning|warnings?)\s+alerts?', q_lower)
            if all_severity_match:
                severity = all_severity_match.group(1).lower().rstrip('s')
                target_severity = "CRITICAL" if severity == "critical" else "WARNING"
                result = self._handle_direct_severity_query(question, target_severity, alerts)
                if result:
                    return result
            
            # Check for "how many warning/critical alerts" pattern
            how_many_match = re.search(r'how\s+many\s+(warning|warnings?|critical)\s*(?:alerts?)?', q_lower)
            if how_many_match:
                severity = how_many_match.group(1).lower().rstrip('s')
                target_severity = "CRITICAL" if severity == "critical" else "WARNING"
                result = self._handle_severity_count_query(question, target_severity, alerts)
                if result:
                    return result
            
            # =====================================================
            # ISSUE 1 FIX: "how many critical alerts for MIDEVSTB"
            # Extract DB-specific severity count
            # =====================================================
            db_severity_match = re.search(
                r'how\s+many\s+(critical|warning|warnings?)\s+alerts?\s+(?:for|on|in|exist\s+for)\s+([A-Za-z0-9_]+)',
                q_lower
            )
            if db_severity_match:
                severity = db_severity_match.group(1).lower().rstrip('s')
                db_name = db_severity_match.group(2).upper()
                target_severity = "CRITICAL" if severity == "critical" else "WARNING"
                result = self._handle_db_severity_count(db_name, target_severity, alerts, question)
                if result:
                    return result
            
            # =====================================================
            # ISSUE 2 FIX: "list critical alerts for MIDEVSTB"
            # Return actual list of alerts, not summary
            # =====================================================
            list_alerts_match = re.search(
                r'list\s+(critical|warning|warnings?|all)?\s*alerts?\s+(?:for|on|in)\s+([A-Za-z0-9_]+)',
                q_lower
            )
            if list_alerts_match:
                severity = (list_alerts_match.group(1) or "").lower().rstrip('s')
                db_name = list_alerts_match.group(2).upper()
                result = self._handle_list_alerts_for_db(db_name, severity, alerts)
                if result:
                    return result
            
            # =====================================================
            # ISSUE 3 FIX: "show first 5 critical alerts"
            # Pagination with first N
            # =====================================================
            first_n_match = re.search(
                r'(?:show|list|display)\s+(?:me\s+)?(?:the\s+)?first\s+(\d+)\s+(critical|warning|warnings?)?\s*alerts?(?:\s+(?:for|on|in)\s+([A-Za-z0-9_]+))?',
                q_lower
            )
            if first_n_match:
                limit = int(first_n_match.group(1))
                severity = (first_n_match.group(2) or "").lower().rstrip('s') if first_n_match.group(2) else None
                db_name = first_n_match.group(3).upper() if first_n_match.group(3) else None
                result = self._handle_first_n_alerts(limit, severity, db_name, alerts)
                if result:
                    return result
            
            # =====================================================
            # ISSUE 4 FIX: "show alerts from 21 to 30"
            # Range-based pagination
            # =====================================================
            range_match = re.search(
                r'(?:show|list|display)\s+(?:me\s+)?alerts?\s+(?:from\s+)?(\d+)\s+(?:to|-)\s+(\d+)(?:\s+(?:for|on|in)\s+([A-Za-z0-9_]+))?',
                q_lower
            )
            if range_match:
                start_idx = int(range_match.group(1))
                end_idx = int(range_match.group(2))
                db_name = range_match.group(3).upper() if range_match.group(3) else None
                result = self._handle_range_alerts(start_idx, end_idx, db_name, alerts)
                if result:
                    return result
            
            # =====================================================
            # ISSUE 5 FIX: "compare alerts between MIDEVSTB and MIDEVSTBN"
            # Database comparison
            # =====================================================
            compare_match = re.search(
                r'compare\s+(?:alerts?\s+)?(?:between\s+)?([A-Za-z0-9_]+)\s+(?:and|vs|versus|with)\s+([A-Za-z0-9_]+)',
                q_lower
            )
            if compare_match:
                db1 = compare_match.group(1).upper()
                db2 = compare_match.group(2).upper()
                result = self._handle_db_comparison(db1, db2, alerts)
                if result:
                    return result
            
            # =====================================================
            # ISSUE 6 FIX: "how many standby alerts"
            # Standby/DataGuard alert count
            # =====================================================
            standby_count_match = re.search(
                r'how\s+many\s+(standby|dataguard|data\s*guard)\s*(?:alerts?)?',
                q_lower
            )
            if standby_count_match:
                result = self._handle_standby_count(alerts)
                if result:
                    return result
            
            # =====================================================
            # STANDARD PROCESSING: Process through pipeline
            # =====================================================
            
            # Detect topic type for context storage
            is_standby_question = any(kw in q_lower for kw in [
                "standby", "data guard", "dataguard", "apply lag", 
                "transport lag", "mrp", "redo apply", "dr", "replica"
            ])
            
            # Get session context for follow-up questions
            session_context = SessionStore.get_context_phrase()
            session_state = SessionStore.get_state()
            
            # Process through reasoning pipeline
            result = self.pipeline.process(question)
            
            # Extract key information
            answer = result.get("answer", "Unable to process question.")
            target = result.get("target")
            intent = result.get("intent")
            confidence = result.get("confidence", 0.5)
            confidence_label = result.get("confidence_label", "MEDIUM")
            evidence = result.get("evidence", [])
            question_type = result.get("question_type", "FACT")  # Default to FACT
            
            # =====================================================
            # SINGLE RESPONSE RULE (NON-NEGOTIABLE)
            # =====================================================
            # The pipeline has returned a response. This IS the answer.
            # DO NOT regenerate, validate, or override the response.
            # Trust the pipeline. ONE HANDLER → ONE RESPONSE → STOP.
            # =====================================================
            
            # =====================================================
            # PRODUCTION: 5-INTENT CLASSIFICATION (MANDATORY)
            # =====================================================
            # Use IntentResponseRouter for strict 5-intent classification
            # This determines what goes in the response
            # =====================================================
            if ROUTER_AVAILABLE:
                question_type = IntentResponseRouter.get_question_type(question, intent)
                should_have_actions = IntentResponseRouter.should_include_actions(question, intent)
                should_include_root_cause = IntentResponseRouter.should_include_root_cause(question, intent)
            elif INTENT_ENGINE_AVAILABLE:
                should_have_actions = OEMIntentEngine.should_include_actions(intent, question)
                should_include_root_cause = OEMIntentEngine.should_include_root_cause(intent, question)
            else:
                should_have_actions = False
                should_include_root_cause = False
            
            # =====================================================
            # STRICT ACTION SPAM PREVENTION (NON-NEGOTIABLE)
            # =====================================================
            # IF intent ≠ ACTION: DO NOT include action plan
            # This is enforced at the service layer to prevent any
            # downstream components from adding actions
            # =====================================================
            actions = []
            if should_have_actions:
                actions = self._extract_actions_from_answer(answer)
            
            # Extract root cause info only if relevant
            # CRITICAL: Use fresh context, NOT cached from previous question
            root_cause = None
            if should_include_root_cause:
                root_cause = self._extract_root_cause(answer)
            
            # =====================================================
            # ROOT CAUSE CONFIDENCE LOGIC (MANDATORY FIX)
            # =====================================================
            # If evidence_score >= 0.80 → HIGH confidence
            # If evidence_score >= 0.60 → MEDIUM confidence (inferred)
            # Else → May still infer if patterns exist
            #
            # ORA-600/INTERNAL_ERROR with high volume MUST NOT be UNKNOWN
            # =====================================================
            if should_include_root_cause:
                locked_rc = SessionStore.get_locked_root_cause(target)
                if locked_rc:
                    # Use locked root cause - do NOT change it
                    root_cause = locked_rc
                elif PRODUCTION_ENGINE_AVAILABLE:
                    # Infer root cause with strict confidence rules
                    rc_result = RootCauseFallbackEngine.infer_root_cause(alerts, target)
                    rc_score = rc_result.get("total_score", 0) if rc_result else 0
                    rc_count = rc_result.get("count", 0) if rc_result else 0
                    
                    # Apply strict confidence rules
                    if rc_score >= 0.80 or rc_count >= 10000:
                        # HIGH confidence - use computed root cause
                        confidence_label = "HIGH"
                        root_cause = rc_result.get("abstract_cause") or rc_result.get("root_cause")
                    elif rc_score >= 0.60 or rc_count >= 1000:
                        # MEDIUM confidence - inferred
                        confidence_label = "MEDIUM"
                        root_cause = rc_result.get("abstract_cause") or rc_result.get("root_cause")
                    elif rc_result.get("root_cause") and "not found" not in rc_result.get("root_cause", "").lower():
                        # Some evidence exists - use inferred cause
                        root_cause = rc_result.get("abstract_cause") or rc_result.get("root_cause")
                        confidence_label = "LOW" if rc_score < 0.30 else "MEDIUM"
                    
                    # Lock HIGH confidence root cause for session
                    if confidence_label == "HIGH" and root_cause:
                        SessionStore.lock_root_cause(root_cause, target)
            
            # =====================================================
            # ACTION FALLBACK GUARANTEE (ONLY FOR ACTION INTENT)
            # =====================================================
            # Actions must NEVER be empty for ACTION-type questions
            # But MUST be empty for all other question types
            # =====================================================
            if should_have_actions and not actions and PRODUCTION_ENGINE_AVAILABLE:
                # Build root cause result for action engine
                rc_result = RootCauseFallbackEngine.infer_root_cause(alerts, target)
                
                # Detect temporal pattern
                breakdown = rc_result.get("score_breakdown", {})
                temporal_pattern = "sustained"
                if breakdown.get("burst", 0) > 0.5:
                    temporal_pattern = "burst"
                elif breakdown.get("repetition", 0) > 0.5:
                    temporal_pattern = "repeating"
                
                # Get production-grade actions
                actions = ActionFallbackEngine.get_actions(
                    rc_result,
                    confidence_label if confidence_label in ["CRITICAL", "HIGH", "MEDIUM", "LOW"] else "MEDIUM",
                    temporal_pattern
                )
            
            # =====================================================
            # SESSION MEMORY (ACTIVE USE, NOT DECORATIVE)
            # =====================================================
            if PRODUCTION_ENGINE_AVAILABLE:
                SessionMemoryEngine.update(
                    last_root_cause=root_cause,
                    last_abstract_cause=ORACodeMappingEngine.get_abstract_cause(root_cause) if root_cause else None,
                    risk_posture=confidence_label
                )
                if target:
                    SessionMemoryEngine.set_highest_risk(target, confidence)
                if root_cause and "ORA-" in str(root_cause):
                    SessionMemoryEngine.add_ora_code(str(root_cause).split()[0])
            
            # Update session memory (existing) - only if analytical/action question
            if should_include_root_cause:
                self._update_session(
                    question=question,
                    target=target,
                    intent=intent,
                    root_cause=root_cause,
                    confidence=confidence,
                    answer=answer
                )
            
            # =====================================================
            # CONVERSATIONAL CONTEXT: Store context for follow-ups
            # =====================================================
            # This enables "show me 20", "only critical", "this database"
            # =====================================================
            alert_type = None
            topic = None
            result_count = 0
            databases_mentioned = []
            
            # Detect topic from intent/question
            if is_standby_question or intent == "STANDBY_DATAGUARD":
                alert_type = "dataguard"
                topic = "STANDBY_ALERTS"
            elif "tablespace" in q_lower:
                alert_type = "tablespace"
                topic = "TABLESPACE_ALERTS"
            elif "critical" in q_lower:
                topic = "CRITICAL_ALERTS"
            elif target:
                topic = "{0}_ALERTS".format(target.upper())
            
            # Try to extract count from answer
            import re
            count_match = re.search(r'\*\*(\d+(?:,\d+)*)\*\*', answer)
            if count_match:
                try:
                    result_count = int(count_match.group(1).replace(",", ""))
                except ValueError:
                    pass
            
            # Extract databases mentioned
            if target:
                databases_mentioned.append(target)
            db_pattern = re.findall(r'\b([A-Z][A-Z0-9_]{2,}(?:STB|STBN|DB)?)\b', answer)
            for db in db_pattern:
                if db not in databases_mentioned and len(db) > 3:
                    # Verify it's a known database
                    for a in alerts[:100]:  # Check first 100 alerts
                        if (a.get("target_name") or a.get("target") or "").upper() == db:
                            databases_mentioned.append(db)
                            break
            
            # Store context
            SessionStore.set_conversation_context(
                topic=topic,
                alert_type=alert_type,
                result_count=result_count,
                databases=databases_mentioned[:5]  # Keep top 5
            )
            SessionStore.update(last_target=target, last_intent=intent)
            
            # =====================================================
            # PHASE 7: ENTERPRISE TRUST PROCESSING
            # Apply trust, explainability, and guardrails
            # =====================================================
            if PHASE7_TRUST_AVAILABLE:
                # Determine answer type for confidence scoring
                if "how many" in q_lower or result_count > 0:
                    answer_type = "count"
                elif "predict" in q_lower or "will" in q_lower or question_type == "PREDICTION":
                    answer_type = "prediction"
                elif root_cause:
                    answer_type = "root_cause"
                else:
                    answer_type = "general"
                
                # Filter alerts by target for scope validation
                target_alerts = []
                if target:
                    filtered, _ = DB_SCOPE_GUARD.filter_alerts_strict(alerts, target)
                    target_alerts = filtered
                else:
                    target_alerts = alerts
                
                # Process through trust engine
                try:
                    trusted = ENTERPRISE_TRUST.process_answer(
                        question=question,
                        raw_answer=answer,
                        answer_type=answer_type,
                        target_database=target,
                        alerts_used=target_alerts[:100]  # Limit for performance
                    )
                    
                    # Apply sanitized answer
                    answer = trusted.answer
                    
                    # Update confidence from Phase 7
                    confidence = trusted.confidence.score
                    confidence_label = trusted.confidence.level.value
                    
                    # Add Phase 7 metadata
                    phase7_metadata = {
                        "trust_score": trusted.trust_score,
                        "scope_valid": trusted.scope_valid.is_valid,
                        "quality_passed": trusted.quality_check.passed,
                        "phase7_processed": True
                    }
                except Exception as e:
                    # Don't fail on Phase 7 errors - just log and continue
                    print("[Phase7] Trust processing error:", str(e))
                    phase7_metadata = {"phase7_processed": False, "error": str(e)}
            else:
                phase7_metadata = {"phase7_processed": False}
            
            # =====================================================
            # PHASE 11: SELF-AUDITING INTELLIGENCE + DBA GUARDRAILS
            # Apply all 7 guardrails BEFORE returning any response
            # =====================================================
            self_audit_metadata = {"self_audit_processed": False}
            if SELF_AUDIT_AVAILABLE:
                try:
                    # Extract values for fact registration
                    extracted_values = {}
                    count_match = re.search(r'\*\*(\d+(?:,\d+)*)\*\*', answer)
                    if count_match:
                        try:
                            extracted_values["count"] = int(count_match.group(1).replace(",", ""))
                        except ValueError:
                            pass
                    if target:
                        extracted_values["target_database"] = target
                    
                    # Use audit_before_respond which includes ALL 7 DBA Guardrails:
                    # 1. ANSWER PRECISION - Match answer mode to question
                    # 2. SCOPE CONTROL - No data leakage outside requested scope
                    # 3. PREDICTIVE REASONING SAFETY - No absolute predictions
                    # 4. NO-DATA / LOW-DATA HANDLING - Proper uncertainty handling
                    # 5. ANTI-OVEREXPLANATION - Match answer length to question
                    # 6. CONSISTENCY CHECK - No conflicting values
                    # 7. PRODUCTION-SAFE RESPONSE - Calm, professional language
                    audited_answer, audit_result = audit_before_respond(
                        question=question,
                        answer=answer,
                        data_used=alerts[:100],  # Sample for performance
                        extracted_values=extracted_values
                    )
                    
                    # Use the guardrail-processed answer
                    answer = audited_answer
                    
                    # Store audit metadata
                    self_audit_metadata = {
                        "self_audit_processed": True,
                        "dba_guardrails_applied": DBA_GUARDRAILS_AVAILABLE,
                        "passed": audit_result.passed,
                        "trust_mode": audit_result.trust_mode.value,
                        "confidence": audit_result.confidence.value,
                        "violations": audit_result.violations[:3] if audit_result.violations else [],
                    }
                        
                except Exception as e:
                    self_audit_metadata = {"self_audit_processed": False, "error": str(e)}
            
            # Build enhanced response
            response = {
                "answer": answer,
                "target": target,
                "intent": intent,
                "confidence": confidence,
                "confidence_label": confidence_label,
                "actions": actions if should_have_actions else [],  # ENFORCE: No actions unless ACTION intent
                "root_cause": root_cause if should_include_root_cause else None,
                "evidence": evidence,
                "session_context": SessionStore.get_context_summary(),
                "status": "success",
                "question_type": question_type,  # 5-intent type
                "phase7": phase7_metadata,  # Phase 7 trust info
                "self_audit": self_audit_metadata  # Phase 11 self-audit info
            }
            
            # =====================================================
            # PHASE 12.1: PRODUCTION-GRADE DBA INTELLIGENCE GUARDRAILS
            # FINAL enforcement before ANY response is returned
            # =====================================================
            if PHASE12_AVAILABLE:
                try:
                    response = enforce_phase12(
                        question=question,
                        result=response,
                        data_used=alerts[:100]
                    )
                    
                    # Run self-check for violations
                    violations = self_check_answer(question, response.get("answer", ""))
                    if violations:
                        # Downgrade confidence if violations found
                        response["confidence_label"] = "MEDIUM"
                        response["_phase12_violations"] = violations[:3]
                    
                    response["phase12"] = {
                        "processed": True,
                        "db_scope": get_active_db_scope(),
                        "violations": violations[:3] if violations else []
                    }
                except Exception as e:
                    response["phase12"] = {"processed": False, "error": str(e)}
            
            # Add production engine context if available
            if PRODUCTION_ENGINE_AVAILABLE:
                response["production_enhanced"] = True
                response["session_memory"] = SessionMemoryEngine.get_state()
            
            return response
            
        except Exception as e:
            # ===========================================================
            # PRODUCTION RULE: NEVER show "I apologize" or generic errors
            # Always provide a meaningful, helpful response
            # ===========================================================
            import traceback
            error_trace = traceback.format_exc()
            
            # Get question type for appropriate fallback
            question_type = "FACTUAL"
            if ROUTER_AVAILABLE:
                try:
                    question_type = IntentResponseRouter.get_question_type(question)
                except:
                    pass
            
            # Build intelligent fallback response based on question type
            fallback_response = self._build_error_fallback_response(question, question_type, str(e))
            
            return fallback_response
    
    def _extract_actions_from_answer(self, answer):
        """
        Extract structured actions from the answer text.
        
        The pipeline embeds actions in the "What to do now" section.
        
        PRODUCTION v2.1: Returns empty list if no actions found.
        Fallback actions are handled separately based on intent eligibility.
        """
        actions = []
        
        if "What to do now" not in answer:
            # No action section - return empty (caller decides on fallback)
            return []
        
        
        # Find the actions section
        try:
            start_idx = answer.find("What to do now")
            end_idx = answer.find("Confidence:", start_idx)
            if end_idx == -1:
                end_idx = len(answer)
            
            action_section = answer[start_idx:end_idx]
            
            # Parse numbered actions
            import re
            # Match patterns like "1. " or "**1. For"
            matches = re.findall(r'\*\*(\d+)\. For ([^:*]+):', action_section)
            
            for num, cause in matches:
                # Find the actions for this cause
                cause_start = action_section.find("For {}:".format(cause))
                if cause_start == -1:
                    continue
                
                # Extract action lines
                cause_section = action_section[cause_start:cause_start+500]
                action_lines = re.findall(r'^\s+(\d+)\. (.+)$', cause_section, re.MULTILINE)
                
                urgency_match = re.search(r'Urgency: (\w+)', cause_section)
                urgency = urgency_match.group(1) if urgency_match else "MEDIUM"
                
                actions.append({
                    "cause": cause.strip(),
                    "steps": [line[1] for line in action_lines[:4]],
                    "urgency": urgency
                })
            
            if actions:
                return actions
                
        except Exception:
            pass
        
        # PRODUCTION v2.1: Return empty, not fallback (caller decides based on intent)
        return []
    
    def _extract_root_cause(self, answer):
        """Extract root cause information from the answer."""
        import re
        
        # Look for root cause patterns
        patterns = [
            r'Underlying Root Cause:\*\*\s*([^\n]+)',
            r'Inferred Root Cause[^:]*:\*\*\s*([^\n]+)',
            r'Computed Root Cause:\*\*\s*([^\n]+)',
            r'Primary root cause is ([^\(]+)',
            r'Root cause:\s*([^\(]+)',
            r'Abstract Cause:\*\*\s*([^\n]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, answer, re.IGNORECASE)
            if match:
                result = match.group(1).strip()
                # Filter out false positives
                if result.upper().startswith("HIGH") or result.upper().startswith("MEDIUM") or result.upper().startswith("LOW"):
                    continue  # Skip confidence level matches
                if "%" in result and "Confidence" in result:
                    continue  # Skip confidence percentage
                return result
        
        return None
    
    def _generate_standby_specific_answer(self, question, alerts):
        """
        CRITICAL FIX: Generate answer using ONLY standby/dataguard alerts.
        
        This ensures STANDBY_DATAGUARD intent NEVER returns overall alert counts.
        Standby questions MUST be answered with standby-specific data only.
        
        Args:
            question: The user's question
            alerts: All alerts from GLOBAL_DATA
            
        Returns:
            Dict with standby-specific answer or None if no standby alerts
        """
        from collections import defaultdict
        
        # Data Guard specific keywords for filtering
        DATAGUARD_KEYWORDS = [
            "standby", "data guard", "dataguard", "apply lag", "transport lag",
            "mrp", "redo apply", "gap", "archive gap", "switchover", "failover",
            "dg", "dgmgrl", "redo transport"
        ]
        
        # Data Guard specific ORA codes
        DG_ORA_CODES = {
            "ORA-16014": "Archive log destination issue",
            "ORA-16058": "Data Guard configuration error",
            "ORA-16000": "Database open for read-only access",
            "ORA-16004": "Backup in progress",
            "ORA-16006": "Archive log cannot be applied",
            "ORA-16008": "Recovery operation suspended",
            "ORA-16009": "Archivelog gap",
            "ORA-16016": "Archive log gap",
            "ORA-16038": "Log cannot be archived",
            "ORA-16047": "DGID mismatch",
            "ORA-16066": "Redo transport connection failure",
            "ORA-16191": "Redo transport session reinstatement required"
        }
        
        # Filter ONLY standby/dataguard alerts
        standby_alerts = []
        for alert in alerts:
            if not alert:
                continue
            message = (alert.get("message") or alert.get("msg_text") or "").lower()
            
            # Check for dataguard keywords
            is_dg = False
            for kw in DATAGUARD_KEYWORDS:
                if kw in message:
                    is_dg = True
                    break
            
            # Check for DG-specific ORA codes
            if not is_dg:
                for ora_code in DG_ORA_CODES.keys():
                    if ora_code in message or ora_code.replace("ORA-", "ORA-0") in message:
                        is_dg = True
                        break
            
            if is_dg:
                standby_alerts.append(alert)
        
        # If no standby alerts found, return appropriate message
        if not standby_alerts:
            return {
                "answer": "No Data Guard or Standby database errors found in the current OEM alert data. "
                          "This indicates Data Guard configurations are operating normally, or standby monitoring is not configured.",
                "target": None,
                "confidence": 0.90,
                "confidence_label": "HIGH",
                "evidence": ["Searched {:,} total alerts for Data Guard-specific patterns".format(len(alerts))],
                "question_type": "FACT"
            }
        
        # Analyze standby-specific alerts
        db_counts = defaultdict(int)
        dg_ora_codes = defaultdict(int)
        dg_issues = []
        
        for alert in standby_alerts:
            # Count by database
            db = alert.get("target_name") or alert.get("target") or "Unknown"
            db_counts[db] += 1
            
            # Extract DG-specific ORA codes
            msg = alert.get("message") or alert.get("msg_text") or ""
            for ora_code, desc in DG_ORA_CODES.items():
                if ora_code in msg or ora_code.replace("ORA-", "ORA-0") in msg:
                    dg_ora_codes[ora_code] += 1
                    if len(dg_issues) < 5:
                        dg_issues.append("{}: {}".format(ora_code, desc))
        
        # Build standby-specific answer
        total_dg_alerts = len(standby_alerts)
        top_db = max(db_counts.items(), key=lambda x: x[1]) if db_counts else ("Unknown", 0)
        
        # Format answer
        answer_parts = []
        answer_parts.append("**{:,} Data Guard/Standby errors found**".format(total_dg_alerts))
        
        if top_db[0] != "Unknown":
            answer_parts.append("Most affected standby: **{}** ({} alerts)".format(top_db[0], top_db[1]))
        
        if dg_ora_codes:
            answer_parts.append("\n**Data Guard-specific errors:**")
            for ora, count in sorted(dg_ora_codes.items(), key=lambda x: x[1], reverse=True)[:5]:
                desc = DG_ORA_CODES.get(ora, "Data Guard error")
                answer_parts.append("• {}: {} ({:,} occurrences)".format(ora, desc, count))
        
        # Add affected databases
        if len(db_counts) > 1:
            answer_parts.append("\n**Affected standby databases:**")
            for db, count in sorted(db_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                answer_parts.append("• {}: {} alerts".format(db, count))
        
        return {
            "answer": "\n".join(answer_parts),
            "target": top_db[0] if top_db[0] != "Unknown" else None,
            "confidence": 0.90,
            "confidence_label": "HIGH",
            "evidence": dg_issues[:3] if dg_issues else ["Data Guard alerts detected"],
            "question_type": "FACT"
        }
    
    def _update_session(self, question, target, intent, root_cause, confidence, answer):
        """Update session memory after analysis."""
        
        # Update basic state
        SessionStore.update(
            last_question=question,
            last_target=target,
            last_intent=intent,
            last_confidence=confidence
        )
        
        # Track root cause
        if root_cause:
            SessionStore.update(last_root_cause=root_cause)
            
            # Check if it's an abstract cause
            abstract_causes = [
                "Internal Oracle engine",
                "Network / listener",
                "Storage / tablespace",
                "Memory pressure",
                "Data Guard",
                "Oracle operational"
            ]
            for abstract in abstract_causes:
                if abstract.lower() in root_cause.lower():
                    SessionStore.update(last_abstract_cause=root_cause)
                    break
        
        # Track ORA codes
        import re
        ora_matches = re.findall(r'ORA-\d+', answer)
        for ora in ora_matches[:3]:
            SessionStore.add_dominant_ora(ora)
        
        # Track peak hour
        peak_match = re.search(r'[Pp]eak[^0-9]*(\d{1,2}):00', answer)
        if peak_match:
            SessionStore.update(peak_alert_hour=int(peak_match.group(1)))
        
        # Track risk level
        risk_match = re.search(r'Risk Level:\s*(\w+)', answer)
        if risk_match:
            SessionStore.update(overall_risk_posture=risk_match.group(1))
        
        # Track highest risk database
        if target and "CRITICAL" in answer.upper():
            SessionStore.set_highest_risk_db(target)
        
        # Record in history
        SessionStore.record_analysis({
            "question": question,
            "target": target,
            "intent": intent,
            "root_cause": root_cause,
            "confidence": confidence
        })
    
    def _get_fallback_actions(self):
        """
        Get fallback actions when normal extraction fails.
        
        CRITICAL: Actions must NEVER be empty.
        PRODUCTION RULE: Use locked session values for consistency.
        """
        session = SessionStore.get_context_summary()
        state = SessionStore.get_state()
        
        actions = []
        
        # PRODUCTION FIX: Use locked values when available
        locked_rc = state.get("locked_root_cause")
        if locked_rc and locked_rc not in ["OTHER", "UNKNOWN", "Unknown"]:
            # Map locked root cause to actions
            if PRODUCTION_ENGINE_AVAILABLE:
                ora_actions = ORACodeMappingEngine.get_actions_for_code(locked_rc)
                actions.append({
                    "cause": "{} (from session - locked)".format(locked_rc),
                    "steps": ora_actions.get("actions", [
                        "Search My Oracle Support for {}".format(locked_rc),
                        "Review alert log for detailed context",
                        "Check trace files for stack dump"
                    ]),
                    "urgency": ora_actions.get("urgency", "HIGH")
                })
        
        # Use session context if available
        if not actions and session.get("dominant_ora_codes"):
            top_ora = session["dominant_ora_codes"][0]
            if PRODUCTION_ENGINE_AVAILABLE:
                ora_actions = ORACodeMappingEngine.get_actions_for_code(top_ora)
                actions.append({
                    "cause": "{} (from session history)".format(top_ora),
                    "steps": ora_actions.get("actions", [
                        "Search My Oracle Support for {}".format(top_ora),
                        "Review alert log for detailed error context",
                        "Check trace files for stack dump"
                    ]),
                    "urgency": ora_actions.get("urgency", "HIGH")
                })
            else:
                actions.append({
                    "cause": "{} (from session history)".format(top_ora),
                    "steps": [
                        "Search My Oracle Support for {}".format(top_ora),
                        "Review alert log for detailed error context",
                        "Check trace files for stack dump"
                    ],
                    "urgency": "HIGH"
                })
        
        # Use locked highest risk database
        locked_db = state.get("locked_highest_risk_db") or session.get("highest_risk_database")
        if locked_db:
            actions.append({
                "cause": "{} (highest risk - locked)".format(locked_db),
                "steps": [
                    "Monitor database status continuously",
                    "Check resource utilization (CPU, memory, I/O)",
                    "Review recent configuration changes",
                    "Prepare escalation if situation degrades"
                ],
                "urgency": "HIGH" if state.get("overall_risk_posture") == "CRITICAL" else "MEDIUM"
            })
        
        # PRODUCTION RULE: Always have at least one action - NEVER empty
        if not actions:
            actions.append({
                "cause": "General Database Health",
                "steps": [
                    "Review Oracle alert log for recent errors",
                    "Check listener status: lsnrctl status",
                    "Monitor tablespace usage",
                    "Verify database status: SELECT STATUS FROM v$instance"
                ],
                "urgency": "MEDIUM"
            })
        
        return actions
    
    def _build_error_fallback_response(self, question, question_type, error_msg):
        """
        PRODUCTION CRITICAL: Build intelligent fallback when an error occurs.
        
        RULE: NEVER show "I apologize" or "Error processing request"
        ALWAYS provide a meaningful, helpful answer based on available data.
        
        Args:
            question: The user's question
            question_type: FACTUAL, ANALYTICAL, or ACTION
            error_msg: The error message (for logging only)
            
        Returns:
            Dict with fallback response
        """
        alerts = GLOBAL_DATA.get("alerts", [])
        session = SessionStore.get_context_summary()
        
        # Determine what the user was asking about
        q_lower = question.lower()
        
        # =====================================================
        # FACTUAL QUESTION FALLBACK
        # =====================================================
        if question_type == "FACTUAL":
            # Count questions
            if any(w in q_lower for w in ["how many", "count", "total"]):
                if any(w in q_lower for w in ["database", "db"]):
                    unique_dbs = set()
                    for a in alerts:
                        if a and a.get("target"):
                            from data_engine.target_normalizer import TargetNormalizer
                            db = TargetNormalizer.normalize(a.get("target"))
                            if db:
                                unique_dbs.add(db)
                    return {
                        "answer": "{} databases are monitored in OEM.".format(len(unique_dbs)),
                        "status": "success",
                        "confidence": 0.8,
                        "actions": [],
                        "question_type": "FACTUAL"
                    }
                elif any(w in q_lower for w in ["alert"]):
                    return {
                        "answer": "{:,} alerts in the system.".format(len(alerts)),
                        "status": "success",
                        "confidence": 0.8,
                        "actions": [],
                        "question_type": "FACTUAL"
                    }
            
            # Hour/time questions
            if any(w in q_lower for w in ["hour", "peak", "when"]):
                # Try to compute peak hour from alerts
                from collections import Counter
                import re
                hour_counts = Counter()
                for a in alerts:
                    ts = a.get("time") or a.get("collection_timestamp") or ""
                    if ts and isinstance(ts, str):
                        match = re.search(r'(\d{1,2}):\d{2}', ts)
                        if match:
                            hour_counts[int(match.group(1))] += 1
                
                if hour_counts:
                    peak = max(hour_counts.keys(), key=lambda h: hour_counts[h])
                    return {
                        "answer": "Peak hour is {}:00 with {:,} alerts.".format(peak, hour_counts[peak]),
                        "status": "success",
                        "confidence": 0.7,
                        "actions": [],
                        "question_type": "FACTUAL"
                    }
            
            # Which/status questions
            if any(w in q_lower for w in ["which", "status", "critical"]):
                if session.get("highest_risk_database"):
                    return {
                        "answer": "{} is the highest risk database.".format(session["highest_risk_database"]),
                        "status": "success",
                        "confidence": 0.7,
                        "actions": [],
                        "question_type": "FACTUAL"
                    }
        
        # =====================================================
        # ANALYTICAL QUESTION FALLBACK
        # =====================================================
        elif question_type == "ANALYTICAL":
            # Why questions - use session root cause
            if "why" in q_lower or "reason" in q_lower or "cause" in q_lower:
                locked_rc = SessionStore.get_locked_root_cause()
                if locked_rc:
                    return {
                        "answer": "Based on earlier analysis, the primary root cause is **{}**.\n\nThis was identified from alert patterns showing repeated occurrences.".format(locked_rc),
                        "status": "success",
                        "confidence": 0.6,
                        "root_cause": locked_rc,
                        "actions": [],
                        "question_type": "ANALYTICAL"
                    }
                elif session.get("dominant_ora_codes"):
                    top_ora = session["dominant_ora_codes"][0]
                    return {
                        "answer": "The dominant error pattern is **{}**, which suggests Oracle operational issues that require investigation.\n\nReview the alert log for detailed context.".format(top_ora),
                        "status": "success",
                        "confidence": 0.5,
                        "root_cause": top_ora,
                        "actions": [],
                        "question_type": "ANALYTICAL"
                    }
        
        # =====================================================
        # ACTION QUESTION FALLBACK
        # =====================================================
        elif question_type == "ACTION":
            actions = self._get_fallback_actions()
            return {
                "answer": "**Recommended Actions:**\n\n1. Review Oracle alert log for recent errors\n2. Check listener status: `lsnrctl status`\n3. Monitor tablespace usage\n4. Verify database status: `SELECT STATUS FROM v$instance`",
                "status": "success",
                "confidence": 0.5,
                "actions": actions,
                "question_type": "ACTION"
            }
        
        # =====================================================
        # ULTIMATE FALLBACK (never apologize)
        # =====================================================
        # CRITICAL FIX: If there's active context, use it to provide
        # a scoped response instead of generic global summary
        context = SessionStore.get_conversation_context()
        if context.get("has_context"):
            topic = context.get("topic", "alerts")
            scope_label = self._get_scope_label(topic, context.get("alert_type"))
            return {
                "answer": "I'm not sure what you'd like to know about {0}.\n\nTry:\n- \"show me 20\" (to see top alerts)\n- \"for [database name]\" (to filter by database)\n- \"only critical\" (to filter by severity)".format(scope_label),
                "status": "success",
                "confidence": 0.4,
                "actions": [],
                "question_type": "FACT"
            }
        
        # No context - provide general system status
        return {
            "answer": "The OEM system is monitoring {:,} alerts across {} databases.\n\nTo get specific information, try:\n- \"How many databases are monitored?\"\n- \"Which database has the most alerts?\"\n- \"What is the peak alert hour?\"".format(
                len(alerts),
                len(set(a.get("target", "") for a in alerts if a))
            ),
            "status": "success",
            "confidence": 0.4,
            "actions": [],
            "question_type": "FACTUAL"
        }
    
    def get_session_summary(self):
        """Get current session summary for API response."""
        return SessionStore.get_context_summary()


# Global instance
INTELLIGENCE_SERVICE = IntelligenceService()
