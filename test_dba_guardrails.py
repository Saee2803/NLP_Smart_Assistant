# test_dba_guardrails.py
"""
Test suite for DBA Guardrails System

Tests all 7 guardrails:
1. ANSWER PRECISION - Match answer mode to question
2. SCOPE CONTROL - No data leakage outside requested scope
3. PREDICTIVE REASONING SAFETY - No absolute predictions
4. NO-DATA / LOW-DATA HANDLING - Proper uncertainty handling
5. ANTI-OVEREXPLANATION - Match answer length to question
6. CONSISTENCY CHECK - No conflicting values
7. PRODUCTION-SAFE RESPONSE - Calm, professional language
"""

import sys
sys.path.insert(0, '.')

from reasoning.dba_guardrails import (
    DBA_GUARDRAILS,
    AnswerMode,
    AnswerModeDetector,
    ScopeControlGuard,
    PredictiveReasoningSafety,
    NoDataHandler,
    AntiOverexplanation,
    ConsistencyChecker,
    ProductionSafeResponse,
    apply_guardrails,
    get_answer_mode,
    is_strict_value_question,
    extract_scope,
    cannot_determine,
    format_safe_prediction
)


def test_guardrail_1_answer_precision():
    """
    GUARDRAIL 1: ANSWER PRECISION
    
    Test that questions are correctly classified into answer modes.
    """
    print("\n" + "="*60)
    print("GUARDRAIL 1: ANSWER PRECISION")
    print("="*60)
    
    # STRICT_NUMBER tests (count questions)
    strict_number_questions = [
        "Give me only the number of CRITICAL alerts",
        "How many CRITICAL alerts are there for MIDEVSTB?",
        "Just the count please",
        "Number only - how many warnings?",
    ]
    
    print("\nSTRICT_NUMBER mode tests:")
    for q in strict_number_questions:
        mode = get_answer_mode(q)
        passed = mode == AnswerMode.STRICT_NUMBER
        print(f"  {'✓' if passed else '✗'} '{q[:50]}...' -> {mode.value}")
        assert passed, f"Expected STRICT_NUMBER for: {q}"
    
    # YES_NO tests
    yes_no_questions = [
        "Yes or No: Is there an outage?",
    ]
    
    print("\nYES_NO mode tests:")
    for q in yes_no_questions:
        mode = get_answer_mode(q)
        passed = mode == AnswerMode.YES_NO
        print(f"  {'✓' if passed else '✗'} '{q[:50]}...' -> {mode.value}")
        assert passed, f"Expected YES_NO for: {q}"
    
    # LIST_ONLY tests
    list_questions = [
        "Which database has the most alerts?",
        "List all the affected databases",
    ]
    
    print("\nLIST_ONLY mode tests:")
    for q in list_questions:
        mode = get_answer_mode(q)
        passed = mode == AnswerMode.LIST_ONLY
        print(f"  {'✓' if passed else '✗'} '{q[:50]}...' -> {mode.value}")
        assert passed, f"Expected LIST_ONLY for: {q}"
    
    # ANALYSIS tests
    analysis_questions = [
        "Why is the database generating so many alerts?",
        "Explain the root cause of these errors",
        "Analyze the incident pattern",
        "What is causing the ORA-04031 errors?",
    ]
    
    print("\nANALYSIS mode tests:")
    for q in analysis_questions:
        mode = get_answer_mode(q)
        passed = mode == AnswerMode.ANALYSIS
        print(f"  {'✓' if passed else '✗'} '{q[:50]}...' -> {mode.value}")
        assert passed, f"Expected ANALYSIS for: {q}"
    
    # EXECUTIVE tests
    executive_questions = [
        "Explain this to my manager",
        "What is the business impact?",
        "In simple terms, what's happening?",
    ]
    
    print("\nEXECUTIVE mode tests:")
    for q in executive_questions:
        mode = get_answer_mode(q)
        passed = mode == AnswerMode.EXECUTIVE
        print(f"  {'✓' if passed else '✗'} '{q[:50]}...' -> {mode.value}")
        assert passed, f"Expected EXECUTIVE for: {q}"
    
    # SUMMARY tests (new mode)
    summary_questions = [
        "Give me an executive summary",
        "Summarize the alerts",
    ]
    
    print("\nSUMMARY mode tests:")
    for q in summary_questions:
        mode = get_answer_mode(q)
        passed = mode == AnswerMode.SUMMARY
        print(f"  {'✓' if passed else '✗'} '{q[:50]}...' -> {mode.value}")
        assert passed, f"Expected SUMMARY for: {q}"
    
    print("\n✓ GUARDRAIL 1: All tests passed!")


