# -*- coding: utf-8 -*-
"""
Unified NLP Orchestrator - Single entry point for all NLP processing
Chains: Intent → Entity → Context → Plan → Execute → Response
"""

import logging
from typing import Dict, Any, Optional, Tuple

# Import all NLP modules
from nlp_engine.entity_extractor import EntityExtractor, get_entity_extractor
from nlp_engine.smart_intent import SmartIntentClassifier, get_intent_classifier
from services.context_manager import ContextManager
from services.query_planner import QueryPlanner, get_query_planner
from data_engine.query_executor import QueryExecutor, get_executor
from services.response_generator import ResponseGenerator, get_generator

logger = logging.getLogger(__name__)


class NLPOrchestrator:
    """
    Unified orchestrator for NLP-driven query processing.
    
    Flow:
    1. Classify intent from user query
    2. Extract entities (database, severity, limit, etc.)
    3. Merge with conversation context
    4. Generate query plan
    5. Execute query against data
    6. Generate natural language response
    """
    
    def __init__(self):
        self.intent_classifier = get_intent_classifier()
        self.entity_extractor = get_entity_extractor()
        # ContextManager is a class with classmethods, not an instance
        self.query_planner = get_query_planner()
        self.query_executor = get_executor()
        self.response_generator = get_generator()
        
        self._debug_mode = False
    
    def set_debug(self, enabled: bool):
        """Enable/disable debug mode"""
        self._debug_mode = enabled
    
    def process(self, query: str, session_id: str = 'default') -> Dict[str, Any]:
        """
        Process a user query and return a response.
        
        Args:
            query: User's natural language query
            session_id: Session identifier for context tracking
            
        Returns:
            Dict with 'answer', 'intent', 'entities', 'suggestions', etc.
        """
        debug_info = {} if self._debug_mode else None
        
        try:
            # Step 1: Classify intent
            intent_result = self.intent_classifier.classify(query)
            intent = intent_result['intent']
            confidence = intent_result['confidence']
            question_type = intent_result.get('question_type', 'FACT')
            
            if self._debug_mode:
                debug_info['step1_intent'] = intent_result
            
            logger.debug(f"[NLP] Intent: {intent} (confidence: {confidence})")
            
            # Handle FRESH_QUERY intent - reset context and check if user wants to see all alerts
            if intent == 'FRESH_QUERY':
                self.clear_session(session_id)
                
                # Check if query asks to show all alerts after reset
                query_lower = query.lower()
                if 'show' in query_lower and 'alert' in query_lower:
                    # User wants to see all alerts after reset - treat as ALERT_LIST
                    intent = 'ALERT_LIST'
                    entities = self.entity_extractor.extract(query)
                    merged_entities = entities  # No context to merge
                    query_plan = self.query_planner.plan(intent, merged_entities, question_type)
                    result = self.query_executor.execute(query_plan)
                    response = self.response_generator.generate(result, query_plan, intent, question_type)
                    
                    return {
                        'success': True,
                        'answer': response if isinstance(response, str) else 'Here are all alerts.',
                        'intent': intent,
                        'confidence': confidence,
                        'question_type': question_type,
                        'entities': merged_entities,
                        'result_count': result.filtered_count if hasattr(result, 'filtered_count') else result.total_count,
                        'suggestions': []
                    }
                else:
                    # Just a reset command without data request
                    return {
                        'success': True,
                        'answer': "Context cleared. Ready for a fresh query. What would you like to know?",
                        'intent': intent,
                        'confidence': confidence,
                        'question_type': question_type,
                        'entities': {},
                        'result_count': 0,
                        'suggestions': []
                    }
            
            # Step 2: Extract entities
            entities = self.entity_extractor.extract(query)
            
            if self._debug_mode:
                debug_info['step2_entities'] = entities
            
            logger.debug(f"[NLP] Entities: {entities}")
            
            # Step 3: Check if context should reset (for "show only" type queries)
            if ContextManager.should_reset(session_id, entities, intent_result):
                self.clear_session(session_id)
                logger.debug(f"[NLP] Context reset for intent: {intent}")
            
            # Step 4: Merge with conversation context
            # ContextManager uses classmethods
            merged_entities = ContextManager.merge_entities(session_id, entities, intent_result)
            
            if self._debug_mode:
                debug_info['step3_merged_entities'] = merged_entities
                debug_info['step3_context'] = ContextManager.get_context(session_id).to_dict()
            
            logger.debug(f"[NLP] Merged entities: {merged_entities}")
            
            # Step 5: Handle special intent: MAX_DATABASE_QUERY
            if intent == 'MAX_DATABASE_QUERY':
                return self._handle_max_database_query(merged_entities, session_id)
            
            # Step 6: Generate query plan
            query_plan = self.query_planner.plan(intent, merged_entities, question_type)
            
            if self._debug_mode:
                debug_info['step4_query_plan'] = query_plan.to_dict()
            
            logger.debug(f"[NLP] Query plan: {query_plan.query_type} with filters: {query_plan.filters}")
            
            # Step 7: Execute query
            query_result = self.query_executor.execute(query_plan)
            
            if self._debug_mode:
                debug_info['step5_result_summary'] = {
                    'success': query_result.success,
                    'total_count': query_result.total_count,
                    'filtered_count': query_result.filtered_count,
                    'data_count': len(query_result.data),
                    'aggregations': query_result.aggregations
                }
            
            logger.debug(f"[NLP] Query result: {query_result.filtered_count} alerts found")
            
            # Step 6: Update context with results
            results_dict = {
                'total_count': query_result.filtered_count,
                'displayed_count': len(query_result.data),
                'answer': ''  # Will be set after generation
            }
            ContextManager.update_context(session_id, query, merged_entities, intent_result, results_dict)
            
            # Step 7: Generate response
            response = self.response_generator.generate(
                query_result, 
                query_plan, 
                intent, 
                question_type
            )
            
            # Generate follow-up suggestions
            suggestions = self.response_generator.generate_followup_suggestions(
                query_result, query_plan, intent
            )
            
            result = {
                'success': True,
                'answer': response,
                'intent': intent,
                'confidence': confidence,
                'question_type': question_type,
                'entities': merged_entities,
                'result_count': query_result.filtered_count,
                'suggestions': suggestions
            }
            
            if self._debug_mode:
                result['debug'] = debug_info
            
            return result
            
        except Exception as e:
            logger.error(f"[NLP] Error processing query: {e}", exc_info=True)
            return {
                'success': False,
                'answer': f"Sorry, I encountered an error processing your question: {str(e)}",
                'intent': 'ERROR',
                'confidence': 0,
                'entities': {},
                'result_count': 0,
                'suggestions': ["Try rephrasing your question"]
            }
    
    def _handle_max_database_query(self, merged_entities: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """
        Handle MAX_DATABASE_QUERY intent.
        Find which database has the most alerts.
        """
        try:
            # Execute query to get all databases with counts
            from services.query_planner import QueryPlan
            
            plan = QueryPlan()
            plan.query_type = 'AGGREGATE'
            plan.filters = {}  # No filters - get all
            plan.aggregation = {'group_by': 'target_name'}
            
            result = self.query_executor.execute(plan)
            
            if not result.success or not result.aggregations:
                return {
                    'success': False,
                    'answer': "Unable to determine which database has the most alerts.",
                    'intent': 'MAX_DATABASE_QUERY',
                    'confidence': 0.5,
                    'question_type': 'FACT',
                    'entities': merged_entities,
                    'result_count': 0,
                    'suggestions': []
                }
            
            # Get database counts
            db_counts = result.aggregations.get('counts', {})
            if not db_counts:
                return {
                    'success': True,
                    'answer': "No alert data available.",
                    'intent': 'MAX_DATABASE_QUERY',
                    'confidence': 0.8,
                    'question_type': 'FACT',
                    'entities': merged_entities,
                    'result_count': 0,
                    'suggestions': []
                }
            
            # Find max
            max_db = max(db_counts.items(), key=lambda x: x[1])
            max_db_name = max_db[0]
            max_count = max_db[1]
            
            # Format response
            answer = f"**{max_db_name}** has the most alerts with **{max_count}** alerts.\n\n"
            answer += "**Top 5 Databases by Alert Count:**\n"
            
            sorted_dbs = sorted(db_counts.items(), key=lambda x: x[1], reverse=True)
            for i, (db, count) in enumerate(sorted_dbs[:5], 1):
                pct = (count / result.total_count * 100) if result.total_count > 0 else 0
                answer += f"{i}. **{db}**: {count} ({pct:.1f}%)\n"
            
            return {
                'success': True,
                'answer': answer,
                'intent': 'MAX_DATABASE_QUERY',
                'confidence': 0.95,
                'question_type': 'FACT',
                'entities': merged_entities,
                'result_count': result.total_count,
                'suggestions': [
                    f"Show me alerts for {max_db_name}",
                    f"Which are the critical alerts in {max_db_name}?",
                    "Show me the second highest"
                ]
            }
        except Exception as e:
            logger.error(f"[NLP] Error handling MAX_DATABASE_QUERY: {e}", exc_info=True)
            return {
                'success': False,
                'answer': f"Error: {str(e)}",
                'intent': 'MAX_DATABASE_QUERY',
                'confidence': 0,
                'question_type': 'FACT',
                'entities': merged_entities,
                'result_count': 0,
                'suggestions': []
            }
    
    def process_with_fallback(self, query: str, session_id: str = 'default') -> Dict[str, Any]:
        """
        Process query with fallback handling for low confidence intents.
        """
        result = self.process(query, session_id)
        
        # If low confidence, try to provide helpful response
        if result.get('confidence', 0) < 0.3 and result.get('success'):
            result['answer'] = self._add_low_confidence_note(result['answer'], query)
            result['suggestions'] = [
                "Can you be more specific about what you're looking for?",
                "Try asking about alerts for a specific database",
                "Ask about alert counts or summaries"
            ]
        
        return result
    
    def _add_low_confidence_note(self, answer: str, query: str) -> str:
        """Add a note when confidence is low"""
        note = "*I'm not entirely sure what you're asking. Here's what I found:*\n\n"
        return note + answer
    
    def clear_session(self, session_id: str):
        """Clear session context"""
        ContextManager.reset_context(session_id)
    
    def get_session_context(self, session_id: str) -> Dict[str, Any]:
        """Get current session context for debugging"""
        context = ContextManager.get_context(session_id)
        if context:
            return context.to_dict()
        return {}
    
    def handle_special_commands(self, query: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Handle special commands like 'reset', 'help', etc."""
        query_lower = query.strip().lower()
        
        if query_lower in ['reset', 'clear', 'start over', 'new session']:
            self.clear_session(session_id)
            return {
                'success': True,
                'answer': "Session cleared. What would you like to know about your alerts?",
                'intent': 'RESET',
                'confidence': 1.0,
                'entities': {},
                'result_count': 0,
                'suggestions': [
                    "Show me alert summary",
                    "How many critical alerts are there?",
                    "What alerts does MIDEVSTB have?"
                ]
            }
        
        if query_lower in ['help', '?', 'what can you do']:
            return {
                'success': True,
                'answer': self._get_help_text(),
                'intent': 'HELP',
                'confidence': 1.0,
                'entities': {},
                'result_count': 0,
                'suggestions': [
                    "Show me alert summary",
                    "How many critical alerts are there?",
                    "List alerts for MIDEVSTB"
                ]
            }
        
        return None  # Not a special command
    
    def _get_help_text(self) -> str:
        """Get help text"""
        return """**I can help you with:**

📊 **Alert Queries:**
- "How many alerts are there?" - Get total count
- "Show me critical alerts" - Filter by severity
- "What alerts does MIDEVSTB have?" - Filter by database
- "List top 10 alerts" - Get specific number of alerts

🔍 **Analysis:**
- "What's the root cause?" - Get root cause analysis
- "Compare MIDEVSTB and MIDEVSTBN" - Compare databases
- "What are the dataguard issues?" - Filter by issue type

📝 **Follow-ups:**
- "Show me more" / "Next 10" - Pagination
- "What about warnings?" - Change severity filter
- "And for MIDEVSTBN?" - Change database

💡 **Tips:**
- I remember your previous questions in this session
- You can ask follow-up questions naturally
- Say "reset" to start a new conversation"""


# Singleton instance
_orchestrator = None

def get_orchestrator() -> NLPOrchestrator:
    """Get singleton orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = NLPOrchestrator()
    return _orchestrator


def process_query(query: str, session_id: str = 'default') -> Dict[str, Any]:
    """Convenience function to process a query"""
    orchestrator = get_orchestrator()
    
    # Check for special commands first
    special_result = orchestrator.handle_special_commands(query, session_id)
    if special_result:
        return special_result
    
    return orchestrator.process_with_fallback(query, session_id)


# Test
if __name__ == '__main__':
    import sys
    
    # Set up logging
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
    
    orchestrator = NLPOrchestrator()
    orchestrator.set_debug(True)
    
    # Test conversation
    test_queries = [
        "How many alerts are there for MIDEVSTB?",
        "Show me the critical ones",
        "List top 5",
        "What about MIDEVSTBN?",
        "Compare both databases"
    ]
    
    session_id = 'test_session'
    
    print("=" * 60)
    print("NLP Orchestrator Test")
    print("=" * 60)
    
    for query in test_queries:
        print(f"\n📝 User: {query}")
        print("-" * 40)
        
        result = orchestrator.process(query, session_id)
        
        print(f"🎯 Intent: {result['intent']} (confidence: {result['confidence']:.2f})")
        print(f"📦 Entities: {result['entities']}")
        print(f"📊 Result count: {result['result_count']}")
        print(f"\n💬 Answer:\n{result['answer']}")
        
        if result.get('suggestions'):
            print(f"\n💡 Suggestions: {result['suggestions']}")
        
        print("=" * 60)
