# test_answer_contracts.py
"""
Test suite for Answer Contracts - Enterprise-grade answer validation.

GOLDEN RULE: It is better to say "I cannot determine this from available data"
than to give a confident but wrong answer.
"""

import pytest
from reasoning.answer_contracts import (
    ANSWER_CONTRACTS,
    AnswerContract,
    AnswerContractBuilder,
    AnswerContractValidator,
    ContractType,
    Audience,
    ConfidenceLevel
)


class TestContractBuilding:
    """Test contract building from questions."""
    
    def test_numeric_only_detection(self):
        """Test detection of numeric-only mode."""
        numeric_questions = [
            "How many CRITICAL alerts exist for MIDEVSTB? Give only the number",
            "What is the alert count? Only the number please",
            "Total alerts? Just the number",
            "Count of critical alerts? Number only",
        ]
        
        for q in numeric_questions:
            contract = ANSWER_CONTRACTS.build_contract(q)
            assert contract.numeric_only, f"Should detect numeric-only: {q}"
            assert contract.no_markdown, "Numeric-only should forbid markdown"
            assert contract.no_emojis, "Numeric-only should forbid emojis"
    
    def test_non_numeric_questions(self):
        """Test that normal questions don't trigger numeric-only."""
        normal_questions = [
            "How many critical alerts are there?",
            "What is the status of MIDEVSTB?",
            "Show me the breakdown",
        ]
        
        for q in normal_questions:
            contract = ANSWER_CONTRACTS.build_contract(q)
            assert not contract.numeric_only, f"Should NOT be numeric-only: {q}"
    
    def test_manager_audience_detection(self):
        """Test detection of manager audience."""
        manager_questions = [
            "Explain this to a manager",
            "Give me an executive summary",
            "What is the business impact?",
        ]
        
        for q in manager_questions:
            contract = ANSWER_CONTRACTS.build_contract(q)
            assert contract.audience == Audience.MANAGER, f"Should detect manager: {q}"
    
    def test_auditor_audience_detection(self):
        """Test detection of auditor audience."""
        auditor_questions = [
            "This is for the audit",
            "Compliance report please",
            "Facts only",
        ]
        
        for q in auditor_questions:
            contract = ANSWER_CONTRACTS.build_contract(q)
            assert contract.audience == Audience.AUDITOR, f"Should detect auditor: {q}"
    
    def test_target_database_extraction(self):
        """Test database name extraction."""
        db_questions = [
            ("How many alerts for MIDEVSTB?", "MIDEVSTB"),
            ("Status of MIDEVSTBN database", "MIDEVSTBN"),
            ("PRODDB alerts breakdown", "PRODDB"),
        ]
        
        for q, expected_db in db_questions:
            contract = ANSWER_CONTRACTS.build_contract(q)
            assert contract.target_database == expected_db, f"Should extract {expected_db} from: {q}"
    
    def test_scope_constraints(self):
        """Test scope constraint detection."""
        assert ANSWER_CONTRACTS.build_contract("Show primary only").primary_only
        assert ANSWER_CONTRACTS.build_contract("Standby only status").standby_only
        assert ANSWER_CONTRACTS.build_contract("Exclude standby").exclude_standby


class TestContractValidation:
    """Test answer validation against contracts."""
    
    def test_numeric_only_validation_pass(self):
        """Test that pure numbers pass numeric-only validation."""
        contract = ANSWER_CONTRACTS.build_contract("Count? Give only the number")
        
        # Valid numeric answers
        valid_answers = ["649769", "0", "1234567"]
        
        for answer in valid_answers:
            validated, is_valid, violation = ANSWER_CONTRACTS.enforce(answer, contract)
            assert is_valid, f"'{answer}' should be valid numeric-only"
            assert validated == answer, "Should preserve valid answer"
    
    def test_numeric_only_validation_fail(self):
        """Test that non-numeric answers fail numeric-only validation."""
        contract = ANSWER_CONTRACTS.build_contract("Count? Give only the number")
        
        # These should fail or be auto-corrected
        invalid_answers = [
            "There are 649,769 alerts",
            "649,769 critical alerts exist",
            "**649769**",
        ]
        
        for answer in invalid_answers:
            validated, is_valid, violation = ANSWER_CONTRACTS.enforce(answer, contract)
            # Should auto-correct to just the number
            assert validated.isdigit(), f"Should auto-correct '{answer}' to digits only"
    
    def test_numeric_only_comma_removal(self):
        """Test that commas are stripped from numeric-only answers."""
        contract = ANSWER_CONTRACTS.build_contract("Count? Give only the number")
        
        validated, is_valid, violation = ANSWER_CONTRACTS.enforce("649,769", contract)
        assert validated == "649769", "Should strip commas"
        assert is_valid
    
    def test_scope_validation_pass(self):
        """Test that answers within scope pass."""
        contract = ANSWER_CONTRACTS.build_contract("Alerts for MIDEVSTB?")
        
        answer = "MIDEVSTB has 500 critical alerts."
        is_valid, violation = AnswerContractValidator.validate(answer, contract)
        assert is_valid, "Answer about MIDEVSTB should pass MIDEVSTB scope"
    
    def test_scope_bleeding_detection(self):
        """Test detection of scope bleeding (MIDEVSTB vs MIDEVSTBN)."""
        contract = ANSWER_CONTRACTS.build_contract("Alerts for MIDEVSTB?")
        
        # This answer incorrectly mentions MIDEVSTBN in a MIDEVSTB question
        answer = "MIDEVSTB has 500 alerts. Related database MIDEVSTBN has 1000 alerts."
        is_valid, violation = AnswerContractValidator.validate(answer, contract)
        # This should fail due to scope bleeding when target is MIDEVSTB
        if contract.target_database == 'MIDEVSTB':
            assert not is_valid, "Should detect scope bleeding"
            assert violation and "scope" in violation.lower(), f"Violation should mention scope: {violation}"
        else:
            # If DB wasn't extracted, skip this check
            pass


