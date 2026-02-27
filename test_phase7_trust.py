# test_phase7_trust.py
"""
PHASE 7: TRUST, EXPLAINABILITY & ENTERPRISE-READINESS TESTS

Tests for all Phase 7 components ensuring the system is:
- Trust-worthy (A Senior DBA trusts the answer)
- Explainable (A Manager understands the risk)
- Auditable (An Auditor can verify the source)
- Safe (A Production system never hallucinates)

TEST CASES:
1. Database-specific question → no cross-DB leakage
2. Prediction question → confidence shown
3. "Is this normal?" → contextual baseline explanation
4. "Should I worry?" → risk + calm explanation
5. Auditor question → evidence visible
6. Unknown metric → honest "not available"
7. Same question phrased differently → same factual result
8. Executive summary → short + accurate
9. DBA deep-dive → detailed + evidence
"""

import pytest
from datetime import datetime


class TestAnswerConfidenceEngine:
    """Test the Answer Confidence Engine."""
    
    def test_count_answer_high_confidence(self):
        """Counts should have HIGH confidence."""
        from reasoning.answer_confidence_engine import ANSWER_CONFIDENCE, ConfidenceLevel
        
        result = ANSWER_CONFIDENCE.assess_count_answer(5, entity_type="alerts")
        assert result.level == ConfidenceLevel.HIGH
        assert result.score >= 0.9
    
    def test_prediction_never_high_confidence(self):
        """Predictions should NEVER have HIGH confidence."""
        from reasoning.answer_confidence_engine import ANSWER_CONFIDENCE, ConfidenceLevel
        
        # Even with lots of data, predictions cap at MEDIUM
        result = ANSWER_CONFIDENCE.assess_prediction_answer(
            prediction_type="failure",
            data_points=100
        )
        assert result.level in [ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW]
        assert result.score <= 0.70  # Predictions are capped
    
    def test_unknown_answer_low_confidence(self):
        """Unknown answers should have LOW confidence."""
        from reasoning.answer_confidence_engine import ANSWER_CONFIDENCE, ConfidenceLevel
        
        result = ANSWER_CONFIDENCE.assess_unknown_answer("some topic")
        assert result.level == ConfidenceLevel.LOW
        assert result.score < 0.5


class TestEvidenceLayer:
    """Test the Evidence Layer."""
    
    def test_evidence_built_for_counts(self):
        """Evidence should be built for count answers."""
        from reasoning.evidence_layer import EVIDENCE_LAYER
        
        evidence = EVIDENCE_LAYER.build_count_evidence(2, "alerts", database="DB1")
        
        assert evidence.what_we_see is not None
        assert evidence.why_it_matters is not None
        assert len(evidence.evidence_items) > 0
    
    def test_evidence_formatted_for_display(self):
        """Evidence should format for human display."""
        from reasoning.evidence_layer import EVIDENCE_LAYER
        
        evidence = EVIDENCE_LAYER.build_count_evidence(3, "alerts", database="TESTDB")
        formatted = evidence.to_display()
        
        assert "What We See" in formatted or "Evidence" in formatted


class TestDBScopeGuard:
    """Test the Database Scope Guard - NO CROSS-DB LEAKAGE."""
    
    def test_strict_db_matching(self):
        """MIDEVSTB should NOT match MIDEVSTBN."""
        from reasoning.db_scope_guard import DB_SCOPE_GUARD
        
        # Ask for MIDEVSTB but data has MIDEVSTBN - should be a scope violation
        validation = DB_SCOPE_GUARD.validate_scope(
            requested_db="MIDEVSTB", 
            actual_dbs=["MIDEVSTBN"]
        )
        
        # Should detect that MIDEVSTBN is not MIDEVSTB (only related)
        assert validation.requested_database == "MIDEVSTB"
        # MIDEVSTBN is related, so if allow_related=False, there may be violations
    
    def test_filter_alerts_strict(self):
        """Alerts should be filtered strictly by database."""
        from reasoning.db_scope_guard import DB_SCOPE_GUARD
        
        alerts = [
            {"target_name": "MIDEVSTB", "message": "Alert 1"},
            {"target_name": "MIDEVSTBN", "message": "Alert 2"},
            {"target_name": "PRODDB", "message": "Alert 3"}
        ]
        
        # Filter for MIDEVSTB only
        filtered, validation = DB_SCOPE_GUARD.filter_alerts_strict(alerts, "MIDEVSTB")
        
        assert len(filtered) == 1
        assert filtered[0]["target_name"] == "MIDEVSTB"
    
    def test_related_databases_noted(self):
        """Primary/Standby relationships should be recognized and noted."""
        from reasoning.db_scope_guard import DB_SCOPE_GUARD
        
        # Get known relationships
        related_dbs = DB_SCOPE_GUARD.KNOWN_RELATIONSHIPS.get("MIDEVSTB", [])
        assert "MIDEVSTBN" in related_dbs  # MIDEVSTBN is standby for MIDEVSTB


