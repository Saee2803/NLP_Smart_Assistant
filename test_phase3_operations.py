# test_phase3_operations.py
"""
Phase 3 Operations Tests

Tests for:
- SLA Tracking and Compliance
- Automated Reporting
- Auto-Remediation Framework

Python 3.6 compatible unit tests.
"""

import unittest
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sla'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reporting'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'remediation'))


# Mock database
class MockDatabase(object):
    """Mock database for testing."""
    
    def __init__(self):
        self.incidents = []
        self.anomalies = []
    
    def get_incidents(self, target=None, days=7):
        """Get incidents."""
        results = self.incidents
        if target:
            results = [i for i in results if i.get('target') == target]
        return results
    
    def get_anomalies(self, target=None, days=7):
        """Get anomalies."""
        results = self.anomalies
        if target:
            results = [a for a in results if a.get('target') == target]
        return results
    
    def query(self, sql, params=None):
        """Query mock database."""
        if 'sla_configs' in sql and 'SELECT' in sql:
            return [
                {
                    'target': 'DB_TEST',
                    'availability_pct': 99.0,
                    'max_incidents': 5,
                    'max_mttr_minutes': 30,
                    'window': 'daily',
                    'enabled': True
                }
            ]
        return []
    
    def execute(self, sql, params=None):
        """Execute mock database."""
        pass


# =====================================================
# TEST: SLA Configuration
# =====================================================

class TestSLAConfig(unittest.TestCase):
    """Tests for SLA configuration."""
    
    def test_sla_config_creation(self):
        """Test SLA config creation."""
        from sla_config import SLAConfig
        
        config = SLAConfig(
            target='FINDB',
            availability_pct=99.5,
            max_incidents=3,
            max_mttr_minutes=20
        )
        
        self.assertEqual(config.target, 'FINDB')
        self.assertEqual(config.availability_pct, 99.5)
        self.assertEqual(config.max_incidents, 3)
    
    def test_sla_presets(self):
        """Test SLA presets."""
        from sla_config import SLAPresets
        
        critical = SLAPresets.critical('FINDB')
        self.assertEqual(critical.availability_pct, 99.9)
        self.assertEqual(critical.max_incidents, 2)
        
        standard = SLAPresets.standard('FINDB')
        self.assertEqual(standard.availability_pct, 99.0)
    
    def test_sla_config_serialization(self):
        """Test SLA config to/from dict."""
        from sla_config import SLAConfig
        
        original = SLAConfig('FINDB', 99.0, 5, 30, 'daily')
        config_dict = original.to_dict()
        restored = SLAConfig.from_dict(config_dict)
        
        self.assertEqual(restored.target, original.target)
        self.assertEqual(restored.availability_pct, original.availability_pct)


# =====================================================
# TEST: SLA Tracker
# =====================================================

class TestSLATracker(unittest.TestCase):
    """Tests for SLA tracking."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.db = MockDatabase()
        
        # Add test incidents
        for i in range(6):
            self.db.incidents.append({
                'target': 'DB_TEST',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'last_seen': (datetime.now() + timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M:%S'),
                'severity': 'HIGH',
                'description': 'Test incident'
            })
        
        from sla_tracker import SLATracker
        self.tracker = SLATracker(self.db)
    
    def test_sla_tracking_availability(self):
        """Test availability calculation."""
        availability = self.tracker.calculate_availability('DB_TEST', days=1)
        
        self.assertGreaterEqual(availability, 0)
        self.assertLessEqual(availability, 100)
    
    def test_sla_breach_detection(self):
        """Test SLA breach detection."""
        self.tracker.set_standard_sla('DB_TEST')
        status = self.tracker.get_sla_status('DB_TEST', days=1)
        
        self.assertIsNotNone(status)
        # Should breach due to >5 incidents
        self.assertTrue(status.breached)
        self.assertIn('incident', str(status.breach_reasons).lower())
    
    def test_sla_status_dict(self):
        """Test SLA status dict conversion."""
        self.tracker.set_standard_sla('DB_TEST')
        status = self.tracker.get_sla_status('DB_TEST', days=1)
        
        status_dict = status.to_dict()
        
        self.assertIn('availability_pct', status_dict)
        self.assertIn('incident_count', status_dict)
        self.assertIn('breached', status_dict)


# =====================================================
# TEST: Report Generation
# =====================================================

class TestReportGeneration(unittest.TestCase):
    """Tests for report generation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.db = MockDatabase()
        self.db.incidents.append({
            'target': 'DB_TEST',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'severity': 'HIGH',
            'description': 'Test incident'
        })
    
    def test_daily_report_generation(self):
        """Test daily incident report."""
        from report_generator import DailyIncidentReport
        
        generator = DailyIncidentReport(self.db)
        report = generator.generate()
        
        text = report.to_text()
        self.assertIn('Daily Incident Summary', text)
        self.assertIn('DB_TEST', text)
    
    def test_report_text_format(self):
        """Test text format report."""
        from report_generator import DailyIncidentReport
        
        generator = DailyIncidentReport(self.db)
        report = generator.generate()
        
        text = report.to_text()
        self.assertGreater(len(text), 100)
        self.assertIn('Overview', text)
    
    def test_report_json_format(self):
        """Test JSON format report."""
        from report_generator import DailyIncidentReport
        
        generator = DailyIncidentReport(self.db)
        report = generator.generate()
        
        json_str = report.to_json()
        self.assertGreater(len(json_str), 20)
        self.assertIn('metadata', json_str)
    
    def test_report_builder_sections(self):
        """Test report builder."""
        from report_generator import ReportBuilder
        
        builder = ReportBuilder('Test Report')
        builder.add_section('Test Section', ['Line 1', 'Line 2'])
        
        self.assertEqual(len(builder.sections), 1)
        self.assertEqual(builder.sections[0]['name'], 'Test Section')