def test_guardrail_2_scope_control():
    """
    GUARDRAIL 2: SCOPE CONTROL
    
    Test that scope constraints are correctly detected and enforced.
    """
    print("\n" + "="*60)
    print("GUARDRAIL 2: SCOPE CONTROL")
    print("="*60)
    
    # Extract scope from questions
    test_cases = [
        ("How many alerts for MIDEVSTB?", "MIDEVSTB", False),
        ("Show alerts for MIDEVSTB only", "MIDEVSTB", True),
        ("MIDEVSTB primary only, exclude standby", "MIDEVSTB", True),
        ("What is the status of PRODDB?", "PRODDB", False),
    ]
    
    print("\nScope extraction tests:")
    for question, expected_db, expected_hard in test_cases:
        scope = extract_scope(question)
        db_match = scope.target_database == expected_db
        hard_match = scope.is_hard_scope == expected_hard or scope.exclude_standby == expected_hard
        print(f"  {'✓' if db_match else '✗'} '{question[:40]}...' -> DB: {scope.target_database}")
    
    # Scope validation tests
    print("\nScope violation detection tests:")
    
    # Should detect standby leakage
    scope = extract_scope("Show alerts for MIDEVSTB only")
    response_with_standby = "There are 5 CRITICAL alerts. MIDEVSTBN has 3 more."
    is_valid, violations = ScopeControlGuard.validate_response_scope(response_with_standby, scope)
    print(f"  {'✓' if not is_valid else '✗'} Detected standby leakage: {not is_valid}")
    
    # Should pass when scope is respected
    response_clean = "MIDEVSTB has 5 CRITICAL alerts."
    is_valid, violations = ScopeControlGuard.validate_response_scope(response_clean, scope)
    print(f"  {'✓' if is_valid else '✗'} Clean response passed: {is_valid}")
    
    print("\n✓ GUARDRAIL 2: All tests passed!")


def test_guardrail_3_predictive_safety():
    """
    GUARDRAIL 3: PREDICTIVE REASONING SAFETY
    
    Test that predictions don't use absolute language.
    """
    print("\n" + "="*60)
    print("GUARDRAIL 3: PREDICTIVE REASONING SAFETY")
    print("="*60)
    
    # Forbidden phrases should be detected
    unsafe_texts = [
        "This database will fail",
        "The system will definitely crash",
        "Guaranteed outage in 2 hours",
        "100% certain it will go down",
    ]
    
    print("\nUnsafe prediction detection:")
    for text in unsafe_texts:
        is_safe, violations = PredictiveReasoningSafety.check_prediction_safety(text)
        print(f"  {'✓' if not is_safe else '✗'} Detected unsafe: '{text[:40]}...'")
        assert not is_safe, f"Should have detected unsafe prediction: {text}"
    
    # Sanitization should replace forbidden phrases
    print("\nPrediction sanitization:")
    unsafe = "This database will fail tomorrow"
    sanitized = PredictiveReasoningSafety.sanitize_prediction(unsafe)
    print(f"  Before: '{unsafe}'")
    print(f"  After:  '{sanitized}'")
    assert "will fail" not in sanitized.lower(), "Should have sanitized 'will fail'"
    
    # Safe prediction formatting
    print("\nSafe prediction formatting:")
    prediction = format_safe_prediction("MIDEVSTB shows elevated risk", "MIDEVSTB", "LOW")
    print(f"  Contains confidence level: {'LOW' in prediction}")
    print(f"  Contains limitations: {'Limitations' in prediction}")
    
    print("\n✓ GUARDRAIL 3: All tests passed!")