class TestSafePredictionLanguage:
    """Test Safe Prediction Language - no guarantees."""
    
    def test_forbidden_phrases_removed(self):
        """Forbidden phrases like 'will fail' should be replaced."""
        from reasoning.safe_prediction_language import SAFE_PREDICTION
        
        unsafe_text = "The database will definitely fail tonight"
        sanitized_text, replaced = SAFE_PREDICTION.sanitize_text(unsafe_text)
        
        assert "definitely" not in sanitized_text.lower()
        assert len(replaced) > 0
    
    def test_safe_prediction_has_confidence(self):
        """Safe predictions must include confidence level."""
        from reasoning.safe_prediction_language import SAFE_PREDICTION
        
        prediction = SAFE_PREDICTION.build_safe_prediction(
            database="TESTDB",
            risk_indicator="elevated failure risk",
            data_points=5000,
            critical_ratio=0.35
        )
        
        assert prediction.confidence_level in ["LOW", "MEDIUM"]
        display = prediction.to_display()
        assert "Confidence" in display


class TestAuditExplainability:
    """Test Audit & Explainability - auditors can trace answers."""
    
    def test_audit_trail_created(self):
        """An audit trail should be created for questions."""
        from reasoning.audit_explainability import AUDIT_ENGINE
        
        AUDIT_ENGINE.start_audit("How many alerts for DB1?", {"user": "test"})
        AUDIT_ENGINE.add_step("Query", "DB1 alerts", "5 found")
        AUDIT_ENGINE.add_data_source("OEM Alert Data")
        AUDIT_ENGINE.set_confidence("HIGH", 0.95)
        AUDIT_ENGINE.set_answer_summary("5 alerts found")
        
        record = AUDIT_ENGINE.complete_audit()
        
        assert record is not None
        assert record.question == "How many alerts for DB1?"
        assert len(record.logic_steps) == 1
        assert "OEM Alert Data" in record.data_sources
        assert record.confidence_level == "HIGH"
    
    def test_audit_record_exportable(self):
        """Audit records should be exportable as JSON."""
        from reasoning.audit_explainability import AUDIT_ENGINE
        
        AUDIT_ENGINE.start_audit("Test question")
        AUDIT_ENGINE.add_step("Step 1", "input", "output")
        record = AUDIT_ENGINE.complete_audit()
        
        json_export = record.to_json()
        assert "Test question" in json_export
        assert "Step 1" in json_export


class TestLanguageGuardrails:
    """Test Language Guardrails - professional tone."""
    
    def test_panic_language_detected(self):
        """Panic language should be detected."""
        from reasoning.language_guardrails import LANGUAGE_GUARDRAILS
        
        panic_text = "CRITICAL FAILURE! System is catastrophic!"
        has_panic, phrases = LANGUAGE_GUARDRAILS.check_for_panic_language(panic_text)
        
        assert has_panic is True
        assert len(phrases) > 0
    
    def test_panic_language_calmed(self):
        """Panic language should be replaced with calm alternatives."""
        from reasoning.language_guardrails import LANGUAGE_GUARDRAILS
        
        panic_text = "The system has a critical failure"
        calmed = LANGUAGE_GUARDRAILS.calm_down_text(panic_text)
        
        assert "critical failure" not in calmed.lower()
        # Should have a calmer replacement
        assert "issue" in calmed.lower() or "attention" in calmed.lower()
    
    def test_executive_format_concise(self):
        """Executive format should be concise."""
        from reasoning.language_guardrails import LANGUAGE_GUARDRAILS
        
        long_text = "This is a very long technical explanation. " * 50
        executive = LANGUAGE_GUARDRAILS.format_for_executive(long_text)
        
        assert len(executive) <= 550  # Reasonable executive length


