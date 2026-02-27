"""
PHASE 2: Conversational Intelligence
=====================================
Adds conversation context and follow-up handling on top of Phase 1.

COMPONENTS:
- ContextManager: Manages conversation state per session
- FollowUpDetector: Detects and classifies follow-up questions
- Phase2Service: Main orchestrator wrapping Phase 1

USAGE:
    from phase2 import Phase2Service
    
    service = Phase2Service()
    
    # First question - creates context
    result1 = service.process_question("show me alerts for MIDEVSTB", "session1")
    
    # Follow-up - uses context
    result2 = service.process_question("ok show me 18 warning", "session1")
"""

__version__ = "1.0.0"
__phase__ = 2

from .context_manager import (
    ConversationContext,
    ContextManager,
    ContextBuilder,
    get_context_manager,
    get_context,
    update_context,
    reset_context,
    build_context
)

from .followup_detector import (
    FollowUpType,
    FollowUpDetector,
    ContextResolver,
    get_followup_detector,
    get_context_resolver,
    detect_followup,
    resolve_context
)

from .service import (
    Phase2Service,
    process_question,
    is_phase2_question
)

__all__ = [
    # Context Management
    'ConversationContext',
    'ContextManager',
    'ContextBuilder',
    'get_context_manager',
    'get_context',
    'update_context',
    'reset_context',
    'build_context',
    
    # Follow-up Detection
    'FollowUpType',
    'FollowUpDetector',
    'ContextResolver',
    'get_followup_detector',
    'get_context_resolver',
    'detect_followup',
    'resolve_context',
    
    # Main Service
    'Phase2Service',
    'process_question',
    'is_phase2_question'
]