# test_phase2_intelligence.py
"""
Phase 2 Intelligence Engine Tests

Tests for:
- TimeAwarePredictor (time-aware failure predictions)
- DatabaseHealthScorer (composite health scoring)
- MultiCauseRCA (multi-cause root cause analysis)
- AdvancedIntentClassifier (NLP with synonyms)
- EvidenceBasedAnswerGenerator (Phase 2-informed answers)

Python 3.6 compatible unit tests.
"""

import unittest
import sys
import os
from datetime import datetime, timedelta

# Add paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock database for testing
class MockDatabase(object):
    """Mock database for testing without real database."""
    
    def __init__(self):
        self.incidents = []
        self.metrics = []
        self.anomalies = []
        self.patterns = []
        self.recommendations = []
    
    def get_incidents(self, target, days=7):
        """Get incidents for target."""
        return [i for i in self.incidents if i.get('target') == target]
    
    def get_anomalies(self, target, days=7):
        """Get anomalies for target."""
        return [a for a in self.anomalies if a.get('target') == target]
    
    def get_patterns(self, target):
        """Get patterns for target."""
        return [p for p in self.patterns if p.get('target') == target]
    
    def get_recommendations(self, target):
        """Get recommendations for target."""
        return [r for r in self.recommendations if r.get('target') == target]
    
    def get_metrics(self, target, days=7):
        """Get metrics for target."""
        return [m for m in self.metrics if m.get('target') == target]


# =====================================================
# TEST: TimeAwarePredictor
# =====================================================