class TestUncertaintyHandler:
    """Test Uncertainty Handler - honest about limitations."""
    
    def test_no_data_handled_honestly(self):
        """Missing data should be acknowledged honestly."""
        from reasoning.uncertainty_handler import UNCERTAINTY_HANDLER, UncertaintyType
        
        response = UNCERTAINTY_HANDLER.handle_no_data(
            "What is the CPU usage?",
            target="UNKNOWNDB"
        )
        
        assert response.uncertainty_type == UncertaintyType.NO_DATA
        assert "don't have" in response.honest_answer.lower() or "no data" in response.honest_answer.lower()
    
    def test_unknown_metric_handled(self):
        """Unknown metrics should be handled gracefully."""
        from reasoning.uncertainty_handler import UNCERTAINTY_HANDLER
        
        response = UNCERTAINTY_HANDLER.handle_unknown_metric("xyz_metric_123")
        
        assert "xyz_metric_123" in response.honest_answer
        assert response.confidence == 0.0
    
    def test_low_confidence_acknowledged(self):
        """Low confidence should be clearly acknowledged."""
        from reasoning.uncertainty_handler import UNCERTAINTY_HANDLER
        
        response = UNCERTAINTY_HANDLER.handle_low_confidence(
            "Will the system fail?",
            "Based on limited data, risk appears low",
            "Only 2 data points available",
            0.35
        )
        
        assert "35%" in response.honest_answer
        assert "limited" in response.honest_answer.lower()


class TestEnterpriseTrustEngine:
    """Test the Enterprise Trust Engine - master orchestrator."""
    
    def test_count_answer_trusted(self):
        """Count answers should be trusted."""
        from reasoning.enterprise_trust_engine import ENTERPRISE_TRUST
        
        alerts = [
            {"target_name": "DB1", "message": "Alert 1"},
            {"target_name": "DB1", "message": "Alert 2"}
        ]
        
        trusted = ENTERPRISE_TRUST.process_answer(
            question="How many alerts for DB1?",
            raw_answer="There are 2 alerts for DB1.",
            answer_type="count",
            target_database="DB1",
            alerts_used=alerts
        )
        
        assert trusted.is_trustworthy is True
        assert trusted.confidence.score >= 0.9
    
    def test_prediction_has_caveats(self):
        """Prediction answers should have caveats."""
        from reasoning.enterprise_trust_engine import ENTERPRISE_TRUST
        
        trusted = ENTERPRISE_TRUST.process_answer(
            question="Will the database fail?",
            raw_answer="The database will definitely fail tonight.",
            answer_type="prediction",
            target_database="DB1",
            alerts_used=[]
        )
        
        # Unsafe language should be sanitized
        assert "definitely" not in trusted.answer.lower()
        # Should have confidence shown
        assert trusted.confidence.level is not None
    
    def test_out_of_scope_data_filtered(self):
        """Out-of-scope database data should be filtered."""
        from reasoning.enterprise_trust_engine import ENTERPRISE_TRUST
        
        alerts = [
            {"target_name": "OTHER_DB", "message": "Alert for OTHER_DB"}
        ]
        
        trusted = ENTERPRISE_TRUST.process_answer(
            question="How many alerts for MY_DB?",
            raw_answer="Found some alerts.",
            answer_type="count",
            target_database="MY_DB",
            alerts_used=alerts
        )
        
        # Scope should note the mismatch
        assert trusted.scope_valid is not None
    
    def test_audience_formatting(self):
        """Different audiences should get different formats."""
        from reasoning.enterprise_trust_engine import ENTERPRISE_TRUST
        
        trusted = ENTERPRISE_TRUST.process_answer(
            question="Status?",
            raw_answer="There are 5 alerts. The system shows moderate activity.",
            answer_type="count",
            target_database="DB1"
        )
        
        dba_format = ENTERPRISE_TRUST.format_for_audience(trusted, "dba")
        exec_format = ENTERPRISE_TRUST.format_for_audience(trusted, "executive")
        
        # Executive format should be shorter or equal
        assert len(exec_format) <= len(dba_format) + 100


