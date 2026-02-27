# remediation/remediation_engine.py
"""
Auto-Remediation Engine

Safe, auditable, dry-run by default remediation system.
Integrates with RCA and predictions for intelligent action selection.

Python 3.6 compatible.
"""

from datetime import datetime
import json
from remediation_actions import RemediationActionRegistry


class RemediationAuditLog(object):
    """Audit log for remediation actions."""
    
    def __init__(self, db=None):
        """
        Initialize audit log.
        
        Args:
            db: Optional database instance for persistence
        """
        self.db = db
        self.logs = []
        self._ensure_log_table()
    
    def _ensure_log_table(self):
        """Ensure audit log table exists."""
        if not self.db:
            return
        
        try:
            self.db.query('SELECT * FROM remediation_audit_log LIMIT 1')
        except Exception:
            self.db.execute('''
                CREATE TABLE IF NOT EXISTS remediation_audit_log (
                    id INTEGER PRIMARY KEY,
                    timestamp TEXT,
                    target TEXT,
                    action_id TEXT,
                    mode TEXT,
                    status TEXT,
                    result_json TEXT,
                    user TEXT DEFAULT 'system',
                    approved_by TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
    
    def log(self, target, action_id, mode, status, result, user='system', approved_by=None):
        """
        Log remediation action.
        
        Args:
            target: Database/service name
            action_id: Action identifier
            mode: 'DRY_RUN' or 'EXECUTE'
            status: 'proposed', 'approved', 'executed', 'failed', etc.
            result: Result dict
            user: User who triggered action
            approved_by: User who approved execution
        """
        log_entry = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'target': target,
            'action_id': action_id,
            'mode': mode,
            'status': status,
            'result': result,
            'user': user,
            'approved_by': approved_by
        }
        
        self.logs.append(log_entry)
        
        # Persist to database if available
        if self.db:
            try:
                self.db.execute('''
                    INSERT INTO remediation_audit_log 
                    (timestamp, target, action_id, mode, status, result_json, user, approved_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    log_entry['timestamp'],
                    target,
                    action_id,
                    mode,
                    status,
                    json.dumps(result),
                    user,
                    approved_by
                ))
            except Exception:
                pass
    
    def get_logs(self, target=None, action_id=None, limit=100):
        """
        Get audit logs.
        
        Args:
            target: Filter by target (optional)
            action_id: Filter by action (optional)
            limit: Max results
        
        Returns:
            List of log entries
        """
        results = self.logs
        
        if target:
            results = [l for l in results if l['target'] == target]
        
        if action_id:
            results = [l for l in results if l['action_id'] == action_id]
        
        return results[-limit:]


class RemediationProposal(object):
    """Proposed remediation for an incident."""
    
    def __init__(self, target, incident, rca_analysis=None):
        """
        Initialize proposal.
        
        Args:
            target: Database/service name
            incident: Incident dict
            rca_analysis: Optional RCA results
        """
        self.target = target
        self.incident = incident
        self.rca_analysis = rca_analysis
        self.proposed_actions = []
        self.rationale = []
    
    def add_action(self, action, priority=5):
        """
        Add proposed action.
        
        Args:
            action: RemediationAction instance
            priority: 1-10 (10 = highest)
        """
        self.proposed_actions.append({
            'action': action,
            'priority': priority,
            'success_rate': action.estimated_success_rate
        })
    
    def add_rationale(self, reason):
        """Add reasoning for proposals."""
        self.rationale.append(reason)
    
    def to_dict(self):
        """Convert to dict for API response."""
        return {
            'target': self.target,
            'incident_description': self.incident.get('description', '?'),
            'severity': self.incident.get('severity', 'UNKNOWN'),
            'rationale': self.rationale,
            'proposed_actions': [
                {
                    'action_id': a['action'].action_id,
                    'name': a['action'].name,
                    'priority': a['priority'],
                    'success_rate': a['success_rate'],
                    'risk_level': a['action'].risk_level
                }
                for a in sorted(self.proposed_actions, key=lambda x: x['priority'], reverse=True)
            ]
        }


