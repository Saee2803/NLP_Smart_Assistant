# -*- coding: utf-8 -*-
"""
Phase-12.1 Guardrails Test Suite
=================================

Tests all 6 HARD GUARDRAILS:
1. DATABASE SCOPE LOCK
2. ENVIRONMENT vs DB NUMBERS
3. ROOT CAUSE CONFIDENCE CLAMP
4. PREDICTIVE LANGUAGE SAFETY
5. UNIQUE INCIDENT COUNT
6. EXECUTION & GUARANTEE BLOCK
"""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reasoning.phase12_guardrails import (
    Phase12Guardrails,
    enforce_phase12,
    get_active_db_scope,
    reset_db_scope,
    self_check_answer,
    ScopeType,
    ActiveScope
)


class TestGuardrail1_DatabaseScopeLock:
    """GUARDRAIL 1: DATABASE SCOPE LOCK (CRITICAL)"""
    
    def setup_method(self):
        """Reset scope before each test."""
        reset_db_scope()
    
    def test_extract_database_from_explicit_question(self):
        """Extract DB name from explicit mention."""
        db = Phase12Guardrails.extract_database_from_question(
            "How many critical alerts for MIDEVSTB?"
        )
        assert db == "MIDEVSTB"
    
    def test_extract_database_from_standby_mention(self):
        """Extract standby DB name."""
        db = Phase12Guardrails.extract_database_from_question(
            "Show alerts for MIDEVSTBN"
        )
        assert db == "MIDEVSTBN"
    
    def test_followup_inherits_scope(self):
        """Follow-up questions inherit previous DB scope."""
        # First question sets scope
        Phase12Guardrails.update_scope("How many critical alerts for MIDEVSTB?")
        assert get_active_db_scope() == "MIDEVSTB"
        
        # Follow-up should inherit
        assert Phase12Guardrails.is_scope_inheriting_followup("Critical count?")
        Phase12Guardrails.update_scope("Critical count?")
        assert get_active_db_scope() == "MIDEVSTB"
    
    def test_this_db_looks_fine_inherits_scope(self):
        """'This DB looks fine right?' should inherit scope."""
        Phase12Guardrails.update_scope("Show alerts for MIDEVSTB")
        assert get_active_db_scope() == "MIDEVSTB"
        
        # This exact pattern from screenshot
        assert Phase12Guardrails.is_scope_inheriting_followup("This DB looks fine right?")
        Phase12Guardrails.update_scope("This DB looks fine right?")
        assert get_active_db_scope() == "MIDEVSTB"  # Still MIDEVSTB
    
    def test_is_ora_root_cause_inherits_scope(self):
        """'Is ORA-600 the confirmed root cause?' inherits scope."""
        Phase12Guardrails.update_scope("How many critical for MIDEVSTBN?")
        assert get_active_db_scope() == "MIDEVSTBN"
        
        assert Phase12Guardrails.is_scope_inheriting_followup(
            "Is ORA-600 the confirmed root cause?"
        )
    
    def test_explicit_environment_request(self):
        """Explicit environment request changes scope."""
        Phase12Guardrails.update_scope("Show alerts for MIDEVSTB")
        assert get_active_db_scope() == "MIDEVSTB"
        
        # Explicit environment request
        Phase12Guardrails.update_scope("Show all databases")
        scope = Phase12Guardrails.get_current_scope()
        assert scope.scope_type == ScopeType.ENVIRONMENT


class TestGuardrail2_EnvironmentVsDBNumbers:
    """GUARDRAIL 2: ENVIRONMENT vs DB NUMBERS (STRICT)"""
    
    def setup_method(self):
        reset_db_scope()
    
    def test_detect_scope_drift_with_large_number(self):
        """Detect when environment total is used for DB question."""
        # Set DB scope
        Phase12Guardrails.update_scope("How many critical for MIDEVSTB?")
        
        # Answer with environment total (like 649,787)
        answer = "There are 649,787 critical alerts."
        
        has_drift, corrected = Phase12Guardrails.check_scope_drift(
            "Critical count?",
            answer,
            data_used=[{"target_name": "MIDEVSTB"}] * 10  # Only 10 for this DB
        )
        
        assert has_drift  # Should detect drift


