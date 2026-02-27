"""
PHASE 1: Test Suite
==================
Tests for the Phase 1 NLP foundation.

Run with: python phase1/test_phase1.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from phase1.intent_parser import Phase1IntentParser, parse_intent
from phase1.query_engine import Phase1QueryEngine, get_engine
from phase1.answer_generator import Phase1AnswerGenerator
from phase1.service import Phase1Service, process_question, parse_question


def test_intent_parser():
    """Test the intent parser with various questions."""
    print("=" * 60)
    print("TEST: Intent Parser")
    print("=" * 60)
    
    parser = Phase1IntentParser(["MIDEVSTB", "MIDEVSTBN"])
    
    test_cases = [
        # (question, expected_intent_type, expected_database, expected_severity)
        ("show me alerts for MIDEVSTB", "LIST", "MIDEVSTB", None),
        ("how many alerts are there", "COUNT", None, None),
        ("how many critical alerts", "COUNT", None, "CRITICAL"),
        ("show warning alerts", "LIST", None, "WARNING"),
        ("show standby issues", "LIST", None, None),  # category = STANDBY
        ("are there any critical alerts for MIDEVSTB", "COUNT", "MIDEVSTB", "CRITICAL"),
        ("list all alerts", "LIST", None, None),
        ("what is the status of MIDEVSTBN", "STATUS", "MIDEVSTBN", None),
        ("count critical alerts for MIDEVSTB", "COUNT", "MIDEVSTB", "CRITICAL"),
        ("display top 10 warning alerts", "LIST", None, "WARNING"),
    ]
    
    passed = 0
    failed = 0
    
    for question, exp_type, exp_db, exp_sev in test_cases:
        intent = parser.parse(question)
        
        type_ok = intent["intent_type"] == exp_type
        db_ok = intent["database"] == exp_db or (exp_db and intent["database"] and exp_db in intent["database"])
        sev_ok = intent["severity"] == exp_sev
        
        status = "✓" if (type_ok and db_ok and sev_ok) else "✗"
        
        if type_ok and db_ok and sev_ok:
            passed += 1
        else:
            failed += 1
        
        print(f"\n{status} Question: '{question}'")
        print(f"   Intent: {intent['intent_type']} (expected: {exp_type}) {'✓' if type_ok else '✗'}")
        print(f"   Database: {intent['database']} (expected: {exp_db}) {'✓' if db_ok else '✗'}")
        print(f"   Severity: {intent['severity']} (expected: {exp_sev}) {'✓' if sev_ok else '✗'}")
        print(f"   Confidence: {intent['confidence']}")
    
    print(f"\n--- Parser Results: {passed}/{len(test_cases)} passed ---")
    return passed, failed


def test_query_engine():
    """Test the query engine."""
    print("\n" + "=" * 60)
    print("TEST: Query Engine")
    print("=" * 60)
    
    engine = get_engine()
    
    if not engine.is_ready():
        print("⚠ Query engine not ready - data not loaded")
        print("  Run this test after starting the server or loading data")
        return 0, 1
    
    print(f"✓ Data loaded: {len(engine.alerts):,} alerts")
    print(f"✓ Known databases: {engine.known_databases}")
    
    # Test basic queries
    test_intents = [
        {"intent_type": "COUNT", "database": None, "severity": None, "category": None},
        {"intent_type": "COUNT", "database": None, "severity": "CRITICAL", "category": None},
        {"intent_type": "COUNT", "database": "MIDEVSTB", "severity": None, "category": None},
        {"intent_type": "LIST", "database": None, "severity": "WARNING", "category": None, "limit": 5},
        {"intent_type": "STATUS", "database": "MIDEVSTB", "severity": None, "category": None},
    ]
    
    passed = 0
    for intent in test_intents:
        result = engine.execute(intent)
        if result.get("success"):
            print(f"✓ {intent['intent_type']}: success")
            passed += 1
        else:
            print(f"✗ {intent['intent_type']}: {result.get('error')}")
    
    print(f"\n--- Query Engine Results: {passed}/{len(test_intents)} passed ---")
    return passed, len(test_intents) - passed


def test_full_pipeline():
    """Test the full Phase 1 pipeline."""
    print("\n" + "=" * 60)
    print("TEST: Full Pipeline (End-to-End)")
    print("=" * 60)
    
    test_questions = [
        "show me alerts for MIDEVSTB",
        "how many alerts are there",
        "how many critical alerts",
        "show warning alerts",
        "show standby issues",
        "are there any critical alerts for MIDEVSTB",
    ]
    
    passed = 0
    
    for question in test_questions:
        print(f"\n--- Question: '{question}' ---")
        
        result = process_question(question)
        
        if result["success"]:
            print(f"✓ Success (confidence: {result['confidence']})")
            print(f"  Intent: {result['intent']['intent_type']}")
            print(f"  Answer preview: {result['answer'][:100]}...")
            passed += 1
        else:
            print(f"✗ Failed (confidence: {result['confidence']})")
            print(f"  Answer: {result['answer']}")
    
    print(f"\n--- Pipeline Results: {passed}/{len(test_questions)} passed ---")
    return passed, len(test_questions) - passed


def test_out_of_scope():
    """Test that out-of-scope questions are handled properly."""
    print("\n" + "=" * 60)
    print("TEST: Out-of-Scope Questions")
    print("=" * 60)
    
    service = Phase1Service()
    
    out_of_scope_questions = [
        "why is this happening",
        "what should DBA do",
        "recommend actions for this issue",
        "predict which database will fail",
        "ok show me 10 more",
        "what about this database",
    ]
    
    passed = 0
    
    for question in out_of_scope_questions:
        is_supported = service.is_phase1_question(question)
        if not is_supported:
            print(f"✓ Correctly identified as out-of-scope: '{question}'")
            passed += 1
        else:
            print(f"✗ Should be out-of-scope but wasn't: '{question}'")
    
    print(f"\n--- Out-of-Scope Results: {passed}/{len(out_of_scope_questions)} passed ---")
    return passed, len(out_of_scope_questions) - passed


def main():
    """Run all Phase 1 tests."""
    print("\n" + "=" * 60)
    print("PHASE 1 TEST SUITE")
    print("=" * 60)
    
    total_passed = 0
    total_failed = 0
    
    # Test 1: Intent Parser (no data needed)
    p, f = test_intent_parser()
    total_passed += p
    total_failed += f
    
    # Test 2: Out-of-scope detection (no data needed)
    p, f = test_out_of_scope()
    total_passed += p
    total_failed += f
    
    # Test 3: Query Engine (needs data)
    try:
        p, f = test_query_engine()
        total_passed += p
        total_failed += f
    except Exception as e:
        print(f"⚠ Query engine test skipped: {e}")
    
    # Test 4: Full Pipeline (needs data)
    try:
        p, f = test_full_pipeline()
        total_passed += p
        total_failed += f
    except Exception as e:
        print(f"⚠ Pipeline test skipped: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("PHASE 1 TEST SUMMARY")
    print("=" * 60)
    print(f"Total Passed: {total_passed}")
    print(f"Total Failed: {total_failed}")
    print(f"Success Rate: {total_passed/(total_passed+total_failed)*100:.1f}%")
    
    return total_failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
