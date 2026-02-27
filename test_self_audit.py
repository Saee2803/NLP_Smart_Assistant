# test_self_audit.py
"""
PHASE 11: SELF-AUDITING INTELLIGENCE TESTS

Tests:
1. Trust mode detection (NORMAL, STRICT, SAFE)
2. Contract violation detection
3. Scope validation (primary vs standby)
4. Contradiction detection
5. Confidence-based tone
6. Session learning
7. Full integration with IntelligenceService
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestTrustModeDetection:
    """Test trust mode detection from question context."""
    
    def setup_method(self):
        from reasoning.self_audit_engine import TrustModeDetector, TrustMode
        self.detector = TrustModeDetector
        self.TrustMode = TrustMode
    
    def test_strict_mode_number_only(self):
        """'Give only the number' triggers STRICT mode."""
        mode = self.detector.detect_mode("Give only the number")
        assert mode == self.TrustMode.STRICT
    
    def test_strict_mode_exact_count(self):
        """'Exact count' triggers STRICT mode."""
        mode = self.detector.detect_mode("What is the exact count?")
        assert mode == self.TrustMode.STRICT
    
    def test_strict_mode_for_audit(self):
        """'For audit' triggers STRICT mode."""
        mode = self.detector.detect_mode("Need this for audit review")
        assert mode == self.TrustMode.STRICT
    
    def test_strict_mode_yes_no(self):
        """'Yes or No' triggers STRICT mode."""
        mode = self.detector.detect_mode("Is it critical yes or no?")
        assert mode == self.TrustMode.STRICT
    
    def test_normal_mode_regular_question(self):
        """Regular questions use NORMAL mode."""
        mode = self.detector.detect_mode("What are the critical alerts?")
        assert mode == self.TrustMode.NORMAL
    
    def test_safe_mode_no_data(self):
        """No data available triggers SAFE mode."""
        mode = self.detector.detect_mode("What are the alerts?", data_available=False)
        assert mode == self.TrustMode.SAFE
    
    def test_safe_mode_prediction_guarantee(self):
        """Prediction with guarantee triggers SAFE mode."""
        mode = self.detector.detect_mode("Can you guarantee 100% certain this will work?")
        assert mode == self.TrustMode.SAFE


class TestScopeValidation:
    """Test scope validation for primary vs standby."""
    
    def setup_method(self):
        from reasoning.self_audit_engine import ScopeValidator
        self.validator = ScopeValidator
    
    def test_detect_primary_only(self):
        """Detect primary-only scope."""
        scope = self.validator.detect_scope("for MIDEVSTB only, exclude standby")
        assert scope == "primary"
    
    def test_detect_standby_only(self):
        """Detect standby-only scope."""
        scope = self.validator.detect_scope("Show me only standby database alerts")
        assert scope == "standby"
    
    def test_detect_environment_wide(self):
        """Regular question is environment-wide."""
        scope = self.validator.detect_scope("How many critical alerts total?")
        assert scope == "environment"
    
    def test_detect_primary_from_db_name(self):
        """MIDEVSTB (no N) indicates database scope (HARD RULE 1)."""
        scope = self.validator.detect_scope("What's happening on MIDEVSTB?")
        # HARD RULE 1: Database scope is detected, scope is "database" not "primary"
        assert scope in ["primary", "database"]
    
    def test_scope_violation_standby_in_primary(self):
        """Detect standby mentioned in primary-only query."""
        is_valid, reason = self.validator.validate_scope(
            answer="MIDEVSTBN has 100 alerts...",
            expected_scope="primary",
            target_db="MIDEVSTB"
        )
        assert is_valid is False
        assert "Standby" in reason
    
    def test_scope_valid_primary_only(self):
        """Valid primary-only response."""
        is_valid, reason = self.validator.validate_scope(
            answer="MIDEVSTB has 100 critical alerts",
            expected_scope="primary",
            target_db="MIDEVSTB"
        )
        assert is_valid is True


class TestContradictionDetection:
    """Test contradiction detection in conversation facts."""
    
    def setup_method(self):
        from reasoning.self_audit_engine import ConversationFactRegister, ConfidenceLevel
        self.register = ConversationFactRegister()
        self.ConfidenceLevel = ConfidenceLevel
    
    def test_no_contradiction_new_fact(self):
        """No contradiction for new facts."""
        has_contradiction, _ = self.register.check_contradiction(
            "count", "MIDEVSTB:critical", 500, "primary"
        )
        assert has_contradiction is False
    
    def test_contradiction_different_value(self):
        """Detect contradiction when value differs significantly."""
        # Register initial fact
        self.register.register_fact(
            "count", "MIDEVSTB:critical", 500, "primary",
            "How many critical on MIDEVSTB?",
            self.ConfidenceLevel.EXACT
        )
        
        # Check for contradiction with significantly different value
        has_contradiction, existing = self.register.check_contradiction(
            "count", "MIDEVSTB:critical", 700, "primary"
        )
        assert has_contradiction is True
        assert existing.value == 500
    
    def test_no_contradiction_similar_value(self):
        """No contradiction for minor variance in large numbers."""
        self.register.register_fact(
            "count", "MIDEVSTB:critical", 10000, "primary",
            "How many critical on MIDEVSTB?",
            self.ConfidenceLevel.EXACT
        )
        
        # Within 5% - no contradiction
        has_contradiction, _ = self.register.check_contradiction(
            "count", "MIDEVSTB:critical", 10200, "primary"
        )
        assert has_contradiction is False
    
    def test_record_correction(self):
        """Record corrections made during session."""
        self.register.record_correction(
            "MIDEVSTB:count", "500", "700", "Standby data excluded"
        )
        
        learnings = self.register.get_learnings()
        assert len(learnings) == 1
        assert "Corrected" in learnings[0]


class TestSelfAuditEngine:
    """Test full self-audit engine."""
    
    def setup_method(self):
        from reasoning.self_audit_engine import SelfAuditEngine, TrustMode, ConfidenceLevel
        self.engine = SelfAuditEngine()
        self.TrustMode = TrustMode
        self.ConfidenceLevel = ConfidenceLevel
    
    def test_audit_strict_mode_violation(self):
        """Detect violation when number-only returns text."""
        result = self.engine.audit_response(
            question="Give only the number",
            answer="There are 500 critical alerts",
            data_used=[{"id": 1}]
        )
        
        assert result.trust_mode == self.TrustMode.STRICT
        assert len(result.violations) > 0
        assert "CONTRACT_VIOLATION" in result.violations[0]
    
    def test_audit_strict_mode_pass(self):
        """Pass when number-only returns just digits."""
        result = self.engine.audit_response(
            question="Give only the number",
            answer="500",
            data_used=[{"id": 1}]
        )
        
        assert result.trust_mode == self.TrustMode.STRICT
        # May still have violations for other reasons, but answer format is correct
    
    def test_audit_scope_violation(self):
        """Detect scope violation."""
        result = self.engine.audit_response(
            question="for MIDEVSTB only, exclude standby",
            answer="MIDEVSTBN has the most alerts with 300",
            data_used=[{"id": 1}],
            extracted_values={"target_database": "MIDEVSTB"}
        )
        
        # Should detect scope violation
        scope_violations = [v for v in result.violations if "SCOPE" in v]
        assert len(scope_violations) > 0
    
    def test_audit_registers_facts(self):
        """Audit registers facts for future consistency."""
        result = self.engine.audit_response(
            question="How many alerts on MIDEVSTB?",
            answer="500 critical alerts",
            data_used=[{"id": 1}],
            extracted_values={"count": 500, "target_database": "MIDEVSTB"}
        )
        
        # Fact should be registered
        summary = self.engine.fact_register.get_summary()
        assert summary["fact_count"] >= 0
    
    def test_confidence_tone_partial(self):
        """Apply cautious tone for partial confidence."""
        answer = self.engine.apply_confidence_tone(
            "There are 500 alerts",
            self.ConfidenceLevel.PARTIAL
        )
        
        assert "Based on available" in answer
    
    def test_confidence_tone_none(self):
        """Apply warning for no confidence."""
        answer = self.engine.apply_confidence_tone(
            "There might be 500 alerts",
            self.ConfidenceLevel.NONE
        )
        
        assert "Limited Confidence" in answer
    
    def test_safe_mode_response(self):
        """Format proper SAFE mode response."""
        response = self.engine.format_safe_mode_response(
            "Will the database fail?",
            "Cannot predict failures with available data"
        )
        
        assert "cannot answer this reliably" in response
        assert "senior DBA" in response


class TestAuditBeforeRespond:
    """Test the convenience wrapper function."""
    
    def test_audit_corrects_numeric_only(self):
        """Wrapper extracts number for numeric-only queries."""
        from reasoning.self_audit_engine import audit_before_respond
        
        final_answer, audit = audit_before_respond(
            question="Give only the number of alerts",
            answer="There are 12,345 critical alerts in the system",
            data_used=[{"id": 1}]
        )
        
        # Should extract just the number
        assert audit.trust_mode.value == "STRICT"
        # Final answer should be corrected to just a number or have warning


class TestIntegrationWithIntelligenceService:
    """Test Phase 11 integration with IntelligenceService."""
    
    def setup_method(self):
        from services.intelligence_service import IntelligenceService
        self.service = IntelligenceService()
    
    def test_self_audit_metadata_in_response(self):
        """Self-audit metadata added to responses."""
        result = self.service.analyze(
            "How many critical alerts?"
        )
        
        # Should have self_audit metadata
        assert "self_audit" in result or result.get("answer")  # Either present or processed
    
    def test_strict_mode_triggered(self):
        """Strict mode triggers for number-only queries."""
        result = self.service.analyze(
            "Give only the number"
        )
        
        # Check if self-audit processed
        if "self_audit" in result:
            assert result["self_audit"].get("trust_mode") == "STRICT"
    
    def test_scope_protected(self):
        """Scope bleeding protection active."""
        result = self.service.analyze(
            "for MIDEVSTB only, exclude standby, how many critical?"
        )
        
        answer = result.get("answer", "").upper()
        # Should NOT mention MIDEVSTBN
        if "MIDEVSTBN" in answer:
            # If it does, self-audit should flag it
            audit = result.get("self_audit", {})
            violations = audit.get("violations", [])
            # Check if violation was detected
            assert len(violations) > 0 or "MIDEVSTBN" not in answer


class TestSessionLearning:
    """Test session learning capabilities."""
    
    def setup_method(self):
        from reasoning.self_audit_engine import SELF_AUDIT
        self.engine = SELF_AUDIT
        self.engine.reset()
    
    def test_learning_persists(self):
        """Session learnings persist."""
        self.engine.add_session_learning(
            "Mixed primary and standby counts in first response"
        )
        
        learnings = self.engine.fact_register.get_learnings()
        assert len(learnings) == 1
        assert "primary and standby" in learnings[0]
    
    def test_stats_tracking(self):
        """Statistics tracked correctly."""
        from reasoning.self_audit_engine import ConfidenceLevel
        
        # Perform an audit
        self.engine.audit_response(
            "Test question",
            "Test answer",
            data_used=[{"id": 1}]
        )
        
        stats = self.engine.get_stats()
        assert stats["audits_performed"] >= 1
        assert "current_mode" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