class TestGuardrail3_RootCauseConfidenceClamp:
    """GUARDRAIL 3: ROOT CAUSE CONFIDENCE CLAMP"""
    
    def test_clamp_high_confidence_root_cause(self):
        """HIGH confidence root cause should be clamped to MEDIUM."""
        answer = "**Root Cause (HIGH Confidence - Computed)**\n\nORA-600 is the confirmed root cause."
        
        clamped = Phase12Guardrails.clamp_root_cause_confidence(answer)
        
        assert "HIGH" not in clamped or "MEDIUM" in clamped
        assert "confirmed root cause" not in clamped.lower()
    
    def test_clamp_confidence_label_in_result(self):
        """Confidence label should be clamped unless proven."""
        result = {
            "answer": "Root cause identified",
            "confidence_label": "HIGH"
        }
        
        clamped = Phase12Guardrails.clamp_confidence_label(result)
        
        assert clamped["confidence_label"] == "MEDIUM"
    
    def test_allow_high_for_direct_data(self):
        """HIGH confidence allowed when direct data proves it."""
        result = {
            "answer": "Count: 165837",
            "confidence_label": "HIGH",
            "_has_direct_data": True
        }
        
        clamped = Phase12Guardrails.clamp_confidence_label(result)
        
        # Should keep HIGH because direct data flag is set
        assert clamped["confidence_label"] == "HIGH"


class TestGuardrail4_PredictiveLanguageSafety:
    """GUARDRAIL 4: PREDICTIVE LANGUAGE SAFETY"""
    
    def test_sanitize_will_fail(self):
        """'Will fail' should be replaced."""
        answer = "This database will fail soon."
        sanitized = Phase12Guardrails.sanitize_predictions(
            "Will this cause an outage?",
            answer
        )
        
        assert "will fail" not in sanitized.lower()
        assert "may fail" in sanitized.lower()
    
    def test_sanitize_will_escalate(self):
        """'Will escalate' should be replaced."""
        answer = "This issue will escalate to an outage."
        sanitized = Phase12Guardrails.sanitize_predictions(
            "Is this going to get worse?",
            answer
        )
        
        assert "will escalate" not in sanitized.lower()
        assert "may escalate" in sanitized.lower()
    
    def test_add_disclaimer_for_predictive_question(self):
        """Predictive questions should get disclaimer."""
        answer = "Risk is elevated."
        sanitized = Phase12Guardrails.sanitize_predictions(
            "Will this cause an outage today?",
            answer
        )
        
        assert "based on alert data only" in sanitized.lower()


class TestGuardrail5_UniqueIncidentCount:
    """GUARDRAIL 5: UNIQUE INCIDENT COUNT GUARDRAIL"""
    
    def test_detect_incident_count_question(self):
        """Detect questions about unique incidents."""
        assert Phase12Guardrails.is_incident_count_question(
            "How many unique incidents exist?"
        )
        assert Phase12Guardrails.is_incident_count_question(
            "Is this 165,837 issues?"
        )
    
    def test_fix_exact_incident_number(self):
        """Exact numbers should become approximations."""
        reset_db_scope()
        
        # Just a number response (like in screenshot: "649787")
        answer = "649787"
        fixed = Phase12Guardrails.fix_incident_count(
            "How many unique incidents exist?",
            answer
        )
        
        assert "649787" not in fixed or "~" in fixed or "approximation" in fixed.lower()
        assert "approximation" in fixed.lower() or "pattern" in fixed.lower()


class TestGuardrail6_ExecutionGuaranteeBlock:
    """GUARDRAIL 6: EXECUTION & GUARANTEE BLOCK"""
    
    def test_detect_execution_request(self):
        """Detect requests to execute SQL."""
        assert Phase12Guardrails.needs_execution_refusal("Run this SQL for me")
        assert Phase12Guardrails.needs_execution_refusal("Execute the query")
        assert Phase12Guardrails.needs_execution_refusal("Restart the database")
    
    def test_detect_guarantee_request(self):
        """Detect requests for guarantees."""
        assert Phase12Guardrails.needs_execution_refusal("Guarantee no outage")
        assert Phase12Guardrails.needs_execution_refusal("Promise it will work")
    
    def test_execution_refusal_response(self):
        """Execution refusal should be clear."""
        refusal = Phase12Guardrails.get_execution_refusal("Run this SQL")
        
        assert "cannot execute" in refusal.lower()
        assert "cannot guarantee" in refusal.lower()


class TestEnforceAll:
    """Test master enforcement method."""
    
    def setup_method(self):
        reset_db_scope()
    
    def test_enforce_all_on_db_scoped_question(self):
        """Full enforcement on DB-scoped question."""
        # Set scope
        Phase12Guardrails.update_scope("How many critical for MIDEVSTB?")
        
        result = {
            "answer": "165837 alerts found with HIGH confidence root cause.",
            "confidence_label": "HIGH",
            "target": None
        }
        
        enforced = Phase12Guardrails.enforce_all(
            "Critical count?",
            result,
            data_used=[]
        )
        
        # Should have MEDIUM confidence (clamped)
        assert enforced["confidence_label"] == "MEDIUM"
        # Should have target set
        assert enforced["target"] == "MIDEVSTB"
    
    def test_enforce_blocks_execution(self):
        """Execution requests should be blocked first."""
        result = {"answer": "Here's how to restart"}
        
        enforced = Phase12Guardrails.enforce_all(
            "Restart the database",
            result,
            data_used=[]
        )
        
        assert enforced["intent"] == "EXECUTION_BLOCKED"
        assert "cannot execute" in enforced["answer"].lower()


