# services/context_manager.py
"""
==============================================================
CONTEXT MANAGER - Conversation context and follow-up handling
==============================================================

Manages:
- Conversation history per session
- Context merging for follow-up queries
- Entity inheritance from previous queries
- Pagination state tracking

Python 3.6.8 compatible.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import copy


class ConversationContext:
    """
    Represents the current conversation context.
    
    Tracks:
    - Current database target
    - Applied filters (severity, issue_type)
    - Pagination state
    - Query history
    """
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset all context to initial state."""
        self.database = None
        self.severity = None
        self.issue_type = None
        self.limit = 20  # Default limit
        self.offset = 0
        self.total_results = 0
        self.displayed_count = 0
        self.topic = None
        self.last_intent = None
        self.last_query = None
        self.last_answer = None
        self.query_history = []
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "database": self.database,
            "severity": self.severity,
            "issue_type": self.issue_type,
            "limit": self.limit,
            "offset": self.offset,
            "total_results": self.total_results,
            "displayed_count": self.displayed_count,
            "topic": self.topic,
            "last_intent": self.last_intent,
            "last_query": self.last_query,
            "has_context": self.has_context()
        }
    
    def has_context(self) -> bool:
        """Check if we have any active context."""
        return bool(self.database or self.topic or self.issue_type)
    
    def update(self, **kwargs):
        """Update context with new values."""
        for key, value in kwargs.items():
            if hasattr(self, key) and value is not None:
                setattr(self, key, value)
        self.timestamp = datetime.now()


