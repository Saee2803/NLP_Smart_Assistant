"""
DBA Reasoning Modules

Provides expert-level reasoning capabilities for database operations.

==========================================================================
🔒 PHASE 7: TRUST, EXPLAINABILITY & ENTERPRISE-READINESS
==========================================================================
Enterprise-grade trust and explainability for production deployments:

1️⃣ ANSWER CONFIDENCE ENGINE - Confidence scoring for every answer
2️⃣ EVIDENCE LAYER - Evidence-backed explanations
3️⃣ DB SCOPE GUARD - Strict database scope enforcement
4️⃣ SAFE PREDICTION LANGUAGE - Safe prediction formatting
5️⃣ AUDIT & EXPLAINABILITY - Full audit trails
6️⃣ LANGUAGE GUARDRAILS - Professional tone enforcement
7️⃣ UNCERTAINTY HANDLER - Honest uncertainty handling
8️⃣ ENTERPRISE TRUST ENGINE - Master orchestrator

==========================================================================
🧠 PHASE 6: DBA INTELLIGENCE PARTNER
==========================================================================
Production-Grade DBA Intelligence Partner that thinks like a senior human DBA:

1️⃣ DBA KNOWLEDGE BASE - Curated Oracle error knowledge
2️⃣ INCIDENT MEMORY - Historical learning from past incidents  
3️⃣ CONFIDENCE ENGINE - Uncertainty scoring (HIGH/MEDIUM/LOW)
4️⃣ QUESTION UNDERSTANDING - Handle any DBA question naturally
5️⃣ HUMAN DBA STYLE - Calm, senior DBA response tone
6️⃣ KNOWLEDGE MERGER - Combine data + knowledge + history

==========================================================================
🧠 PHASE 5: PREDICTIVE INTELLIGENCE ENGINE
==========================================================================
The PredictiveIntelligenceEngine transforms the system from:
    "This is what is happening" → "This is likely to happen next"

1️⃣ TREND DETECTION - Improving/Stable/Deteriorating patterns
2️⃣ TRAJECTORY PREDICTION - Self-resolve/Persist/Escalate
3️⃣ EARLY WARNING SIGNALS - Pre-incident indicators
4️⃣ DBA BEHAVIOR LEARNING - Operational sensitivity detection
5️⃣ PROACTIVE GUIDANCE - Preventive awareness (not fixes)

==========================================================================
🧠 PHASE 4: INCIDENT INTELLIGENCE ENGINE
==========================================================================
The IncidentIntelligenceEngine behaves like a Principal DBA / Incident Commander:

1️⃣ INCIDENT CORRELATION - Group alerts into incident clusters
2️⃣ TEMPORAL INTELLIGENCE - Analyze timing patterns (transient/persistent/escalating)
3️⃣ PRIORITY SCORING - Assign P1/P2/P3 priority levels
4️⃣ NOISE VS SIGNAL - Separate real incidents from alert noise
5️⃣ EXECUTIVE SUMMARY - Readable by DBA, Manager, Incident bridge lead

🧠 DBA INTELLIGENCE FORMATTER (Legacy)
The DBAIntelligenceFormatter provides 5 layers of enterprise-grade intelligence.
"""

from .hypothesis_engine import HypothesisEngine
from .evidence_collector import EvidenceCollector
from .decision_engine import DecisionEngine
from .action_recommender import ActionRecommender
from .pattern_recognizer import PatternRecognizer
from .confidence_scorer import ConfidenceScorer
from .context_tracker import ContextTracker, CONTEXT
from .risk_predictor import RiskPredictor
from .answer_formatter import AnswerFormatter
from .orchestrator import ReasoningOrchestrator

# DBA Intelligence Formatter (Legacy)
from .dba_intelligence_formatter import (
    DBAIntelligenceFormatter,
    get_dba_formatter,
    format_dba_response
)

# Incident Intelligence Engine (Phase 4)
from .incident_intelligence_engine import (
    IncidentIntelligenceEngine,
    IncidentCluster,
    INCIDENT_INTELLIGENCE_ENGINE
)

# Predictive Intelligence Engine (Phase 5)
from .predictive_intelligence_engine import (
    PredictiveIntelligenceEngine,
    TrendDetectionEngine,
    IncidentTrajectoryPredictor,
    EarlyWarningDetector,
    DBABehaviorLearner,
    ProactiveDBAGuidance,
    PREDICTIVE_INTELLIGENCE
)

# DBA Intelligence Engine (Phase 6)
from .dba_knowledge_base import (
    DBAKnowledgeBase,
    OracleErrorKnowledge,
    DataGuardKnowledge,
    CommonRootCauses,
    DBAFirstChecks,
    DBA_KNOWLEDGE_BASE
)

