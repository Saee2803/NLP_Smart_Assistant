# sla/sla_tracker.py
"""
SLA Tracking Engine

Tracks SLA compliance, detects breaches, explains root causes.
Integrates with health score and predictions.

Python 3.6 compatible.
"""

from datetime import datetime, timedelta
from sla_config import SLAConfig, SLAConfigManager


class SLAMetrics(object):
    """Current SLA metrics for a target."""
    
    def __init__(self, target, sla_config):
        """
        Initialize metrics container.
        
        Args:
            target: Database/service name
            sla_config: SLAConfig instance
        """
        self.target = target
        self.sla_config = sla_config
        
        # Calculated metrics
        self.availability_pct = 100.0
        self.incident_count = 0
        self.mean_mttr_minutes = 0
        self.max_mttr_minutes = 0
        self.total_downtime_minutes = 0
        
        # Status
        self.breached = False
        self.breach_reasons = []
        self.breach_severity = 'NONE'  # NONE, LOW, MEDIUM, HIGH, CRITICAL
    
    def check_breach(self):
        """
        Check if SLA is breached.
        
        Returns:
            (breached, reasons, severity)
        """
        self.breach_reasons = []
        
        # Check availability
        if self.availability_pct < self.sla_config.availability_pct:
            gap = self.sla_config.availability_pct - self.availability_pct
            self.breach_reasons.append(
                'Availability {0:.1f}% (target {1:.1f}%, gap {2:.1f}%)'.format(
                    self.availability_pct,
                    self.sla_config.availability_pct,
                    gap
                )
            )
        
        # Check incident count
        if self.incident_count > self.sla_config.max_incidents:
            excess = self.incident_count - self.sla_config.max_incidents
            self.breach_reasons.append(
                '{0} incidents (target {1}, excess {2})'.format(
                    self.incident_count,
                    self.sla_config.max_incidents,
                    excess
                )
            )
        
        # Check MTTR
        if self.mean_mttr_minutes > self.sla_config.max_mttr_minutes:
            excess = self.mean_mttr_minutes - self.sla_config.max_mttr_minutes
            self.breach_reasons.append(
                'Mean MTTR {0:.0f} min (target {1} min, excess {2:.0f} min)'.format(
                    self.mean_mttr_minutes,
                    self.sla_config.max_mttr_minutes,
                    excess
                )
            )
        
        # Determine severity
        self.breached = len(self.breach_reasons) > 0
        
        if not self.breached:
            self.breach_severity = 'NONE'
        elif len(self.breach_reasons) == 1:
            # Single breach
            if self.incident_count > self.sla_config.max_incidents * 2:
                self.breach_severity = 'CRITICAL'
            elif self.availability_pct < self.sla_config.availability_pct * 0.95:
                self.breach_severity = 'CRITICAL'
            elif self.mean_mttr_minutes > self.sla_config.max_mttr_minutes * 2:
                self.breach_severity = 'HIGH'
            else:
                self.breach_severity = 'MEDIUM'
        else:
            # Multiple breaches
            self.breach_severity = 'HIGH'
        
        return (self.breached, self.breach_reasons, self.breach_severity)
    
    def to_dict(self):
        """Convert to dict for reporting."""
        return {
            'target': self.target,
            'availability_pct': self.availability_pct,
            'availability_target': self.sla_config.availability_pct,
            'incident_count': self.incident_count,
            'incident_limit': self.sla_config.max_incidents,
            'mean_mttr_minutes': self.mean_mttr_minutes,
            'max_mttr_minutes': self.sla_config.max_mttr_minutes,
            'total_downtime_minutes': self.total_downtime_minutes,
            'breached': self.breached,
            'breach_reasons': self.breach_reasons,
            'breach_severity': self.breach_severity,
            'window': self.sla_config.window
        }


