from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
import re

from data_engine.global_cache import GLOBAL_DATA, SYSTEM_READY
from data_engine.target_normalizer import TargetNormalizer
from incident_engine.correlation_engine import CorrelationEngine
from incident_engine.recommendation_engine import RecommendationEngine
from nlp_engine.nlp_reasoner import NLPReasoner
from services.intelligence_service import INTELLIGENCE_SERVICE
from services.session_store import SessionStore

# PHASE-12.1: Import scope reset
try:
    from reasoning.phase12_guardrails import Phase12Guardrails
    PHASE12_AVAILABLE = True
except ImportError:
    PHASE12_AVAILABLE = False

# NEW: Import NLP Orchestrator for v2 API
try:
    from services.nlp_orchestrator import get_orchestrator, process_query
    NLP_ORCHESTRATOR_AVAILABLE = True
except ImportError:
    NLP_ORCHESTRATOR_AVAILABLE = False
    print("[WARNING] NLP Orchestrator not available, v2 API will be disabled")

# PRODUCTION INTELLIGENCE IMPORT
try:
    from incident_engine.production_intelligence_engine import (
        PRODUCTION_INTELLIGENCE,
        ORACodeMappingEngine,
        DownVsCriticalEngine,
        SessionMemoryEngine
    )
    PRODUCTION_ENGINE_AVAILABLE = True
except ImportError:
    PRODUCTION_ENGINE_AVAILABLE = False

chat_router = APIRouter(tags=["Chatbot"])


# =====================================================
# Request schema
# =====================================================
class ChatRequest(BaseModel):
    message: str = ""
    session_id: str = ""  # Client-provided session ID for conversation tracking
    new_conversation: bool = False  # Reset session for new UI conversations


# =====================================================
# Lazy-loaded components
# =====================================================
_reasoner = None
_recommendation_engine = None
_last_target = None


def get_reasoner() -> NLPReasoner:
    """
    Get or create the NLP reasoner instance.
    CRITICAL: Uses the new reasoning pipeline.
    """
    global _reasoner
    if _reasoner is None:
        _reasoner = NLPReasoner()
    return _reasoner


def get_recommendation_engine() -> RecommendationEngine:
    global _recommendation_engine
    if _recommendation_engine is None:
        _recommendation_engine = RecommendationEngine()
    return _recommendation_engine


# =====================================================
# AUTH GUARD
# =====================================================
def require_login(request):
    if not request.cookies.get("logged_in"):
        raise HTTPException(status_code=401, detail="Unauthorized")


# =====================================================
# TARGET NORMALIZATION (CRITICAL FIX)
# =====================================================
def normalize_target(target):
    # Use centralized TargetNormalizer
    return TargetNormalizer.normalize(target)


# =====================================================
# TARGET EXTRACTION
# =====================================================
def extract_target_from_question(question):
    alerts = GLOBAL_DATA.get("alerts", [])
    if not alerts:
        return None

    known_targets = set()
    for a in alerts:
        if not a:
            continue
        t = normalize_target(a.get("target"))
        if t:
            known_targets.add(t)

    tokens = re.findall(r"[A-Za-z0-9_.-]{3,}", question.upper())
    for t in tokens:
        if t in known_targets:
            return t

    return None


# =====================================================
# VALIDATION STATUS
# =====================================================
def validation_status(target) -> str:
    if not target:
        return "No database specified."

    validations = GLOBAL_DATA.get("validated_alerts", [])
    related = []

    for v in validations:
        if not v:
            continue
        vt = normalize_target(v.get("target"))
        if vt == target:
            related.append(v)

    if not related:
        return "No metric validation data available."

    unsupported = [v for v in related if not v.get("metric_supported")]
    if unsupported:
        return "{0} alerts were NOT supported by metrics, indicating possible application or configuration issues.".format(
            len(unsupported)
        )

    return "All recent alerts are supported by abnormal metrics."


# =====================================================
# RISK TREND STATUS
# =====================================================
def trend_status(target) -> str:
    if not target:
        return "No database specified."

    for t in GLOBAL_DATA.get("risk_trends", []):
        if not t:
            continue
        tt = normalize_target(t.get("target"))
        if tt == target:
            return "Risk trend is {0} (score: {1}). Reason: {2}.".format(
                t.get("trend", "UNKNOWN"),
                t.get("risk_score", 0),
                t.get("reason", "No reason available")
            )

    return "No risk trend data available."


