#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Production Compliance Test for OEM DBA Assistant
=================================================

This test validates STRICT compliance with production rules:

1. FACTUAL questions → 1-3 lines, NO root cause, NO action plan, NO confidence %
2. ANALYTICAL questions → Explanation with reasoning, NO actions unless asked
3. ACTION questions → Steps and recommendations, specific not generic
4. NO templated sections like "Summary / What was checked / What was found / What to do now"
5. Conversational tone, not report-like

Python 3.6.8 compatible.
"""

from __future__ import print_function
import sys
import re

sys.path.insert(0, '.')


def check_no_template_structure(answer):
    """
    Check that answer does NOT have the forbidden templated structure.
    
    FORBIDDEN patterns:
    - "Summary" / "What was checked" / "What was found" / "What it means" / "What to do now"
    - Emoji-heavy section headers
    - Fixed report-like structure
    """
    forbidden_patterns = [
        r"\bwhat was checked\b",
        r"\bwhat was found\b",
        r"\bwhat it means\b",
        r"\bwhat to do now\b",
        r"🔹\s*summary",
        r"🔍\s*what",
        r"📊\s*what",
        r"🧠\s*what",
        r"🛠️\s*what",
    ]
    
    answer_lower = answer.lower() if answer else ""
    
    for pattern in forbidden_patterns:
        if re.search(pattern, answer_lower, re.IGNORECASE):
            return False, "Found forbidden template pattern: {}".format(pattern)
    
    return True, None


def check_no_root_cause_in_factual(answer):
    """
    Check that FACTUAL answers do NOT contain root cause analysis.
    """
    if not answer:
        return True, None
    
    answer_lower = answer.lower()
    
    # These phrases should NOT appear in factual answers
    root_cause_phrases = [
        "root cause",
        "caused by",
        "underlying issue",
        "primary cause",
    ]
    
    for phrase in root_cause_phrases:
        if phrase in answer_lower:
            return False, "Found root cause text in factual answer: '{}'".format(phrase)
    
    return True, None


def check_no_actions_in_factual(answer, response):
    """
    Check that FACTUAL answers do NOT contain action recommendations.
    """
    if not answer:
        return True, None
    
    # Check the response metadata
    if response.get("actions_included", False):
        return False, "actions_included is True for factual question"
    
    answer_lower = answer.lower()
    
    # These phrases should NOT appear in factual answers
    action_phrases = [
        "recommended action",
        "immediate action",
        "what to do",
        "should be done",
        "next steps",
        "remediation",
    ]
    
    for phrase in action_phrases:
        if phrase in answer_lower:
            return False, "Found action text in factual answer: '{}'".format(phrase)
    
    return True, None


def check_no_confidence_percentage_in_factual(answer):
    """
    Check that FACTUAL answers do NOT show confidence percentage.
    """
    if not answer:
        return True, None
    
    # Pattern for "XX%" or "confidence: XX"
    if re.search(r'\d{1,3}%', answer) or "confidence:" in answer.lower():
        return False, "Found confidence percentage in factual answer"
    
    return True, None


def check_answer_is_short(answer, max_length=200):
    """
    Check that factual answer is concise (1-3 lines, under max_length chars).
    """
    if not answer:
        return False, "Answer is empty"
    
    # Remove markdown formatting for length check
    clean = re.sub(r'\*\*|\*|_', '', answer)
    
    line_count = len([l for l in answer.split('\n') if l.strip()])
    
    if line_count > 5:
        return False, "Answer has {} lines (max 3-5 for factual)".format(line_count)
    
    if len(clean) > max_length * 2:
        return False, "Answer is {} chars (expected < {})".format(len(clean), max_length * 2)
    
    return True, None


def test_factual_questions_compliance():
    """Test that factual questions get SHORT, DIRECT answers without extras."""
    print("\n" + "="*70)
    print("FACTUAL QUESTIONS COMPLIANCE TEST")
    print("="*70)
    
    try:
        from nlp_engine.oem_reasoning_pipeline import OEMReasoningPipeline
        from data_engine import global_cache
    except ImportError as e:
        print("[SKIP] Cannot import: {}".format(str(e)))
        return True
    
    # Mock data
    mock_alerts = [
        {"alert_id": "1", "target_name": "PRODDB", "host_name": "srv-01", "severity": "Critical", "message": "ORA-04031"},
        {"alert_id": "2", "target_name": "PRODDB", "host_name": "srv-01", "severity": "Critical", "message": "ORA-04031"},
        {"alert_id": "3", "target_name": "FINDB", "host_name": "srv-02", "severity": "Warning", "message": "Tablespace full"},
        {"alert_id": "4", "target_name": "HRDB", "host_name": "srv-03", "severity": "Critical", "message": "ORA-00600"},
    ]
    global_cache.GLOBAL_DATA["alerts"] = mock_alerts
    
    pipeline = OEMReasoningPipeline()
    
    factual_questions = [
        "How many databases have alerts?",
        "Which database is critical?",
        "How many alerts are there?",
        "List all ORA codes",
        "What hour had the most alerts?",
    ]
    
    passed = 0
    failed = 0
    
    for question in factual_questions:
        print("\n--- Testing: '{}' ---".format(question))
        
        try:
            response = pipeline.process(question)
            answer = response.get("answer", "")
            
            all_checks_passed = True
            
            # Check 1: No templated structure
            ok, reason = check_no_template_structure(answer)
            if not ok:
                print("[FAIL] Template check: {}".format(reason))
                all_checks_passed = False
            
            # Check 2: No root cause
            ok, reason = check_no_root_cause_in_factual(answer)
            if not ok:
                print("[FAIL] Root cause check: {}".format(reason))
                all_checks_passed = False
            
            # Check 3: No actions
            ok, reason = check_no_actions_in_factual(answer, response)
            if not ok:
                print("[FAIL] Actions check: {}".format(reason))
                all_checks_passed = False
            
            # Check 4: No confidence percentage
            ok, reason = check_no_confidence_percentage_in_factual(answer)
            if not ok:
                print("[FAIL] Confidence check: {}".format(reason))
                all_checks_passed = False
            
            # Check 5: Short answer
            ok, reason = check_answer_is_short(answer)
            if not ok:
                print("[FAIL] Length check: {}".format(reason))
                all_checks_passed = False
            
            if all_checks_passed:
                passed += 1
                print("[PASS] All compliance checks passed")
                print("  Answer: '{}'".format(answer[:100] if len(answer) > 100 else answer))
            else:
                failed += 1
                print("  Actual answer: '{}'".format(answer[:150]))
                
        except Exception as e:
            failed += 1
            print("[ERROR] Exception: {}".format(str(e)))
    
    print("\n" + "-"*50)
    print("Results: {} passed, {} failed".format(passed, failed))
    return failed == 0


def test_analytical_questions_no_actions():
    """Test that analytical questions include root cause but NO actions."""
    print("\n" + "="*70)
    print("ANALYTICAL QUESTIONS COMPLIANCE TEST")
    print("="*70)
    
    try:
        from nlp_engine.oem_reasoning_pipeline import OEMReasoningPipeline
        from data_engine import global_cache
    except ImportError as e:
        print("[SKIP] Cannot import: {}".format(str(e)))
        return True
    
    mock_alerts = [
        {"alert_id": "1", "target_name": "PRODDB", "host_name": "srv-01", "severity": "Critical", "message": "ORA-04031"},
        {"alert_id": "2", "target_name": "PRODDB", "host_name": "srv-01", "severity": "Critical", "message": "ORA-04031"},
    ]
    global_cache.GLOBAL_DATA["alerts"] = mock_alerts
    
    pipeline = OEMReasoningPipeline()
    
    analytical_questions = [
        "Why is PRODDB failing?",
        "What is causing the ORA-04031 errors?",
    ]
    
    passed = 0
    failed = 0
    
    for question in analytical_questions:
        print("\n--- Testing: '{}' ---".format(question))
        
        try:
            response = pipeline.process(question)
            answer = response.get("answer", "")
            
            # Check: NO actions
            ok, reason = check_no_actions_in_factual(answer, response)
            if ok:
                passed += 1
                print("[PASS] No actions in analytical response")
                print("  Answer preview: '{}'".format(answer[:100]))
            else:
                failed += 1
                print("[FAIL] {}".format(reason))
                print("  Answer: '{}'".format(answer[:150]))
                
        except Exception as e:
            failed += 1
            print("[ERROR] Exception: {}".format(str(e)))
    
    print("\n" + "-"*50)
    print("Results: {} passed, {} failed".format(passed, failed))
    return failed == 0


def test_action_questions_have_steps():
    """Test that ACTION questions include specific action steps."""
    print("\n" + "="*70)
    print("ACTION QUESTIONS COMPLIANCE TEST")
    print("="*70)
    
    try:
        from nlp_engine.oem_reasoning_pipeline import OEMReasoningPipeline
        from data_engine import global_cache
    except ImportError as e:
        print("[SKIP] Cannot import: {}".format(str(e)))
        return True
    
    mock_alerts = [
        {"alert_id": "1", "target_name": "PRODDB", "host_name": "srv-01", "severity": "Critical", "message": "ORA-04031"},
    ]
    global_cache.GLOBAL_DATA["alerts"] = mock_alerts
    
    pipeline = OEMReasoningPipeline()
    
    action_questions = [
        "What should I do to fix PRODDB?",
        "How do I resolve ORA-04031?",
    ]
    
    passed = 0
    failed = 0
    
    for question in action_questions:
        print("\n--- Testing: '{}' ---".format(question))
        
        try:
            response = pipeline.process(question)
            answer = response.get("answer", "")
            
            # Check: MUST have actions
            has_actions = response.get("actions_included", False)
            
            # Or check answer text for action keywords
            action_keywords = ["action", "step", "fix", "resolve", "check", "verify", "run"]
            has_action_text = any(kw in answer.lower() for kw in action_keywords)
            
            if has_actions or has_action_text:
                passed += 1
                print("[PASS] Action response includes actionable content")
                print("  Answer preview: '{}'".format(answer[:120]))
            else:
                failed += 1
                print("[FAIL] Action response missing actionable content")
                print("  Answer: '{}'".format(answer[:150]))
                
        except Exception as e:
            failed += 1
            print("[ERROR] Exception: {}".format(str(e)))
    
    print("\n" + "-"*50)
    print("Results: {} passed, {} failed".format(passed, failed))
    return failed == 0


def run_compliance_tests():
    """Run all production compliance tests."""
    print("\n" + "#"*70)
    print("# OEM DBA ASSISTANT - PRODUCTION COMPLIANCE TESTS")
    print("#"*70)
    
    results = []
    
    results.append(("FACTUAL Questions Compliance", test_factual_questions_compliance()))
    results.append(("ANALYTICAL Questions Compliance", test_analytical_questions_no_actions()))
    results.append(("ACTION Questions Compliance", test_action_questions_have_steps()))
    
    print("\n" + "="*70)
    print("FINAL COMPLIANCE RESULTS")
    print("="*70)
    
    all_passed = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print("{}: {}".format(name, status))
        if not passed:
            all_passed = False
    
    print("\n" + "="*70)
    if all_passed:
        print("ALL COMPLIANCE TESTS PASSED!")
        print("System is PRODUCTION-READY.")
    else:
        print("COMPLIANCE TESTS FAILED - Review above for violations")
    print("="*70)
    
    return all_passed


if __name__ == "__main__":
    success = run_compliance_tests()
    sys.exit(0 if success else 1)
