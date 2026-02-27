# test_incident_commander.py
"""
Test suite for Phase 9: Autonomous DBA Incident Commander.

Tests the Incident Command Mode queries:
- Incident Status
- Priority/Triage
- Next Actions
- Escalation
- Predictions
- Blast Radius
"""

import pytest
from reasoning.incident_commander import INCIDENT_COMMANDER, IncidentCommander


class TestIncidentCommanderCore:
    """Test core Incident Commander functionality."""
    
    @pytest.fixture
    def mock_alerts(self):
        """Create mock alerts for testing."""
        alerts = []
        # MIDEVSTBN - 200k critical
        for _ in range(200000):
            alerts.append({
                'target_name': 'MIDEVSTBN',
                'severity': 'CRITICAL',
                'message': 'ORA-600 internal error',
                'issue_type': 'INTERNAL_ERROR'
            })
        # MIDEVSTB - 100k warnings
        for _ in range(100000):
            alerts.append({
                'target_name': 'MIDEVSTB',
                'severity': 'WARNING',
                'message': 'Standby apply lag',
                'issue_type': 'DATAGUARD'
            })
        return alerts
    
    def test_assess_production_state(self, mock_alerts):
        """Test that assessment returns all required fields."""
        assessment = INCIDENT_COMMANDER.assess_production_state(mock_alerts)
        
        assert "incident_status" in assessment
        assert "priorities" in assessment
        assert "actions" in assessment
        assert "predictions" in assessment
        assert "escalation" in assessment
    
    def test_incident_status_detection(self, mock_alerts):
        """Test that critical volume triggers ACTIVE_INCIDENT."""
        assessment = INCIDENT_COMMANDER.assess_production_state(mock_alerts)
        
        status = assessment.get("incident_status", {})
        assert status.get("status") == "ACTIVE_INCIDENT"
        assert status.get("severity") == "CRITICAL"
    
    def test_priority_ranking(self, mock_alerts):
        """Test that priorities are ranked correctly (P1 assigned)."""
        assessment = INCIDENT_COMMANDER.assess_production_state(mock_alerts)
        
        priorities = assessment.get("priorities", [])
        assert len(priorities) > 0
        
        # First priority should be P1
        p1 = priorities[0]
        assert p1["priority"] == "P1"
        assert p1["database"] == "MIDEVSTBN"  # Highest critical count
    
    def test_single_p1(self, mock_alerts):
        """Test that only ONE P1 is assigned."""
        assessment = INCIDENT_COMMANDER.assess_production_state(mock_alerts)
        
        priorities = assessment.get("priorities", [])
        p1_count = sum(1 for p in priorities if p["priority"] == "P1")
        
        assert p1_count == 1, "Only ONE P1 should be assigned"
    
    def test_actions_structure(self, mock_alerts):
        """Test that actions have do_now, can_wait, do_not_touch."""
        assessment = INCIDENT_COMMANDER.assess_production_state(mock_alerts)
        
        actions = assessment.get("actions", {})
        assert "do_now" in actions
        assert "can_wait" in actions
        assert "do_not_touch" in actions
    
    def test_escalation_required(self, mock_alerts):
        """Test that escalation is recommended for critical incidents."""
        assessment = INCIDENT_COMMANDER.assess_production_state(mock_alerts)
        
        escalation = assessment.get("escalation", {})
        assert escalation.get("needed") is True
        assert len(escalation.get("targets", [])) > 0


class TestIncidentCommanderOutput:
    """Test Incident Commander output formatting."""
    
    @pytest.fixture
    def mock_alerts(self):
        """Create mock alerts for testing."""
        return [
            {'target_name': 'MIDEVSTBN', 'severity': 'CRITICAL', 'message': 'ORA-600', 'issue_type': 'INTERNAL_ERROR'}
        ] * 100000
    
    def test_format_dba_audience(self, mock_alerts):
        """Test DBA-targeted output contains technical details."""
        assessment = INCIDENT_COMMANDER.assess_production_state(mock_alerts)
        output = INCIDENT_COMMANDER.format_incident_response(assessment, audience="DBA")
        
        assert "INCIDENT STATUS" in output
        assert "PRIORITY" in output or "P1" in output
        assert "EVIDENCE" in output
    
    def test_format_manager_audience(self, mock_alerts):
        """Test Manager-targeted output is less technical."""
        assessment = INCIDENT_COMMANDER.assess_production_state(mock_alerts)
        output = INCIDENT_COMMANDER.format_incident_response(assessment, audience="MANAGER")
        
        assert "WHAT THIS MEANS" in output
        assert "blast radius" in output.lower() or "affected" in output.lower()
    
    def test_suggested_question(self, mock_alerts):
        """Test that a next question is suggested."""
        assessment = INCIDENT_COMMANDER.assess_production_state(mock_alerts)
        
        question = INCIDENT_COMMANDER.get_suggested_question(assessment)
        assert question is not None
        assert len(question) > 10


class TestIncidentCommanderSafety:
    """Test Incident Commander safety features."""
    
    def test_no_data_handling(self):
        """Test handling of empty alert list."""
        assessment = INCIDENT_COMMANDER.assess_production_state([])
        
        status = assessment.get("incident_status", {})
        assert status.get("status") == "NO_DATA"
    
    def test_prediction_has_confidence(self):
        """Test that predictions include confidence levels."""
        alerts = [
            {'target_name': 'DB1', 'severity': 'CRITICAL', 'message': 'error', 'issue_type': 'ERROR'}
        ] * 50000
        
        assessment = INCIDENT_COMMANDER.assess_production_state(alerts)
        predictions = assessment.get("predictions", [])
        
        for pred in predictions:
            assert "confidence" in pred
            assert pred["confidence"] in ["HIGH", "MEDIUM", "LOW"]
    
    def test_prediction_has_evidence(self):
        """Test that predictions include evidence."""
        alerts = [
            {'target_name': 'DB1', 'severity': 'CRITICAL', 'message': 'ORA-600', 'issue_type': 'INTERNAL_ERROR'}
        ] * 50000
        
        assessment = INCIDENT_COMMANDER.assess_production_state(alerts)
        predictions = assessment.get("predictions", [])
        
        for pred in predictions:
            assert "evidence" in pred
            assert len(pred["evidence"]) > 0


class TestIncidentCommanderSubsystems:
    """Test subsystem detection."""
    
    def test_data_guard_detection(self):
        """Test Data Guard subsystem detection."""
        alerts = [
            {'target_name': 'DB1', 'severity': 'CRITICAL', 'message': 'standby apply failed', 'issue_type': 'DATAGUARD'}
        ] * 1000
        
        assessment = INCIDENT_COMMANDER.assess_production_state(alerts)
        subsystems = assessment.get("subsystem_status", {})
        
        assert "DATA_GUARD" in subsystems
    
    def test_internal_error_detection(self):
        """Test internal error subsystem detection."""
        alerts = [
            {'target_name': 'DB1', 'severity': 'CRITICAL', 'message': 'ORA-00600 internal error', 'issue_type': 'INTERNAL_ERROR'}
        ] * 1000
        
        assessment = INCIDENT_COMMANDER.assess_production_state(alerts)
        subsystems = assessment.get("subsystem_status", {})
        
        assert "INTERNAL" in subsystems


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
