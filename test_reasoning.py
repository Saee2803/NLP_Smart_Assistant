"""
Test Reasoning Modules
"""
import sys
sys.path.insert(0, '.')

from reasoning import (
    HypothesisEngine,
    EvidenceCollector,
    DecisionEngine,
    ActionRecommender,
    PatternRecognizer,
    ConfidenceScorer,
    RiskPredictor,
    ReasoningOrchestrator,
    AnswerFormatter
)

# Sample test alerts
TEST_ALERTS = [
    {"target": "PRODDB01", "message": "ORA-1653: unable to extend table", "severity": "CRITICAL", "alert_time": "2026-01-15T14:30:00"},
    {"target": "PRODDB01", "message": "ORA-1653: tablespace USERS full", "severity": "CRITICAL", "alert_time": "2026-01-15T14:35:00"},
    {"target": "PRODDB01", "message": "ORA-1654: unable to extend index", "severity": "CRITICAL", "alert_time": "2026-01-15T14:40:00"},
    {"target": "PRODDB02", "message": "ORA-600: internal error code", "severity": "CRITICAL", "alert_time": "2026-01-15T15:00:00"},
    {"target": "PRODDB02", "message": "ORA-600 [kghfrf]", "severity": "CRITICAL", "alert_time": "2026-01-15T15:05:00"},
    {"target": "DEVDB01", "message": "ORA-4031: shared pool exhausted", "severity": "WARNING", "alert_time": "2026-01-15T16:00:00"},
]


def test_hypothesis_engine():
    print("=" * 50)
    print("Testing HypothesisEngine")
    print("=" * 50)
    
    engine = HypothesisEngine()
    hypotheses = engine.generate_hypotheses(TEST_ALERTS, target="PRODDB01")
    
    print(f"Generated {len(hypotheses)} hypotheses for PRODDB01:")
    for h in hypotheses[:3]:
        print(f"  - {h.get('pattern')}: {h.get('probability'):.0%}")
        print(f"    Evidence: {h.get('evidence_for', [])[:2]}")
    print()


def test_evidence_collector():
    print("=" * 50)
    print("Testing EvidenceCollector")
    print("=" * 50)
    
    collector = EvidenceCollector()
    hypothesis = {"pattern": "TABLESPACE_EXHAUSTION", "id": "H1"}
    evidence = collector.collect_evidence(hypothesis, TEST_ALERTS, target="PRODDB01")
    
    print(f"Evidence Strength: {evidence.get('evidence_strength')}")
    print(f"Evidence Items: {evidence.get('evidence_count')}")
    for e in evidence.get('evidence_items', [])[:3]:
        print(f"  - {e.get('item')}")
    print()


def test_decision_engine():
    print("=" * 50)
    print("Testing DecisionEngine")
    print("=" * 50)
    
    hyp_engine = HypothesisEngine()
    ev_collector = EvidenceCollector()
    dec_engine = DecisionEngine()
    
    hypotheses = hyp_engine.generate_hypotheses(TEST_ALERTS, target="PRODDB01")
    evidence_packages = {}
    for h in hypotheses[:3]:
        h_id = h.get("id") or h.get("pattern")
        evidence_packages[h_id] = ev_collector.collect_evidence(h, TEST_ALERTS)
    
    decision = dec_engine.make_decision(hypotheses, evidence_packages)
    
    print(f"Decision: {decision.get('decision')}")
    print(f"Confidence: {decision.get('confidence'):.0%}")
    print(f"Certainty: {decision.get('certainty')}")
    print(f"Urgency: {decision.get('action_urgency')}")
    print()


def test_action_recommender():
    print("=" * 50)
    print("Testing ActionRecommender")
    print("=" * 50)
    
    recommender = ActionRecommender()
    decision = {"decision": "TABLESPACE_EXHAUSTION", "action_urgency": "HIGH"}
    
    actions = recommender.recommend(decision, {"target": "PRODDB01"})
    
    print(f"Cause: {actions.get('cause')}")
    print("Immediate Actions:")
    for a in actions.get('immediate_actions', [])[:3]:
        print(f"  - {a.get('action')}")
    print()


def test_pattern_recognizer():
    print("=" * 50)
    print("Testing PatternRecognizer")
    print("=" * 50)
    
    recognizer = PatternRecognizer()
    pattern = recognizer.recognize(TEST_ALERTS, target="PRODDB01")
    
    print(f"Pattern ID: {pattern.get('pattern_id')}")
    print(f"Pattern Name: {pattern.get('pattern_name')}")
    print(f"Confidence: {pattern.get('confidence')}")
    if pattern.get('resolution'):
        print(f"Resolution: {pattern.get('resolution')}")
    print()


def test_risk_predictor():
    print("=" * 50)
    print("Testing RiskPredictor")
    print("=" * 50)
    
    predictor = RiskPredictor()
    predictions = predictor.predict_failures(TEST_ALERTS)
    
    print(f"Total Databases Analyzed: {predictions.get('total_databases')}")
    print("Risk Predictions:")
    for p in predictions.get('predictions', [])[:3]:
        print(f"  - {p.get('database')}: {p.get('risk_level')} (Score: {p.get('risk_score'):.3f})")
        print(f"    Primary Issue: {p.get('primary_issue')}")
    print()


def test_orchestrator():
    print("=" * 50)
    print("Testing ReasoningOrchestrator (Full Pipeline)")
    print("=" * 50)
    
    orchestrator = ReasoningOrchestrator(alerts=TEST_ALERTS)
    result = orchestrator.analyze(target="PRODDB01")
    
    print(f"Target: {result.get('target')}")
    print(f"Alerts Analyzed: {result.get('alert_count')}")
    print(f"Decision: {result.get('decision', {}).get('decision')}")
    print(f"Confidence: {result.get('confidence', {}).get('level')}")
    print(f"Analysis Time: {result.get('analysis_time_seconds')}s")
    print()
    print("Generated Answer:")
    print("-" * 40)
    print(result.get('answer', ''))
    print()


def test_answer_formatter():
    print("=" * 50)
    print("Testing AnswerFormatter")
    print("=" * 50)
    
    answer = AnswerFormatter.format_analysis(
        summary="Analysis for PRODDB01",
        checked=["Analyzed 100 alerts", "Scored 5 hypotheses"],
        findings=["Primary cause: Tablespace Full", "ORA-1653 found 3 times"],
        assessment="Storage capacity critical",
        actions=["Add datafile", "Enable autoextend"],
        stats={"alerts": 100, "databases": 1}
    )
    print(answer)
    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("REASONING MODULE TESTS")
    print("=" * 60 + "\n")
    
    test_hypothesis_engine()
    test_evidence_collector()
    test_decision_engine()
    test_action_recommender()
    test_pattern_recognizer()
    test_risk_predictor()
    test_answer_formatter()
    test_orchestrator()
    
    print("=" * 60)
    print("ALL TESTS COMPLETED!")
    print("=" * 60)
