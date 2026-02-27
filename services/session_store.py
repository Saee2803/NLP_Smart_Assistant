# services/session_store.py
"""
==============================================================
GLOBAL SESSION STORE (BACKEND MEMORY)
==============================================================

This module provides a persistent session store that:
1. Remembers analysis context across API requests
2. Tracks highest risk database, dominant ORA codes, etc.
3. Enables follow-up questions to reuse prior findings

PRODUCTION ENHANCEMENT (v2.0):
- Integrated with SessionMemoryEngine for enhanced tracking
- Tracks unstable systems across sessions
- Maintains analysis history for context
- Enables "Based on earlier analysis..." responses

PRODUCTION FIX (v3.0):
- Added per-session_id storage to prevent cross-session contamination
- Dashboard can now properly isolate conversations

Python 3.6.8 compatible.
"""

from datetime import datetime


# =====================================================
# PER-SESSION STORAGE (v3.0 - DASHBOARD FIX)
# =====================================================
# Stores per session_id state to prevent cross-session contamination
_SESSION_STORAGE = {}  # session_id -> state dict
_ACTIVE_SESSION_ID = None  # Currently active session_id


class SessionStore:
    """
    Global session store for backend intelligence memory.
    
    Singleton pattern - state persists across all API requests.
    
    PRODUCTION ENHANCEMENT:
    - Syncs with SessionMemoryEngine when available
    - Tracks unstable systems and risk patterns
    - Maintains analysis history for contextual responses
    
    CRITICAL RULES (ENFORCED):
    - Once a root cause is identified, it is LOCKED for the session
    - Highest risk database is LOCKED once computed
    - Peak alert hour is LOCKED once computed
    - Session context MUST be reused in future answers
    
    PRODUCTION FIX (v2.2):
    - Formatter context is ISOLATED per question type
    - Historical facts can be stored but NOT forced into response structure
    - Each question starts with a clean formatter context
    
    CONVERSATIONAL INTELLIGENCE (v2.3):
    - Tracks topic, alert_type, databases for follow-up queries
    - Enables "show me 20", "only critical", "this database"
    
    DASHBOARD FIX (v3.0):
    - Per-session_id storage to prevent cross-session contamination
    - Use set_session_id() to activate a specific session
    """
    
    # Class-level singleton state
    _instance = None
    _state = {
        # Core analysis memory
        "highest_risk_database": None,
        "highest_risk_score": 0,  # ADDED: Track score for comparison
        "dominant_ora_codes": [],
        "peak_alert_hour": None,
        "last_root_cause": None,
        "last_abstract_cause": None,
        "overall_risk_posture": None,
        
        # PRODUCTION: Locked values (once set, don't change in session)
        "locked_root_cause": None,
        "locked_root_cause_db": {},  # db -> locked root cause mapping
        "locked_highest_risk_db": None,
        "locked_peak_hour": None,
        
        # ADDED: Unstable systems tracking
        "unstable_systems": [],
        "down_events": [],
        "critical_but_running": [],  # DBs that are running but unstable
        
        # Session tracking
        "question_count": 0,
        "last_question": None,
        "last_answer": None,          # Store last answer for "explain this" follow-ups
        "last_target": None,
        "last_intent": None,
        "last_confidence": None,
        
        # Analysis history (circular buffer - last 20)
        "analysis_history": [],
        
        # Timestamps
        "session_start": None,
        "last_activity": None,
        
        # CONVERSATIONAL CONTEXT (NEW)
        "last_topic": None,           # e.g., "STANDBY_ALERTS", "CRITICAL_ALERTS"
        "last_alert_type": None,      # e.g., "dataguard", "tablespace"
        "last_severity_filter": None, # e.g., "CRITICAL"
        "last_result_count": 0,       # Count from last query (total matching alerts)
        "last_displayed_count": 0,    # CRITICAL FIX: Actual alerts SHOWN to user (for pagination)
        "last_databases": [],         # Databases mentioned in last result
        "conversation_context": {}    # Rich context for follow-ups
    }
    
    # CRITICAL FIX: Per-question formatter context (NOT persisted)
    # This is reset at the START of each new question
    _current_question_context = {
        "formatter_root_cause": None,
        "formatter_actions": [],
        "formatter_evidence": [],
        "question_type": None
    }
    
    # =====================================================
    # SESSION ID MANAGEMENT (v3.0 - DASHBOARD FIX)
    # =====================================================
    @classmethod
    def set_session_id(cls, session_id):
        """
        Set the active session ID.
        
        DASHBOARD FIX: This enables per-session storage.
        All subsequent get/set operations will use this session's state.
        
        Args:
            session_id: Client-provided session ID
        """
        global _ACTIVE_SESSION_ID, _SESSION_STORAGE
        
        if not session_id:
            return
        
        _ACTIVE_SESSION_ID = session_id
        
        # Initialize session storage if not exists
        if session_id not in _SESSION_STORAGE:
            _SESSION_STORAGE[session_id] = cls._create_empty_state()
            print("[SESSION] Created new session:", session_id)
        else:
            print("[SESSION] Resumed session:", session_id)
        
        # Sync class-level state to this session
        cls._state = _SESSION_STORAGE[session_id]
    
    @classmethod
    def _create_empty_state(cls):
        """Create an empty session state."""
        return {
            "highest_risk_database": None,
            "highest_risk_score": 0,
            "dominant_ora_codes": [],
            "peak_alert_hour": None,
            "last_root_cause": None,
            "last_abstract_cause": None,
            "overall_risk_posture": None,
            "locked_root_cause": None,
            "locked_root_cause_db": {},
            "locked_highest_risk_db": None,
            "locked_peak_hour": None,
            "unstable_systems": [],
            "down_events": [],
            "critical_but_running": [],
            "question_count": 0,
            "last_question": None,
            "last_target": None,
            "last_intent": None,
            "last_confidence": None,
            "analysis_history": [],
            "session_start": datetime.now().isoformat(),
            "last_activity": None,
            "last_topic": None,
            "last_alert_type": None,
            "last_severity_filter": None,
            "last_result_count": 0,
            "last_databases": [],
            "conversation_context": {},
            # PHASE-12.1: Database scope persistence
            "active_db_scope": None,           # Locked database name (e.g., "MIDEVSTB")
            "active_scope_type": "AMBIGUOUS",  # "DATABASE", "ENVIRONMENT", "AMBIGUOUS"
        }
    
    @classmethod
    def get_session_id(cls):
        """Get the currently active session ID."""
        global _ACTIVE_SESSION_ID
        return _ACTIVE_SESSION_ID
    
    @classmethod
    def reset_session(cls, session_id):
        """
        Reset a specific session's state.
        
        Args:
            session_id: Session to reset
        """
        global _SESSION_STORAGE
        
        if session_id and session_id in _SESSION_STORAGE:
            _SESSION_STORAGE[session_id] = cls._create_empty_state()
            print("[SESSION] Reset session:", session_id)
            
            # If this is the active session, sync state
            if session_id == _ACTIVE_SESSION_ID:
                cls._state = _SESSION_STORAGE[session_id]
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SessionStore, cls).__new__(cls)
            cls._state["session_start"] = datetime.now().isoformat()
        return cls._instance
    
    @classmethod
    def reset_question_context(cls):
        """
        CRITICAL: Reset per-question formatter context.
        
        Call this at the START of processing each new question to prevent
        root cause, actions, and evidence from bleeding into unrelated questions.
        
        This is DIFFERENT from reset() which clears the entire session.
        """
        cls._current_question_context = {
            "formatter_root_cause": None,
            "formatter_actions": [],
            "formatter_evidence": [],
            "question_type": None
        }
    
    @classmethod
    def get_question_context(cls):
        """Get the current question's formatter context."""
        return cls._current_question_context.copy()
    
    @classmethod
    def set_question_context(cls, **kwargs):
        """Set values in the current question's formatter context."""
        for key, value in kwargs.items():
            if key in cls._current_question_context:
                cls._current_question_context[key] = value
    
    @classmethod
    def get_state(cls):
        """Get the full session state."""
        return cls._state.copy()
    
    # =====================================================
    # PHASE-12.1: DATABASE SCOPE PERSISTENCE
    # =====================================================
    @classmethod
    def get_active_db_scope(cls):
        """
        Get the currently active database scope from session.
        
        Returns:
            Tuple of (database_name, scope_type) or (None, "AMBIGUOUS")
        """
        return (
            cls._state.get("active_db_scope"),
            cls._state.get("active_scope_type", "AMBIGUOUS")
        )
    
    @classmethod
    def set_active_db_scope(cls, database_name, scope_type="DATABASE"):
        """
        Set the active database scope in session.
        
        Args:
            database_name: Name of database (e.g., "MIDEVSTB") or None
            scope_type: "DATABASE", "ENVIRONMENT", or "AMBIGUOUS"
        """
        cls._state["active_db_scope"] = database_name
        cls._state["active_scope_type"] = scope_type
        print(f"[SESSION] Scope locked: {database_name} ({scope_type})")
    
    @classmethod
    def clear_db_scope(cls):
        """Clear the database scope (on new conversation)."""
        cls._state["active_db_scope"] = None
        cls._state["active_scope_type"] = "AMBIGUOUS"
        print("[SESSION] Scope cleared")
    
    @classmethod
    def update(cls, **kwargs):
        """
        Update session state with new values.
        
        Args:
            **kwargs: Key-value pairs to update
        """
        for key, value in kwargs.items():
            if key in cls._state and value is not None:
                cls._state[key] = value
        
        cls._state["last_activity"] = datetime.now().isoformat()
        cls._state["question_count"] += 1
    
    @classmethod
    def set_highest_risk_db(cls, db_name):
        """Explicitly set the highest risk database."""
        cls._state["highest_risk_database"] = db_name
        # PRODUCTION FIX: Lock highest risk DB once set
        if not cls._state.get("locked_highest_risk_db"):
            cls._state["locked_highest_risk_db"] = db_name
    
    @classmethod
    def lock_root_cause(cls, root_cause, db_name=None):
        """
        PRODUCTION FIX: Lock root cause for session consistency.
        
        Once a dominant root cause is identified for a database,
        LOCK it for the session. Do NOT alternate between:
        - OTHER
        - UNKNOWN  
        - INTERNAL_ERROR
        
        Args:
            root_cause: The computed/inferred root cause
            db_name: Optional - lock for specific database
        """
        if not root_cause:
            return
        
        # Filter out invalid root causes
        invalid_causes = ["OTHER", "UNKNOWN", "Unknown", "N/A", None, ""]
        if root_cause in invalid_causes:
            return
        
        # Lock global root cause if not already set
        if not cls._state.get("locked_root_cause"):
            cls._state["locked_root_cause"] = root_cause
        
        # Lock for specific database
        if db_name:
            db_upper = db_name.upper()
            if db_upper not in cls._state.get("locked_root_cause_db", {}):
                cls._state["locked_root_cause_db"][db_upper] = root_cause
    
    @classmethod
    def get_locked_root_cause(cls, db_name=None):
        """
        Get locked root cause for session or specific database.
        
        PRODUCTION RULE: Once identified, root cause is locked.
        
        Args:
            db_name: Optional - get locked cause for specific DB
            
        Returns:
            Locked root cause string or None
        """
        if db_name:
            db_upper = db_name.upper()
            db_locked = cls._state.get("locked_root_cause_db", {}).get(db_upper)
            if db_locked:
                return db_locked
        
        return cls._state.get("locked_root_cause")
    
    @classmethod
    def lock_peak_hour(cls, hour):
        """Lock peak alert hour for session consistency."""
        if hour is not None and cls._state.get("locked_peak_hour") is None:
            cls._state["locked_peak_hour"] = hour
            cls._state["peak_alert_hour"] = hour
    
    @classmethod
    def get_locked_peak_hour(cls):
        """Get locked peak hour."""
        return cls._state.get("locked_peak_hour")
    
    @classmethod
    def add_critical_but_running(cls, db_name):
        """Track database that is CRITICAL but still running (not DOWN)."""
        if db_name and db_name not in cls._state.get("critical_but_running", []):
            cls._state["critical_but_running"].append(db_name)
            cls._state["critical_but_running"] = cls._state["critical_but_running"][-10:]
    
    @classmethod
    def get_critical_but_running(cls):
        """Get list of CRITICAL but running databases."""
        return cls._state.get("critical_but_running", [])
    
    @classmethod
    def add_dominant_ora(cls, ora_code):
        """Add an ORA code to the dominant list (max 5)."""
        if ora_code:
            ora_clean = ora_code.split()[0] if " " in ora_code else ora_code
            if ora_clean not in cls._state["dominant_ora_codes"]:
                cls._state["dominant_ora_codes"].insert(0, ora_clean)
                cls._state["dominant_ora_codes"] = cls._state["dominant_ora_codes"][:5]
    
    @classmethod
    def record_analysis(cls, analysis_result):
        """
        Record an analysis in history.
        
        Args:
            analysis_result: Dict with analysis details
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "question": analysis_result.get("question"),
            "target": analysis_result.get("target"),
            "intent": analysis_result.get("intent"),
            "root_cause": analysis_result.get("root_cause"),
            "confidence": analysis_result.get("confidence")
        }
        
        cls._state["analysis_history"].append(entry)
        
        # Keep only last 20 entries
        if len(cls._state["analysis_history"]) > 20:
            cls._state["analysis_history"] = cls._state["analysis_history"][-20:]
    
    @classmethod
    def get_context_summary(cls):
        """
        Get a summary of session context for use in responses.
        
        Returns:
            Dict with key session facts
        """
        return {
            "has_prior_analysis": cls._state["question_count"] > 0,
            "highest_risk_database": cls._state["highest_risk_database"],
            "dominant_ora_codes": cls._state["dominant_ora_codes"][:3],
            "peak_alert_hour": cls._state["peak_alert_hour"],
            "last_root_cause": cls._state["last_abstract_cause"] or cls._state["last_root_cause"],
            "risk_posture": cls._state["overall_risk_posture"],
            "questions_analyzed": cls._state["question_count"],
            "last_target": cls._state["last_target"]
        }
    
    @classmethod
    def get_context_phrase(cls):
        """
        Build a context phrase for follow-up questions.
        
        PRODUCTION RULE: Responses MUST include "Based on earlier analysis..."
        when prior analysis exists.
        
        Returns:
            String like "Based on earlier analysis: ..."
        """
        if cls._state["question_count"] == 0:
            return None
        
        parts = []
        
        # Use locked values when available (session consistency)
        highest_risk = cls._state.get("locked_highest_risk_db") or cls._state.get("highest_risk_database")
        if highest_risk:
            parts.append("highest risk database is {}".format(highest_risk))
        
        # Use locked root cause for consistency
        locked_rc = cls._state.get("locked_root_cause")
        if locked_rc:
            parts.append("primary issue identified as {}".format(locked_rc))
        elif cls._state["last_abstract_cause"]:
            parts.append("primary issue identified as {}".format(
                cls._state["last_abstract_cause"]
            ))
        elif cls._state["last_root_cause"]:
            parts.append("root cause is {}".format(
                cls._state["last_root_cause"]
            ))
        
        if cls._state["dominant_ora_codes"]:
            top_oras = cls._state["dominant_ora_codes"][:2]
            parts.append("dominant ORA codes are {}".format(", ".join(top_oras)))
        
        # Use locked peak hour for consistency
        peak_hour = cls._state.get("locked_peak_hour") or cls._state.get("peak_alert_hour")
        if peak_hour is not None:
            parts.append("peak hour at {}:00".format(peak_hour))
        
        # Include risk posture
        if cls._state.get("overall_risk_posture"):
            parts.append("environment risk is {}".format(cls._state["overall_risk_posture"]))
        
        # ADDED: Include unstable systems if tracked
        if cls._state.get("unstable_systems"):
            parts.append("{} unstable system(s) identified".format(
                len(cls._state["unstable_systems"])
            ))
        
        # ADDED: Include CRITICAL but running databases
        if cls._state.get("critical_but_running"):
            parts.append("{} database(s) running but unstable".format(
                len(cls._state["critical_but_running"])
            ))
        
        if parts:
            return "Based on earlier analysis: " + ", ".join(parts) + "."
        return None
    
    @classmethod
    def add_unstable_system(cls, system_name):
        """
        Track an unstable system.
        
        Args:
            system_name: Name of the unstable system
        """
        if system_name and system_name not in cls._state["unstable_systems"]:
            cls._state["unstable_systems"].append(system_name)
            # Keep only last 10
            cls._state["unstable_systems"] = cls._state["unstable_systems"][-10:]
    
    @classmethod
    def record_down_event(cls, target, timestamp=None):
        """
        Record a DOWN event for tracking.
        
        Args:
            target: Database that went down
            timestamp: When it went down (defaults to now)
        """
        event = {
            "target": target,
            "timestamp": timestamp or datetime.now().isoformat()
        }
        cls._state["down_events"].append(event)
        # Keep only last 20
        cls._state["down_events"] = cls._state["down_events"][-20:]
    
    @classmethod
    def get_unstable_systems(cls):
        """Get list of unstable systems."""
        return cls._state.get("unstable_systems", [])
    
    @classmethod
    def get_recent_down_events(cls):
        """Get recent DOWN events."""
        return cls._state.get("down_events", [])
    
    @classmethod
    def set_highest_risk_with_score(cls, db_name, score):
        """
        Set highest risk database if score is higher than current.
        
        Args:
            db_name: Database name
            score: Risk score (0-1)
        """
        if score > cls._state.get("highest_risk_score", 0):
            cls._state["highest_risk_database"] = db_name
            cls._state["highest_risk_score"] = score
    
    @classmethod
    def reset(cls):
        """Reset session state (for testing)."""
        cls._state = {
            "highest_risk_database": None,
            "highest_risk_score": 0,
            "dominant_ora_codes": [],
            "peak_alert_hour": None,
            "last_root_cause": None,
            "last_abstract_cause": None,
            "overall_risk_posture": None,
            # PRODUCTION: Reset locked values
            "locked_root_cause": None,
            "locked_root_cause_db": {},
            "locked_highest_risk_db": None,
            "locked_peak_hour": None,
            "unstable_systems": [],
            "down_events": [],
            "critical_but_running": [],
            "question_count": 0,
            "last_question": None,
            "last_target": None,
            "last_intent": None,
            "last_confidence": None,
            "analysis_history": [],
            "session_start": datetime.now().isoformat(),
            "last_activity": None,
            # CONVERSATIONAL CONTEXT (NEW)
            "last_topic": None,           # e.g., "STANDBY_ALERTS", "CRITICAL_ALERTS"
            "last_alert_type": None,      # e.g., "dataguard", "tablespace"
            "last_severity_filter": None, # e.g., "CRITICAL"
            "last_result_count": 0,       # Count from last query
            "last_databases": [],         # Databases mentioned in last result
            "conversation_context": {}    # Rich context for follow-ups
        }
    
    # =====================================================
    # CONVERSATIONAL CONTEXT METHODS (NEW)
    # =====================================================
    
    @classmethod
    def set_conversation_context(cls, **kwargs):
        """
        Store conversation context for follow-up queries.
        
        This enables intelligent follow-ups like:
        - "show me 20" → uses last topic
        - "only critical" → filters last result
        - "this database" → uses last target
        
        Args:
            **kwargs: Context fields to update
                - topic: alert topic (STANDBY_ALERTS, etc.)
                - alert_type: type of alerts (dataguard, tablespace, etc.)
                - severity: severity filter
                - databases: list of databases in result
                - result_count: number of results
                - query_type: COUNT, LIST, ENTITY, etc.
                - has_context: If False with explicit reset fields, clears context
        """
        context = cls._state.get("conversation_context", {})
        
        # CRITICAL FIX: If has_context=False is explicitly passed,
        # this is a RESET request - clear the entire context first
        if "has_context" in kwargs and kwargs["has_context"] is False:
            # Full context reset
            context = {
                "topic": None,
                "alert_type": None,
                "severity": None,
                "databases": [],
                "result_count": 0,
                "displayed_count": 0,  # CRITICAL FIX: Track actual alerts shown
                "has_context": False
            }
            cls._state["conversation_context"] = context
            # Clear shortcut fields too
            cls._state["last_topic"] = None
            cls._state["last_alert_type"] = None
            cls._state["last_severity_filter"] = None
            cls._state["last_result_count"] = 0
            cls._state["last_displayed_count"] = 0  # CRITICAL FIX
            cls._state["last_databases"] = []
            return
        
        # Update context with new values (only non-None)
        for key, value in kwargs.items():
            if value is not None:
                context[key] = value
        
        # Set has_context=True when setting valid context
        if any(k in kwargs for k in ["topic", "alert_type", "databases"]):
            if any(kwargs.get(k) for k in ["topic", "alert_type", "databases"]):
                context["has_context"] = True
        
        cls._state["conversation_context"] = context
        
        # Also update shortcut fields for quick access
        if "topic" in kwargs and kwargs["topic"]:
            cls._state["last_topic"] = kwargs["topic"]
        if "alert_type" in kwargs and kwargs["alert_type"]:
            cls._state["last_alert_type"] = kwargs["alert_type"]
        if "severity" in kwargs and kwargs["severity"]:
            cls._state["last_severity_filter"] = kwargs["severity"]
        if "result_count" in kwargs and kwargs["result_count"] is not None:
            cls._state["last_result_count"] = kwargs["result_count"]
        # CRITICAL FIX: Track displayed_count separately
        if "displayed_count" in kwargs and kwargs["displayed_count"] is not None:
            cls._state["last_displayed_count"] = kwargs["displayed_count"]
        if "databases" in kwargs and kwargs["databases"]:
            cls._state["last_databases"] = kwargs["databases"]
        # FIX: Also sync last_target to shortcut field
        if "last_target" in kwargs and kwargs["last_target"]:
            cls._state["last_target"] = kwargs["last_target"]
        
        # INTELLIGENCE UPGRADE: Track query mode for follow-ups
        if "query_mode" in kwargs and kwargs["query_mode"]:
            cls._state["last_query_mode"] = kwargs["query_mode"]
        if "filters" in kwargs and kwargs["filters"]:
            cls._state["last_filters"] = kwargs["filters"]
        if "limit" in kwargs:
            cls._state["last_limit"] = kwargs["limit"]
    
    @classmethod
    def get_conversation_context(cls):
        """
        Get full conversation context for follow-up resolution.
        
        INTELLIGENCE UPGRADE: Now includes query mode, filters, and result scope
        for comprehensive follow-up handling.
        
        Returns:
            Dict with all context fields
        """
        return {
            # Core context
            "topic": cls._state.get("last_topic"),
            "alert_type": cls._state.get("last_alert_type"),
            "severity": cls._state.get("last_severity_filter"),
            "result_count": cls._state.get("last_result_count", 0),
            # CRITICAL FIX: Track displayed_count separately from result_count
            # displayed_count = actual alerts USER HAS SEEN (for pagination)
            # result_count = total matching alerts
            "displayed_count": cls._state.get("last_displayed_count", 0),
            "databases": cls._state.get("last_databases", []),
            "last_target": cls._state.get("last_target"),
            "last_intent": cls._state.get("last_intent"),
            
            # INTELLIGENCE UPGRADE: Query mode and filters
            "query_mode": cls._state.get("last_query_mode"),  # COUNT, LIST, ENTITY, EXPLAIN, ACTION
            "filters": cls._state.get("last_filters", {}),    # Applied filters
            "limit": cls._state.get("last_limit"),            # Last limit applied
            
            # Context flags
            "has_context": bool(cls._state.get("last_topic") or cls._state.get("last_target") or cls._state.get("last_query_mode")),
            "has_entity": bool(cls._state.get("last_target")),
            "has_filters": bool(cls._state.get("last_filters")),
            
            # Full context blob
            "full_context": cls._state.get("conversation_context", {})
        }
    
    @classmethod
    def get_last_query_mode(cls):
        """
        Get the last query mode (COUNT, LIST, ENTITY, EXPLAIN, ACTION).
        
        CRITICAL for follow-up handling:
        - If last mode was LIST, "show 20" means "show 20 of same list"
        - If last mode was COUNT, "show 20" means "list 20 from that count"
        """
        return cls._state.get("last_query_mode")
    
    @classmethod
    def get_last_filters(cls):
        """Get the last applied filters."""
        return cls._state.get("last_filters", {})
    
    @classmethod
    def clear_conversation_context(cls):
        """
        Clear conversation context when topic changes.
        
        Called when user asks about a DIFFERENT topic.
        """
        cls._state["last_topic"] = None
        cls._state["last_alert_type"] = None
        cls._state["last_severity_filter"] = None
        cls._state["last_result_count"] = 0
        cls._state["last_databases"] = []
        cls._state["last_query_mode"] = None
        cls._state["last_filters"] = {}
        cls._state["last_limit"] = None
        cls._state["conversation_context"] = {}
    
    @classmethod
    def get_last_topic(cls):
        """Get the last topic discussed (for follow-ups)."""
        return cls._state.get("last_topic")
    
    @classmethod
    def get_last_alert_type(cls):
        """Get the last alert type (dataguard, tablespace, etc.)."""
        return cls._state.get("last_alert_type")
    
    @classmethod
    def get_last_databases(cls):
        """Get databases from the last result."""
        return cls._state.get("last_databases", [])


# Global instance for import
SESSION_STORE = SessionStore()