class ContextManager:
    """
    Manages conversation context for NLP sessions.
    
    Features:
    - Per-session context isolation
    - Follow-up query resolution
    - Entity inheritance
    - Pagination tracking
    """
    
    # Storage for per-session contexts
    _sessions = {}  # session_id -> ConversationContext
    
    @classmethod
    def get_context(cls, session_id: str) -> ConversationContext:
        """
        Get or create context for a session.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            ConversationContext for this session
        """
        if session_id not in cls._sessions:
            cls._sessions[session_id] = ConversationContext()
        return cls._sessions[session_id]
    
    @classmethod
    def reset_context(cls, session_id: str):
        """Reset context for a session."""
        if session_id in cls._sessions:
            cls._sessions[session_id].reset()
        else:
            cls._sessions[session_id] = ConversationContext()
    
    @classmethod
    def merge_entities(cls, session_id: str, 
                       current_entities: Dict[str, Any],
                       current_intent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge current entities with previous context.
        
        CRITICAL LOGIC:
        - Explicit entities in current query OVERRIDE previous
        - Missing entities INHERIT from previous (if follow-up)
        - New database RESETS severity/issue_type filters
        
        Args:
            session_id: Session identifier
            current_entities: Entities from current query
            current_intent: Intent classification result
            
        Returns:
            Merged entity dictionary with all resolved values
        """
        ctx = cls.get_context(session_id)
        is_followup = current_intent.get("is_followup", False)
        
        merged = {
            "database": None,
            "severity": None,
            "issue_type": None,
            "limit": 20,
            "offset": 0,
            "time_range": None,
            "action": "list",
            "ora_codes": [],
            "from_context": False
        }
        
        # Get current values
        current_dbs = current_entities.get("databases", [])
        current_severity = current_entities.get("severity")
        current_issue_type = current_entities.get("issue_type")
        current_limit = current_entities.get("limit")
        current_offset = current_entities.get("offset", 0)
        
        # RULE 1: Explicit database in query OVERRIDES and RESETS filters
        if current_dbs:
            merged["database"] = current_dbs[0]  # Use first database
            # Reset filters when database changes
            if current_dbs[0] != ctx.database:
                merged["severity"] = current_severity  # Only from current query
                merged["issue_type"] = current_issue_type
            else:
                # Same database - allow filter inheritance
                merged["severity"] = current_severity or ctx.severity
                merged["issue_type"] = current_issue_type or ctx.issue_type
        
        # RULE 2: For follow-ups, inherit database from context
        elif is_followup and ctx.has_context():
            merged["database"] = ctx.database
            merged["from_context"] = True
            
            # Severity: Current overrides, else inherit
            merged["severity"] = current_severity if current_severity else ctx.severity
            
            # Issue type: Current overrides, else inherit
            merged["issue_type"] = current_issue_type if current_issue_type else ctx.issue_type
        
        # RULE 3: If severity mentioned but database not, keep previous database
        elif current_severity and ctx.database:
            merged["database"] = ctx.database
            merged["severity"] = current_severity
            merged["issue_type"] = ctx.issue_type
            merged["from_context"] = True
        
        # No context to inherit
        else:
            merged["database"] = current_dbs[0] if current_dbs else None
            merged["severity"] = current_severity
            merged["issue_type"] = current_issue_type
        
        # RULE 4: Handle limit and offset
        if current_limit:
            merged["limit"] = current_limit
            # If severity changes, reset offset
            if current_severity and current_severity != ctx.severity:
                merged["offset"] = 0
            else:
                merged["offset"] = current_offset if current_offset >= 0 else ctx.offset + ctx.limit
        elif is_followup:
            merged["limit"] = ctx.limit or 20
            merged["offset"] = current_offset if current_offset >= 0 else ctx.offset + ctx.limit
        
        # RULE 5: Handle "next" pagination
        if current_offset == -1:  # Special "next" marker
            merged["offset"] = ctx.offset + ctx.limit
        
        # Copy other entities
        merged["time_range"] = current_entities.get("time_range")
        merged["action"] = current_entities.get("action", "list")
        merged["ora_codes"] = current_entities.get("ora_codes", [])
        
        return merged
    
    @classmethod
    def update_context(cls, session_id: str, 
                       query: str,
                       merged_entities: Dict[str, Any],
                       intent: Dict[str, Any],
                       results: Dict[str, Any]):
        """
        Update context after processing a query.
        
        Args:
            session_id: Session identifier
            query: Original query text
            merged_entities: Resolved entities
            intent: Intent classification
            results: Query results (for pagination tracking)
        """
        ctx = cls.get_context(session_id)
        
        # Update context with new values
        ctx.database = merged_entities.get("database") or ctx.database
        ctx.severity = merged_entities.get("severity") or ctx.severity
        ctx.issue_type = merged_entities.get("issue_type") or ctx.issue_type
        ctx.limit = merged_entities.get("limit", ctx.limit)
        ctx.offset = merged_entities.get("offset", ctx.offset)
        
        # Update from results
        ctx.total_results = results.get("total_count", ctx.total_results)
        ctx.displayed_count = results.get("displayed_count", 0)
        
        # Update topic based on intent/entities
        if merged_entities.get("issue_type"):
            ctx.topic = "{}_ALERTS".format(merged_entities["issue_type"].upper())
        elif merged_entities.get("database"):
            ctx.topic = "{}_ALERTS".format(merged_entities["database"])
        
        ctx.last_intent = intent.get("intent")
        ctx.last_query = query
        ctx.last_answer = results.get("answer")
        
        # Add to history
        ctx.query_history.append({
            "query": query,
            "intent": intent.get("intent"),
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only last 10 queries
        if len(ctx.query_history) > 10:
            ctx.query_history = ctx.query_history[-10:]
    
    @classmethod
    def get_context_summary(cls, session_id: str) -> str:
        """
        Get a human-readable context summary for follow-up understanding.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Summary string like "MIDEVSTB alerts (CRITICAL filter, showing 20 of 100)"
        """
        ctx = cls.get_context(session_id)
        
        if not ctx.has_context():
            return "No active context"
        
        parts = []
        if ctx.database:
            parts.append(ctx.database)
        if ctx.topic and not ctx.database:
            parts.append(ctx.topic)
        if ctx.severity:
            parts.append("{} only".format(ctx.severity))
        if ctx.total_results > 0:
            parts.append("showing {}-{} of {}".format(
                ctx.offset + 1,
                min(ctx.offset + ctx.displayed_count, ctx.total_results),
                ctx.total_results
            ))
        
        return " | ".join(parts) if parts else "Active context"
    
    @classmethod
    def should_reset(cls, session_id: str, new_entities: Dict, new_intent: Dict) -> bool:
        """
        Determine if context should be reset.
        
        Context resets when:
        - User asks about different database
        - User explicitly asks for fresh/new query
        - User asks "show only" with NO previous context (need to reset to get ALL)
        - User asks completely new question type
        """
        ctx = cls.get_context(session_id)
        
        # CRITICAL: FRESH_QUERY intent always resets
        intent_name = new_intent.get("intent", "")
        if intent_name == "FRESH_QUERY":
            return True
        
        # "show only" patterns should reset ONLY if NO previous context exists
        # If context exists, follow-ups should use it
        if intent_name == "FOLLOWUP_SEVERITY":
            new_severity = new_entities.get("severity")
            if new_severity and not new_entities.get("databases"):
                # Only reset if there's NO existing context
                # This means "show only warnings" without prior DB specified
                if not ctx.has_context():
                    return False  # No context to reset, proceed normally
                # If context exists, DON'T reset - inherit the database
                return False
        
        # New database that's different from current
        new_dbs = new_entities.get("databases", [])
        if new_dbs and ctx.database and new_dbs[0] != ctx.database:
            # Check if it's a partial match (MIDEVSTB vs MIDEVSTBN)
            if not (new_dbs[0] in ctx.database or ctx.database in new_dbs[0]):
                return True
        
        # Intent change from list to analysis (unless follow-up)
        if not new_intent.get("is_followup"):
            if ctx.last_intent in ["ALERT_LIST", "ALERT_SUMMARY"] and intent_name == "ROOT_CAUSE":
                return False  # Allow asking "why" about current alerts
            if intent_name in ["RECOMMENDATION", "ROOT_CAUSE"] and not ctx.has_context():
                return True  # Need context for these
        
        return False


# Singleton instance
_manager = None

def get_context_manager() -> ContextManager:
    """Get the context manager class."""
    return ContextManager


# Convenience functions
def get_session_context(session_id: str) -> ConversationContext:
    """Get context for a session."""
    return ContextManager.get_context(session_id)


def merge_with_context(session_id: str, entities: Dict, intent: Dict) -> Dict:
    """Merge current entities with session context."""
    return ContextManager.merge_entities(session_id, entities, intent)


def update_session_context(session_id: str, query: str, entities: Dict, intent: Dict, results: Dict):
    """Update session context after processing."""
    ContextManager.update_context(session_id, query, entities, intent, results)


# Test
if __name__ == "__main__":
    session_id = "test-session-123"
    
    # Simulate conversation
    print("=== Query 1: show alerts for MIDEVSTB ===")
    entities1 = {"databases": ["MIDEVSTB"], "severity": None, "limit": None}
    intent1 = {"intent": "ALERT_SUMMARY", "is_followup": False}
    merged1 = ContextManager.merge_entities(session_id, entities1, intent1)
    print("Merged:", merged1)
    ContextManager.update_context(session_id, "show alerts for MIDEVSTB", merged1, intent1, 
                                   {"total_count": 165855, "displayed_count": 0})
    
    print("\n=== Query 2: ok show me 18 warning ===")
    entities2 = {"databases": [], "severity": "WARNING", "limit": 18}
    intent2 = {"intent": "FOLLOWUP_LIMIT", "is_followup": True}
    merged2 = ContextManager.merge_entities(session_id, entities2, intent2)
    print("Merged:", merged2)
    
    print("\n=== Context Summary ===")
    print(ContextManager.get_context_summary(session_id))
