# nlp_engine/unified_nlp_reasoner.py
"""
Unified NLP Reasoner

Consolidates NLPReasoner, IntentClassifier, IntentDetector with Phase 2 engines.
Single entry point for natural language understanding.

Integration with:
- Advanced intent classification (with synonyms)
- Evidence-based answer generation (with Phase 2 insights)
- Context management for multi-turn conversations

Python 3.6 compatible.
"""

from advanced_intent_classifier import AdvancedIntentClassifier
from evidence_based_answer_generator import EvidenceBasedAnswerGenerator


class ContextMemory(object):
    """
    Maintains conversation context for multi-turn dialogs.
    """
    
    def __init__(self, max_history=10):
        """Initialize context memory."""
        self.max_history = max_history
        self.conversation_history = []
        self.last_target = None
        self.last_intent = None
        self.session_context = {}
    
    def add_turn(self, question, answer, intent, target):
        """
        Add conversation turn to history.
        
        Args:
            question: User question
            answer: System answer
            intent: Detected intent
            target: Target database mentioned
        """
        turn = {
            'question': question,
            'answer': answer,
            'intent': intent,
            'target': target
        }
        
        self.conversation_history.append(turn)
        
        # Keep only last N turns
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]
        
        # Update last known values
        if target:
            self.last_target = target
        if intent:
            self.last_intent = intent
    
    def get_last_target(self):
        """Get last mentioned target."""
        return self.last_target
    
    def get_context(self):
        """Get current session context."""
        return {
            'last_target': self.last_target,
            'last_intent': self.last_intent,
            'conversation_history': self.conversation_history
        }
    
    def infer_target_from_context(self):
        """
        If no target mentioned in current question, use last known target.
        
        Returns:
            Last target or None
        """
        return self.last_target