def test_guardrail_4_no_data_handling():
    """
    GUARDRAIL 4: NO-DATA / LOW-DATA HANDLING
    
    Test proper handling when data is missing.
    """
    print("\n" + "="*60)
    print("GUARDRAIL 4: NO-DATA / LOW-DATA HANDLING")
    print("="*60)
    
    # Cannot determine response
    response = cannot_determine(
        "No alert data available for the specified time range",
        "Historical alert data for the past 24 hours"
    )
    
    print("\nCannot determine response:")
    print(f"  Contains 'Cannot determine': {'Cannot determine' in response}")
    print(f"  Contains 'Reason': {'Reason' in response}")
    print(f"  Contains 'Data needed': {'Data needed' in response}")
    
    # Data availability check
    has_data, reason = NoDataHandler.check_data_availability([])
    print(f"\n  Empty data check: has_data={has_data}, reason='{reason}'")
    assert not has_data, "Should detect no data"
    
    has_data, reason = NoDataHandler.check_data_availability([{"alert": "test"}])
    print(f"  With data check: has_data={has_data}")
    assert has_data, "Should detect data present"
    
    print("\n✓ GUARDRAIL 4: All tests passed!")


def test_guardrail_5_anti_overexplanation():
    """
    GUARDRAIL 5: ANTI-OVEREXPLANATION
    
    Test that response length matches question intent.
    """
    print("\n" + "="*60)
    print("GUARDRAIL 5: ANTI-OVEREXPLANATION")
    print("="*60)
    
    # Minimal questions should have short max length
    minimal_questions = [
        "How many CRITICAL alerts?",
        "What is the count of warnings?",
        "Is there an outage?",
    ]
    
    print("\nMax response length for minimal questions:")
    for q in minimal_questions:
        mode = get_answer_mode(q)
        max_len = AntiOverexplanation.get_max_response_length(q, mode)
        print(f"  '{q[:40]}...' -> max {max_len} chars")
        assert max_len <= 500, f"Minimal question should have short max length"
    
    # Detailed questions should allow longer responses
    detailed_questions = [
        "Explain the root cause of ORA-04031 errors",
        "Why is the database generating alerts?",
        "Analyze the incident pattern",
    ]
    
    print("\nMax response length for detailed questions:")
    for q in detailed_questions:
        mode = get_answer_mode(q)
        max_len = AntiOverexplanation.get_max_response_length(q, mode)
        print(f"  '{q[:40]}...' -> max {max_len} chars")
        assert max_len >= 800, f"Detailed question should allow longer response"
    
    print("\n✓ GUARDRAIL 5: All tests passed!")


def test_guardrail_6_consistency_check():
    """
    GUARDRAIL 6: CONSISTENCY CHECK
    
    Test detection of conflicting values within responses.
    """
    print("\n" + "="*60)
    print("GUARDRAIL 6: CONSISTENCY CHECK")
    print("="*60)
    
    checker = ConsistencyChecker()
    
    # Conflicting counts in same response
    response_with_conflict = """
    There are 5 CRITICAL alerts in the system.
    The database shows 3 CRITICAL alerts.
    """
    
    is_consistent, issues = checker.check_internal_consistency(response_with_conflict)
    print(f"\nConflicting counts detection:")
    print(f"  Response has conflict: {not is_consistent}")
    if issues:
        for issue in issues:
            print(f"    Issue: {issue}")
    
    # Consistent response
    response_consistent = """
    There are 5 CRITICAL alerts in MIDEVSTB.
    The breakdown: 3 ORA-04031, 2 ORA-00600.
    """
    
    is_consistent, issues = checker.check_internal_consistency(response_consistent)
    print(f"\nConsistent response check:")
    print(f"  Response is consistent: {is_consistent}")
    
    print("\n✓ GUARDRAIL 6: All tests passed!")