class TestTimeAwarePredictor(unittest.TestCase):
    """Tests for TimeAwarePredictor."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.db = MockDatabase()
        
        # Add test incidents
        for hour in [2, 3, 4]:  # Morning hours
            for day in range(7):  # Week of incidents
                self.db.incidents.append({
                    'target': 'DB_TEST',
                    'timestamp': '2024-01-{0:02d} {1:02d}:00:00'.format(
                        (day % 28) + 1, hour
                    ),
                    'description': 'Test incident',
                    'severity': 'HIGH'
                })
        
        # Add evening incidents (less frequent)
        for hour in [18, 19]:
            for day in range(3):
                self.db.incidents.append({
                    'target': 'DB_TEST',
                    'timestamp': '2024-01-{0:02d} {1:02d}:00:00'.format(
                        (day % 28) + 1, hour
                    ),
                    'description': 'Test incident',
                    'severity': 'MEDIUM'
                })
        
        # Import predictor
        from incident_engine.time_aware_predictor import TimeAwarePredictor
        self.predictor = TimeAwarePredictor(self.db)
    
    def test_hour_of_day_risk_detection(self):
        """Test detection of high-risk hours."""
        risk = self.predictor.get_hour_of_day_risk('DB_TEST', 2)
        
        self.assertIsNotNone(risk)
        self.assertGreater(risk.get('probability', 0), 0)
        self.assertGreater(risk.get('confidence', 0), 0.4)  # Should be confident
    
    def test_low_risk_hours(self):
        """Test detection of low-risk hours."""
        risk = self.predictor.get_hour_of_day_risk('DB_TEST', 12)  # Noon
        
        self.assertIsNotNone(risk)
        # Low-risk hours should have lower confidence
        self.assertLess(risk.get('confidence', 1), 0.7)
    
    def test_high_risk_window_prediction(self):
        """Test high-risk window prediction."""
        prediction = self.predictor.predict_high_risk_window('DB_TEST')
        
        self.assertIsNotNone(prediction)
        self.assertIn('hour_window', prediction)
        self.assertIn('combined_confidence', prediction)
        self.assertGreater(prediction.get('combined_confidence', 0), 0.5)
    
    def test_next_failure_prediction(self):
        """Test prediction of next failure window."""
        prediction = self.predictor.predict_next_failure_window('DB_TEST')
        
        self.assertIsNotNone(prediction)
        self.assertIn('hours_from_now', prediction)
        self.assertGreaterEqual(prediction.get('hours_from_now', 0), 0)
    
    def test_prediction_summary(self):
        """Test comprehensive prediction summary."""
        summary = self.predictor.predict_summary('DB_TEST')
        
        self.assertIsNotNone(summary)
        self.assertIn('top_hours', summary)
        self.assertIn('top_days', summary)


# =====================================================
# TEST: DatabaseHealthScorer
# =====================================================

class TestDatabaseHealthScorer(unittest.TestCase):
    """Tests for DatabaseHealthScorer."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.db = MockDatabase()
        
        # Add healthy target data
        self.db.incidents = [
            {
                'target': 'HEALTHY_DB',
                'timestamp': '2024-01-01 10:00:00',
                'severity': 'LOW',
                'description': 'Minor issue'
            }
        ]
        
        self.db.anomalies = [
            {
                'target': 'HEALTHY_DB',
                'severity': 'LOW',
                'metric': 'CPU'
            }
        ]
        
        self.db.recommendations = [
            {
                'target': 'HEALTHY_DB',
                'status': 'implemented',
                'effectiveness': 'good'
            }
        ]
        
        # Add unhealthy target data
        for i in range(10):
            self.db.incidents.append({
                'target': 'SICK_DB',
                'timestamp': '2024-01-{0:02d} 10:00:00'.format((i % 28) + 1),
                'severity': 'CRITICAL',
                'description': 'Critical incident'
            })
        
        # Import scorer
        from incident_engine.database_health_scorer import DatabaseHealthScorer
        self.scorer = DatabaseHealthScorer(self.db)
    
    def test_health_scoring_produces_valid_range(self):
        """Test that health scores are 0-100."""
        health = self.scorer.score_database('HEALTHY_DB')
        
        self.assertIsNotNone(health)
        self.assertGreaterEqual(health.get('health_score', -1), 0)
        self.assertLessEqual(health.get('health_score', 101), 100)
    
    def test_healthy_database_scores_high(self):
        """Test that healthy database has high score."""
        health = self.scorer.score_database('HEALTHY_DB')
        
        self.assertGreaterEqual(health.get('health_score', 0), 60)
    
    def test_sick_database_scores_low(self):
        """Test that sick database has low score."""
        health = self.scorer.score_database('SICK_DB')
        
        self.assertLess(health.get('health_score', 100), 60)
    
    def test_health_state_classification(self):
        """Test health state classification."""
        health_high = self.scorer.score_database('HEALTHY_DB')
        health_low = self.scorer.score_database('SICK_DB')
        
        self.assertIn(health_high.get('health_state'), 
                     ['HEALTHY', 'ACCEPTABLE', 'DEGRADED', 'CRITICAL'])
        self.assertIn(health_low.get('health_state'),
                     ['HEALTHY', 'ACCEPTABLE', 'DEGRADED', 'CRITICAL'])
    
    def test_component_scores_present(self):
        """Test that component breakdown is provided."""
        health = self.scorer.score_database('HEALTHY_DB')
        components = health.get('component_scores', {})
        
        self.assertGreater(len(components), 0)
        for component, score in components.items():
            self.assertGreaterEqual(score, 0)
            self.assertLessEqual(score, 100)
    
    def test_top_issues_identified(self):
        """Test that top issues are identified."""
        health = self.scorer.score_database('SICK_DB')
        top_issues = health.get('top_issues', [])
        
        self.assertGreater(len(top_issues), 0)
        for issue in top_issues:
            self.assertIn('component', issue)
            self.assertIn('explanation', issue)


# =====================================================
# TEST: MultiCauseRCA
# =====================================================