class UnifiedNLPReasoner(object):
    """
    Single entry point for NLP processing.
    
    Consolidates:
    - Intent classification (now with synonym support)
    - Entity extraction (database name, metric, time window, etc.)
    - Answer generation (with Phase 2 intelligence)
    - Context management (multi-turn support)
    """
    
    def __init__(self, db, intelligence_engines=None):
        """
        Initialize unified reasoner.
        
        Args:
            db: Database instance
            intelligence_engines: Dict with optional engines:
                - time_aware_predictor
                - health_scorer
                - multi_cause_rca
                - pattern_engine
                - anomaly_detector
        """
        self.db = db
        self.intelligence_engines = intelligence_engines or {}
        
        # Initialize components
        self.intent_classifier = AdvancedIntentClassifier(db)
        self.answer_generator = EvidenceBasedAnswerGenerator(
            db,
            time_aware_predictor=self.intelligence_engines.get('time_aware_predictor'),
            health_scorer=self.intelligence_engines.get('health_scorer'),
            multi_cause_rca=self.intelligence_engines.get('multi_cause_rca'),
            pattern_engine=self.intelligence_engines.get('pattern_engine'),
            anomaly_detector=self.intelligence_engines.get('anomaly_detector')
        )
        
        # Context management
        self.context_memory = ContextMemory()
    
    # =====================================================
    # PRIMARY ENTRY POINT
    # =====================================================
    
    def process_question(self, question):
        """
        Process user question end-to-end.
        
        Args:
            question: User's natural language question
        
        Returns:
            Dict with answer, intent, target, confidence, etc.
        """
        # Step 1: Classify intent with synonym support
        classification = self.intent_classifier.classify(question)
        intent = classification['intent']
        intent_confidence = classification['confidence']
        
        # Step 2: Extract entities
        entities = classification['entities']
        target = entities.get('target')
        
        # Step 3: Use context to infer target if not explicit
        if not target:
            target = self.context_memory.infer_target_from_context()
        
        # Step 4: Check if answerable
        is_answerable, answerability_reason = self.intent_classifier.is_answerable(
            classification
        )
        
        if not is_answerable:
            answer = answerability_reason
        else:
            # Step 5: Generate evidence-based answer
            context = self.intent_classifier.extract_context(classification)
            answer = self.answer_generator.generate_answer(intent, target, context)
        
        # Step 6: Update context memory
        self.context_memory.add_turn(question, answer, intent, target)
        
        # Return comprehensive result
        return {
            'question': question,
            'answer': answer,
            'intent': intent,
            'intent_confidence': intent_confidence,
            'target': target,
            'entities': entities,
            'synonyms_matched': classification['synonyms_matched'],
            'is_answerable': is_answerable,
            'raw_classification': classification
        }
    
    # =====================================================
    # BACKWARD COMPATIBILITY API
    # =====================================================
    
    def reason(self, question):
        """
        Backward compatible 'reason' method.
        
        Args:
            question: User question
        
        Returns:
            Answer string (for backward compatibility)
        """
        result = self.process_question(question)
        return result['answer']
    
    def get_intent(self, question):
        """Get intent for question (backward compatible)."""
        result = self.process_question(question)
        return result['intent']
    
    # =====================================================
    # MULTI-TURN SUPPORT
    # =====================================================
    
    def get_context(self):
        """Get current conversation context."""
        return self.context_memory.get_context()
    
    def clear_context(self):
        """Clear conversation history."""
        self.context_memory = ContextMemory()
    
    def get_conversation_history(self):
        """Get full conversation history."""
        return self.context_memory.conversation_history
    
    # =====================================================
    # DIAGNOSIS & TRANSPARENCY
    # =====================================================
    
    def explain_classification(self, question):
        """
        Explain how question was classified.
        
        Useful for understanding/debugging intent detection.
        """
        classification = self.intent_classifier.classify(question)
        
        explanation = []
        explanation.append("Classification Analysis:")
        explanation.append("  Intent: {0} (confidence: {1:.2%})".format(
            classification['intent'],
            classification['confidence']
        ))
        
        explanation.append("  Intent Scores:")
        for intent, score in sorted(classification['intent_scores'].items(), 
                                   key=lambda x: x[1], reverse=True):
            explanation.append("    - {0}: {1:.2f}".format(intent, score))
        
        explanation.append("  Entities Extracted:")
        for key, value in classification['entities'].items():
            explanation.append("    - {0}: {1}".format(key, value))
        
        if classification['synonyms_matched']:
            explanation.append("  Synonyms Used:")
            for syn in classification['synonyms_matched']:
                explanation.append(
                    "    - '{0}' → {1} concept".format(
                        syn['word'], syn['concept']
                    )
                )
        
        return "\n".join(explanation)
    
    def explain_answer(self, question):
        """
        Explain how answer was generated.
        
        Shows which intelligence engines contributed.
        """
        result = self.process_question(question)
        
        explanation = []
        explanation.append("Answer Generation for: {0}".format(question))
        explanation.append("")
        explanation.append("Intent: {0}".format(result['intent']))
        explanation.append("Target: {0}".format(result['target']))
        explanation.append("")
        explanation.append("Answer:")
        explanation.append(result['answer'])
        
        if result['intelligence_engines_used']:
            explanation.append("")
            explanation.append("Intelligence Engines Used:")
            for engine in result['intelligence_engines_used']:
                explanation.append("  - {0}".format(engine))
        
        return "\n".join(explanation)


class NLPReasonerFactory(object):
    """
    Factory for creating reasoner with all Phase 2 engines.
    """
    
    @staticmethod
    def create_with_all_engines(db):
        """
        Create reasoner with all available Phase 2 intelligence engines.
        
        Args:
            db: Database instance
        
        Returns:
            UnifiedNLPReasoner with all engines initialized
        """
        # Try to import and initialize Phase 2 engines
        engines = {}
        
        try:
            from incident_engine.time_aware_predictor import TimeAwarePredictor
            engines['time_aware_predictor'] = TimeAwarePredictor(db)
        except (ImportError, Exception):
            pass
        
        try:
            from incident_engine.database_health_scorer import DatabaseHealthScorer
            engines['health_scorer'] = DatabaseHealthScorer(db)
        except (ImportError, Exception):
            pass
        
        try:
            from incident_engine.multi_cause_rca import MultiCauseRCA
            engines['multi_cause_rca'] = MultiCauseRCA(db)
        except (ImportError, Exception):
            pass
        
        try:
            from learning.pattern_engine import PatternEngine
            engines['pattern_engine'] = PatternEngine(db)
        except (ImportError, Exception):
            pass
        
        try:
            from anomaly.detector import AnomalyDetector
            engines['anomaly_detector'] = AnomalyDetector(db)
        except (ImportError, Exception):
            pass
        
        return UnifiedNLPReasoner(db, engines)
    
    @staticmethod
    def create_basic(db):
        """
        Create minimal reasoner (just classification and basic answers).
        
        Args:
            db: Database instance
        
        Returns:
            UnifiedNLPReasoner without Phase 2 engines
        """
        return UnifiedNLPReasoner(db)