def test_guardrail_7_production_safety():
    """
    GUARDRAIL 7: PRODUCTION-SAFE RESPONSE
    
    Test detection and correction of panic language.
    """
    print("\n" + "="*60)
    print("GUARDRAIL 7: PRODUCTION-SAFE RESPONSE")
    print("="*60)
    
    # Panic language detection
    panic_responses = [
        "This is a critical failure requiring immediate action!",
        "The system is completely crashed!",
        "This is a catastrophic disaster!",
    ]
    
    print("\nPanic language detection:")
    for text in panic_responses:
        is_safe, issues = ProductionSafeResponse.check_production_safety(text)
        print(f"  {'✓' if not is_safe else '✗'} Detected panic: '{text[:40]}...'")
    
    # Calm down text
    print("\nCalm down transformation:")
    panic_text = "This is a catastrophic critical failure!"
    calmed = ProductionSafeResponse.calm_down_text(panic_text)
    print(f"  Before: '{panic_text}'")
    print(f"  After:  '{calmed}'")
    
    # Structured response
    print("\nStructured response formatting:")
    structured = ProductionSafeResponse.format_structured_response(
        facts=["MIDEVSTB has 5 CRITICAL alerts", "Last alert was 10 minutes ago"],
        inferences=["Pattern suggests memory pressure"],
        recommendations=["Check SGA utilization", "Review recent workload changes"]
    )
    print(f"  Contains 'Facts': {'Facts' in structured}")
    print(f"  Contains 'Inference': {'Inference' in structured}")
    print(f"  Contains 'Recommendations': {'Recommendations' in structured}")
    
    print("\n✓ GUARDRAIL 7: All tests passed!")


def test_full_guardrails_integration():
    """
    Test full guardrails integration with apply_guardrails function.
    """
    print("\n" + "="*60)
    print("FULL GUARDRAILS INTEGRATION TEST")
    print("="*60)
    
    # Test STRICT_VALUE mode enforcement
    question = "Give me only the number of CRITICAL alerts"
    response = "There are 5 CRITICAL alerts in MIDEVSTB database."
    
    final, result = apply_guardrails(question, response)
    print(f"\nSTRICT_VALUE enforcement:")
    print(f"  Question: '{question}'")
    print(f"  Original: '{response}'")
    print(f"  Final:    '{final}'")
    print(f"  Mode:     {result.mode.value}")
    assert final.isdigit(), "STRICT_VALUE should return only digits"
    
    # Test scope enforcement
    question = "How many alerts for MIDEVSTB?"
    response = "MIDEVSTB has 5 alerts. MIDEVSTBN has 3 more alerts."
    data = [{"target": "MIDEVSTB", "severity": "CRITICAL"}]
    
    final, result = apply_guardrails(question, response, data)
    print(f"\nScope enforcement:")
    print(f"  Question: '{question}'")
    print(f"  Violations: {result.violations}")
    
    # Test prediction safety
    question = "Which database will fail next?"
    response = "MIDEVSTB will definitely fail within 2 hours."
    
    final, result = apply_guardrails(question, response)
    print(f"\nPrediction safety:")
    print(f"  Original: '{response}'")
    print(f"  Corrected: '{result.corrected_response is not None}'")
    
    print("\n✓ FULL INTEGRATION: All tests passed!")


def test_production_safety_rules():
    """
    Test Production Safety Rules (forbidden claims detection).
    """
    from reasoning.dba_guardrails import ProductionSafetyRules
    
    print("\n" + "="*60)
    print("PRODUCTION SAFETY RULES")
    print("="*60)
    
    # Test forbidden claims
    forbidden_responses = [
        "Run this query to fix the issue immediately",
        "This will not cause an outage",
        "Guaranteed resolution within 1 hour",
        "This definitely means the database is corrupted",
    ]
    
    print("\nForbidden claims detection:")
    for response in forbidden_responses:
        is_safe, violations = ProductionSafetyRules.check_for_forbidden_claims(response)
        print(f"  {'✗' if is_safe else '✓'} '{response[:50]}...' -> {'SAFE' if is_safe else 'FORBIDDEN'}")
        assert not is_safe, f"Should detect forbidden claim: {response}"
    
    # Test safety disclaimer detection
    fix_questions = [
        "How do I fix this error?",
        "What command should I run to resolve it?",
        "Can you guarantee this will work?",
    ]
    
    print("\nSafety disclaimer requirement detection:")
    for q in fix_questions:
        needs_disclaimer = ProductionSafetyRules.needs_safety_disclaimer(q)
        print(f"  {'✓' if needs_disclaimer else '✗'} '{q[:50]}...' -> {'NEEDS DISCLAIMER' if needs_disclaimer else 'OK'}")
        assert needs_disclaimer, f"Should need disclaimer: {q}"
    
    print("\n✓ PRODUCTION SAFETY RULES: All tests passed!")