class TestMultiCauseRCA(unittest.TestCase):
    """Tests for MultiCauseRCA."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.db = MockDatabase()
        
        # Add test data
        test_incident = {
            'target': 'DB_TEST',
            'timestamp': '2024-01-15 10:00:00',
            'severity': 'CRITICAL',
            'description': 'CPU high, memory full',
            'alert_messages': ['CPU > 90%', 'Memory usage high']
        }
        self.db.incidents.append(test_incident)
        self.incident = test_incident
        
        # Add patterns
        self.db.patterns = [
            {
                'target': 'DB_TEST',
                'hour_of_day': 10,
                'day_of_week': 'MONDAY',
                'incident_count': 5
            }
        ]
        
        # Add anomalies
        self.db.anomalies = [
            {
                'target': 'DB_TEST',
                'metric': 'CPU%',
                'z_score': 3.2,
                'severity': 'HIGH'
            },
            {
                'target': 'DB_TEST',
                'metric': 'MEMORY_MB',
                'z_score': 2.8,
                'severity': 'HIGH'
            }
        ]
        
        # Import RCA
        from incident_engine.multi_cause_rca import MultiCauseRCA
        self.rca = MultiCauseRCA(self.db)
    
    def test_causes_identified(self):
        """Test that causes are identified."""
        analysis = self.rca.analyze_incident(self.incident)
        
        self.assertIsNotNone(analysis)
        self.assertIn('causes', analysis)
        self.assertGreater(len(analysis.get('causes', [])), 0)
    
    def test_causes_ranked_by_confidence(self):
        """Test that causes are ranked by confidence."""
        analysis = self.rca.analyze_incident(self.incident)
        causes = analysis.get('causes', [])
        
        if len(causes) > 1:
            # Causes should be in descending confidence order
            for i in range(len(causes) - 1):
                conf1 = causes[i].get('weighted_confidence', 0)
                conf2 = causes[i + 1].get('weighted_confidence', 0)
                self.assertGreaterEqual(conf1, conf2)
    
    def test_cause_has_evidence(self):
        """Test that each cause has supporting evidence."""
        analysis = self.rca.analyze_incident(self.incident)
        causes = analysis.get('causes', [])
        
        for cause in causes:
            self.assertIn('evidence', cause)
            self.assertGreater(len(cause.get('evidence', '')), 0)
    
    def test_confidence_in_valid_range(self):
        """Test that confidence scores are 0-1."""
        analysis = self.rca.analyze_incident(self.incident)
        causes = analysis.get('causes', [])
        
        for cause in causes:
            conf = cause.get('weighted_confidence', 0)
            self.assertGreaterEqual(conf, 0)
            self.assertLessEqual(conf, 1.0)


# =====================================================
# TEST: AdvancedIntentClassifier
# =====================================================

class TestAdvancedIntentClassifier(unittest.TestCase):
    """Tests for AdvancedIntentClassifier."""
    
    def setUp(self):
        """Set up test fixtures."""
        from nlp_engine.advanced_intent_classifier import AdvancedIntentClassifier
        self.classifier = AdvancedIntentClassifier()
    
    def test_why_question_detected(self):
        """Test detection of 'Why' questions."""
        result = self.classifier.classify("Why is FINDB failing?")
        
        self.assertEqual(result['intent'], 'WHY')
        self.assertGreater(result['confidence'], 0.5)
    
    def test_when_question_detected(self):
        """Test detection of 'When' questions."""
        result = self.classifier.classify("When did HRDB crash last time?")
        
        self.assertEqual(result['intent'], 'WHEN')
        self.assertGreater(result['confidence'], 0.5)
    
    def test_health_question_detected(self):
        """Test detection of health questions."""
        result = self.classifier.classify("What is the health status of FINDB?")
        
        self.assertIn(result['intent'], ['HEALTH', 'WHY'])
        self.assertGreater(result['confidence'], 0.5)
    
    def test_synonym_detection_unstable(self):
        """Test synonym detection for 'unstable'."""
        result = self.classifier.classify("Is FINDB unstable?")
        synonyms = result['synonyms_matched']
        
        # Should detect 'unstable' as risk concept
        concepts = [s['concept'] for s in synonyms]
        self.assertIn('unstable', concepts)
    
    def test_synonym_detection_failing(self):
        """Test synonym detection for 'failing'."""
        result = self.classifier.classify("HRDB keeps crashing every day")
        synonyms = result['synonyms_matched']
        
        concepts = [s['concept'] for s in synonyms]
        self.assertIn('failing', concepts)
    
    def test_database_extraction(self):
        """Test database name extraction."""
        result = self.classifier.classify("FINDB has issues")
        
        self.assertIn('target', result['entities'])
        self.assertEqual(result['entities']['target'], 'FINDB')
    
    def test_metric_extraction(self):
        """Test metric extraction."""
        result = self.classifier.classify("CPU usage on FINDB is high")
        
        self.assertIn('metric', result['entities'])
        self.assertEqual(result['entities']['metric'], 'CPU')
    
    def test_severity_extraction(self):
        """Test severity extraction."""
        result = self.classifier.classify("Critical issue with FINDB")
        
        self.assertIn('severity', result['entities'])
        self.assertEqual(result['entities']['severity'], 'CRITICAL')
    
    def test_answerability_check(self):
        """Test answerability check."""
        result = self.classifier.classify("What?")
        is_answerable, reason = self.classifier.is_answerable(result)
        
        self.assertFalse(is_answerable)  # No target specified


# =====================================================
# TEST: EvidenceBasedAnswerGenerator
# =====================================================

class TestEvidenceBasedAnswerGenerator(unittest.TestCase):
    """Tests for EvidenceBasedAnswerGenerator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.db = MockDatabase()
        
        # Add test incident
        self.db.incidents.append({
            'target': 'DB_TEST',
            'timestamp': '2024-01-15 10:00:00',
            'severity': 'HIGH',
            'description': 'CPU spike'
        })
        
        # Add recommendation
        self.db.recommendations.append({
            'target': 'DB_TEST',
            'recommendation': 'Increase CPU limit',
            'status': 'pending'
        })
        
        from nlp_engine.evidence_based_answer_generator import EvidenceBasedAnswerGenerator
        self.generator = EvidenceBasedAnswerGenerator(self.db)
    
    def test_why_answer_generated(self):
        """Test WHY answer generation."""
        answer = self.generator.generate_answer('WHY', 'DB_TEST', {})
        
        self.assertIsNotNone(answer)
        self.assertGreater(len(answer), 0)
    
    def test_health_answer_generated(self):
        """Test HEALTH answer generation."""
        answer = self.generator.generate_answer('HEALTH', 'DB_TEST', {})
        
        self.assertIsNotNone(answer)
        self.assertGreater(len(answer), 0)
    
    def test_recommendation_answer_generated(self):
        """Test RECOMMENDATION answer generation."""
        answer = self.generator.generate_answer('RECOMMENDATION', 'DB_TEST', {})
        
        self.assertIsNotNone(answer)
        self.assertGreater(len(answer), 0)
        self.assertIn('recommend', answer.lower())
    
    def test_missing_target_handled(self):
        """Test handling of missing target."""
        answer = self.generator.generate_answer('WHY', None, {})
        
        self.assertIsNotNone(answer)
        self.assertIn('database', answer.lower())