# =====================================================
# OUTAGE PROBABILITY
# =====================================================
def outage_probability_status(target) -> str:
    if not target:
        return "No database specified."

    alerts = GLOBAL_DATA.get("alerts", [])
    metrics = GLOBAL_DATA.get("metrics", [])
    incidents = GLOBAL_DATA.get("incidents", [])

    if not incidents:
        return "No incident data available for outage prediction."

    try:
        engine: CorrelationEngine[list, list] = CorrelationEngine(alerts, metrics, incidents)
        result = engine.outage_probability(target, incidents)

        if not result:
            return "Unable to calculate outage probability."

        summary = "Outage probability: {0}% ({1})".format(
            result.get("probability", 0),
            result.get("risk_level", "UNKNOWN")
        )

        reasons = result.get("reasons", [])
        if reasons:
            summary += ". Key factors: " + ", ".join(reasons[:3])

        return summary
    except Exception:
        return "Unable to predict outage probability at this time."


# =====================================================
# RECOMMENDED FIX
# =====================================================
def recommended_fix_status(target) -> str:
    if not target:
        return "No database specified."

    incidents = []
    for i in GLOBAL_DATA.get("incidents", []):
        if not i:
            continue
        it = normalize_target(i.get("target"))
        if it == target:
            incidents.append(i)

    if not incidents:
        return "No incident data available for recommendations."

    issue_counts = {}
    for inc in incidents:
        issue = inc.get("issue_type", "OTHER")
        issue_counts[issue] = issue_counts.get(issue, 0) + 1

    most_common_issue = max(issue_counts, key=issue_counts.get)

    try:
        rec = get_recommendation_engine().recommend_fix(most_common_issue)
        if not rec:
            return "No recommendation available."

        return "For {0} issues: {1}. Confidence: {2}% ({3}).".format(
            most_common_issue,
            rec.get("recommended_action", "Unknown"),
            rec.get("confidence", 0),
            rec.get("evidence", "No evidence")
        )
    except Exception:
        return "Unable to generate recommendation at this time."