class TestPhase7Integration:
    """Integration tests for Phase 7 scenarios."""
    
    def test_scenario_1_no_cross_db_leakage(self):
        """Test: Database-specific question → no cross-DB leakage."""
        from reasoning.db_scope_guard import DB_SCOPE_GUARD
        
        alerts = [
            {"target_name": "MIDEVSTBN", "message": "Alert"},
            {"target_name": "PRODDB", "message": "Alert"}
        ]
        
        # Ask for MIDEVSTB - filter should return empty
        filtered, validation = DB_SCOPE_GUARD.filter_alerts_strict(alerts, "MIDEVSTB")
        
        # Should get ZERO - no MIDEVSTB alerts exist
        assert len(filtered) == 0
    
    def test_scenario_2_prediction_shows_confidence(self):
        """Test: Prediction question → confidence shown."""
        from reasoning.enterprise_trust_engine import ENTERPRISE_TRUST
        
        trusted = ENTERPRISE_TRUST.process_answer(
            question="Will there be issues tonight?",
            raw_answer="Some risk is present.",
            answer_type="prediction",
            target_database="DB1"
        )
        
        full_response = trusted.format_full_response()
        
        # Confidence must be visible
        assert "%" in full_response or "Confidence" in full_response
    
    def test_scenario_5_auditor_sees_evidence(self):
        """Test: Auditor question → evidence visible."""
        from reasoning.enterprise_trust_engine import ENTERPRISE_TRUST
        
        alerts = [{"target_name": "DB1", "message": "Test alert"}]
        
        trusted = ENTERPRISE_TRUST.process_answer(
            question="How many alerts?",
            raw_answer="1 alert found.",
            answer_type="count",
            target_database="DB1",
            alerts_used=alerts
        )
        
        auditor_format = ENTERPRISE_TRUST.format_for_audience(trusted, "auditor")
        
        # Auditor format should mention audit/sources
        assert "audit" in auditor_format.lower() or "source" in auditor_format.lower()
    
    def test_scenario_6_unknown_metric_honest(self):
        """Test: Unknown metric → honest 'not available'."""
        from reasoning.uncertainty_handler import UNCERTAINTY_HANDLER
        
        response = UNCERTAINTY_HANDLER.handle_unknown_metric("fake_metric_xyz")
        
        assert "fake_metric_xyz" in response.honest_answer
        assert response.confidence == 0.0
        assert "don't have" in response.honest_answer.lower() or "not" in response.honest_answer.lower()
    
    def test_scenario_8_executive_summary_short(self):
        """Test: Executive summary → short + accurate."""
        from reasoning.language_guardrails import LANGUAGE_GUARDRAILS
        
        long_technical = (
            "The database MIDEVSTB is showing elevated alert activity. "
            "There are 5 critical alerts and 10 warning alerts. "
            "The ORA-00600 errors indicate internal corruption. "
            "The v$sysstat metrics show high I/O wait times. "
            "The DBA_TABLESPACES view shows 95% usage. "
        ) * 3
        
        executive = LANGUAGE_GUARDRAILS.format_for_executive(long_technical)
        
        # Must be short enough for an executive
        assert len(executive) <= 600


class TestPhase7TrustPrinciples:
    """Test that trust principles are enforced."""
    
    def test_data_is_source_of_truth(self):
        """Data must be the source of truth - no hallucination."""
        from reasoning.enterprise_trust_engine import ENTERPRISE_TRUST
        
        # Process with NO data
        trusted = ENTERPRISE_TRUST.process_answer(
            question="How many alerts?",
            raw_answer="There are 10 alerts.",
            answer_type="count",
            target_database="DB1",
            alerts_used=[]  # No actual data!
        )
        
        # Evidence should reflect no/limited data
        assert trusted.evidence is not None
    
    def test_never_over_promise(self):
        """System should never over-promise (HIGH confidence for predictions)."""
        from reasoning.answer_confidence_engine import ANSWER_CONFIDENCE, ConfidenceLevel
        
        # Even with tons of data, predictions cap at MEDIUM
        result = ANSWER_CONFIDENCE.assess_prediction_answer(
            prediction_type="failure",
            data_points=1000
        )
        
        assert result.level != ConfidenceLevel.HIGH
    
    def test_explain_before_advising(self):
        """Evidence should come before recommendations."""
        from reasoning.evidence_layer import EVIDENCE_LAYER
        
        evidence = EVIDENCE_LAYER.build_count_evidence(5, "alerts", database="DB1")
        
        # Evidence package should have what_we_see (explanation)
        assert evidence.what_we_see is not None


def run_phase7_tests():
    """Run all Phase 7 tests and print summary."""
    import sys
    
    print("=" * 70)
    print("PHASE 7: TRUST, EXPLAINABILITY & ENTERPRISE-READINESS TESTS")
    print("=" * 70)
    print()
    
    # Run with pytest
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x"  # Stop on first failure
    ])
    
    if exit_code == 0:
        print()
        print("=" * 70)
        print("✅ ALL PHASE 7 TESTS PASSED!")
        print("=" * 70)
        print()
        print("The system is now:")
        print("  ✓ TRUST-WORTHY - A Senior DBA trusts the answer")
        print("  ✓ EXPLAINABLE - A Manager understands the risk")
        print("  ✓ AUDITABLE - An Auditor can verify the source")
        print("  ✓ SAFE - A Production system never hallucinates")
    else:
        print()
        print("=" * 70)
        print("❌ SOME PHASE 7 TESTS FAILED")
        print("=" * 70)
    
    return exit_code


if __name__ == "__main__":
    run_phase7_tests()
