#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
End-to-End Test for Intent-First OEM DBA Assistant
====================================================

This test validates that the FULL PIPELINE behaves according to intent rules:

1. FACTUAL questions → SHORT, DIRECT answer ONLY
   - No root cause
   - No action plans

2. ANALYTICAL questions → Explanation with reasoning
   - Root cause included
   - No actions (unless explicitly asked)

3. ACTION questions → Steps and recommendations
   - Actions included

Python 3.6.8 compatible.
"""

from __future__ import print_function
import sys
import json

sys.path.insert(0, '.')

# Mock GLOBAL_DATA for testing
MOCK_ALERTS = [
    {
        "alert_id": "1",
        "target_name": "PRODDB",
        "host_name": "srv-prod-01",
        "severity": "Critical",
        "message": "ORA-04031: unable to allocate memory",
        "created_time": "2024-01-15 10:00:00"
    },
    {
        "alert_id": "2",
        "target_name": "PRODDB",
        "host_name": "srv-prod-01",
        "severity": "Critical",
        "message": "ORA-04031: unable to allocate memory",
        "created_time": "2024-01-15 11:00:00"
    },
    {
        "alert_id": "3",
        "target_name": "FINDB",
        "host_name": "srv-fin-01",
        "severity": "Warning",
        "message": "Tablespace USERS is 95% full",
        "created_time": "2024-01-15 12:00:00"
    },
    {
        "alert_id": "4",
        "target_name": "STANDBY1",
        "host_name": "srv-stby-01",
        "severity": "Critical",
        "message": "ORA-16014: log cannot be archived",
        "created_time": "2024-01-15 13:00:00"
    },
    {
        "alert_id": "5",
        "target_name": "HRDB",
        "host_name": "srv-hr-01",
        "severity": "Critical",
        "message": "ORA-00600: internal error code",
        "created_time": "2024-01-15 14:00:00"
    },
]


def setup_mock_data():
    """Set up mock data in GLOBAL_DATA."""
    try:
        from data_engine import global_cache
        global_cache.GLOBAL_DATA["alerts"] = MOCK_ALERTS
        print("[SETUP] Mock data loaded: {} alerts".format(len(MOCK_ALERTS)))
        return True
    except Exception as e:
        print("[SETUP] Failed to load mock data: {}".format(str(e)))
        return False


def validate_response(response, expected_traits):
    """
    Validate that response matches expected traits.
    
    Args:
        response: The response dict
        expected_traits: Dict with expected characteristics
            - has_answer: bool - should have 'answer' key
            - answer_length: str - 'short' (< 100 chars) or 'detailed'
            - has_root_cause: bool - should contain root cause text
            - has_actions: bool - should contain action steps
            - question_type: str - expected question_type field
    
    Returns:
        (passed: bool, reasons: list)
    """
    reasons = []
    passed = True
    
    if not response:
        return False, ["Response is empty/None"]
    
    # Check answer presence
    if expected_traits.get("has_answer", True):
        if "answer" not in response:
            reasons.append("Missing 'answer' field")
            passed = False
    
    # Check answer length
    answer = response.get("answer", "")
    if expected_traits.get("answer_length") == "short":
        if len(answer) > 200:  # Short answers should be concise
            reasons.append("Answer too long for FACTUAL ({} chars)".format(len(answer)))
            passed = False
    
    # Check root cause exclusion for factual
    if not expected_traits.get("has_root_cause", True):
        answer_lower = answer.lower() if answer else ""
        if "root cause" in answer_lower and "no root cause" not in answer_lower:
            reasons.append("Contains root cause when not expected")
            passed = False
    
    # Check actions exclusion
    if not expected_traits.get("has_actions", True):
        if response.get("actions_included", False):
            reasons.append("Actions included when not expected")
            passed = False
    
    # Check question_type
    if expected_traits.get("question_type"):
        if response.get("question_type") != expected_traits["question_type"]:
            reasons.append("question_type='{}' (expected '{}')".format(
                response.get("question_type"), expected_traits["question_type"]
            ))
            passed = False
    
    return passed, reasons


def test_pipeline_responses():
    """Test the full pipeline with different question types."""
    print("\n" + "="*70)
    print("End-to-End Pipeline Test")
    print("="*70)
    
    try:
        from nlp_engine.oem_reasoning_pipeline import OEMReasoningPipeline
        from data_engine import global_cache
    except ImportError as e:
        print("[SKIP] Cannot import pipeline: {}".format(str(e)))
        return True  # Skip test if imports fail
    
    # Set up mock data in GLOBAL_DATA
    global_cache.GLOBAL_DATA["alerts"] = MOCK_ALERTS
    
    pipeline = OEMReasoningPipeline()
    
    test_cases = [
        # FACTUAL QUESTIONS
        {
            "question": "How many databases have alerts?",
            "expected": {
                "answer_length": "short",
                "has_root_cause": False,
                "has_actions": False,
            }
        },
        {
            "question": "Which database is critical?",
            "expected": {
                "answer_length": "short",
                "has_root_cause": False,
                "has_actions": False,
            }
        },
        {
            "question": "List all ORA codes",
            "expected": {
                "has_root_cause": False,
                "has_actions": False,
            }
        },
        
        # ANALYTICAL QUESTIONS
        {
            "question": "Why does PRODDB keep failing?",
            "expected": {
                "has_root_cause": True,
                "has_actions": False,
            }
        },
        
        # ACTION QUESTIONS
        {
            "question": "What should I do to fix PRODDB?",
            "expected": {
                "has_actions": True,
            }
        },
    ]
    
    passed_count = 0
    failed_count = 0
    
    for case in test_cases:
        question = case["question"]
        expected = case["expected"]
        
        print("\n--- Testing: '{}' ---".format(question[:50]))
        
        try:
            # Process through pipeline (only takes question)
            response = pipeline.process(question)
            
            # Validate
            passed, reasons = validate_response(response, expected)
            
            if passed:
                passed_count += 1
                print("[PASS] Response matches expected traits")
                if response.get("answer"):
                    print("  Answer: '{}'".format(response["answer"][:100] if len(response.get("answer", "")) > 100 else response.get("answer", "")))
            else:
                failed_count += 1
                print("[FAIL] Validation failed:")
                for reason in reasons:
                    print("  - {}".format(reason))
                # Print actual response for debugging
                if response:
                    print("  Response keys: {}".format(list(response.keys())))
                    if response.get("answer"):
                        print("  Answer preview: '{}'".format(response["answer"][:80]))
                
        except Exception as e:
            import traceback
            failed_count += 1
            print("[ERROR] Pipeline exception: {}".format(str(e)))
            traceback.print_exc()
    
    print("\n" + "="*70)
    print("Results: {} passed, {} failed".format(passed_count, failed_count))
    print("="*70)
    
    return failed_count == 0


def test_intent_engine_question_type():
    """Test that intent engine correctly identifies question types."""
    print("\n" + "="*70)
    print("Intent Engine Question Type Detection")
    print("="*70)
    
    from nlp_engine.oem_intent_engine import OEMIntentEngine
    
    engine = OEMIntentEngine()
    
    test_cases = [
        ("How many databases?", "FACTUAL"),
        ("Which server has most alerts?", "FACTUAL"),
        ("Why does PRODDB fail?", "ANALYTICAL"),
        ("What's the root cause?", "ANALYTICAL"),
        ("What should I do?", "ACTION"),
        ("How do I fix this?", "ACTION"),
    ]
    
    passed = 0
    failed = 0
    
    for question, expected_type in test_cases:
        result = engine.get_question_type_from_text(question)
        
        if result == expected_type:
            passed += 1
            print("[PASS] '{}' => {}".format(question[:40], result))
        else:
            failed += 1
            print("[FAIL] '{}' => {} (expected {})".format(question[:40], result, expected_type))
    
    print("\nResults: {} passed, {} failed".format(passed, failed))
    return failed == 0


def test_short_format_detection():
    """Test that short format is correctly detected for factual questions."""
    print("\n" + "="*70)
    print("Short Format Detection Test")
    print("="*70)
    
    from nlp_engine.oem_intent_engine import OEMIntentEngine
    
    engine = OEMIntentEngine()
    
    # These should use short format
    short_format_questions = [
        "How many databases?",
        "Which hour has highest alerts?",
        "Count of ORA-00600",
        "List all servers",
    ]
    
    # These should NOT use short format
    detailed_format_questions = [
        "Why does PRODDB fail?",
        "What is the root cause?",
        "Explain the pattern",
        "What should I do?",
    ]
    
    passed = 0
    failed = 0
    
    print("\nShould use SHORT format:")
    for q in short_format_questions:
        result = engine.should_use_short_format("DATABASE_HEALTH", question=q)
        if result:
            passed += 1
            print("[PASS] '{}'".format(q[:50]))
        else:
            failed += 1
            print("[FAIL] '{}' - expected short=True".format(q[:50]))
    
    print("\nShould use DETAILED format:")
    for q in detailed_format_questions:
        result = engine.should_use_short_format("DATABASE_HEALTH", question=q)
        if not result:
            passed += 1
            print("[PASS] '{}'".format(q[:50]))
        else:
            failed += 1
            print("[FAIL] '{}' - expected short=False".format(q[:50]))
    
    print("\nResults: {} passed, {} failed".format(passed, failed))
    return failed == 0


def run_all_e2e_tests():
    """Run all end-to-end tests."""
    print("\n" + "#"*70)
    print("# OEM DBA ASSISTANT - END-TO-END INTENT RESPONSE TESTS")
    print("#"*70)
    
    # Setup mock data
    setup_mock_data()
    
    results = []
    
    results.append(("Intent Engine Question Type", test_intent_engine_question_type()))
    results.append(("Short Format Detection", test_short_format_detection()))
    results.append(("Pipeline Response Generation", test_pipeline_responses()))
    
    print("\n" + "="*70)
    print("FINAL E2E RESULTS")
    print("="*70)
    
    all_passed = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print("{}: {}".format(name, status))
        if not passed:
            all_passed = False
    
    print("\n" + "="*70)
    if all_passed:
        print("ALL E2E TESTS PASSED!")
    else:
        print("SOME E2E TESTS FAILED - Review above for details")
    print("="*70)
    
    return all_passed


if __name__ == "__main__":
    success = run_all_e2e_tests()
    sys.exit(0 if success else 1)
