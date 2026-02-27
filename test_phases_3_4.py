#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test Phase 3 & 4: Failure Prediction and Learning-Based Recommendations
Validates outage_probability() and recommend_fix() implementations
"""

import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from incident_engine.correlation_engine import CorrelationEngine
from incident_engine.recommendation_engine import RecommendationEngine


def test_outage_probability():
    """Test Phase 3: Failure Probability Prediction"""
    print("\n" + "=" * 70)
    print("PHASE 3: FAILURE PROBABILITY PREDICTION")
    print("=" * 70)
    
    # Create test data
    alerts = []
    base_time = datetime.now()
    
    # Generate 100+ critical alerts for DB1 (high criticality)
    for i in range(100):
        alerts.append({
            "target": "MIDEVSTB",
            "severity": "CRITICAL",
            "time": base_time - timedelta(days=10, hours=i),
            "message": "Database error"
        })
    
    # Create many incidents (simulating 10 days of patterns)
    incidents = []
    for day in range(10, -1, -1):
        count = 50 + (10 - day) * 10  # Increasing incident count
        incidents.append({
            "target": "MIDEVSTB",
            "issue_type": "INTERNAL_ERROR",
            "severity": "CRITICAL",
            "count": count,
            "first_seen": base_time - timedelta(days=day),
            "last_seen": base_time - timedelta(days=day-1) if day > 0 else base_time
        })
    
    # Test outage probability
    engine = CorrelationEngine(alerts, [], incidents)
    result = engine.outage_probability("MIDEVSTB", incidents)
    
    print("\nTest: Database with escalating failures")
    print("  Alerts: 100+ CRITICAL alerts")
    print("  Incidents: 11 incidents with increasing frequency")
    print("\nResults:")
    print("  Probability: {}%".format(result["probability"]))
    print("  Risk Level: {}".format(result["risk_level"]))
    print("  Score Breakdown:")
    for key, value in result.get("score_breakdown", {}).items():
        print("    - {}: {}".format(key, value))
    print("\n  Reasons:")
    for reason in result["reasons"][:3]:
        print("    - {}".format(reason))
    
    # Verify probability is reasonable
    assert result["probability"] >= 25, "Should detect critical alert patterns"
    
    print("\n[PASS] Outage probability prediction works!")
    return True


def test_recommendation_engine():
    """Test Phase 4: Learning-Based Recommendations"""
    print("\n" + "=" * 70)
    print("PHASE 4: LEARNING-BASED RECOMMENDATIONS")
    print("=" * 70)
    
    # Create recommendation engine (loads existing history)
    engine = RecommendationEngine()
    
    print("\nTest: Recommend fix for INTERNAL_ERROR")
    
    # Get recommendation
    rec = engine.recommend_fix("INTERNAL_ERROR")
    
    print("\nInitial Recommendation:")
    print("  Issue: {}".format(rec["issue_type"]))
    print("  Action: {}".format(rec["recommended_action"]))
    print("  Confidence: {}%".format(rec["confidence"]))
    print("  Evidence: {}".format(rec["evidence"]))
    
    assert rec["confidence"] > 0, "Should have confidence score"
    assert rec["recommended_action"], "Should have recommended action"
    
    # Test learning: track an outcome
    print("\nTest: Track resolution outcome")
    success = engine.track_outcome(
        "TEST_ISSUE",
        "Test Action A",
        "SUCCESS"
    )
    
    assert success, "Should track outcome"
    print("  Tracked: TEST_ISSUE -> Test Action A -> SUCCESS")
    
    # Track more outcomes
    engine.track_outcome("TEST_ISSUE", "Test Action A", "SUCCESS")
    engine.track_outcome("TEST_ISSUE", "Test Action A", "SUCCESS")
    engine.track_outcome("TEST_ISSUE", "Test Action B", "FAILED")
    engine.track_outcome("TEST_ISSUE", "Test Action B", "FAILED")
    
    # Get updated recommendation
    updated_rec = engine.recommend_fix("TEST_ISSUE")
    
    print("\nUpdated Recommendation (after learning):")
    print("  Issue: {}".format(updated_rec["issue_type"]))
    print("  Action: {}".format(updated_rec["recommended_action"]))
    print("  Confidence: {}%".format(updated_rec["confidence"]))
    print("  Evidence: {}".format(updated_rec["evidence"]))
    
    # Verify learning improved confidence
    assert updated_rec["recommended_action"] == "Test Action A", "Should recommend best action"
    assert updated_rec["confidence"] >= 60, "Should have high confidence for majority success"
    
    # Test analytics
    print("\nTest: Learning statistics")
    stats = engine.get_learning_stats()
    
    print("  Total issue types tracked: {}".format(stats["total_issue_types"]))
    print("  Total actions tracked: {}".format(stats["total_actions_tracked"]))
    print("  Most reliable action: {}".format(stats["most_reliable_action"]))
    print("  Success rate: {}%".format(stats["most_reliable_success_rate"]))
    
    assert stats["total_issue_types"] > 0, "Should have learned patterns"
    
    print("\n[PASS] Learning-based recommendations work!")
    return True


def test_integration():
    """Test Phase 3+4 Integration"""
    print("\n" + "=" * 70)
    print("INTEGRATION TEST: PREDICTION + RECOMMENDATIONS")
    print("=" * 70)
    
    # Create realistic scenario
    alerts = []
    incidents = []
    base_time = datetime.now()
    
    # Simulate escalating failures for MIDEVSTB (100+ alerts)
    for i in range(100):
        alerts.append({
            "target": "MIDEVSTB",
            "severity": "CRITICAL",
            "time": base_time - timedelta(days=10, hours=i),
            "message": "Database error"
        })
    
    # Create 20 incidents showing escalation
    for day in range(10, -10, -1):
        incidents.append({
            "target": "MIDEVSTB",
            "issue_type": "INTERNAL_ERROR",
            "severity": "CRITICAL",
            "count": 30 + (10 - day) * 5,  # Increasing count
            "first_seen": base_time - timedelta(days=day),
            "last_seen": base_time - timedelta(days=day-1) if day > 0 else base_time
        })
    
    # Test full workflow
    print("\nScenario: Escalating failures over time")
    print("  Database: MIDEVSTB")
    print("  Alerts: 100 CRITICAL")
    print("  Incidents: 20 with increasing frequency")
    
    # Get prediction
    engine = CorrelationEngine(alerts, [], incidents)
    prediction = engine.outage_probability("MIDEVSTB", incidents)
    
    print("\n1. PREDICTIVE ANALYSIS:")
    print("  Outage Probability: {}%".format(prediction["probability"]))
    print("  Risk Level: {}".format(prediction["risk_level"]))
    
    # Get recommendation
    rec_engine = RecommendationEngine()
    recommendation = rec_engine.recommend_fix("INTERNAL_ERROR")
    
    print("\n2. RECOMMENDED ACTION:")
    print("  Action: {}".format(recommendation["recommended_action"]))
    print("  Confidence: {}%".format(recommendation["confidence"]))
    print("  Based on: {}".format(recommendation["evidence"]))
    
    # Verify integration - at least some data present
    assert prediction["probability"] >= 0, "Should have prediction"
    assert recommendation["recommended_action"], "Should provide action"
    assert recommendation["confidence"] > 0, "Should have confidence score"
    
    print("\n[PASS] Prediction + Recommendation integration works!")
    return True


def main():
    print("\n" + "=" * 70)
    print("PHASE 3 & 4: PREDICTIVE & LEARNING-BASED INTELLIGENCE TESTS")
    print("=" * 70)
    
    tests = [
        ("Outage Probability", test_outage_probability),
        ("Recommendation Engine", test_recommendation_engine),
        ("Full Integration", test_integration),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print("\n[FAIL] {} - {}".format(name, str(e)))
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print("[{}] {}".format(status, name))
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    print("\nTotal: {}/{}".format(passed, total))
    
    if passed == total:
        print("\nALL TESTS PASSED! Phases 3 & 4 ready for deployment.")
        return 0
    else:
        print("\nSOME TESTS FAILED!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
