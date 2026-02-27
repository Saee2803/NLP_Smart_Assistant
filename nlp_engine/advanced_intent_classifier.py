# nlp_engine/advanced_intent_classifier.py
"""
Advanced Intent Classifier and Question Parser

Consolidates IntentClassifier + IntentDetector
Adds synonym support for improved understanding
Extracts rich context for answering

Python 3.6 compatible.
"""

import re
from datetime import datetime, timedelta


class AdvancedIntentClassifier(object):
    """
    Enhanced intent classification with synonym support and rich entity extraction.
    """
    
    # Synonyms for common concepts
    SYNONYMS = {
        'unstable': ['risky', 'fragile', 'unreliable', 'wobbly', 'shaky'],
        'failing': ['crashing', 'breaking', 'failing', 'dying', 'collapsing'],
        'slow': ['sluggish', 'latency', 'lagging', 'performance', 'speed'],
        'down': ['unavailable', 'offline', 'crashed', 'stopped'],
        'memory': ['heap', 'pga', 'sga', 'ram', 'oom'],
        'cpu': ['processor', 'compute', 'utilization'],
        'disk': ['storage', 'space', 'io', 'throughput'],
        'network': ['connectivity', 'bandwidth', 'latency', 'timeout'],
        'frequent': ['often', 'many times', 'repeatedly', 'recurring'],
        'recover': ['heal', 'self-correct', 'bounce back', 'resume'],
        'pattern': ['trend', 'cycle', 'repeating', 'recurring'],
        'health': ['status', 'condition', 'state', 'well-being']
    }
    
    # Intent mappings
    INTENT_PATTERNS = {
        'WHY': {
            'keywords': ['why', 'reason', 'caused', 'due to', 'what caused', 'explanation'],
            'weight': 1.0
        },
        'WHEN': {
            'keywords': ['when', 'time', 'occurred', 'started', 'happened'],
            'weight': 0.9
        },
        'FREQUENT': {
            'keywords': ['frequent', 'often', 'many times', 'recurring', 'pattern'],
            'weight': 0.9
        },
        'HEALTH': {
            'keywords': ['health', 'status', 'stable', 'condition', 'state'],
            'weight': 0.85
        },
        'RISK': {
            'keywords': ['risk', 'safe', 'danger', 'vulnerable', 'exposed'],
            'weight': 0.85
        },
        'RECOMMENDATION': {
            'keywords': ['what to do', 'solution', 'recommend', 'fix', 'action', 'prevent'],
            'weight': 0.85
        },
        'COMPARISON': {
            'keywords': ['compare', 'difference', 'versus', 'vs', 'better', 'worse'],
            'weight': 0.8
        },
        'PREDICTION': {
            'keywords': ['next', 'when will', 'going to', 'predict', 'forecast'],
            'weight': 0.8
        }
    }
    
    def __init__(self, db=None):
        """
        Initialize classifier.
        
        Args:
            db: Optional database instance for context lookups
        """
        self.db = db
    
    # =====================================================
    # PRIMARY API
    # =====================================================
    
    def classify(self, question):
        """
        Classify question into intent with rich context.
        
        Returns:
            Dict with intent, confidence, entities, synonyms_matched
        """
        q_lower = question.lower().strip()
        
        # Detect primary intent
        intent_scores = {}
        for intent_name, intent_config in self.INTENT_PATTERNS.items():
            score = self._score_intent(q_lower, intent_config['keywords'])
            if score > 0:
                intent_scores[intent_name] = score * intent_config['weight']
        
        # Get highest scoring intent
        if intent_scores:
            primary_intent = max(intent_scores, key=intent_scores.get)
            confidence = min(0.99, intent_scores[primary_intent])
        else:
            primary_intent = 'GENERAL'
            confidence = 0.3
        
        # Extract entities
        entities = self._extract_entities(question, q_lower)
        
        # Find synonyms matched
        synonyms_used = self._find_synonyms_in_question(q_lower)
        
        return {
            'intent': primary_intent,
            'confidence': confidence,
            'intent_scores': intent_scores,  # All intents scored
            'entities': entities,
            'synonyms_matched': synonyms_used,
            'raw_question': question
        }
    
    # =====================================================
    # INTENT SCORING
    # =====================================================
    
    def _score_intent(self, question, keywords):
        """
        Score how well question matches intent keywords.
        
        Uses synonym expansion for better matching.
        """
        score = 0
        
        for keyword in keywords:
            # Direct match
            if keyword in question:
                score += 1.0
            
            # Synonym match
            if keyword in self.SYNONYMS:
                for synonym in self.SYNONYMS[keyword]:
                    if synonym in question:
                        score += 0.7  # Slightly lower confidence for synonyms
        
        return score
    
    def _find_synonyms_in_question(self, question):
        """Find which concepts were mentioned via synonyms."""
        matched = []
        
        for concept, synonyms in self.SYNONYMS.items():
            if concept in question:
                matched.append({
                    'concept': concept,
                    'form': 'direct',
                    'word': concept
                })
            else:
                for synonym in synonyms:
                    if synonym in question:
                        matched.append({
                            'concept': concept,
                            'form': 'synonym',
                            'word': synonym
                        })
                        break
        
        return matched
    
    # =====================================================
    # ENTITY EXTRACTION
    # =====================================================
    
    def _extract_entities(self, question, question_lower):
        """
        Extract database/target, metrics, time windows, etc.
        """
        entities = {}
        
        # Extract database name
        db_name = self._extract_database_name(question)
        if db_name:
            entities['target'] = db_name
            entities['target_confidence'] = 0.95
        
        # Extract metric category
        metric = self._extract_metric_category(question_lower)
        if metric:
            entities['metric'] = metric
        
        # Extract time window
        time_window = self._extract_time_window(question_lower)
        if time_window:
            entities['time_window'] = time_window
        
        # Extract severity level
        severity = self._extract_severity(question_lower)
        if severity:
            entities['severity'] = severity
        
        return entities
    
    def _extract_database_name(self, question):
        """
        Extract database name from question.
        
        Looks for patterns like FINDB, HRDB, MIDEVSTBN, etc.
        """
        # All caps 3+ chars, usually ending in DB or containing DB
        tokens = re.findall(r'[A-Z0-9_]{3,}', question)
        
        for token in tokens:
            if 'DB' in token or token.isupper():
                return token
        
        return None
    
    def _extract_metric_category(self, question):
        """
        Extract metric type: CPU, MEMORY, DISK, NETWORK, etc.
        """
        metric_patterns = {
            'CPU': ['cpu', 'processor', 'utilization', 'compute'],
            'MEMORY': ['memory', 'heap', 'pga', 'sga', 'ram', 'oom'],
            'DISK': ['disk', 'storage', 'io', 'throughput', 'tablespace'],
            'NETWORK': ['network', 'connectivity', 'bandwidth', 'timeout'],
            'AVAILABILITY': ['down', 'offline', 'crashed', 'unavailable'],
        }
        
        for category, keywords in metric_patterns.items():
            if any(kw in question for kw in keywords):
                return category
        
        return None
    
    def _extract_time_window(self, question):
        """
        Extract time window: TODAY, YESTERDAY, LAST_NIGHT, WEEK, MONTH, etc.
        """
        time_patterns = {
            'YESTERDAY': ['yesterday', 'yesterday'],
            'LAST_NIGHT': ['last night', 'last nite'],
            'TODAY': ['today', 'this morning'],
            'LAST_WEEK': ['last week'],
            'LAST_MONTH': ['last month'],
            'HOUR': ['hour', 'last hour', 'past hour']
        }
        
        for window, keywords in time_patterns.items():
            if any(kw in question for kw in keywords):
                return window
        
        # Try to extract specific hour
        hour_match = re.search(r'(\d{1,2})\s*(am|pm|a\.m|p\.m)', question)
        if hour_match:
            hour = hour_match.group(1)
            meridiem = hour_match.group(2)
            return 'HOUR_{0}_{1}'.format(hour, meridiem)
        
        return None
    
    def _extract_severity(self, question):
        """Extract severity level from question."""
        severity_keywords = {
            'CRITICAL': ['critical', 'emergency', 'urgent', 'down'],
            'HIGH': ['high', 'severe', 'serious'],
            'MEDIUM': ['medium', 'moderate'],
            'LOW': ['low', 'minor']
        }
        
        for severity, keywords in severity_keywords.items():
            if any(kw in question for kw in keywords):
                return severity
        
        return None
    
    # =====================================================
    # CONTEXT AWARENESS
    # =====================================================
    
    def extract_context(self, classification_result):
        """
        Extract structured context for answer generation.
        
        Args:
            classification_result: Result from classify()
        
        Returns:
            Context dict for downstream components
        """
        intent = classification_result['intent']
        entities = classification_result['entities']
        synonyms = classification_result['synonyms_matched']
        
        context = {
            'intent': intent,
            'target': entities.get('target'),
            'metric': entities.get('metric'),
            'time_window': entities.get('time_window'),
            'severity': entities.get('severity'),
            'synonyms_normalized': {}
        }
        
        # Map synonyms to canonical forms for downstream
        for syn in synonyms:
            context['synonyms_normalized'][syn['form'] + ':' + syn['word']] = syn['concept']
        
        return context
    
    # =====================================================
    # CONFIDENCE & VALIDATION
    # =====================================================
    
    def is_answerable(self, classification_result):
        """
        Determine if question is answerable with high confidence.
        
        Returns:
            (boolean, explanation)
        """
        intent_confidence = classification_result['confidence']
        entities = classification_result['entities']
        
        # Questions need target to be answerable
        if 'target' not in entities:
            return (False, 'Please specify which database you are asking about')
        
        # Minimum confidence threshold
        if intent_confidence < 0.4:
            return (False, 'Question intent unclear. Please rephrase.')
        
        return (True, 'Question is clear and answerable')


class SynonymAwareQuestionParser(object):
    """
    Enhanced question parser with synonym support.
    Wraps AdvancedIntentClassifier for backward compatibility.
    """
    
    def __init__(self, db=None):
        """Initialize parser."""
        self.classifier = AdvancedIntentClassifier(db)
    
    @classmethod
    def parse(cls, question, db=None):
        """
        Parse question - static method for backward compatibility.
        """
        parser = cls(db)
        result = parser.classifier.classify(question)
        
        # Convert to old format for backward compatibility
        return {
            'intent': result['intent'],
            'confidence': result['confidence'],
            'target': result['entities'].get('target'),
            'metric': result['entities'].get('metric'),
            'time_window': result['entities'].get('time_window'),
            'severity': result['entities'].get('severity'),
            'raw_question': question,
            'synonyms_used': len(result['synonyms_matched']) > 0
        }