class TestSelfCheck:
    """Test final self-check."""
    
    def setup_method(self):
        reset_db_scope()
    
    def test_self_check_detects_high_confidence_without_proof(self):
        """Self-check should flag HIGH confidence without proof."""
        Phase12Guardrails.update_scope("Show MIDEVSTB alerts")
        
        violations = Phase12Guardrails.self_check(
            "Root cause?",
            "The root cause is ORA-600 (HIGH confidence)"
        )
        
        assert any("HIGH confidence" in v for v in violations)
    
    def test_self_check_detects_environment_drift(self):
        """Self-check should flag environment drift."""
        Phase12Guardrails.update_scope("Critical count for MIDEVSTB?")
        
        violations = Phase12Guardrails.self_check(
            "Total?",
            "There are 649,787 alerts in the environment."
        )
        
        assert len(violations) > 0  # Should have at least one violation


class TestScreenshotScenarios:
    """
    Test exact scenarios from the screenshot:
    
    1. "This DB looks fine right?" → Should NOT return "OEM Environment Analysis"
    2. "Is ORA-600 the confirmed root cause?" → Should NOT say "HIGH Confidence"
    3. "How many unique incidents exist?" → Should NOT return "649787"
    4. "Will this cause an outage today?" → Should have predictive safety
    """
    
    def setup_method(self):
        reset_db_scope()
    
    def test_screenshot_scenario_1_db_looks_fine(self):
        """'This DB looks fine right?' after MIDEVSTB query."""
        # User first asks about MIDEVSTB
        Phase12Guardrails.update_scope("How many CRITICAL alerts exist for MIDEVSTB?")
        assert get_active_db_scope() == "MIDEVSTB"
        
        # Then asks "This DB looks fine right?"
        result = {
            "answer": "OEM Environment Analysis\n\nConfidence: HIGH",
            "confidence_label": "HIGH"
        }
        
        enforced = enforce_phase12("This DB looks fine right?", result)
        
        # Should maintain MIDEVSTB scope, not environment
        assert enforced["target"] == "MIDEVSTB"
        # Should NOT have HIGH confidence
        assert enforced["confidence_label"] == "MEDIUM"
    
    def test_screenshot_scenario_2_root_cause_high_confidence(self):
        """'Is ORA-600 the confirmed root cause?' should be MEDIUM."""
        Phase12Guardrails.update_scope("Show MIDEVSTBN alerts")
        
        result = {
            "answer": "**Root Cause (HIGH Confidence - Computed)**\n\nORA-600 [13011] is confirmed root cause.",
            "confidence_label": "HIGH"
        }
        
        enforced = enforce_phase12("Is ORA-600 the confirmed root cause?", result)
        
        # HIGH should be clamped to MEDIUM
        assert enforced["confidence_label"] == "MEDIUM"
        # "confirmed root cause" should be replaced
        assert "confirmed root cause" not in enforced["answer"].lower()
    
    def test_screenshot_scenario_3_unique_incidents(self):
        """'How many unique incidents exist?' should NOT return exact number."""
        # First set a database scope
        Phase12Guardrails.update_scope("Show alerts for MIDEVSTB")
        
        result = {
            "answer": "649787",
            "confidence_label": "HIGH"
        }
        
        enforced = enforce_phase12("How many unique incidents exist?", result)
        
        # Should have approximation language (when DB-scoped)
        assert "approximation" in enforced["answer"].lower() or "pattern" in enforced["answer"].lower()
    
    def test_screenshot_scenario_3b_no_scope_asks_clarification(self):
        """Without scope, unique incident question should ask for clarification."""
        reset_db_scope()  # No active scope
        
        result = {
            "answer": "649787",
            "confidence_label": "HIGH"
        }
        
        enforced = enforce_phase12("How many unique incidents exist?", result)
        
        # Should ask for clarification since no scope set
        assert "clarification" in enforced["answer"].lower() or "specify" in enforced["answer"].lower()
    
    def test_screenshot_scenario_4_outage_prediction(self):
        """'Will this cause an outage today?' should have safety language."""
        result = {
            "answer": "This will cause an outage.",
            "confidence_label": "HIGH"
        }
        
        enforced = enforce_phase12("Will this cause an outage today?", result)
        
        # "will cause" should be replaced with "may cause"
        assert "will cause" not in enforced["answer"].lower()
        # Should have disclaimer
        assert "based on alert data only" in enforced["answer"].lower()


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