# =====================================================
# TEST: UnifiedNLPReasoner
# =====================================================

class TestUnifiedNLPReasoner(unittest.TestCase):
    """Tests for UnifiedNLPReasoner."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.db = MockDatabase()
        
        # Add test data
        self.db.incidents.append({
            'target': 'FINDB',
            'timestamp': '2024-01-15 10:00:00',
            'severity': 'HIGH'
        })
        
        from nlp_engine.unified_nlp_reasoner import UnifiedNLPReasoner
        self.reasoner = UnifiedNLPReasoner(self.db)
    
    def test_process_question_returns_answer(self):
        """Test that process_question returns answer."""
        result = self.reasoner.process_question("Why is FINDB failing?")
        
        self.assertIsNotNone(result)
        self.assertIn('answer', result)
        self.assertGreater(len(result['answer']), 0)
    
    def test_intent_captured(self):
        """Test that intent is captured."""
        result = self.reasoner.process_question("Why is FINDB failing?")
        
        self.assertIn('intent', result)
        self.assertEqual(result['intent'], 'WHY')
    
    def test_target_extracted(self):
        """Test that target is extracted."""
        result = self.reasoner.process_question("Why is FINDB failing?")
        
        self.assertIn('target', result)
        self.assertEqual(result['target'], 'FINDB')
    
    def test_context_memory_updated(self):
        """Test that context memory is updated."""
        self.reasoner.process_question("Why is FINDB failing?")
        
        context = self.reasoner.get_context()
        self.assertEqual(context['last_target'], 'FINDB')
    
    def test_multi_turn_context(self):
        """Test multi-turn context using last target."""
        self.reasoner.process_question("Why is FINDB failing?")
        
        # Second question without specifying target
        result = self.reasoner.process_question("How often does this happen?")
        
        # Should infer FINDB from context
        self.assertEqual(result.get('target'), 'FINDB')
    
    def test_backward_compatible_reason_method(self):
        """Test backward compatible 'reason' method."""
        answer = self.reasoner.reason("Why is FINDB failing?")
        
        self.assertIsNotNone(answer)
        self.assertIsInstance(answer, str)
        self.assertGreater(len(answer), 0)
    
    def test_explain_classification(self):
        """Test classification explanation."""
        explanation = self.reasoner.explain_classification("Why is FINDB failing?")
        
        self.assertIn('Intent', explanation)
        self.assertIn('FINDB', explanation)


# =====================================================
# MAIN TEST RUNNER
# =====================================================

if __name__ == '__main__':
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestTimeAwarePredictor))
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseHealthScorer))
    suite.addTests(loader.loadTestsFromTestCase(TestMultiCauseRCA))
    suite.addTests(loader.loadTestsFromTestCase(TestAdvancedIntentClassifier))
    suite.addTests(loader.loadTestsFromTestCase(TestEvidenceBasedAnswerGenerator))
    suite.addTests(loader.loadTestsFromTestCase(TestUnifiedNLPReasoner))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
