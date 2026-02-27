"""
PHASE 2: Conversation Context Manager
=====================================
Manages persistent conversation context across messages.

CONTEXT STRUCTURE (MANDATORY):
{
    "topic": str | None,              # e.g., "MIDEVSTB_ALERTS", "STANDBY_ISSUES"
    "last_intent": str | None,        # COUNT, LIST, STATUS, FACT
    "last_database": str | None,      # e.g., "MIDEVSTB"
    "last_severity": str | None,      # CRITICAL, WARNING
    "last_category": str | None,      # standby, tablespace, listener
    "last_result_count": int | None,  # Number of results from last query
    "displayed_count": int,           # How many alerts user has seen
    "active_filters": dict,           # Currently applied filters
    "has_context": bool,              # Whether context is active
    "last_question": str | None,      # The last question asked
    "last_answer": str | None,        # Summary of last answer
}

RULES:
- Context persists across messages in same session
- Context is created after valid Phase 1 answer
- Context can be reset explicitly or implicitly
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import threading


class ConversationContext:
    """
    Represents a single conversation's context state.
    
    This is an immutable-style object - modifications create new state.
    """
    
    def __init__(
        self,
        topic: Optional[str] = None,
        last_intent: Optional[str] = None,
        last_database: Optional[str] = None,
        last_severity: Optional[str] = None,
        last_category: Optional[str] = None,
        last_result_count: Optional[int] = None,
        displayed_count: int = 0,
        active_filters: Optional[Dict] = None,
        has_context: bool = False,
        last_question: Optional[str] = None,
        last_answer: Optional[str] = None
    ):
        self.topic = topic
        self.last_intent = last_intent
        self.last_database = last_database
        self.last_severity = last_severity
        self.last_category = last_category
        self.last_result_count = last_result_count
        self.displayed_count = displayed_count
        self.active_filters = active_filters or {}
        self.has_context = has_context
        self.last_question = last_question
        self.last_answer = last_answer
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for debugging/serialization."""
        return {
            "topic": self.topic,
            "last_intent": self.last_intent,
            "last_database": self.last_database,
            "last_severity": self.last_severity,
            "last_category": self.last_category,
            "last_result_count": self.last_result_count,
            "displayed_count": self.displayed_count,
            "active_filters": self.active_filters.copy(),
            "has_context": self.has_context,
            "last_question": self.last_question,
            "last_answer": self.last_answer[:100] if self.last_answer else None,
        }
    
    def copy(self, **updates) -> 'ConversationContext':
        """Create a copy with optional updates."""
        data = self.to_dict()
        data.update(updates)
        data["updated_at"] = datetime.now()
        # Remove answer truncation for copy
        data["last_answer"] = updates.get("last_answer", self.last_answer)
        return ConversationContext(**{k: v for k, v in data.items() 
                                      if k not in ["updated_at"]})
    
    @classmethod
    def empty(cls) -> 'ConversationContext':
        """Create an empty (reset) context."""
        return cls(has_context=False)
    
    def __repr__(self):
        return f"ConversationContext(topic={self.topic}, db={self.last_database}, has_context={self.has_context})"