class SLATracker(object):
    """
    Tracks SLA compliance across all targets.
    """
    
    def __init__(self, db, health_scorer=None, predictor=None):
        """
        Initialize tracker.
        
        Args:
            db: Database instance
            health_scorer: Optional DatabaseHealthScorer for context
            predictor: Optional TimeAwarePredictor for context
        """
        self.db = db
        self.config_manager = SLAConfigManager(db)
        self.health_scorer = health_scorer
        self.predictor = predictor
    
    # =====================================================
    # SLA CONFIGURATION
    # =====================================================
    
    def set_sla(self, target, sla_config):
        """Set SLA config for target."""
        self.config_manager.set_sla(sla_config)
    
    def get_sla(self, target):
        """Get SLA config for target."""
        return self.config_manager.get_sla(target)
    
    def set_standard_sla(self, target):
        """Apply standard SLA preset."""
        from sla_config import SLAPresets
        config = SLAPresets.standard(target)
        self.set_sla(target, config)
    
    def set_critical_sla(self, target):
        """Apply critical SLA preset."""
        from sla_config import SLAPresets
        config = SLAPresets.critical(target)
        self.set_sla(target, config)
    
    # =====================================================
    # COMPLIANCE TRACKING
    # =====================================================
    
    def calculate_availability(self, target, days=1):
        """
        Calculate availability % for target.
        
        Args:
            target: Database/service name
            days: Lookback days
        
        Returns:
            Availability percentage (0-100)
        """
        try:
            total_incidents = self.db.get_incidents(target, days=days)
            
            if not total_incidents:
                return 100.0
            
            # Calculate downtime
            total_downtime = 0
            for incident in total_incidents:
                # Get duration from timestamp to last_seen
                first_seen = incident.get('timestamp')
                last_seen = incident.get('last_seen', first_seen)
                
                # Simple duration calculation
                try:
                    if isinstance(first_seen, str):
                        # Parse timestamps
                        start_time = datetime.strptime(
                            first_seen[:19], '%Y-%m-%d %H:%M:%S'
                        )
                        end_time = datetime.strptime(
                            last_seen[:19], '%Y-%m-%d %H:%M:%S'
                        )
                        duration = (end_time - start_time).total_seconds() / 60.0
                    else:
                        duration = incident.get('duration_minutes', 30)
                    
                    total_downtime += duration
                except Exception:
                    total_downtime += 30  # Assume 30 min default
            
            # Calculate availability
            total_minutes = days * 24 * 60
            uptime_minutes = total_minutes - total_downtime
            availability = (uptime_minutes / float(total_minutes)) * 100.0
            
            return max(0, min(100, availability))
        
        except Exception:
            return 100.0
    
    def get_sla_status(self, target, days=1):
        """
        Get current SLA status for target.
        
        Args:
            target: Database/service name
            days: Lookback window
        
        Returns:
            SLAMetrics object
        """
        # Get SLA config
        config = self.get_sla(target)
        if not config:
            return None
        
        # Create metrics object
        metrics = SLAMetrics(target, config)
        
        # Calculate metrics
        metrics.availability_pct = self.calculate_availability(target, days=days)
        
        incidents = self.db.get_incidents(target, days=days)
        metrics.incident_count = len(incidents)
        
        # Calculate MTTR
        if incidents:
            total_mttr = 0
            max_mttr = 0
            
            for incident in incidents:
                try:
                    first_seen = incident.get('timestamp')
                    last_seen = incident.get('last_seen', first_seen)
                    
                    if isinstance(first_seen, str):
                        start_time = datetime.strptime(
                            first_seen[:19], '%Y-%m-%d %H:%M:%S'
                        )
                        end_time = datetime.strptime(
                            last_seen[:19], '%Y-%m-%d %H:%M:%S'
                        )
                        mttr = (end_time - start_time).total_seconds() / 60.0
                    else:
                        mttr = incident.get('duration_minutes', 30)
                    
                    total_mttr += mttr
                    max_mttr = max(max_mttr, mttr)
                except Exception:
                    total_mttr += 30
                    max_mttr = max(max_mttr, 30)
            
            metrics.mean_mttr_minutes = total_mttr / float(len(incidents))
            metrics.max_mttr_minutes = max_mttr
            metrics.total_downtime_minutes = total_mttr
        
        # Check for breach
        metrics.check_breach()
        
        return metrics
    
    def get_all_sla_status(self, days=1):
        """
        Get SLA status for all configured targets.
        
        Args:
            days: Lookback window
        
        Returns:
            List of SLAMetrics
        """
        all_slas = self.config_manager.get_all_slas()
        results = []
        
        for config in all_slas:
            metrics = self.get_sla_status(config.target, days=days)
            if metrics:
                results.append(metrics)
        
        return results
    
    # =====================================================
    # BREACH EXPLANATION
    # =====================================================
    
    def explain_breach(self, target, days=1):
        """
        Explain SLA breach in context of health and predictions.
        
        Args:
            target: Database/service name
            days: Lookback window
        
        Returns:
            Explanation dict with context
        """
        metrics = self.get_sla_status(target, days=days)
        
        if not metrics or not metrics.breached:
            return {
                'target': target,
                'breached': False,
                'explanation': 'SLA is compliant'
            }
        
        explanation = []
        explanation.append('SLA BREACHED for {0} ({1})'.format(
            target, metrics.breach_severity
        ))
        explanation.append('')
        
        # Reasons for breach
        explanation.append('Breach Reasons:')
        for reason in metrics.breach_reasons:
            explanation.append('  - {0}'.format(reason))
        
        explanation.append('')
        
        # Context from health scorer
        if self.health_scorer:
            try:
                health = self.health_scorer.score_database(target, days=days)
                health_score = health.get('health_score', 50)
                health_state = health.get('health_state', 'UNKNOWN')
                
                explanation.append('Health Context:')
                explanation.append('  Score: {0}/100 ({1})'.format(
                    health_score, health_state
                ))
                
                top_issues = health.get('top_issues', [])
                if top_issues:
                    explanation.append('  Top Issues:')
                    for issue in top_issues[:2]:
                        explanation.append('    - {0}: {1}'.format(
                            issue.get('component', '?'),
                            issue.get('explanation', '')
                        ))
            except Exception:
                pass
        
        explanation.append('')
        
        # Predictions
        if self.predictor:
            try:
                pred = self.predictor.predict_high_risk_window(target)
                if pred:
                    explanation.append('Predicted Risk:')
                    explanation.append('  High-risk window: {0} on {1}'.format(
                        pred.get('hour_window', '?'),
                        pred.get('day_window', '?')
                    ))
                    explanation.append('  Confidence: {0:.0%}'.format(
                        pred.get('combined_confidence', 0)
                    ))
            except Exception:
                pass
        
        return {
            'target': target,
            'breached': True,
            'severity': metrics.breach_severity,
            'metrics': metrics.to_dict(),
            'explanation': '\n'.join(explanation)
        }