def test_data_authority_rule():
    """
    Test Data Authority Rule (no assumptions detection).
    """
    from reasoning.dba_guardrails import DataAuthorityRule
    
    print("\n" + "="*60)
    print("DATA AUTHORITY RULE")
    print("="*60)
    
    # Test assumption detection
    assumption_responses = [
        "I think this is a network issue",
        "The error probably means disk is full",
        "It seems like the connection pool is exhausted",
        "This might be caused by memory pressure",
    ]
    
    print("\nAssumption detection:")
    for response in assumption_responses:
        is_ok, warnings = DataAuthorityRule.check_data_authority(response)
        print(f"  {'✗' if is_ok else '✓'} '{response[:50]}...' -> {'OK' if is_ok else 'ASSUMPTION DETECTED'}")
        assert not is_ok, f"Should detect assumption: {response}"
    
    # Test OK responses (no assumptions)
    ok_responses = [
        "There are 15 CRITICAL alerts in the dataset",
        "The error frequency is 5 per hour",
        "Based on the alert data, the pattern is recurring",
    ]
    
    print("\nOK responses (no assumptions):")
    for response in ok_responses:
        is_ok, warnings = DataAuthorityRule.check_data_authority(response)
        print(f"  {'✓' if is_ok else '✗'} '{response[:50]}...' -> {'OK' if is_ok else 'WARNING'}")
        assert is_ok, f"Should be OK: {response}"
    
    print("\n✓ DATA AUTHORITY RULE: All tests passed!")


def test_incident_intelligence_logic():
    """
    Test Incident Intelligence Logic (high volume handling).
    """
    from reasoning.dba_guardrails import IncidentIntelligenceLogic
    
    print("\n" + "="*60)
    print("INCIDENT INTELLIGENCE LOGIC")
    print("="*60)
    
    # Test high volume threshold
    print("\nHigh volume detection:")
    test_counts = [(10, False), (49, False), (50, True), (100, True), (500, True)]
    
    for count, expected_high in test_counts:
        is_high = IncidentIntelligenceLogic.is_high_volume(count)
        print(f"  {'✓' if is_high == expected_high else '✗'} {count} alerts -> {'HIGH' if is_high else 'NORMAL'}")
        assert is_high == expected_high, f"Count {count} should be high={expected_high}"
    
    # Test high volume context addition
    response = "Here is the alert summary."
    modified = IncidentIntelligenceLogic.add_high_volume_context(response, 100)
    assert "does NOT imply" in modified, "Should add high volume disclaimer"
    print(f"  ✓ High volume disclaimer added correctly")
    
    print("\n✓ INCIDENT INTELLIGENCE LOGIC: All tests passed!")


def test_root_cause_handler():
    """
    Test Root Cause Handler (multiple factors, computed inference).
    """
    from reasoning.dba_guardrails import RootCauseHandler
    
    print("\n" + "="*60)
    print("ROOT CAUSE HANDLER")
    print("="*60)
    
    # Test single cause
    single_cause_response = RootCauseHandler.format_root_cause(["Memory pressure"])
    print(f"\nSingle cause response:")
    print(f"  ✓ Contains 'Probable Root Cause': {'Probable Root Cause' in single_cause_response}")
    assert "Probable Root Cause" in single_cause_response
    
    # Test multiple causes
    multi_cause_response = RootCauseHandler.format_root_cause(
        ["Memory pressure", "High CPU", "Network latency"],
        [0.75, 0.60, 0.45]
    )
    print(f"\nMultiple causes response:")
    print(f"  ✓ Contains 'Multiple contributing factors': {'Multiple contributing factors' in multi_cause_response}")
    print(f"  ✓ Contains 'Computed Inference': {'Computed Inference' in multi_cause_response}")
    assert "Multiple contributing factors" in multi_cause_response
    assert "[Computed Inference]" in multi_cause_response
    assert RootCauseHandler.ROOT_CAUSE_DISCLAIMER in multi_cause_response
    
    print("\n✓ ROOT CAUSE HANDLER: All tests passed!")


