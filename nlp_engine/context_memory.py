class ContextMemory:
    """
    Session-level memory for conversational follow-up queries.
    
    CONVERSATIONAL INTELLIGENCE UPGRADE:
    Tracks the last query context to enable natural follow-ups:
    - "show me 20 alerts" → uses last_topic/last_database
    - "only critical ones" → applies filter on last_result_set
    - "same database" → references last_database
    
    Python 3.6.8 compatible.
    """

    def __init__(self):
        # Legacy fields (keep for backward compatibility)
        self.last_target = None
        self.last_intent = None
        
        # NEW: Conversational context for follow-up queries
        self.last_topic = None          # e.g., "STANDBY_ALERTS", "CRITICAL_ALERTS"
        self.last_database = None       # e.g., "MIDEVSTBN"
        self.last_severity = None       # e.g., "CRITICAL", "WARNING"
        self.last_result_set = []       # Last computed result for filtering
        self.last_result_count = 0      # Total count in last result
        self.last_question = None       # Last question text
        self.last_answer_type = None    # e.g., "COUNT", "LIST", "TIME"

    def update(self, target=None, intent=None, **kwargs):
        """
        Update context memory.
        
        Args:
            target: Database/target name
            intent: Question intent
            **kwargs: Additional context fields:
                - topic: e.g., "STANDBY_ALERTS"
                - severity: e.g., "CRITICAL"
                - result_set: List of items
                - result_count: Total count
                - question: Question text
                - answer_type: Response type
        """
        if target:
            self.last_target = target
            self.last_database = target
        if intent:
            self.last_intent = intent
        
        # Update conversational context
        if "topic" in kwargs:
            self.last_topic = kwargs["topic"]
        if "severity" in kwargs:
            self.last_severity = kwargs["severity"]
        if "result_set" in kwargs:
            self.last_result_set = kwargs["result_set"]
        if "result_count" in kwargs:
            self.last_result_count = kwargs["result_count"]
        if "question" in kwargs:
            self.last_question = kwargs["question"]
        if "answer_type" in kwargs:
            self.last_answer_type = kwargs["answer_type"]

    def get_target(self):
        """Get last mentioned target (legacy compatibility)."""
        return self.last_target
    
    def get_database(self):
        """Get last mentioned database."""
        return self.last_database

    def get_intent(self):
        """Get last intent (legacy compatibility)."""
        return self.last_intent
    
    def get_context_summary(self):
        """
        Get a summary of current context for follow-up resolution.
        
        Returns dict with available context for intelligent follow-ups.
        """
        return {
            "has_context": bool(self.last_topic or self.last_database),
            "topic": self.last_topic,
            "database": self.last_database,
            "severity": self.last_severity,
            "result_count": self.last_result_count,
            "answer_type": self.last_answer_type,
            "can_filter": len(self.last_result_set) > 0
        }
    
    def clear(self):
        """Clear all context (for new conversation)."""
        self.__init__()