from .incident_memory import (
    IncidentMemoryStore,
    IncidentMemoryEntry,
    IncidentSignature,
    IncidentOutcome,
    INCIDENT_MEMORY
)

from .confidence_engine import (
    ConfidenceEngine,
    ConfidenceScore,
    QuestionConfidenceScorer,
    AnswerConfidenceScorer,
    CONFIDENCE_ENGINE
)

from .question_understanding import (
    QuestionUnderstandingEngine,
    QuestionType,
    QuestionInterpretation,
    EntityExtractor,
    IntentClassifier,
    QUESTION_ENGINE
)

from .human_dba_style import (
    HumanDBAStyleFormatter,
    HumanPhrasing,
    ResponseTemplates,
    DBAResponseContext,
    HUMAN_STYLE
)

from .knowledge_merger import (
    KnowledgeMerger,
    MergedIntelligence,
    KNOWLEDGE_MERGER
)

from .dba_intelligence_engine import (
    DBAIntelligenceEngine,
    DBA_INTELLIGENCE
)

# Enterprise Trust Engine (Phase 7)
from .answer_confidence_engine import (
    AnswerConfidenceEngine,
    ConfidenceLevel,
    ConfidenceAssessment,
    ANSWER_CONFIDENCE
)

from .evidence_layer import (
    EvidenceLayer,
    EvidenceItem,
    EvidencePackage,
    EVIDENCE_LAYER
)

from .db_scope_guard import (
    DBScopeGuard,
    ScopeValidation,
    DB_SCOPE_GUARD
)

from .safe_prediction_language import (
    SafePredictionLanguage,
    SafePrediction,
    SAFE_PREDICTION
)

from .audit_explainability import (
    AuditExplainabilityEngine,
    AuditRecord,
    AuditStep,
    AUDIT_ENGINE
)

from .language_guardrails import (
    LanguageGuardrails,
    QualityCheck,
    LANGUAGE_GUARDRAILS
)

from .uncertainty_handler import (
    UncertaintyHandler,
    UncertaintyResponse,
    UncertaintyType,
    UNCERTAINTY_HANDLER
)

from .enterprise_trust_engine import (
    EnterpriseTrustEngine,
    TrustedAnswer,
    ENTERPRISE_TRUST,
    process_answer,
    quick_validate
)

# Self-Audit Engine (Phase 11)
from .self_audit_engine import (
    SelfAuditEngine,
    TrustMode,
    ConfidenceLevel as AuditConfidenceLevel,
    ConversationFactRegister,
    TrustModeDetector,
    ScopeValidator,
    AuditResult,
    SELF_AUDIT,
    audit_before_respond,
    apply_full_guardrails
)

# DBA Guardrails (8 RULES - Oracle OEM Assistant)
from .dba_guardrails import (
    # Core Classes
    DBAGuardrailEnforcer,
    AnswerMode,
    AnswerModeDetector,
    ScopeConstraint,
    ScopeLevel,
    ConfidenceLevel,
    ScopeControlGuard,
    PredictiveReasoningSafety,
    NoDataHandler,
    AntiOverexplanation,
    ConsistencyChecker,
    ProductionSafeResponse,
    GuardrailResult,
    # Enterprise-Grade Classes
    ProductionSafetyRules,
    DataAuthorityRule,
    IncidentIntelligenceLogic,
    IncidentAlertIntelligence,
    RootCauseHandler,
    ConfidenceFormatter,
    SelfValidation,
    LIMITED_DATA_RESPONSE,
    # 8 RULES Classes
    DBAToneEnforcer,            # RULE 8: Shared Context Tone
    IncidentCountGuardrail,     # RULE 4: Unique Incident Count
    SafeActionBoundaries,       # RULE 6: Execution & Action Safety
    RiskEscalationLanguage,     # RULE 5: Risk & Escalation Language
    ConfidenceLabelingStandard, # RULE 7: Confidence Labeling Standard
    # Singleton and Functions
    DBA_GUARDRAILS,
    apply_guardrails,
    get_answer_mode,
    is_strict_value_question,
    extract_scope,
    cannot_determine,
    format_safe_prediction
)

# Phase-12.1: Production-Grade DBA Intelligence Guardrails
from .phase12_guardrails import (
    Phase12Guardrails,
    ActiveScope,
    ScopeType,
    enforce_phase12,
    get_active_db_scope,
    reset_db_scope,
    self_check_answer,
    PHASE12_AVAILABLE
)