# =====================================================
# TEST: Remediation Actions
# =====================================================

class TestRemediationActions(unittest.TestCase):
    """Tests for remediation actions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.incident = {
            'target': 'DB_TEST',
            'severity': 'CRITICAL',
            'description': 'Memory usage high'
        }
    
    def test_action_registration(self):
        """Test action registry."""
        from remediation_actions import RemediationActionRegistry
        
        registry = RemediationActionRegistry()
        
        self.assertGreater(len(registry.list_actions()), 0)
        self.assertIsNotNone(registry.get_action('restart_service'))
    
    def test_restart_action_dry_run(self):
        """Test restart action dry-run."""
        from remediation_actions import RestartServiceAction
        
        action = RestartServiceAction()
        result = action.dry_run('DB_TEST', self.incident)
        
        self.assertEqual(result['mode'], 'DRY_RUN')
        self.assertIn('expected_duration_seconds', result)
    
    def test_restart_action_execution(self):
        """Test restart action execution."""
        from remediation_actions import RestartServiceAction
        
        action = RestartServiceAction()
        result = action.execute('DB_TEST', self.incident)
        
        self.assertEqual(result['mode'], 'EXECUTE')
        self.assertEqual(result['status'], 'executed')
    
    def test_cache_action_safe(self):
        """Test cache clear is safe."""
        from remediation_actions import ClearCacheAction
        
        action = ClearCacheAction()
        self.assertEqual(action.risk_level, 'SAFE')
        
        result = action.dry_run('DB_TEST', self.incident)
        self.assertIn('expected_freed_mb', result)
    
    def test_action_applicable_filtering(self):
        """Test action applicability."""
        from remediation_actions import RemediationActionRegistry
        
        registry = RemediationActionRegistry()
        
        # Memory action should apply to memory incidents
        applicable = registry.get_applicable_actions(
            'DB_TEST',
            {'severity': 'HIGH', 'description': 'Memory usage high'}
        )
        
        # Should have some applicable actions
        self.assertGreater(len(applicable), 0)


# =====================================================
# TEST: Remediation Engine
# =====================================================

class TestRemediationEngine(unittest.TestCase):
    """Tests for remediation engine."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.db = MockDatabase()
        self.incident = {
            'target': 'DB_TEST',
            'severity': 'CRITICAL',
            'description': 'Service down'
        }
        
        from remediation_engine import RemediationEngine
        self.engine = RemediationEngine(self.db)
    
    def test_remediation_proposal(self):
        """Test remediation proposal."""
        proposal = self.engine.propose_remediation('DB_TEST', self.incident)
        
        self.assertEqual(proposal.target, 'DB_TEST')
        self.assertGreater(len(proposal.proposed_actions), 0)
    
    def test_dry_run_action(self):
        """Test action dry-run."""
        result = self.engine.dry_run_action('DB_TEST', self.incident, 'notify_oncall')
        
        self.assertEqual(result['mode'], 'DRY_RUN')
        self.assertEqual(result['status'], 'would_execute')
    
    def test_auto_execution_disabled_by_default(self):
        """Test auto-execution is disabled by default."""
        self.assertFalse(self.engine.auto_execute_enabled)
    
    def test_enable_auto_execution(self):
        """Test enabling auto-execution."""
        self.engine.enable_auto_execution()
        self.assertTrue(self.engine.auto_execute_enabled)
        
        self.engine.disable_auto_execution()
        self.assertFalse(self.engine.auto_execute_enabled)
    
    def test_audit_logging(self):
        """Test audit logging."""
        self.engine.dry_run_action('DB_TEST', self.incident, 'notify_oncall')
        
        logs = self.engine.get_audit_log('DB_TEST')
        self.assertGreater(len(logs), 0)
        self.assertEqual(logs[-1]['mode'], 'DRY_RUN')
    
    def test_action_execution_flow(self):
        """Test complete action execution flow."""
        # Propose
        proposal = self.engine.propose_remediation('DB_TEST', self.incident)
        self.assertGreater(len(proposal.proposed_actions), 0)
        
        # Get first applicable action
        applicable = self.engine.get_applicable_actions('DB_TEST', self.incident)
        if applicable:
            action_id = applicable[0].action_id
            
            # Dry-run
            dry_result = self.engine.dry_run_action('DB_TEST', self.incident, action_id)
            self.assertEqual(dry_result['mode'], 'DRY_RUN')


# =====================================================
# MAIN TEST RUNNER
# =====================================================

if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestSLAConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestSLATracker))
    suite.addTests(loader.loadTestsFromTestCase(TestReportGeneration))
    suite.addTests(loader.loadTestsFromTestCase(TestRemediationActions))
    suite.addTests(loader.loadTestsFromTestCase(TestRemediationEngine))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