class ContextManager:
    """
    Manages conversation contexts for multiple sessions.
    
    Thread-safe implementation for concurrent access.
    """
    
    def __init__(self):
        self._contexts: Dict[str, ConversationContext] = {}
        self._lock = threading.RLock()
        self._default_session = "default"
    
    def get_context(self, session_id: Optional[str] = None) -> ConversationContext:
        """
        Get the context for a session.
        
        Args:
            session_id: Session identifier (uses default if None)
            
        Returns:
            ConversationContext for the session
        """
        session_id = session_id or self._default_session
        
        with self._lock:
            if session_id not in self._contexts:
                self._contexts[session_id] = ConversationContext.empty()
            return self._contexts[session_id]
    
    def set_context(self, context: ConversationContext, session_id: Optional[str] = None):
        """
        Set the context for a session.
        
        Args:
            context: New context to set
            session_id: Session identifier
        """
        session_id = session_id or self._default_session
        
        with self._lock:
            self._contexts[session_id] = context
    
    def update_context(self, session_id: Optional[str] = None, **updates) -> ConversationContext:
        """
        Update specific fields in the context.
        
        Args:
            session_id: Session identifier
            **updates: Fields to update
            
        Returns:
            Updated ConversationContext
        """
        session_id = session_id or self._default_session
        
        with self._lock:
            current = self.get_context(session_id)
            updated = current.copy(**updates)
            self._contexts[session_id] = updated
            return updated
    
    def reset_context(self, session_id: Optional[str] = None):
        """
        Reset the context for a session.
        
        Args:
            session_id: Session identifier
        """
        session_id = session_id or self._default_session
        
        with self._lock:
            self._contexts[session_id] = ConversationContext.empty()
    
    def has_active_context(self, session_id: Optional[str] = None) -> bool:
        """Check if session has active context."""
        context = self.get_context(session_id)
        return context.has_context
    
    def get_debug_info(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get debug information for a session's context."""
        context = self.get_context(session_id)
        return {
            "session_id": session_id or self._default_session,
            "context": context.to_dict(),
            "context_age_seconds": (datetime.now() - context.updated_at).total_seconds() 
                if hasattr(context, 'updated_at') else None
        }


class ContextBuilder:
    """
    Builds conversation context from Phase 1 results.
    
    Called after successful Phase 1 query to establish context.
    """
    
    @staticmethod
    def build_from_phase1_result(
        question: str,
        intent: Dict[str, Any],
        query_result: Dict[str, Any],
        answer: str
    ) -> ConversationContext:
        """
        Build context from Phase 1 processing result.
        
        Args:
            question: Original user question
            intent: Parsed intent from Phase 1
            query_result: Query result from Phase 1
            answer: Generated answer
            
        Returns:
            New ConversationContext
        """
        # Extract data from query result
        data = query_result.get("data", {}) if query_result else {}
        
        # Determine topic
        topic = ContextBuilder._determine_topic(intent, data)
        
        # Determine category
        category = ContextBuilder._determine_category(intent, question)
        
        # Get result count
        result_count = data.get("total_count") or data.get("count") or data.get("total_alerts")
        
        # Get displayed count (for LIST queries)
        displayed_count = data.get("shown_count", 0)
        
        # Build active filters
        active_filters = {}
        if intent.get("severity"):
            active_filters["severity"] = intent["severity"]
        if intent.get("category"):
            active_filters["category"] = intent["category"]
        if intent.get("database"):
            active_filters["database"] = intent["database"]
        
        return ConversationContext(
            topic=topic,
            last_intent=intent.get("intent_type"),
            last_database=intent.get("database"),
            last_severity=intent.get("severity"),
            last_category=category,
            last_result_count=result_count,
            displayed_count=displayed_count,
            active_filters=active_filters,
            has_context=True,
            last_question=question,
            last_answer=answer
        )
    
    @staticmethod
    def _determine_topic(intent: Dict, data: Dict) -> str:
        """Determine the conversation topic."""
        parts = []
        
        # Add database if specific
        if intent.get("database") and intent["database"] != "ALL":
            parts.append(intent["database"])
        
        # Add category
        if intent.get("category"):
            parts.append(intent["category"])
        
        # Add severity
        if intent.get("severity") and intent["severity"] != "ALL":
            parts.append(intent["severity"])
        
        # Add base topic
        parts.append("ALERTS")
        
        return "_".join(parts) if parts else "GENERAL"
    
    @staticmethod
    def _determine_category(intent: Dict, question: str) -> Optional[str]:
        """Determine the alert category from intent or question."""
        # From intent
        if intent.get("category"):
            return intent["category"].lower()
        
        # From question keywords
        q_lower = question.lower()
        if any(kw in q_lower for kw in ["standby", "dataguard", "data guard", "apply lag"]):
            return "standby"
        if any(kw in q_lower for kw in ["tablespace", "space", "storage"]):
            return "tablespace"
        if any(kw in q_lower for kw in ["listener", "tns", "connection"]):
            return "listener"
        
        return None


# Global singleton instance
_context_manager = None

def get_context_manager() -> ContextManager:
    """Get or create the global context manager."""
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
    return _context_manager


def get_context(session_id: Optional[str] = None) -> ConversationContext:
    """Convenience function to get context."""
    return get_context_manager().get_context(session_id)


def update_context(session_id: Optional[str] = None, **updates) -> ConversationContext:
    """Convenience function to update context."""
    return get_context_manager().update_context(session_id, **updates)


def reset_context(session_id: Optional[str] = None):
    """Convenience function to reset context."""
    get_context_manager().reset_context(session_id)


def build_context(question: str, intent: Dict, query_result: Dict, answer: str) -> ConversationContext:
    """Convenience function to build context from Phase 1 result."""
    return ContextBuilder.build_from_phase1_result(question, intent, query_result, answer)