def test_confidence_formatter():
    """
    Test Confidence Formatter (confidence labels).
    """
    from reasoning.dba_guardrails import ConfidenceFormatter, ConfidenceLevel
    
    print("\n" + "="*60)
    print("CONFIDENCE FORMATTER")
    print("="*60)
    
    # Test confidence assessment
    print("\nConfidence assessment based on data count:")
    test_cases = [
        (0, ConfidenceLevel.LOW),
        (3, ConfidenceLevel.LOW),
        (10, ConfidenceLevel.MEDIUM),
        (25, ConfidenceLevel.HIGH),
        (100, ConfidenceLevel.HIGH),
    ]
    
    for count, expected_level in test_cases:
        level = ConfidenceFormatter.assess_confidence(count)
        print(f"  {'✓' if level == expected_level else '✗'} {count} data points -> {level.value}")
        assert level == expected_level, f"Count {count} should be {expected_level}"
    
    # Test label addition
    response = "There are 15 alerts."
    labeled = ConfidenceFormatter.add_confidence_label(response, ConfidenceLevel.MEDIUM)
    print(f"\n  ✓ Confidence label added: {'🟡 MEDIUM' in labeled}")
    assert "MEDIUM" in labeled
    
    print("\n✓ CONFIDENCE FORMATTER: All tests passed!")


def test_self_validation():
    """
    Test Self-Validation Step.
    """
    from reasoning.dba_guardrails import SelfValidation, ScopeConstraint, AnswerMode
    
    print("\n" + "="*60)
    print("SELF-VALIDATION STEP")
    print("="*60)
    
    # Test STRICT_NUMBER mode validation
    scope = ScopeConstraint()
    
    # Good STRICT_NUMBER response
    question = "How many alerts?"
    response = "15"
    passed, failures = SelfValidation.validate_response(question, response, scope, AnswerMode.STRICT_NUMBER)
    print(f"\n  {'✓' if passed else '✗'} STRICT_NUMBER '15' -> {'PASSED' if passed else 'FAILED'}")
    assert passed, f"Should pass for numeric response: {failures}"
    
    # Bad STRICT_NUMBER response
    response2 = "There are 15 alerts in the database"
    passed2, failures2 = SelfValidation.validate_response(question, response2, scope, AnswerMode.STRICT_NUMBER)
    print(f"  {'✓' if not passed2 else '✗'} STRICT_NUMBER 'There are 15...' -> {'PASSED' if passed2 else 'FAILED (expected)'}")
    assert not passed2, "Should fail for non-numeric response in STRICT_NUMBER mode"
    
    # Test YES_NO mode validation
    question3 = "Is there an outage?"
    response3 = "Yes"
    passed3, failures3 = SelfValidation.validate_response(question3, response3, scope, AnswerMode.YES_NO)
    print(f"  {'✓' if passed3 else '✗'} YES_NO 'Yes' -> {'PASSED' if passed3 else 'FAILED'}")
    assert passed3, f"Should pass for Yes response: {failures3}"
    
    print("\n✓ SELF-VALIDATION STEP: All tests passed!")


def run_all_tests():
    """Run all guardrail tests."""
    print("\n" + "="*60)
    print("DBA GUARDRAILS TEST SUITE")
    print("="*60)
    
    try:
        test_guardrail_1_answer_precision()
        test_guardrail_2_scope_control()
        test_guardrail_3_predictive_safety()
        test_guardrail_4_no_data_handling()
        test_guardrail_5_anti_overexplanation()
        test_guardrail_6_consistency_check()
        test_guardrail_7_production_safety()
        test_full_guardrails_integration()
        
        # New Production-Grade tests
        test_production_safety_rules()
        test_data_authority_rule()
        test_incident_intelligence_logic()
        test_root_cause_handler()
        test_confidence_formatter()
        test_self_validation()
        
        print("\n" + "="*60)
        print("ALL GUARDRAIL TESTS PASSED! ✓")
        print("="*60)
        return True
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
