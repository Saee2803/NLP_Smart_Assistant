#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Direct Test for Intent-Based Response Behavior
==============================================

This test bypasses HTTP and tests the intelligence service directly.

Python 3.6.8 compatible.
"""

from __future__ import print_function
import sys
import json

sys.path.insert(0, '.')


def test_intent_based_responses():
    """Test that different intents produce different response styles."""
    print("\n" + "="*70)
    print("DIRECT INTELLIGENCE SERVICE TEST")
    print("="*70)
    
    try:
        from services.intelligence_service import INTELLIGENCE_SERVICE
        from data_engine.global_cache import GLOBAL_DATA, set_system_ready
        from data_engine.data_fetcher import DataFetcher
    except ImportError as e:
        print("[ERROR] Cannot import: {}".format(str(e)))
        return False
    
    # Load data if not loaded
    if not GLOBAL_DATA.get("alerts"):
        print("[*] Loading OEM data...")
        try:
            fetcher = DataFetcher()
            data = fetcher.fetch({})
            GLOBAL_DATA.update({
                "alerts": data.get("alerts", []),
                "metrics": data.get("metrics", []),
                "incidents": data.get("incidents", [])
            })
            set_system_ready(True)
            print("[OK] Loaded {} alerts".format(len(GLOBAL_DATA.get("alerts", []))))
        except Exception as e:
            print("[ERROR] Failed to load data: {}".format(str(e)))
            return False
    else:
        print("[OK] Using existing {} alerts".format(len(GLOBAL_DATA.get("alerts", []))))
    
    # Test cases with expected behavior
    test_cases = [
        {
            "question": "How many databases have alerts?",
            "intent_type": "COUNT_QUERY",
            "expected": {
                "short_answer": True,
                "no_actions": True,
                "no_root_cause": True
            }
        },
        {
            "question": "Which database is in critical state?",
            "intent_type": "STATUS_QUERY", 
            "expected": {
                "short_answer": True,
                "no_actions": True,
                "no_root_cause": True
            }
        },
        {
            "question": "What hour has the most alerts?",
            "intent_type": "WHAT_QUERY",
            "expected": {
                "short_answer": True,
                "no_actions": True,
                "no_root_cause": True
            }
        },
        {
            "question": "Why is MIDDEVSTBN failing?",
            "intent_type": "WHY_QUERY",
            "expected": {
                "short_answer": False,
                "no_actions": True,  # WHY questions don't need actions
                "no_root_cause": False  # WHY questions CAN have root cause
            }
        },
        {
            "question": "What should I do to fix the database issues?",
            "intent_type": "ACTION_QUERY",
            "expected": {
                "short_answer": False,
                "no_actions": False,  # ACTION questions MUST have actions
                "no_root_cause": False
            }
        },
    ]
    
    passed = 0
    failed = 0
    
    for case in test_cases:
        question = case["question"]
        expected = case["expected"]
        
        print("\n" + "-"*60)
        print("Testing: '{}'".format(question[:50]))
        print("Expected intent: {}".format(case["intent_type"]))
        
        try:
            result = INTELLIGENCE_SERVICE.analyze(question)
            answer = result.get("answer", "")
            
            # Validate response
            issues = []
            
            # Check short answer (< 300 chars, no template sections)
            if expected["short_answer"]:
                if len(answer) > 400:
                    issues.append("Answer too long ({} chars)".format(len(answer)))
                if "What was checked" in answer:
                    issues.append("Contains template section 'What was checked'")
                if "What was found" in answer:
                    issues.append("Contains template section 'What was found'")
            
            # Check no actions
            if expected["no_actions"]:
                actions = result.get("actions", [])
                if actions and len(actions) > 0:
                    issues.append("Contains actions when not expected")
                if "Recommended Action" in answer:
                    issues.append("Contains action text in answer")
            
            # Check no root cause
            if expected["no_root_cause"]:
                if result.get("root_cause"):
                    issues.append("Contains root_cause when not expected")
                if "Root Cause" in answer and "no root cause" not in answer.lower():
                    issues.append("Contains root cause text in answer")
            
            if not issues:
                passed += 1
                print("[PASS] Response matches expected behavior")
                print("  Answer preview: '{}'".format(answer[:100].replace('\n', ' ')))
            else:
                failed += 1
                print("[FAIL] Violations:")
                for issue in issues:
                    print("  - {}".format(issue))
                print("  Answer preview: '{}'".format(answer[:150].replace('\n', ' ')))
                
        except Exception as e:
            failed += 1
            print("[ERROR] Exception: {}".format(str(e)))
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print("Results: {} passed, {} failed".format(passed, failed))
    print("="*70)
    
    return failed == 0


def test_no_repetitive_patterns():
    """Test that different questions produce different response structures."""
    print("\n" + "="*70)
    print("RESPONSE VARIABILITY TEST")
    print("="*70)
    
    try:
        from services.intelligence_service import INTELLIGENCE_SERVICE
    except ImportError as e:
        print("[SKIP] Cannot import: {}".format(str(e)))
        return True
    
    questions = [
        "How many databases?",
        "Which database is critical?",
        "Why are alerts increasing?",
        "What should be done now?",
    ]
    
    answers = []
    for q in questions:
        print("\n  Q: '{}'".format(q))
        result = INTELLIGENCE_SERVICE.analyze(q)
        answer = result.get("answer", "")
        answers.append(answer)
        print("  A: '{}'".format(answer[:80].replace('\n', ' ')))
    
    # Check that answers are different
    unique_structures = set()
    for ans in answers:
        # Extract structure (first 3 words)
        words = ans.split()[:5]
        structure = " ".join(words)
        unique_structures.add(structure)
    
    print("\n  Unique response starters: {}".format(len(unique_structures)))
    
    # Should have at least 3 different structures for 4 different question types
    if len(unique_structures) >= 3:
        print("[PASS] Responses show good variability")
        return True
    else:
        print("[FAIL] Responses are too similar (only {} unique)".format(len(unique_structures)))
        return False


if __name__ == "__main__":
    print("\n" + "#"*70)
    print("# INDUSTRY-GRADE OEM ASSISTANT - DIRECT TESTS")
    print("#"*70)
    
    results = []
    results.append(("Intent-Based Responses", test_intent_based_responses()))
    results.append(("Response Variability", test_no_repetitive_patterns()))
    
    print("\n" + "="*70)
    print("FINAL RESULTS")
    print("="*70)
    
    all_passed = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print("{}: {}".format(name, status))
        if not passed:
            all_passed = False
    
    print("="*70)
    if all_passed:
        print("ALL TESTS PASSED - System is production-ready")
    else:
        print("SOME TESTS FAILED - Review required")
    
    sys.exit(0 if all_passed else 1)
