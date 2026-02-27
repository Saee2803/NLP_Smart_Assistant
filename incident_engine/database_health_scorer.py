# incident_engine/database_health_scorer.py
"""
Composite Database Health Scoring Engine

Single 0-100 health score per database considering:
- Incident frequency
- Severity distribution
- Risk trend direction
- Mean Time To Recovery (MTTR)
- Recommendation success rate
- Anomaly frequency

Explainable breakdown. Python 3.6 compatible.
"""

from datetime import datetime, timedelta
from collections import defaultdict


class DatabaseHealthScorer(object):
    """
    Computes single health score (0-100) for each database.
    """
    
    def __init__(self, db):
        """
        Initialize health scorer.
        
        Args:
            db: Database instance (from storage.database)
        """
        self.db = db
    
    # =====================================================
    # COMPONENT SCORES (0-100 each)
    # =====================================================
    
    def score_incident_frequency(self, target, days=7):
        """
        Score based on incident frequency. Lower = healthier.
        
        Returns:
            (score, explanation) where score is 0-100
        """
        incidents = self.db.get_incidents(target=target, days=days)
        count = len(incidents)
        
        # Scoring scale
        if count == 0:
            return (100, 'No incidents in {0} days'.format(days))
        elif count <= 2:
            return (80, '{0} incident(s)'.format(count))
        elif count <= 5:
            return (60, '{0} incidents'.format(count))
        elif count <= 10:
            return (40, '{0} incidents (elevated)'.format(count))
        elif count <= 20:
            return (20, '{0} incidents (high)'.format(count))
        else:
            return (5, '{0} incidents (critical)'.format(count))
    
    def score_severity_distribution(self, target, days=7):
        """
        Score based on severity distribution. Heavy CRITICAL weighting.
        
        Returns:
            (score, explanation)
        """
        incidents = self.db.get_incidents(target=target, days=days)
        
        if not incidents:
            return (100, 'No incidents')
        
        severity_counts = defaultdict(int)
        for incident in incidents:
            severity = incident.get('severity', 'UNKNOWN')
            severity_counts[severity] += 1
        
        # Weighted severity score
        score = 100
        explanation_parts = []
        
        critical_count = severity_counts.get('CRITICAL', 0)
        if critical_count > 0:
            score -= critical_count * 25  # Heavy penalty
            explanation_parts.append('{0} CRITICAL'.format(critical_count))
        
        high_count = severity_counts.get('HIGH', 0)
        if high_count > 0:
            score -= high_count * 10
            explanation_parts.append('{0} HIGH'.format(high_count))
        
        medium_count = severity_counts.get('MEDIUM', 0)
        if medium_count > 0:
            score -= medium_count * 3
            explanation_parts.append('{0} MEDIUM'.format(medium_count))
        
        score = max(0, score)
        
        explanation = 'Severity: ' + ', '.join(explanation_parts) if explanation_parts else 'All LOW/INFO'
        
        return (score, explanation)
    
    def score_risk_trend(self, target, days=7):
        """
        Score based on risk trend direction.
        
        Returns:
            (score, explanation)
        """
        # Get recent incidents (first half of window) vs older (second half)
        all_incidents = self.db.get_incidents(target=target, days=days)
        
        if len(all_incidents) < 2:
            return (100, 'Insufficient data for trend')
        
        midpoint = len(all_incidents) // 2
        recent = all_incidents[:midpoint]
        older = all_incidents[midpoint:]
        
        recent_count = len(recent)
        older_count = len(older)
        
        if older_count == 0:
            return (50, 'No historical data')
        
        trend_ratio = recent_count / float(older_count)
        
        if trend_ratio < 0.5:
            return (90, 'Risk decreasing (improving)')
        elif trend_ratio < 0.8:
            return (75, 'Risk stable with slight improvement')
        elif trend_ratio < 1.2:
            return (70, 'Risk stable')
        elif trend_ratio < 2.0:
            return (50, 'Risk increasing (degrading)')
        else:
            return (20, 'Risk sharply increasing')
    
    def score_mean_time_to_recovery(self, target, days=7):
        """
        Score based on MTTR. Lower MTTR = higher score.
        
        Returns:
            (score, explanation)
        """
        incidents = self.db.get_incidents(target=target, days=days)
        
        if not incidents:
            return (100, 'No incidents (no recovery needed)')
        
        mttr_values = []
        for incident in incidents:
            try:
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
                
                if first_seen and last_seen:
                    duration = (last_seen - first_seen).total_seconds() / 60.0  # Minutes
                    mttr_values.append(duration)
            except Exception:
                pass
        
        if not mttr_values:
            return (100, 'No recovery data')
        
        avg_mttr = sum(mttr_values) / float(len(mttr_values))
        
        # Scoring scale (minutes)
        if avg_mttr < 5:
            return (95, 'MTTR {0:.1f} min (excellent)'.format(avg_mttr))
        elif avg_mttr < 15:
            return (80, 'MTTR {0:.1f} min (good)'.format(avg_mttr))
        elif avg_mttr < 60:
            return (60, 'MTTR {0:.1f} min (acceptable)'.format(avg_mttr))
        elif avg_mttr < 240:
            return (40, 'MTTR {0:.1f} min (slow)'.format(avg_mttr))
        else:
            return (20, 'MTTR {0:.1f} min (critical)'.format(avg_mttr))
    
    def score_recommendation_success(self, target):
        """
        Score based on recommendation success rate.
        
        Returns:
            (score, explanation)
        """
        recommendations = self.db.get_recommendations(target)
        
        if not recommendations:
            return (50, 'No recommendations yet')
        
        total = 0
        successful = 0
        
        for rec in recommendations:
            success_count = rec.get('success_count', 0)
            failure_count = rec.get('failure_count', 0)
            partial_count = rec.get('partial_count', 0)
            
            rec_total = success_count + failure_count + partial_count
            if rec_total > 0:
                total += rec_total
                successful += success_count + (partial_count * 0.5)  # Half credit for partial
        
        if total == 0:
            return (50, 'No recommendation outcomes yet')
        
        success_rate = successful / float(total)
        
        if success_rate >= 0.9:
            return (95, 'Success rate {0:.0f}% (excellent)'.format(success_rate * 100))
        elif success_rate >= 0.7:
            return (80, 'Success rate {0:.0f}% (good)'.format(success_rate * 100))
        elif success_rate >= 0.5:
            return (60, 'Success rate {0:.0f}%'.format(success_rate * 100))
        else:
            return (30, 'Success rate {0:.0f}% (needs review)'.format(success_rate * 100))
    
    def score_anomaly_frequency(self, target, days=7):
        """
        Score based on detected anomalies. Fewer = healthier.
        
        Returns:
            (score, explanation)
        """
        anomalies = self.db.get_anomalies(target=target, days=days)
        
        if not anomalies:
            return (100, 'No anomalies detected')
        
        count = len(anomalies)
        
        # Count by severity
        critical_count = len([a for a in anomalies if a.get('severity') == 'CRITICAL'])
        high_count = len([a for a in anomalies if a.get('severity') == 'HIGH'])
        medium_count = len([a for a in anomalies if a.get('severity') == 'MEDIUM'])
        
        score = 100
        explanation_parts = []
        
        if critical_count > 0:
            score -= critical_count * 20
            explanation_parts.append('{0} CRITICAL'.format(critical_count))
        
        if high_count > 0:
            score -= high_count * 8
            explanation_parts.append('{0} HIGH'.format(high_count))
        
        if medium_count > 0:
            score -= medium_count * 2
            explanation_parts.append('{0} MEDIUM'.format(medium_count))
        
        score = max(0, score)
        explanation = 'Anomalies: ' + ', '.join(explanation_parts) if explanation_parts else 'All LOW/INFO'
        
        return (score, explanation)
    
    # =====================================================
    # COMPOSITE HEALTH SCORE
    # =====================================================
    
    def score_database(self, target, days=7):
        """
        Compute overall health score with weighted components.
        
        Returns:
            Dict with score, state, contributors, breakdown
        """
        # Get component scores
        freq_score, freq_explain = self.score_incident_frequency(target, days)
        severity_score, severity_explain = self.score_severity_distribution(target, days)
        trend_score, trend_explain = self.score_risk_trend(target, days)
        mttr_score, mttr_explain = self.score_mean_time_to_recovery(target, days)
        rec_score, rec_explain = self.score_recommendation_success(target)
        anomaly_score, anomaly_explain = self.score_anomaly_frequency(target, days)
        
        # PRODUCTION CALIBRATION: Detect sparse metrics
        # If anomaly score is high (100) but incidents are high, metrics are likely sparse
        incidents = self.db.get_incidents(target=target, days=days)
        metrics_sparse = (anomaly_score >= 90 and len(incidents) >= 5)
        
        if metrics_sparse:
            # Sparse metrics: increase weight on incident-based signals
            weights = {
                'incident_frequency': 0.30,        # Increased from 0.25
                'severity_distribution': 0.25,     # Increased from 0.20
                'risk_trend': 0.20,                 # Increased from 0.15
                'mttr': 0.15,                       # Same
                'recommendation_success': 0.08,     # Decreased from 0.15
                'anomaly_frequency': 0.02           # Decreased from 0.10
            }
        else:
            # Normal: balanced weighting
            weights = {
                'incident_frequency': 0.25,
                'severity_distribution': 0.20,
                'risk_trend': 0.15,
                'mttr': 0.15,
                'recommendation_success': 0.15,
                'anomaly_frequency': 0.10
            }
        
        overall_score = (
            freq_score * weights['incident_frequency'] +
            severity_score * weights['severity_distribution'] +
            trend_score * weights['risk_trend'] +
            mttr_score * weights['mttr'] +
            rec_score * weights['recommendation_success'] +
            anomaly_score * weights['anomaly_frequency']
        )
        
        # Classify health state
        if overall_score >= 80:
            health_state = 'HEALTHY'
        elif overall_score >= 60:
            health_state = 'ACCEPTABLE'
        elif overall_score >= 40:
            health_state = 'DEGRADED'
        else:
            health_state = 'CRITICAL'
        
        # Find top contributors to poor health (lowest scores)
        contributors = [
            ('incident_frequency', freq_score, freq_explain),
            ('severity_distribution', severity_score, severity_explain),
            ('risk_trend', trend_score, trend_explain),
            ('mttr', mttr_score, mttr_explain),
            ('recommendation_success', rec_score, rec_explain),
            ('anomaly_frequency', anomaly_score, anomaly_explain)
        ]
        
        # Sort by score (lowest first)
        contributors.sort(key=lambda x: x[1])
        top_issues = [c for c in contributors if c[1] < 70][:3]  # Top 3 issues
        
        return {
            'target': target,
            'health_score': int(overall_score),
            'health_state': health_state,
            'score_range': '0-100',
            'assessment_window_days': days,
            'timestamp': datetime.utcnow().isoformat(),
            
            'component_scores': {
                'incident_frequency': {
                    'score': int(freq_score),
                    'explanation': freq_explain,
                    'weight': weights['incident_frequency']
                },
                'severity_distribution': {
                    'score': int(severity_score),
                    'explanation': severity_explain,
                    'weight': weights['severity_distribution']
                },
                'risk_trend': {
                    'score': int(trend_score),
                    'explanation': trend_explain,
                    'weight': weights['risk_trend']
                },
                'mttr': {
                    'score': int(mttr_score),
                    'explanation': mttr_explain,
                    'weight': weights['mttr']
                },
                'recommendation_success': {
                    'score': int(rec_score),
                    'explanation': rec_explain,
                    'weight': weights['recommendation_success']
                },
                'anomaly_frequency': {
                    'score': int(anomaly_score),
                    'explanation': anomaly_explain,
                    'weight': weights['anomaly_frequency']
                }
            },
            
            'top_issues': [
                {
                    'component': c[0],
                    'score': int(c[1]),
                    'explanation': c[2]
                }
                for c in top_issues
            ],
            
            'recommendations': self._health_recommendations(health_state, top_issues)
        }
    
    def _health_recommendations(self, state, top_issues):
        """Generate actionable recommendations based on health state."""
        recommendations = []
        
        if state == 'CRITICAL':
            recommendations.append('URGENT: Immediate investigation required')
            recommendations.append('Escalate to on-call team')
        
        for component, score, explanation in top_issues:
            if component == 'incident_frequency':
                recommendations.append('Reduce incident frequency through root cause elimination')
            elif component == 'severity_distribution':
                recommendations.append('Focus on preventing CRITICAL severity incidents')
            elif component == 'risk_trend':
                recommendations.append('Address increasing risk trend with preventive action')
            elif component == 'mttr':
                recommendations.append('Improve recovery procedures to reduce MTTR')
            elif component == 'recommendation_success':
                recommendations.append('Review failed recommendations and refine approach')
            elif component == 'anomaly_frequency':
                recommendations.append('Investigate and mitigate recurring anomalies')
        
        return recommendations
    
    # =====================================================
    # SAVE TO DATABASE
    # =====================================================
    
    def persist_score(self, target, days=7):
        """
        Calculate and save health score to database.
        
        Returns:
            Health score dict (same as score_database)
        """
        score_result = self.score_database(target, days)
        
        # Log to audit trail
        self.db.log_action(
            action='HEALTH_SCORE_CALCULATED',
            entity_type='DATABASE',
            entity_id=target,
            details='Health score: {0}/100 ({1})'.format(
                score_result['health_score'],
                score_result['health_state']
            )
        )
        
        return score_result
