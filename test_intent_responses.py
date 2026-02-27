#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test Intent-First Response Behavior
====================================
Tests that the OEM DBA Assistant answers questions according to intent:

FACTUAL questions → SHORT, DIRECT answer ONLY
ANALYTICAL questions → Explanation with reasoning (no actions unless asked)
ACTION questions → Actions ONLY when explicitly asked
"""

from __future__ import print_function
import sys
import json

# Add parent to path
sys.path.insert(0, '.')

def test_intent_response_router():
    """Test the IntentResponseRouter class."""
    print("\n" + "="*60)
    print("Testing IntentResponseRouter")
    print("="*60)
    
    from nlp_engine.intent_response_router import IntentResponseRouter
    
    router = IntentResponseRouter()
    
    # Test cases: (question, expected_type)
    test_cases = [
        # FACTUAL - should return "FACTUAL"
        ("How many databases have alerts?", "FACTUAL"),
        ("Which server has the most errors?", "FACTUAL"),
        ("What hour had the highest alert count?", "FACTUAL"),
        ("List all databases with critical status", "FACTUAL"),
        ("Count of ORA-00600 errors", "FACTUAL"),
        ("How many tablespace alerts?", "FACTUAL"),
        ("Which database is critical?", "FACTUAL"),
        
        # ANALYTICAL - should return "ANALYTICAL"  
        ("Why does PRODDB keep failing?", "ANALYTICAL"),
        ("What's causing the ORA-04031 errors?", "ANALYTICAL"),
        ("Explain the pattern of failures", "ANALYTICAL"),
        ("What is the root cause of FINDB issues?", "ANALYTICAL"),
        ("Analyze the trend of alerts this week", "ANALYTICAL"),
        
        # ACTION - should return "ACTION"
        ("What should I do to fix PRODDB?", "ACTION"),
        ("How do I resolve ORA-00600?", "ACTION"),
        ("Give me steps to fix the tablespace issue", "ACTION"),
        ("What actions should I take?", "ACTION"),
        ("Recommend a solution for HRDB", "ACTION"),
    ]
    
    passed = 0
    failed = 0
    
    for question, expected in test_cases:
        result = router.get_question_type(question)
        status = "PASS" if result == expected else "FAIL"
        
        if result == expected:
            passed += 1
            print("[PASS] '{}' => {}".format(question[:40], result))
        else:
            failed += 1
            print("[FAIL] '{}' => {} (expected {})".format(question[:40], result, expected))
    
    print("\n--- Results: {} passed, {} failed ---".format(passed, failed))
    return failed == 0


def test_should_include_methods():
    """Test the should_include_root_cause and should_include_actions methods."""
    print("\n" + "="*60)
    print("Testing should_include_root_cause and should_include_actions")
    print("="*60)
    
    from nlp_engine.intent_response_router import IntentResponseRouter
    
    router = IntentResponseRouter()
    
    # Questions that should NOT include root cause
    no_root_cause_questions = [
        "How many databases?",
        "Which hour has most alerts?",
        "List all servers",
        "Count of tablespace errors",
        "What's the alert count?",
    ]
    
    # Questions that SHOULD include root cause
    root_cause_questions = [
        "Why does PRODDB fail?",
        "What's causing the errors?",
        "Root cause analysis for FINDB",
        "Explain the failures",
    ]
    
    passed = 0
    failed = 0
    
    print("\nTesting questions that should NOT include root cause:")
    for q in no_root_cause_questions:
        result = router.should_include_root_cause(q)
        if not result:
            passed += 1
            print("[PASS] '{}' => should_include_root_cause=False".format(q[:40]))
        else:
            failed += 1
            print("[FAIL] '{}' => should_include_root_cause=True (expected False)".format(q[:40]))
    
    print("\nTesting questions that SHOULD include root cause:")
    for q in root_cause_questions:
        result = router.should_include_root_cause(q)
        if result:
            passed += 1
            print("[PASS] '{}' => should_include_root_cause=True".format(q[:40]))
        else:
            failed += 1
            print("[FAIL] '{}' => should_include_root_cause=False (expected True)".format(q[:40]))
    
    # Test should_include_actions
    no_actions_questions = [
        "How many databases?",
        "Why does PRODDB fail?",  # Analytical - no actions
        "What's the root cause?",
    ]
    
    actions_questions = [
        "What should I do?",
        "How do I fix this?",
        "Give me steps to resolve",
        "Recommend actions",
    ]
    
    print("\nTesting questions that should NOT include actions:")
    for q in no_actions_questions:
        result = router.should_include_actions(q)
        if not result:
            passed += 1
            print("[PASS] '{}' => should_include_actions=False".format(q[:40]))
        else:
            failed += 1
            print("[FAIL] '{}' => should_include_actions=True (expected False)".format(q[:40]))
    
    print("\nTesting questions that SHOULD include actions:")
    for q in actions_questions:
        result = router.should_include_actions(q)
        if result:
            passed += 1
            print("[PASS] '{}' => should_include_actions=True".format(q[:40]))
        else:
            failed += 1
            print("[FAIL] '{}' => should_include_actions=False (expected True)".format(q[:40]))
    
    print("\n--- Results: {} passed, {} failed ---".format(passed, failed))
    return failed == 0


def test_oem_intent_engine_integration():
    """Test that OEMIntentEngine uses the new methods correctly."""
    print("\n" + "="*60)
    print("Testing OEMIntentEngine Integration")
    print("="*60)
    
    from nlp_engine.oem_intent_engine import OEMIntentEngine
    
    engine = OEMIntentEngine()
    
    passed = 0
    failed = 0
    
    # Test get_question_type_from_text
    test_cases = [
        ("How many alerts?", "FACTUAL"),
        ("Why the failures?", "ANALYTICAL"),
        ("What should I do?", "ACTION"),
    ]
    
    print("\nTesting get_question_type_from_text:")
    for question, expected in test_cases:
        result = engine.get_question_type_from_text(question)
        if result == expected:
            passed += 1
            print("[PASS] '{}' => {}".format(question, result))
        else:
            failed += 1
            print("[FAIL] '{}' => {} (expected {})".format(question, result, expected))
    
    # Test should_use_short_format with question
    print("\nTesting should_use_short_format:")
    short_format_cases = [
        ("How many databases?", True),
        ("Why does it fail?", False),
        ("What should I do?", False),
    ]
    
    for question, expected in short_format_cases:
        # Pass a generic intent and let the question override
        result = engine.should_use_short_format("DATABASE_HEALTH", question=question)
        if result == expected:
            passed += 1
            print("[PASS] '{}' => short_format={}".format(question, result))
        else:
            failed += 1
            print("[FAIL] '{}' => short_format={} (expected {})".format(question, result, expected))
    
    print("\n--- Results: {} passed, {} failed ---".format(passed, failed))
    return failed == 0


def test_response_format_check():
    """Test that response format is correct for different question types."""
    print("\n" + "="*60)
    print("Testing Response Format Structure")
    print("="*60)
    
    from nlp_engine.intent_response_router import IntentResponseRouter
    
    router = IntentResponseRouter()
    
    # Test get_response_format - check key attributes
    test_cases = [
        ("How many alerts?", {"include_root_cause": False, "include_actions": False}),
        ("Why failures?", {"include_root_cause": True, "include_actions": False}),
        ("What should I do?", {"include_actions": True}),
    ]
    
    passed = 0
    failed = 0
    
    for question, expected in test_cases:
        result = router.get_response_format(question)
        
        all_match = True
        for key, val in expected.items():
            if result.get(key) != val:
                all_match = False
                break
        
        if all_match:
            passed += 1
            print("[PASS] '{}' => format correct".format(question))
        else:
            failed += 1
            print("[FAIL] '{}' => {} (expected {})".format(question, result, expected))
    
    print("\n--- Results: {} passed, {} failed ---".format(passed, failed))
    return failed == 0


def run_all_tests():
    """Run all tests."""
    print("\n" + "#"*60)
    print("# OEM DBA ASSISTANT - Intent-First Response Tests")
    print("#"*60)
    
    results = []
    
    results.append(("IntentResponseRouter", test_intent_response_router()))
    results.append(("should_include methods", test_should_include_methods()))
    results.append(("OEMIntentEngine Integration", test_oem_intent_engine_integration()))
    results.append(("Response Format Structure", test_response_format_check()))
    
    print("\n" + "="*60)
    print("FINAL RESULTS")
    print("="*60)
    
    all_passed = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print("{}: {}".format(name, status))
        if not passed:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("ALL TESTS PASSED!")
    else:
        print("SOME TESTS FAILED - Review above for details")
    print("="*60)
    
    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