# =====================================================
# CHAT ENDPOINT (PRODUCTION WIRING - CHECK SYSTEM READY)
# =====================================================
@chat_router.post("/")
async def chat(request: Request, payload: ChatRequest) :
    """Main chat endpoint with verbose debug logging."""
    # VERBOSE DEBUG - trace every incoming request
    print("\n" + "="*60)
    print("[CHAT API] INCOMING REQUEST")
    print("[CHAT API] message:", repr(payload.message))
    print("[CHAT API] session_id:", payload.session_id)
    print("[CHAT API] new_conversation:", payload.new_conversation)
    print("="*60 + "\n")
    
    """
    ENHANCED: Now uses IntelligenceService for:
    - Root cause inference with confidence (NEVER Unknown)
    - Actions that are ALWAYS present (NEVER empty)
    - Session memory across requests (locked values)
    - DOWN vs CRITICAL proper separation
    - Enhanced response structure with session context
    
    PRODUCTION RULES:
    - Root cause NEVER "Unknown" if evidence exists
    - Actions NEVER empty (FOR ACTION INTENTS ONLY)
    - Session context reused: "Based on earlier analysis..."
    - DOWN = stopped/terminated; CRITICAL = running but unstable
    
    DASHBOARD FIX:
    - new_conversation=True resets session memory
    - Prevents root cause leakage between conversations
    - Each new UI chat starts fresh
    - session_id from payload is used to isolate sessions
    
    Response structure (backwards compatible):
    {
        "question": str,
        "answer": str,
        
        # NEW FIELDS (additive - won't break frontend)
        "target": str or None,
        "confidence": float,
        "confidence_label": str,  # HIGH/MEDIUM/LOW
        "actions": list,          # Only for ACTION intents
        "root_cause": str or None,
        "session_context": dict   # Memory summary
    }
    """
    global _last_target
    require_login(request)

    question = payload.message.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Message is required")

    # =====================================================
    # SESSION ID MANAGEMENT (v3.0 - DASHBOARD FIX)
    # =====================================================
    # Use session_id from payload to isolate conversations
    session_id = payload.session_id
    if session_id:
        SessionStore.set_session_id(session_id)
        print("[DEBUG] Using session_id:", session_id)
    
    # =====================================================
    # CRITICAL FIX: ALWAYS reset formatter context per question
    # This prevents root cause/action leakage BETWEEN questions
    # (not just between conversations)
    # =====================================================
    # Formatter context is reset in IntelligenceService.analyze()
    
    # =====================================================
    # DASHBOARD FIX: Reset session for new conversations
    # This prevents root cause/action leakage between chats
    # =====================================================
    # PHASE-12.1 FIX: Don't reset if question is clearly a follow-up
    # This protects against frontend bugs/caching issues
    q_lower = question.lower()
    is_followup_question = any(p in q_lower for p in [
        "this db", "this database", "is it fine", "is this fine",
        "critical count", "warning count", "status?", "root cause?",
        "same one", "same database", "these alerts", "those alerts",
        "explain this", "explain it", "tell me more", "more details",
        "what about", "how about", "and what", "why is that",
        "is this normal", "should i", "what happens if", "what evidence"
    ])
    
    if payload.new_conversation and not is_followup_question:
        print("[DEBUG] new_conversation=True, resetting session for:", session_id)
        # If we have a session_id, reset that specific session
        if session_id:
            SessionStore.reset_session(session_id)
        else:
            SessionStore.reset()
        _last_target = None
        if PRODUCTION_ENGINE_AVAILABLE:
            SessionMemoryEngine.reset()
        # PHASE-12.1: Reset scope on new conversation
        # NOTE: Don't reset scope here - let Phase12Guardrails handle it
        # The scope will be set based on the question in analyze()
        # if PHASE12_AVAILABLE:
        #     Phase12Guardrails.reset_scope()
            print("[DEBUG] Phase12 scope reset")
    elif payload.new_conversation and is_followup_question:
        print("[DEBUG] new_conversation=True BUT question is follow-up, preserving session:", session_id)
        # Don't reset - this is a follow-up question
    else:
        # CRITICAL DEBUG: Log context state for follow-up
        context = SessionStore.get_conversation_context()
        print("[DEBUG] new_conversation=False, session_id:", session_id)
        print("[DEBUG] Context state - topic:", context.get("topic"), "last_target:", context.get("last_target"), "severity:", context.get("severity"), "has_context:", context.get("has_context"))

    # Check if system is initialized
    if not SYSTEM_READY.get("ready", False):
        return {
            "question": question,
            "answer": "System is currently initializing. Please wait a moment while we load the OEM data..."
        }

    # =====================================================
    # SINGLE SOURCE OF TRUTH: IntelligenceService ONLY
    # =====================================================
    # CRITICAL: Do NOT add any extra processing after this call.
    # The answer from INTELLIGENCE_SERVICE is the FINAL answer.
    # No trend appending, no extra detection, no reformatting.
    # Dashboard must behave EXACTLY like terminal tests.
    # =====================================================
    result = INTELLIGENCE_SERVICE.analyze(question)
    
    # Extract the answer - this is the ONLY response
    answer = result.get("answer", "Unable to process question.")
    
    # Get question type for strict field filtering
    question_type = result.get("question_type", "FACT")
    
    # STRICT RULES:
    # - FACT/STATUS: answer only, no root_cause, no actions
    # - ANALYSIS: answer + root_cause, no actions  
    # - ACTION: answer + root_cause + actions
    include_actions = question_type == "ACTION"
    include_root_cause = question_type in ["ANALYSIS", "ACTION", "PREDICTION"]

    # Build response - PURE passthrough from IntelligenceService
    response = {
        "question": question,
        "answer": answer,
        "target": result.get("target"),
        "confidence": result.get("confidence", 0.5),
        "confidence_label": result.get("confidence_label", "MEDIUM"),
        "actions": result.get("actions", []) if include_actions else [],
        "root_cause": result.get("root_cause") if include_root_cause else None,
        "session_context": result.get("session_context", {}),
        "question_type": question_type
    }
    
    return response


