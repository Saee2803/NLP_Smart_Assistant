"""
CONTEXT TRACKER - Tracks conversation context for follow-ups
"""
from datetime import datetime
from typing import Dict, List, Optional


class ContextTracker:
    """Tracks context like DBA remembering recent work."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance
    
    def _init(self):
        self.last_target = None
        self.last_cause = None
        self.last_intent = None
        self.last_findings = {}
        self.last_time_range = None
        self.history = []
    
    def update(self, **kwargs):
        """Update context."""
        if kwargs.get("target"):
            self.last_target = kwargs["target"]
        if kwargs.get("cause"):
            self.last_cause = kwargs["cause"]
        if kwargs.get("intent"):
            self.last_intent = kwargs["intent"]
        if kwargs.get("findings"):
            self.last_findings = kwargs["findings"]
        if kwargs.get("time_range"):
            self.last_time_range = kwargs["time_range"]
        
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            **kwargs
        })
        
        # Keep last 20
        if len(self.history) > 20:
            self.history = self.history[-20:]
    
    def get(self) -> Dict:
        """Get current context."""
        return {
            "last_target": self.last_target,
            "last_cause": self.last_cause,
            "last_intent": self.last_intent,
            "last_findings": self.last_findings,
            "last_time_range": self.last_time_range
        }
    
    def resolve_reference(self, query: str) -> Dict:
        """Resolve pronouns like 'it', 'that database'."""
        q = query.lower()
        resolved = {}
        
        if any(w in q for w in ["it", "that", "this", "same", "that database", "this db"]):
            if self.last_target:
                resolved["target"] = self.last_target
            if self.last_cause:
                resolved["cause"] = self.last_cause
        
        if "again" in q or "more" in q:
            resolved["continue_analysis"] = True
            resolved.update(self.get())
        
        return resolved
    
    def reset(self):
        """Reset context."""
        self._init()
    
    def get_summary(self) -> str:
        """Get context summary."""
        parts = []
        if self.last_target:
            parts.append("Target: {}".format(self.last_target))
        if self.last_cause:
            parts.append("Last Issue: {}".format(self.last_cause))
        if self.last_findings:
            parts.append("Findings: {} items".format(len(self.last_findings)))
        return " | ".join(parts) if parts else "No previous context"


# Singleton instance
CONTEXT = ContextTracker()