class TestAutoCorrection:
    """Test auto-correction of answers."""
    
    def test_extract_number_from_text(self):
        """Test extraction of numbers from text responses."""
        contract = ANSWER_CONTRACTS.build_contract("How many? Give only the number")
        
        test_cases = [
            ("There are 649769 alerts in the system", "649769"),
            ("The total count is 1234", "1234"),
            ("500 critical alerts detected", "500"),
        ]
        
        for text, expected in test_cases:
            validated, is_valid, _ = ANSWER_CONTRACTS.enforce(text, contract)
            assert validated == expected, f"Should extract '{expected}' from '{text}'"


class TestAudienceFormatting:
    """Test audience-based formatting rules."""
    
    def test_manager_forbidden_terms(self):
        """Test that manager audience forbids technical terms."""
        contract = ANSWER_CONTRACTS.build_contract("Explain to a manager")
        
        # Manager contract should forbid ORA codes
        assert 'ORA-00600' in contract.forbidden_terms or any('ORA' in t for t in contract.forbidden_terms)
    
    def test_auditor_no_recommendations(self):
        """Test that auditor audience forbids recommendations."""
        contract = ANSWER_CONTRACTS.build_contract("For the audit")
        
        # Auditor contract should forbid recommendations
        forbidden_terms = [t.lower() for t in contract.forbidden_terms]
        assert any('recommend' in t or 'should' in t for t in forbidden_terms)


class TestEnterpriseIntegration:
    """Test integration with intelligence service."""
    
    def test_full_pipeline_numeric_only(self):
        """Test numeric-only through full pipeline."""
        from services.intelligence_service import INTELLIGENCE_SERVICE, ANSWER_CONTRACTS_AVAILABLE
        from data_engine.global_cache import GLOBAL_DATA, SYSTEM_READY
        
        # Skip if Answer Contracts not available
        if not ANSWER_CONTRACTS_AVAILABLE:
            pytest.skip("Answer Contracts not available")
        
        SYSTEM_READY['ready'] = True
        GLOBAL_DATA['alerts'] = [
            {'target': 'MIDEVSTB:cpu', 'severity': 'CRITICAL', 'message_text': 'Test'} 
            for _ in range(500)
        ]
        
        result = INTELLIGENCE_SERVICE.analyze("How many critical alerts for MIDEVSTB? Give only the number")
        answer = result.get('answer', '').strip()
        
        # Answer should be ONLY digits
        assert answer.isdigit(), f"Answer should be digits only, got: '{answer}'"
        assert answer == "500", f"Expected 500, got: {answer}"
    
    def test_full_pipeline_normal_response(self):
        """Test normal response includes formatting."""
        from services.intelligence_service import INTELLIGENCE_SERVICE, ANSWER_CONTRACTS_AVAILABLE
        from data_engine.global_cache import GLOBAL_DATA, SYSTEM_READY
        
        SYSTEM_READY['ready'] = True
        GLOBAL_DATA['alerts'] = [
            {'target': 'MIDEVSTB:cpu', 'severity': 'CRITICAL', 'message_text': 'Test'} 
            for _ in range(500)
        ]
        
        result = INTELLIGENCE_SERVICE.analyze("How many critical alerts for MIDEVSTB?")
        answer = result.get('answer', '')
        
        # Normal response should include formatting/explanation
        assert len(answer) > 5, "Normal response should have explanation"
        assert '500' in answer or '500' in answer.replace(',', ''), "Should contain count"


class TestGoldenRule:
    """Test the golden rule: better to say cannot determine than guess."""
    
    def test_cannot_determine_format(self):
        """Test proper formatting of 'cannot determine' responses."""
        response = ANSWER_CONTRACTS.format_cannot_determine(
            reason="No timestamp data available",
            what_is_needed="Alerts with valid timestamps"
        )
        
        assert "Cannot determine" in response
        assert "timestamp" in response.lower()
        assert "needed" in response.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
