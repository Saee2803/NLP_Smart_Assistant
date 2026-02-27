# incident_engine/multi_cause_rca.py
"""
Multi-Cause Root Cause Analysis Engine

Identifies multiple contributing factors to incidents.
Weights causes by frequency, severity, and temporal proximity.
Provides ranked list with confidence scores.

Python 3.6 compatible.
"""

from datetime import datetime, timedelta
from collections import defaultdict


class MultiCauseRCA(object):
    """
    Performs comprehensive RCA detecting multiple causes.
    """
    
    def __init__(self, db, anomaly_detector=None):
        """
        Initialize multi-cause RCA.
        
        Args:
            db: Database instance (from storage.database)
            anomaly_detector: Optional AnomalyDetector for metric analysis
        """
        self.db = db
        self.anomaly_detector = anomaly_detector
    
    # =====================================================
    # PRIMARY API
    # =====================================================
    
    def analyze_incident(self, incident):
        """
        Analyze a single incident to identify all contributing causes.
        
        Args:
            incident: Incident dict with target, first_seen, last_seen, severity
        
        Returns:
            Dict with ranked causes, confidence, evidence
        """
        target = incident.get('target')
        first_seen_str = incident.get('first_seen')
        last_seen_str = incident.get('last_seen')
        
        if isinstance(first_seen_str, str):
            first_seen = datetime.fromisoformat(first_seen_str)
        else:
            first_seen = first_seen_str
        
        if isinstance(last_seen_str, str):
            last_seen = datetime.fromisoformat(last_seen_str)
        else:
            last_seen = last_seen_str
        
        duration_minutes = (last_seen - first_seen).total_seconds() / 60.0
        
        # Collect all potential causes
        causes = []
        
        # 1. Metric anomalies during incident
        metric_causes = self._find_anomalous_metrics(target, first_seen, last_seen)
        causes.extend(metric_causes)
        
        # 2. Similar historical incidents
        pattern_causes = self._find_recurring_patterns(target, incident)
        causes.extend(pattern_causes)
        
        # 3. Alert patterns
        alert_causes = self._find_alert_combinations(target, first_seen, last_seen)
        causes.extend(alert_causes)
        
        # 4. Severity-based causes
        severity_causes = self._infer_causes_from_severity(incident)
        causes.extend(severity_causes)
        
        # Weight and rank causes
        ranked_causes = self._rank_causes(causes)
        
        return {
            'target': target,
            'incident_duration_minutes': duration_minutes,
            'incident_period': '{0} to {1}'.format(
                first_seen.isoformat(),
                last_seen.isoformat()
            ),
            'causes': ranked_causes,
            'primary_cause': ranked_causes[0] if ranked_causes else None,
            'total_causes_identified': len(ranked_causes),
            'evidence_summary': self._summarize_evidence(ranked_causes)
        }
    
    # =====================================================
    # CAUSE DETECTION STRATEGIES
    # =====================================================
    
    def _find_anomalous_metrics(self, target, first_seen, last_seen):
        """
        Find metrics that were anomalous during the incident.
        
        Returns:
            List of cause dicts
        """
        causes = []
        
        if not self.anomaly_detector:
            return causes
        
        try:
            # Get metrics during incident period
            window_minutes = int((last_seen - first_seen).total_seconds() / 60.0) + 30
            metrics = self.db.get_metrics(target=target, days=1)
            
            # Filter to incident window
            incident_metrics = [
                m for m in metrics
                if (isinstance(m.get('metric_time'), str) and 
                    datetime.fromisoformat(m.get('metric_time')) >= first_seen and
                    datetime.fromisoformat(m.get('metric_time')) <= last_seen)
                or (not isinstance(m.get('metric_time'), str) and
                    m.get('metric_time') >= first_seen and
                    m.get('metric_time') <= last_seen)
            ]
            
            # Check each metric for anomaly
            metric_names = set()
            for metric in incident_metrics:
                metric_name = metric.get('metric_name')
                value = metric.get('value')
                
                if metric_name not in metric_names and value is not None:
                    metric_names.add(metric_name)
                    
                    try:
                        is_anomalous, z_score = self.anomaly_detector.is_anomaly(
                            target, metric_name, float(value)
                        )
                        
                        if is_anomalous:
                            # Get baseline for comparison
                            mean, stddev, samples = self.anomaly_detector.get_rolling_baseline(
                                target, metric_name
                            )
                            
                            causes.append({
                                'cause_type': 'METRIC_ANOMALY',
                                'cause_name': metric_name,
                                'confidence': min(0.99, z_score / 4.0),  # Normalize z-score to confidence
                                'severity': 'CRITICAL' if z_score > 4.0 else 'HIGH' if z_score > 3.0 else 'MEDIUM',
                                'evidence': '{0} was {1:.1f}x std dev above baseline ({2:.1f} vs {3:.1f})'.format(
                                    metric_name, z_score, value, mean
                                ),
                                'frequency': 'Once during incident',
                                'temporal_proximity': 'Concurrent with incident',
                                'weighting_factors': {
                                    'z_score': z_score,
                                    'baseline': mean,
                                    'observed': value
                                }
                            })
                    except (ValueError, TypeError):
                        pass
        
        except Exception:
            pass
        
        return causes
    
    def _find_recurring_patterns(self, target, incident):
        """
        Find historical patterns similar to this incident.
        
        Returns:
            List of cause dicts
        """
        causes = []
        
        try:
            patterns = self.db.get_patterns(target=target)
            
            incident_type = incident.get('issue_type')
            
            for pattern in patterns:
                if pattern['confidence'] >= 0.60:  # Only high-confidence patterns
                    causes.append({
                        'cause_type': 'RECURRING_PATTERN',
                        'cause_name': pattern.get('pattern_value'),
                        'pattern_type': pattern.get('pattern_type'),
                        'confidence': pattern.get('confidence'),
                        'evidence': pattern.get('evidence'),
                        'frequency': 'Observed {0} times previously'.format(
                            pattern.get('incident_count')
                        ),
                        'temporal_proximity': 'Similar to historical pattern',
                        'weighting_factors': {
                            'incident_count': pattern.get('incident_count'),
                            'pattern_confidence': pattern.get('confidence')
                        }
                    })
        
        except Exception:
            pass
        
        return causes
    
    def _find_alert_combinations(self, target, first_seen, last_seen):
        """
        Find combinations of alerts that co-occurred during incident.
        
        Returns:
            List of cause dicts
        """
        causes = []
        
        try:
            # Get alerts during incident window
            alerts = self.db.get_alerts(target=target, days=1)
            
            incident_alerts = []
            for alert in alerts:
                alert_time = alert.get('alert_time')
                if isinstance(alert_time, str):
                    alert_time = datetime.fromisoformat(alert_time)
                
                if alert_time >= first_seen and alert_time <= last_seen:
                    incident_alerts.append(alert)
            
            if len(incident_alerts) >= 2:
                # Extract unique alert messages
                alert_messages = {}
                for alert in incident_alerts:
                    msg = alert.get('message', 'unknown')
                    if msg not in alert_messages:
                        alert_messages[msg] = 0
                    alert_messages[msg] += 1
                
                # Create combined cause
                if len(alert_messages) > 1:
                    combined_msg = ' + '.join(list(alert_messages.keys())[:3])
                    
                    causes.append({
                        'cause_type': 'ALERT_COMBINATION',
                        'cause_name': combined_msg,
                        'confidence': 0.70,  # High confidence for multi-alert
                        'evidence': '{0} alerts detected concurrently'.format(len(incident_alerts)),
                        'frequency': '{0} alert types'.format(len(alert_messages)),
                        'temporal_proximity': 'Concurrent throughout incident',
                        'weighting_factors': {
                            'alert_count': len(incident_alerts),
                            'alert_types': len(alert_messages)
                        }
                    })
        
        except Exception:
            pass
        
        return causes
    
    def _infer_causes_from_severity(self, incident):
        """
        Infer likely causes based on incident severity and type.
        
        Returns:
            List of cause dicts
        """
        causes = []
        
        severity = incident.get('severity')
        issue_type = incident.get('issue_type')
        
        severity_to_causes = {
            'CRITICAL': ['Resource exhaustion', 'Service crash', 'Cascading failure'],
            'HIGH': ['Performance degradation', 'Connection timeout', 'Memory leak'],
            'MEDIUM': ['Threshold exceeded', 'Anomalous metric', 'Repeated error'],
            'LOW': ['Transient issue', 'Monitoring glitch', 'Expected behavior']
        }
        
        likely_causes = severity_to_causes.get(severity, [])
        
        for cause_name in likely_causes:
            causes.append({
                'cause_type': 'INFERRED_FROM_SEVERITY',
                'cause_name': cause_name,
                'confidence': 0.50,  # Lower confidence for inferred causes
                'evidence': 'Severity {0} often associated with {1}'.format(severity, cause_name),
                'frequency': 'Generic for severity level',
                'temporal_proximity': 'Matches incident severity',
                'weighting_factors': {}
            })
        
        return causes
    
    # =====================================================
    # CAUSE RANKING
    # =====================================================
    
    def _rank_causes(self, causes):
        """
        Rank causes by weighted score.
        
        Factors:
        - Confidence (direct)
        - Type weight (metric anomalies > patterns > inferred)
        - Frequency (how often seen before)
        - Temporal proximity (during vs before incident)
        
        PRODUCTION CALIBRATION: When metrics are sparse, reduce metric weight
        and increase alert/pattern weight.
        
        Returns:
            Sorted list of causes (highest confidence first)
        """
        # PRODUCTION CALIBRATION: Detect if metric evidence is sparse
        metric_causes = [c for c in causes if c.get('cause_type') == 'METRIC_ANOMALY']
        alert_causes = [c for c in causes if c.get('cause_type') == 'ALERT_COMBINATION']
        pattern_causes = [c for c in causes if c.get('cause_type') == 'RECURRING_PATTERN']
        
        metrics_sparse = len(metric_causes) == 0 and (len(alert_causes) > 0 or len(pattern_causes) > 0)
        
        if metrics_sparse:
            # Sparse metrics: boost alert and pattern confidence
            type_weights = {
                'METRIC_ANOMALY': 1.0,
                'ALERT_COMBINATION': 0.95,  # Boosted from 0.85
                'RECURRING_PATTERN': 0.90,   # Boosted from 0.80
                'INFERRED_FROM_SEVERITY': 0.60  # Boosted from 0.50
            }
        else:
            # Normal: metric-heavy weighting
            type_weights = {
                'METRIC_ANOMALY': 1.0,
                'ALERT_COMBINATION': 0.85,
                'RECURRING_PATTERN': 0.80,
                'INFERRED_FROM_SEVERITY': 0.50
            }
        
        for cause in causes:
            cause_type = cause.get('cause_type')
            type_weight = type_weights.get(cause_type, 0.5)
            
            # Base confidence
            base_confidence = cause.get('confidence', 0.5)
            
            # Type adjustment
            adjusted_confidence = base_confidence * type_weight
            
            # Temporal proximity bonus
            if cause.get('temporal_proximity') == 'Concurrent with incident':
                adjusted_confidence *= 1.1
            
            cause['weighted_confidence'] = min(0.99, adjusted_confidence)
            cause['display_confidence'] = '{0:.0f}%'.format(adjusted_confidence * 100)
        
        # Sort by weighted confidence
        ranked = sorted(causes, key=lambda x: x['weighted_confidence'], reverse=True)
        
        return ranked
    
    def _summarize_evidence(self, causes):
        """Create readable summary of all evidence."""
        if not causes:
            return 'No clear causes identified. Recommend deeper investigation.'
        
        summary_parts = []
        for i, cause in enumerate(causes, 1):
            summary_parts.append(
                '{0}. {1} ({2}) - {3}'.format(
                    i,
                    cause['cause_name'],
                    cause['display_confidence'],
                    cause['evidence']
                )
            )
        
        return '\n'.join(summary_parts)
    
    # =====================================================
    # BATCH ANALYSIS
    # =====================================================
    
    def analyze_all_incidents(self, target):
        """
        Analyze all recent incidents for a target.
        
        Returns:
            Dict with incidents and their analyses
        """
        incidents = self.db.get_incidents(target=target, days=7)
        
        analyses = []
        for incident in incidents:
            try:
                analysis = self.analyze_incident(incident)
                analyses.append(analysis)
            except Exception:
                pass
        
        return {
            'target': target,
            'total_incidents_analyzed': len(analyses),
            'analyses': analyses,
            'common_causes': self._summarize_common_causes(analyses)
        }
    
    def _summarize_common_causes(self, analyses):
        """Find causes that appear across multiple incidents."""
        cause_frequency = defaultdict(int)
        cause_confidence = defaultdict(float)
        
        for analysis in analyses:
            for cause in analysis['causes']:
                cause_name = cause['cause_name']
                cause_frequency[cause_name] += 1
                cause_confidence[cause_name] += cause['weighted_confidence']
        
        # Average confidence and sort
        common = []
        for cause_name in cause_frequency:
            avg_confidence = cause_confidence[cause_name] / cause_frequency[cause_name]
            common.append({
                'cause': cause_name,
                'frequency': cause_frequency[cause_name],
                'avg_confidence': avg_confidence
            })
        
        return sorted(common, key=lambda x: x['frequency'], reverse=True)[:5]
