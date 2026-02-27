"""
PHASE 2: Conversational Intelligence Service
=============================================
Wraps Phase 1 with conversation context management.

This is the main entry point for Phase 2. It:
1. Checks for follow-up questions
2. Resolves context if needed
3. Delegates to Phase 1 for actual processing
4. Updates context after each query

FLOW:
User Question → Follow-up Detection → Context Resolution → Phase 1 → Update Context → Answer
"""

from typing import Dict, Any, Optional
import logging

from .context_manager import (
    ContextManager, ConversationContext, ContextBuilder,
    get_context_manager, get_context, update_context, reset_context, build_context
)
from .followup_detector import (
    FollowUpDetector, FollowUpType, ContextResolver,
    get_followup_detector, detect_followup, resolve_context
)

# Import Phase 1
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from phase1.service import Phase1Service
from phase1.intent_parser import Phase1IntentParser
from phase1.query_engine import Phase1QueryEngine
from phase1.answer_generator import Phase1AnswerGenerator


logger = logging.getLogger(__name__)


class Phase2Service:
    """
    Phase 2 Conversational Intelligence Service.
    
    Adds context awareness and follow-up handling on top of Phase 1.
    """
    
    def __init__(self):
        """Initialize Phase 2 service with Phase 1 components."""
        self.phase1 = Phase1Service()
        self.context_manager = get_context_manager()
        self.followup_detector = get_followup_detector()
        self.context_resolver = ContextResolver()
        
        logger.info("Phase2Service initialized")
    
    def process_question(
        self,
        question: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a question with conversational context.
        
        Args:
            question: User's question
            session_id: Session identifier for context tracking
            
        Returns:
            {
                "answer": str,                    # Human-readable answer
                "intent": dict,                   # Parsed intent
                "context_used": bool,             # Whether context was applied
                "followup_type": str,             # Type of follow-up detected
                "new_context": dict,              # Updated context
                "debug": dict                     # Debug information
            }
        """
        question = question.strip()
        
        # Step 1: Get current context
        current_context = self.context_manager.get_context(session_id)
        
        # Step 2: Detect follow-up type
        followup_type, followup_info = self.followup_detector.detect(
            question, current_context
        )
        
        logger.info(f"Follow-up detection: {followup_type.value}, info: {followup_info}")
        
        # Step 3: Route based on follow-up type
        if followup_type in [FollowUpType.NOT_FOLLOWUP, 
                              FollowUpType.NEW_QUESTION,
                              FollowUpType.CONTEXT_RESET]:
            # Process as fresh Phase 1 question
            result = self._process_fresh_question(question, session_id)
            result["followup_type"] = followup_type.value
            result["context_used"] = False
            return result
        
        else:
            # Process as follow-up with context
            result = self._process_followup_question(
                question, session_id, followup_type, followup_info, current_context
            )
            result["followup_type"] = followup_type.value
            result["context_used"] = True
            return result
    
    def _process_fresh_question(
        self,
        question: str,
        session_id: Optional[str]
    ) -> Dict[str, Any]:
        """
        Process a fresh question (no context needed).
        
        Delegates to Phase 1 and updates context afterwards.
        """
        # Process with Phase 1
        phase1_result = self.phase1.process(question)
        
        # Build and store new context if successful
        if phase1_result.get("success"):
            new_context = build_context(
                question=question,
                intent=phase1_result.get("intent", {}),
                query_result=phase1_result.get("query_result", {}),
                answer=phase1_result.get("answer", "")
            )
            self.context_manager.set_context(new_context, session_id)
        else:
            # Reset context on failure
            self.context_manager.reset_context(session_id)
            new_context = ConversationContext.empty()
        
        return {
            "answer": phase1_result.get("answer", ""),
            "intent": phase1_result.get("intent", {}),
            "success": phase1_result.get("success", False),
            "new_context": new_context.to_dict() if new_context else {},
            "debug": {
                "phase": 2,
                "phase1_result": phase1_result,
                "context_action": "created" if phase1_result.get("success") else "reset"
            }
        }
    
    def _process_followup_question(
        self,
        question: str,
        session_id: Optional[str],
        followup_type: FollowUpType,
        followup_info: Dict[str, Any],
        current_context: ConversationContext
    ) -> Dict[str, Any]:
        """
        Process a follow-up question using context.
        
        Resolves context, modifies intent, and processes with Phase 1.
        """
        # Resolve effective parameters from context
        resolved = self.context_resolver.resolve(
            question, followup_type, followup_info, current_context
        )
        
        logger.info(f"Context resolved: {resolved}")
        
        # Build a modified question for Phase 1
        modified_question = self._build_contextual_question(
            question, resolved, followup_type, current_context
        )
        
        logger.info(f"Modified question: {modified_question}")
        
        # Process with Phase 1
        phase1_result = self.phase1.process(modified_question)
        
        # Override intent with resolved values (Phase 1 might not catch context)
        if phase1_result.get("success"):
            intent = phase1_result.get("intent", {})
            
            # Merge resolved context into intent
            if resolved.get("database"):
                intent["database"] = resolved["database"]
            if resolved.get("severity"):
                intent["severity"] = resolved["severity"]
            if resolved.get("category"):
                intent["category"] = resolved["category"]
            if resolved.get("limit"):
                intent["limit"] = resolved["limit"]
            
            phase1_result["intent"] = intent
            
            # Re-run query with context-enhanced intent
            phase1_result = self._reprocess_with_context(intent, phase1_result)
            
            # Update context
            new_context = build_context(
                question=question,
                intent=intent,
                query_result=phase1_result.get("query_result", {}),
                answer=phase1_result.get("answer", "")
            )
            self.context_manager.set_context(new_context, session_id)
        else:
            new_context = current_context
        
        return {
            "answer": phase1_result.get("answer", ""),
            "intent": phase1_result.get("intent", {}),
            "success": phase1_result.get("success", False),
            "new_context": new_context.to_dict() if new_context else {},
            "debug": {
                "phase": 2,
                "followup_type": followup_type.value,
                "followup_info": followup_info,
                "resolved_context": resolved,
                "modified_question": modified_question,
                "phase1_result_keys": list(phase1_result.keys()) if phase1_result else [],
                "context_action": "updated"
            }
        }
    
    def _build_contextual_question(
        self,
        original_question: str,
        resolved: Dict[str, Any],
        followup_type: FollowUpType,
        context: ConversationContext
    ) -> str:
        """
        Build a modified question that includes context information.
        
        This helps Phase 1 understand the complete query.
        """
        parts = []
        
        # Start with base action
        if followup_type == FollowUpType.LIMIT:
            limit = resolved.get("limit", 10)
            parts.append(f"show me {limit}")
        elif followup_type == FollowUpType.FILTER:
            sev = resolved.get("severity", "").lower()
            parts.append(f"show me {sev}")
        elif followup_type == FollowUpType.LIMIT_FILTER:
            limit = resolved.get("limit", 10)
            sev = resolved.get("severity", "").lower()
            parts.append(f"show me {limit} {sev}")
        elif followup_type == FollowUpType.CONTEXTUAL_SWITCH:
            cat = resolved.get("category", "")
            parts.append(f"show me {cat}")
        else:
            parts.append("show me")
        
        parts.append("alerts")
        
        # Add database from context
        if resolved.get("database"):
            parts.append(f"for {resolved['database']}")
        
        # Add category if relevant
        if resolved.get("category") and followup_type != FollowUpType.CONTEXTUAL_SWITCH:
            parts.append(f"category {resolved['category']}")
        
        return " ".join(parts)
    
    def _reprocess_with_context(
        self,
        intent: Dict[str, Any],
        phase1_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Re-process the query with context-enhanced intent.
        
        This ensures the query results respect the context.
        """
        try:
            # Use Phase 1's query engine directly with enhanced intent
            query_result = self.phase1.engine.execute(intent)
            
            # Generate new answer
            answer = self.phase1.generator.generate(query_result, intent)
            
            return {
                "success": True,
                "answer": answer,
                "intent": intent,
                "query_result": query_result
            }
        except Exception as e:
            logger.error(f"Error reprocessing with context: {e}")
            return phase1_result
    
    def get_context_debug(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get debug information about current context."""
        return self.context_manager.get_debug_info(session_id)
    
    def clear_context(self, session_id: Optional[str] = None):
        """Explicitly clear context for a session."""
        self.context_manager.reset_context(session_id)


def is_phase2_question(question: str, session_id: Optional[str] = None) -> bool:
    """
    Check if a question should be handled by Phase 2 (has context).
    
    Args:
        question: User question
        session_id: Session ID
        
    Returns:
        True if context exists and might be used
    """
    context = get_context(session_id)
    if not context.has_context:
        return False
    
    followup_type, _ = detect_followup(question, context)
    return followup_type not in [FollowUpType.NOT_FOLLOWUP, FollowUpType.NEW_QUESTION]


# Convenience function for direct use
def process_question(question: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Process a question with Phase 2 conversational intelligence.
    
    This is the main entry point for Phase 2.
    """
    service = Phase2Service()
    return service.process_question(question, session_id)


# Export main classes
__all__ = [
    'Phase2Service',
    'process_question',
    'is_phase2_question'
]