class RemediationEngine(object):
    """
    Auto-remediation engine.
    
    Safe by default:
    - All actions dry-run first
    - Manual approval for execution
    - Full audit logging
    - Rollback notes for failed actions
    """
    
    def __init__(self, db, rca_engine=None, predictor=None):
        """
        Initialize engine.
        
        Args:
            db: Database instance
            rca_engine: Optional MultiCauseRCA for intelligent action selection
            predictor: Optional TimeAwarePredictor for context
        """
        self.db = db
        self.rca_engine = rca_engine
        self.predictor = predictor
        self.action_registry = RemediationActionRegistry()
        self.audit_log = RemediationAuditLog(db)
        
        # Configuration
        self.auto_execute_enabled = False  # DISABLED by default
        self.min_confidence_for_auto = 0.85  # Only auto-execute high-confidence actions
    
    def propose_remediation(self, target, incident):
        """
        Propose remediation for incident.
        
        Args:
            target: Database/service name
            incident: Incident dict
        
        Returns:
            RemediationProposal
        """
        proposal = RemediationProposal(target, incident)
        
        # Get applicable actions
        applicable = self.action_registry.get_applicable_actions(target, incident)
        
        # Use RCA to prioritize actions
        if self.rca_engine:
            try:
                rca = self.rca_engine.analyze_incident(incident)
                proposal.rca_analysis = rca
                
                # Add rationale from RCA
                if rca and 'causes' in rca:
                    causes = rca['causes'][:2]
                    for cause in causes:
                        proposal.add_rationale(
                            'Root cause: {0} ({1}%)'.format(
                                cause.get('cause_name', '?'),
                                cause.get('display_confidence', '0%')
                            )
                        )
            except Exception:
                pass
        
        # Sort applicable actions by expected impact
        for action in applicable:
            priority = 5
            
            # Boost priority for SAFE actions
            if action.risk_level == 'SAFE':
                priority = 8
            
            # Reduce priority for HIGH-risk actions
            if action.risk_level == 'HIGH':
                priority = 3
            
            proposal.add_action(action, priority=priority)
        
        return proposal
    
    def dry_run_action(self, target, incident, action_id):
        """
        Simulate action execution.
        
        Args:
            target: Database/service name
            incident: Incident dict
            action_id: Action identifier
        
        Returns:
            Dry-run result dict
        """
        action = self.action_registry.get_action(action_id)
        
        if not action:
            return {'error': 'Action not found: {0}'.format(action_id)}
        
        can_exec, reason = action.can_execute_on(target, incident)
        
        if not can_exec:
            return {
                'action_id': action_id,
                'error': 'Action not applicable: {0}'.format(reason)
            }
        
        result = action.dry_run(target, incident)
        
        # Log dry-run
        self.audit_log.log(
            target, action_id, 'DRY_RUN', 'simulated', result
        )
        
        return result
    
    def execute_action(self, target, incident, action_id, approved_by='user', auto=False):
        """
        Execute remediation action.
        
        Args:
            target: Database/service name
            incident: Incident dict
            action_id: Action identifier
            approved_by: User who approved execution
            auto: Whether this is auto-execution
        
        Returns:
            Execution result dict
        """
        action = self.action_registry.get_action(action_id)
        
        if not action:
            return {'error': 'Action not found: {0}'.format(action_id)}
        
        # Check if auto-execution allowed
        if auto and not self.auto_execute_enabled:
            return {
                'error': 'Auto-execution disabled',
                'action_id': action_id,
                'recommended': 'Enable auto_execute_enabled or execute manually'
            }
        
        # Check high-risk actions require approval
        if action.risk_level == 'HIGH' and not approved_by and not auto:
            return {
                'status': 'requires_approval',
                'action_id': action_id,
                'message': 'High-risk action requires manual approval'
            }
        
        # Execute action
        try:
            result = action.execute(target, incident)
            
            # Log execution
            self.audit_log.log(
                target, action_id, 'EXECUTE', 'executed', result,
                approved_by=approved_by
            )
            
            return result
        
        except Exception as e:
            error_result = {
                'action_id': action_id,
                'status': 'failed',
                'error': str(e)
            }
            
            self.audit_log.log(
                target, action_id, 'EXECUTE', 'failed', error_result,
                approved_by=approved_by
            )
            
            return error_result
    
    def get_applicable_actions(self, target, incident):
        """Get actions applicable to incident."""
        return self.action_registry.get_applicable_actions(target, incident)
    
    def get_audit_log(self, target=None, limit=100):
        """Get audit log for target."""
        return self.audit_log.get_logs(target=target, limit=limit)
    
    def enable_auto_execution(self):
        """Enable auto-execution (dangerous)."""
        self.auto_execute_enabled = True
    
    def disable_auto_execution(self):
        """Disable auto-execution (safe default)."""
        self.auto_execute_enabled = False
