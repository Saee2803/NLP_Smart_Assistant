"""
Test Suite for DBA Intelligence Formatter
==========================================
Validates the 5 layers of DBA intelligence:

1️⃣ FACTUAL ACCURACY
2️⃣ INCIDENT REASONING  
3️⃣ CONTEXTUAL DBA EXPLANATION
4️⃣ HUMAN-LIKE RESPONSE STYLE
5️⃣ ACTIONABLE DBA GUIDANCE
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reasoning.dba_intelligence_formatter import (
    DBAIntelligenceFormatter, 
    get_dba_formatter,
    format_dba_response
)


def test_basic_instantiation():
    """Test that the formatter can be instantiated."""
    print("\n" + "="*60)
    print("TEST: Basic Instantiation")
    print("="*60)
    
    formatter = DBAIntelligenceFormatter()
    assert formatter is not None
    print("✓ Formatter instantiated successfully")
    
    # Test singleton
    formatter2 = get_dba_formatter()
    assert formatter2 is not None
    print("✓ Singleton accessor works")
    
    print("\n✅ Basic Instantiation: PASSED")
    return True


def test_layer1_factual_accuracy():
    """Test Layer 1: Factual Accuracy - never fabricate data."""
    print("\n" + "="*60)
    print("TEST: Layer 1 - Factual Accuracy")
    print("="*60)
    
    formatter = get_dba_formatter()
    
    # Test 1: Count response with actual data
    data = {"count": 649769, "database": "MIDEVSTB", "severity": "CRITICAL"}
    response = formatter.format_response(data, "COUNT", {"database": "MIDEVSTB"})
    
    assert "649,769" in response, f"Expected count in response: {response}"
    assert "MIDEVSTB" in response, f"Expected database in response: {response}"
    print(f"✓ Count response includes factual data: {response[:100]}...")
    
    # Test 2: Zero count response
    data = {"count": 0, "database": "TESTDB", "severity": "CRITICAL"}
    response = formatter.format_response(data, "COUNT")
    
    assert "no" in response.lower() or "0" in response, f"Expected zero handling: {response}"
    print(f"✓ Zero count handled factually: {response[:100]}...")
    
    # Test 3: No data response
    response = formatter.format_response(None, "COUNT")
    assert "not available" in response.lower() or "no" in response.lower(), f"No data: {response}"
    print(f"✓ No data handled gracefully: {response[:80]}...")
    
    print("\n✅ Layer 1 - Factual Accuracy: PASSED")
    return True


def test_layer2_incident_reasoning():
    """Test Layer 2: Incident Reasoning - detect duplicates vs unique."""
    print("\n" + "="*60)
    print("TEST: Layer 2 - Incident Reasoning")
    print("="*60)
    
    formatter = get_dba_formatter()
    
    # Create mock alerts with repeating patterns
    alerts = []
    for i in range(1000):
        alerts.append({
            "message": "ORA-600 [internal error code]",
            "severity": "CRITICAL",
            "database": "MIDEVSTB"
        })
    # Add some unique ones
    for i in range(50):
        alerts.append({
            "message": f"Unique issue {i}",
            "severity": "CRITICAL",
            "database": "MIDEVSTB"
        })
    
    # Test pattern analysis
    pattern = formatter._analyze_incident_patterns(alerts)
    
    assert pattern["total_alerts"] == 1050
    assert pattern["unique_messages"] < pattern["total_alerts"]
    print(f"✓ Detected {pattern['unique_messages']} unique messages in {pattern['total_alerts']} alerts")
    
    # Test explanation generation
    explanation = formatter._explain_incident_reasoning(pattern)
    assert "ORA-600" in explanation or "repeated" in explanation.lower() or "single" in explanation.lower()
    print(f"✓ Incident reasoning explanation: {explanation[:100]}...")
    
    # Test high volume count response includes reasoning
    data = {
        "count": len(alerts),
        "database": "MIDEVSTB",
        "severity": "CRITICAL",
        "alerts": alerts
    }
    response = formatter.format_response(data, "COUNT", {"database": "MIDEVSTB"})
    
    # Should mention the high volume or pattern
    assert "1,050" in response or "1050" in response
    print(f"✓ High volume response generated: {response[:150]}...")
    
    print("\n✅ Layer 2 - Incident Reasoning: PASSED")
    return True


def test_layer3_contextual_explanation():
    """Test Layer 3: Contextual DBA Explanation."""
    print("\n" + "="*60)
    print("TEST: Layer 3 - Contextual DBA Explanation")
    print("="*60)
    
    formatter = get_dba_formatter()
    
    # Test severity context assessment
    
    # Critical with high count
    ctx = formatter._assess_severity_context(100, "CRITICAL", "TESTDB")
    assert ctx["assessment"] == "immediate_investigation"
    print(f"✓ High critical count: {ctx['what']}")
    
    # Critical with zero
    ctx = formatter._assess_severity_context(0, "CRITICAL", "TESTDB")
    assert ctx["assessment"] == "healthy"
    print(f"✓ Zero critical: {ctx['what']}")
    
    # Warning moderate count
    ctx = formatter._assess_severity_context(25, "WARNING", "TESTDB")
    assert "warning" in ctx["what"].lower() or "Warning" in ctx["what"]
    print(f"✓ Warning count: {ctx['what']}")
    
    # Test standby context
    alerts = [{"message": "Standby gap detected", "category": "STANDBY"}]
    standby_ctx = formatter._get_standby_context(alerts, "STANDBY_DB")
    assert "standby" in standby_ctx.lower() or "replication" in standby_ctx.lower()
    print(f"✓ Standby context: {standby_ctx[:80]}...")
    
    print("\n✅ Layer 3 - Contextual DBA Explanation: PASSED")
    return True


def test_layer4_human_response_style():
    """Test Layer 4: Human-like Response Style."""
    print("\n" + "="*60)
    print("TEST: Layer 4 - Human-like Response Style")
    print("="*60)
    
    formatter = get_dba_formatter()
    
    # Test 1: Response should start with direct answer
    data = {"count": 649769, "database": "MIDEVSTB", "severity": "CRITICAL"}
    response = formatter.format_response(data, "COUNT", {"database": "MIDEVSTB", "severity": "CRITICAL"})
    
    # Should have conversational opening
    assert response.startswith("Yes") or "MIDEVSTB" in response[:50]
    print(f"✓ Response starts conversationally: {response[:80]}...")
    
    # Test 2: Should NOT be robotic
    bad_patterns = [
        "649,769 CRITICAL alerts exist.",  # Too robotic
        "COUNT: 649769",  # Machine format
        "RESULT:",  # Technical
    ]
    for pattern in bad_patterns:
        assert pattern not in response, f"Found robotic pattern: {pattern}"
    print("✓ Response avoids robotic patterns")
    
    # Test 3: Should include markdown formatting
    assert "**" in response, "Should use markdown bold"
    print("✓ Response uses markdown formatting")
    
    # Test 4: Status response should be clear
    data = {
        "database": "TESTDB",
        "status": "CRITICAL",
        "critical_count": 5,
        "warning_count": 12,
        "total_alerts": 17
    }
    response = formatter.format_response(data, "STATUS")
    assert "TESTDB" in response
    assert "5" in response or "critical" in response.lower()
    print(f"✓ Status response is human-readable: {response[:100]}...")
    
    print("\n✅ Layer 4 - Human-like Response Style: PASSED")
    return True


def test_layer5_actionable_guidance():
    """Test Layer 5: Actionable DBA Guidance (without hallucination)."""
    print("\n" + "="*60)
    print("TEST: Layer 5 - Actionable DBA Guidance")
    print("="*60)
    
    formatter = get_dba_formatter()
    
    # Test 1: Critical alerts should get guidance
    response = "Test response with critical issues."
    enhanced = formatter.add_dba_guidance(
        response, 
        severity="CRITICAL", 
        alert_count=50,
        error_code="ORA-600"
    )
    
    assert len(enhanced) > len(response), "Guidance should be added"
    assert "Suggested" in enhanced or "suggest" in enhanced.lower()
    print(f"✓ Critical guidance added: ...{enhanced[-100:]}")
    
    # Test 2: Guidance should NOT contain SQL commands (unless asked)
    bad_guidance = ["ALTER", "SELECT", "DROP", "CREATE", "EXECUTE"]
    for cmd in bad_guidance:
        assert cmd not in enhanced.upper(), f"Should not contain SQL: {cmd}"
    print("✓ Guidance does not contain unsolicited SQL commands")
    
    # Test 3: Low count should not add excessive guidance
    response2 = "Minor warning detected."
    enhanced2 = formatter.add_dba_guidance(response2, severity="WARNING", alert_count=2)
    # Should not add verbose guidance for minor issues
    assert len(enhanced2) < len(enhanced), "Minor issues get less guidance"
    print("✓ Minor issues don't get excessive guidance")
    
    # Test 4: Guidance should be marked as suggestions, not facts
    enhanced3 = formatter.add_dba_guidance(
        "High critical count.", 
        severity="CRITICAL", 
        alert_count=100
    )
    suggestion_markers = ["suggest", "typical", "recommend", "consider", "usually"]
    has_suggestion_marker = any(m in enhanced3.lower() for m in suggestion_markers)
    assert has_suggestion_marker, f"Guidance should be marked as suggestion: {enhanced3}"
    print("✓ Guidance is properly marked as suggestions")
    
    print("\n✅ Layer 5 - Actionable DBA Guidance: PASSED")
    return True


def test_low_confidence_handling():
    """Test uncertainty and low confidence handling."""
    print("\n" + "="*60)
    print("TEST: Low Confidence Handling")
    print("="*60)
    
    formatter = get_dba_formatter()
    
    # Test 1: Low confidence with partial intent
    response = formatter.format_low_confidence_response(
        confidence=0.5,
        parsed_intent={"database": "MIDEVSTB"},
        suggestions=None
    )
    
    assert "clarify" in response.lower() or "?" in response
    assert "MIDEVSTB" in response
    print(f"✓ Low confidence prompts clarification: {response[:100]}...")
    
    # Test 2: Suggestions offered
    response2 = formatter.format_low_confidence_response(
        confidence=0.4,
        parsed_intent={},
        suggestions=["show alerts for MIDEVSTB", "count critical alerts"]
    )
    
    assert "?" in response2
    print(f"✓ Suggestions offered: {response2[:100]}...")
    
    print("\n✅ Low Confidence Handling: PASSED")
    return True


def test_context_switch():
    """Test context switch notifications."""
    print("\n" + "="*60)
    print("TEST: Context Switch Notifications")
    print("="*60)
    
    formatter = get_dba_formatter()
    
    # Test switching databases
    notice = formatter.format_context_switch_notice(
        from_context={"database": "MIDEVSTB"},
        to_context={"database": "PRODDB"}
    )
    
    assert "MIDEVSTB" in notice or "PRODDB" in notice
    print(f"✓ Context switch notice: {notice}")
    
    # Test switching from specific to all
    notice2 = formatter.format_context_switch_notice(
        from_context={"database": "MIDEVSTB"},
        to_context={}
    )
    
    assert "system" in notice2.lower() or "MIDEVSTB" in notice2
    print(f"✓ DB to system-wide switch: {notice2}")
    
    print("\n✅ Context Switch Notifications: PASSED")
    return True


def test_list_response():
    """Test list response formatting."""
    print("\n" + "="*60)
    print("TEST: List Response Formatting")
    print("="*60)
    
    formatter = get_dba_formatter()
    
    # Create test alerts
    alerts = [
        {"database": "MIDEVSTB", "severity": "CRITICAL", "message": "ORA-600 internal error"},
        {"database": "MIDEVSTB", "severity": "CRITICAL", "message": "Database hang detected"},
        {"database": "MIDEVSTB", "severity": "WARNING", "message": "Tablespace nearing capacity"},
    ]
    
    data = {
        "alerts": alerts,
        "total_count": 3,
        "shown_count": 3,
        "database": "MIDEVSTB",
        "severity": "ALL"
    }
    
    response = formatter.format_response(data, "LIST")
    
    assert "MIDEVSTB" in response
    assert "ORA-600" in response
    assert "1." in response  # Numbered list
    print(f"✓ List response formatted:\n{response[:300]}...")
    
    print("\n✅ List Response Formatting: PASSED")
    return True


def test_full_integration():
    """Test full integration with real-world scenarios."""
    print("\n" + "="*60)
    print("TEST: Full Integration Scenarios")
    print("="*60)
    
    formatter = get_dba_formatter()
    
    # Scenario 1: DBA asks "how many critical alerts for MIDEVSTB"
    print("\n--- Scenario 1: Critical Alert Count ---")
    data = {
        "count": 649769,
        "database": "MIDEVSTB",
        "severity": "CRITICAL",
        "alerts": [{"message": "ORA-600", "severity": "CRITICAL"}] * 100  # Simulated
    }
    response = formatter.format_response(data, "COUNT", {"database": "MIDEVSTB", "severity": "CRITICAL"})
    print(f"Q: how many critical alerts for MIDEVSTB")
    print(f"A: {response}")
    
    # Validate response quality
    assert "649,769" in response
    assert "MIDEVSTB" in response
    assert "investigation" in response.lower() or "higher" in response.lower() or "significant" in response.lower()
    print("✓ Response meets quality standards")
    
    # Scenario 2: Database status check
    print("\n--- Scenario 2: Database Status ---")
    data = {
        "database": "PRODDB",
        "status": "HEALTHY",
        "critical_count": 0,
        "warning_count": 3,
        "total_alerts": 3
    }
    response = formatter.format_response(data, "STATUS")
    print(f"Q: what is the status of PRODDB")
    print(f"A: {response}")
    
    assert "PRODDB" in response
    # Check for various healthy indicators
    healthy_indicators = ["operational", "healthy", "warning", "normally", "no active", "operating"]
    has_status_indicator = any(ind in response.lower() for ind in healthy_indicators)
    assert has_status_indicator, f"Response should indicate status: {response}"
    print("✓ Status response is accurate")
    
    # Scenario 3: No data scenario
    print("\n--- Scenario 3: Unknown Database ---")
    data = {"count": 0, "database": "UNKNOWNDB"}
    response = formatter._format_no_data_response({"database": "UNKNOWNDB"})
    print(f"Q: show alerts for UNKNOWNDB")
    print(f"A: {response}")
    
    assert "UNKNOWNDB" in response
    assert "not" in response.lower() or "no" in response.lower()
    print("✓ Unknown database handled gracefully")
    
    print("\n✅ Full Integration Scenarios: PASSED")
    return True


def run_all_tests():
    """Run all tests."""
    print("\n" + "="*70)
    print("  DBA INTELLIGENCE FORMATTER - TEST SUITE")
    print("="*70)
    
    tests = [
        test_basic_instantiation,
        test_layer1_factual_accuracy,
        test_layer2_incident_reasoning,
        test_layer3_contextual_explanation,
        test_layer4_human_response_style,
        test_layer5_actionable_guidance,
        test_low_confidence_handling,
        test_context_switch,
        test_list_response,
        test_full_integration,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"\n❌ FAILED: {test.__name__}")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*70)
    print(f"  RESULTS: {passed} PASSED, {failed} FAILED")
    print("="*70)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