# =====================================================
# SESSION RESET (DASHBOARD FIX)
# =====================================================
@chat_router.post("/reset")
async def reset_session(request: Request):
    """
    Reset session memory for new conversation.
    
    DASHBOARD FIX: Call this endpoint when user starts a new chat
    to prevent root cause, actions, and locked values from
    bleeding into unrelated conversations.
    """
    global _last_target
    require_login(request)
    
    SessionStore.reset()
    _last_target = None
    
    if PRODUCTION_ENGINE_AVAILABLE:
        SessionMemoryEngine.reset()
    
    return {
        "status": "success",
        "message": "Session memory cleared"
    }


# =====================================================
# DEBUG ENDPOINT (NO AUTH - FOR TESTING)
# =====================================================
@chat_router.get("/debug/context")
async def debug_context(session_id: str = None):
    """Debug endpoint to check session context (no auth required)."""
    # If session_id provided, switch to that session first
    if session_id:
        SessionStore.set_session_id(session_id)
    
    context = SessionStore.get_conversation_context()
    
    # Also show all sessions in storage
    from services.session_store import _SESSION_STORAGE, _ACTIVE_SESSION_ID
    
    return {
        "status": "ok",
        "active_session_id": _ACTIVE_SESSION_ID,
        "requested_session_id": session_id,
        "all_session_ids": list(_SESSION_STORAGE.keys()),
        "context": context,
        "has_context": context.get("has_context", False),
        "topic": context.get("topic"),
        "last_target": context.get("last_target"),
        "severity": context.get("severity")
    }


# =====================================================
# WARMUP
# =====================================================
@chat_router.post("/warmup")
async def warmup(request: Request) :
    require_login(request)
    try:
        get_reasoner().answer("system status", return_target=False)
    except Exception:
        pass
    return {"status": "chatbot ready"}


# =====================================================
# SESSION STATE (NEW - EXPOSES MEMORY)
# =====================================================
@chat_router.get("/session")
async def get_session(request: Request):
    """
    Get current session state.
    
    Returns the accumulated knowledge from prior questions:
    - Highest risk database (LOCKED once identified)
    - Dominant ORA codes
    - Peak alert hour (LOCKED once computed)
    - Last root cause (LOCKED for session consistency)
    - Analysis history
    - Unstable systems (PRODUCTION ENHANCEMENT)
    - DOWN events (PRODUCTION ENHANCEMENT)
    - CRITICAL but running databases
    
    PRODUCTION RULE: Locked values remain consistent across session.
    """
    require_login(request)
    
    state = SessionStore.get_state()
    
    return {
        "status": "success",
        "session": state,
        "context_phrase": SessionStore.get_context_phrase(),
        "summary": SessionStore.get_context_summary(),
        "unstable_systems": SessionStore.get_unstable_systems(),
        "down_events": SessionStore.get_recent_down_events(),
        "critical_but_running": SessionStore.get_critical_but_running(),
        # PRODUCTION: Expose locked values
        "locked_values": {
            "root_cause": state.get("locked_root_cause"),
            "highest_risk_db": state.get("locked_highest_risk_db"),
            "peak_hour": state.get("locked_peak_hour"),
            "root_cause_by_db": state.get("locked_root_cause_db", {})
        }
    }


# =====================================================
# STATS (ENHANCED - INCLUDES SESSION)
# =====================================================
@chat_router.get("/stats")
async def get_stats(request: Request):
    """
    Get learning statistics and session analytics.
    """
    require_login(request)
    
    try:
        rec_engine = get_recommendation_engine()
        learning_stats = rec_engine.get_learning_stats()
    except Exception:
        learning_stats = {}
    
    session_summary = SessionStore.get_context_summary()
    
    return {
        "learning_statistics": learning_stats,
        "session_summary": session_summary,
        "questions_analyzed": session_summary.get("questions_analyzed", 0),
        "highest_risk_database": session_summary.get("highest_risk_database"),
        "dominant_ora_codes": session_summary.get("dominant_ora_codes", []),
        "unstable_systems": SessionStore.get_unstable_systems()
    }


# =====================================================
# FEEDBACK
# =====================================================
class FeedbackRequest(BaseModel):
    issue_type: str = ""
    action_taken: str = ""
    outcome: str = ""