__all__ = [
    'HypothesisEngine',
    'EvidenceCollector', 
    'DecisionEngine',
    'ActionRecommender',
    'PatternRecognizer',
    'ConfidenceScorer',
    'ContextTracker',
    'CONTEXT',
    'RiskPredictor',
    'AnswerFormatter',
    'ReasoningOrchestrator',
    # DBA Intelligence (Legacy)
    'DBAIntelligenceFormatter',
    'get_dba_formatter',
    'format_dba_response',
    # Incident Intelligence Engine (Phase 4)
    'IncidentIntelligenceEngine',
    'IncidentCluster',
    'INCIDENT_INTELLIGENCE_ENGINE',
    # Predictive Intelligence Engine (Phase 5)
    'PredictiveIntelligenceEngine',
    'TrendDetectionEngine',
    'IncidentTrajectoryPredictor',
    'EarlyWarningDetector',
    'DBABehaviorLearner',
    'ProactiveDBAGuidance',
    'PREDICTIVE_INTELLIGENCE',
    # DBA Intelligence Engine (Phase 6)
    'DBAKnowledgeBase',
    'OracleErrorKnowledge',
    'DataGuardKnowledge',
    'CommonRootCauses',
    'DBAFirstChecks',
    'DBA_KNOWLEDGE_BASE',
    'IncidentMemoryStore',
    'IncidentMemoryEntry',
    'IncidentSignature',
    'IncidentOutcome',
    'INCIDENT_MEMORY',
    'ConfidenceEngine',
    'ConfidenceScore',
    'QuestionConfidenceScorer',
    'AnswerConfidenceScorer',
    'CONFIDENCE_ENGINE',
    'QuestionUnderstandingEngine',
    'QuestionType',
    'QuestionInterpretation',
    'EntityExtractor',
    'IntentClassifier',
    'QUESTION_ENGINE',
    'HumanDBAStyleFormatter',
    'HumanPhrasing',
    'ResponseTemplates',
    'DBAResponseContext',
    'HUMAN_STYLE',
    'KnowledgeMerger',
    'MergedIntelligence',
    'KNOWLEDGE_MERGER',
    'DBAIntelligenceEngine',
    'DBA_INTELLIGENCE',
    # Enterprise Trust Engine (Phase 7)
    'AnswerConfidenceEngine',
    'ConfidenceLevel',
    'ConfidenceAssessment',
    'ANSWER_CONFIDENCE',
    'EvidenceLayer',
    'EvidenceItem',
    'EvidencePackage',
    'EVIDENCE_LAYER',
    'DBScopeGuard',
    'ScopeValidation',
    'DB_SCOPE_GUARD',
    'SafePredictionLanguage',
    'SafePrediction',
    'SAFE_PREDICTION',
    'AuditExplainabilityEngine',
    'AuditRecord',
    'AuditStep',
    'AUDIT_ENGINE',
    'LanguageGuardrails',
    'QualityCheck',
    'LANGUAGE_GUARDRAILS',
    'UncertaintyHandler',
    'UncertaintyResponse',
    'UncertaintyType',
    'UNCERTAINTY_HANDLER',
    'EnterpriseTrustEngine',
    'TrustedAnswer',
    'ENTERPRISE_TRUST',
    'process_answer',
    'quick_validate',
    # Self-Audit Engine (Phase 11)
    'SelfAuditEngine',
    'TrustMode',
    'AuditConfidenceLevel',
    'ConversationFactRegister',
    'TrustModeDetector',
    'ScopeValidator',
    'AuditResult',
    'SELF_AUDIT',
    'audit_before_respond',
    'apply_full_guardrails',
    # DBA Guardrails (10 Production-Grade Guardrails)
    'DBAGuardrailEnforcer',
    'AnswerMode',
    'AnswerModeDetector',
    'ScopeConstraint',
    'ScopeLevel',
    'ConfidenceLevel',
    'ScopeControlGuard',
    'PredictiveReasoningSafety',
    'NoDataHandler',
    'AntiOverexplanation',
    'ConsistencyChecker',
    'ProductionSafeResponse',
    'GuardrailResult',
    # New Production-Grade Classes
    'ProductionSafetyRules',
    'DataAuthorityRule',
    'IncidentIntelligenceLogic',
    'RootCauseHandler',
    'ConfidenceFormatter',
    'SelfValidation',
    # Singleton and Functions
    'DBA_GUARDRAILS',
    'apply_guardrails',
    'get_answer_mode',
    'is_strict_value_question',
    'extract_scope',
    'cannot_determine',
    'format_safe_prediction',
    # Phase-12.1: Production-Grade DBA Intelligence Guardrails
    'Phase12Guardrails',
    'ActiveScope',
    'ScopeType',
    'enforce_phase12',
    'get_active_db_scope',
    'reset_db_scope',
    'self_check_answer',
    'PHASE12_AVAILABLE'
]