@chat_router.post("/feedback")
async def track_feedback(request: Request, payload: FeedbackRequest):
    require_login(request)

    if not payload.issue_type:
        raise HTTPException(status_code=400, detail="issue_type is required")

    try:
        rec_engine: RecommendationEngine = get_recommendation_engine()
        rec_engine.track_outcome(payload.issue_type, payload.action_taken, payload.outcome)
        updated = rec_engine.recommend_fix(payload.issue_type) or {}

        return {
            "status": "Learning tracked successfully",
            "issue_type": payload.issue_type,
            "updated_recommendation": updated.get("recommended_action", ""),
            "new_confidence": updated.get("confidence", 0)
        }
    except Exception:
        return {"status": "Error tracking feedback"}


# =====================================================
# V2 API: NEW NLP ORCHESTRATOR (SMART INTELLIGENT ASSISTANT)
# =====================================================
@chat_router.post("/v2")
async def chat_v2(request: Request, payload: ChatRequest):
    """
    NEW V2 Chat API using the unified NLP Orchestrator.
    
    This endpoint provides:
    - Smart intent classification with confidence scores
    - Entity extraction (database, severity, limit, time, etc.)
    - Conversation context management (remembers previous questions)
    - Query planning and execution at data level
    - Natural language response generation
    
    Flow:
    User Query → Intent → Entity → Context → Plan → Execute → Response
    
    Response structure:
    {
        "question": str,
        "answer": str,
        "intent": str,
        "confidence": float,
        "question_type": str,  # FACT, ANALYSIS, ACTION
        "entities": dict,      # Extracted entities
        "result_count": int,   # Number of matching records
        "suggestions": list    # Follow-up suggestions
    }
    """
    require_login(request)
    
    if not NLP_ORCHESTRATOR_AVAILABLE:
        raise HTTPException(
            status_code=503, 
            detail="NLP Orchestrator not available. Please check server logs."
        )
    
    question = payload.message.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Message is required")
    
    # Use session_id from payload or generate default
    session_id = payload.session_id or 'default'
    
    # Handle new conversation - clear session context
    if payload.new_conversation:
        orchestrator = get_orchestrator()
        orchestrator.clear_session(session_id)
    
    # Process query through NLP orchestrator
    result = process_query(question, session_id)
    
    # Build response (compatible with frontend expectations)
    return {
        "question": question,
        "answer": result.get("answer", "Unable to process question."),
        "intent": result.get("intent", "UNKNOWN"),
        "confidence": result.get("confidence", 0.0),
        "confidence_label": _confidence_to_label(result.get("confidence", 0.0)),
        "question_type": result.get("question_type", "FACT"),
        "entities": result.get("entities", {}),
        "result_count": result.get("result_count", 0),
        "suggestions": result.get("suggestions", []),
        "target": result.get("entities", {}).get("databases", [None])[0] if result.get("entities", {}).get("databases") else None,
        "actions": [],  # V2 focuses on data queries, not actions
        "root_cause": None,  # V2 focuses on data queries
        "session_context": {}
    }


def _confidence_to_label(confidence: float) -> str:
    """Convert confidence score to label"""
    if confidence >= 0.8:
        return "HIGH"
    elif confidence >= 0.5:
        return "MEDIUM"
    else:
        return "LOW"


@chat_router.get("/v2/context")
async def get_v2_context(request: Request, session_id: str = "default"):
    """
    Get current NLP conversation context for debugging.
    Shows extracted entities, last intent, and merged context.
    """
    require_login(request)
    
    if not NLP_ORCHESTRATOR_AVAILABLE:
        raise HTTPException(status_code=503, detail="NLP Orchestrator not available")
    
    orchestrator = get_orchestrator()
    context = orchestrator.get_session_context(session_id)
    
    return {
        "status": "ok",
        "session_id": session_id,
        "context": context
    }


@chat_router.post("/v2/reset")
async def reset_v2_session(request: Request, session_id: str = "default"):
    """
    Reset V2 NLP session context.
    """
    require_login(request)
    
    if not NLP_ORCHESTRATOR_AVAILABLE:
        raise HTTPException(status_code=503, detail="NLP Orchestrator not available")
    
    orchestrator = get_orchestrator()
    orchestrator.clear_session(session_id)
    
    return {
        "status": "success",
        "message": f"Session '{session_id}' cleared"
    }

