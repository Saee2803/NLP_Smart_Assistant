# incident_engine/time_aware_predictor.py
"""
Time-Aware Failure Prediction Engine

Learns hour-of-day and day-of-week failure patterns from historical data.
Replaces generic "24-48 hours" predictions with specific risk windows.

Statistical only (chi-square test). No ML.
Python 3.6 compatible.
"""

from datetime import datetime, timedelta
from collections import defaultdict
import math


class TimeAwarePredictor(object):
    """
    Predicts failures based on historical time patterns.
    """
    
    def __init__(self, db, lookback_days=60, min_confidence=0.65):
        """
        Initialize predictor.
        
        Args:
            db: Database instance (from storage.database)
            lookback_days: Historical window for pattern learning
            min_confidence: Minimum confidence to consider pattern real (0.0-1.0)
        """
        self.db = db
        self.lookback_days = lookback_days
        self.min_confidence = min_confidence
    
    # =====================================================
    # HOUR-OF-DAY RISK PREDICTION
    # =====================================================
    
    def get_hour_of_day_risk(self, target, hour=None):
        """
        Get failure probability for a specific hour-of-day.
        
        Args:
            target: Database/target name
            hour: Specific hour (0-23), or None for all hours
        
        Returns:
            Dict with hour, probability, confidence, incident_count, evidence
        """
        if hour is None:
            return self._get_all_hour_risks(target)
        
        # Get incidents for target in lookback window
        incidents = self.db.get_incidents(target=target, days=self.lookback_days)
        if not incidents:
            return {
                'hour': hour,
                'probability': 0.0,
                'confidence': 0.0,
                'incident_count': 0,
                'evidence': 'No incident data'
            }
        
        # Count incidents by hour
        hour_counts = self._count_incidents_by_hour(incidents)
        total_incidents = sum(hour_counts.values())
        
        if total_incidents == 0:
            return {
                'hour': hour,
                'probability': 0.0,
                'confidence': 0.0,
                'incident_count': 0,
                'evidence': 'No incidents at this hour'
            }
        
        # Calculate probability for this hour
        count_at_hour = hour_counts.get(hour, 0)
        expected_if_uniform = total_incidents / 24.0
        
        # Chi-square test for significance
        if count_at_hour > 0:
            chi_sq = ((count_at_hour - expected_if_uniform) ** 2) / expected_if_uniform
            # Confidence: higher chi-sq = higher confidence this hour is different
            confidence = min(0.99, 0.5 + (chi_sq / 15.0))
        else:
            chi_sq = 0
            confidence = 0.0
        
        probability = count_at_hour / float(total_incidents)
        
        return {
            'hour': hour,
            'probability': probability,
            'confidence': confidence,
            'incident_count': count_at_hour,
            'evidence': 'Hour {0:02d}:00 has {1}/{2} incidents ({3:.1f}%)'.format(
                hour, count_at_hour, total_incidents, 100.0 * probability
            )
        }
    
    def _get_all_hour_risks(self, target):
        """Get risk for all 24 hours."""
        risks = []
        for hour in range(24):
            risk = self.get_hour_of_day_risk(target, hour)
            risks.append(risk)
        
        # Filter to high-risk hours
        high_risk = [r for r in risks if r['confidence'] >= self.min_confidence]
        return sorted(high_risk, key=lambda x: x['probability'], reverse=True)
    
    def _count_incidents_by_hour(self, incidents):
        """Count incidents grouped by hour of day."""
        hour_counts = defaultdict(int)
        
        for incident in incidents:
            try:
                first_seen = incident.get('first_seen')
                if isinstance(first_seen, str):
                    dt = datetime.fromisoformat(first_seen)
                else:
                    dt = first_seen
                
                hour = dt.hour
                hour_counts[hour] += 1
            except Exception:
                pass
        
        return hour_counts
    
    # =====================================================
    # DAY-OF-WEEK RISK PREDICTION
    # =====================================================
    
    def get_day_of_week_risk(self, target, day=None):
        """
        Get failure probability for a specific day-of-week.
        
        Args:
            target: Database/target name
            day: Day name (MONDAY, TUESDAY, etc.), or None for all days
        
        Returns:
            Dict with day, probability, confidence, incident_count, evidence
        """
        if day is None:
            return self._get_all_day_risks(target)
        
        # Get incidents
        incidents = self.db.get_incidents(target=target, days=self.lookback_days)
        if not incidents:
            return {
                'day': day,
                'probability': 0.0,
                'confidence': 0.0,
                'incident_count': 0,
                'evidence': 'No incident data'
            }
        
        # Count by day of week
        day_counts = self._count_incidents_by_day(incidents)
        total_incidents = sum(day_counts.values())
        
        if total_incidents == 0:
            return {
                'day': day,
                'probability': 0.0,
                'confidence': 0.0,
                'incident_count': 0,
                'evidence': 'No incidents on this day'
            }
        
        # Calculate probability
        count_on_day = day_counts.get(day, 0)
        expected_if_uniform = total_incidents / 7.0
        
        if count_on_day > 0:
            chi_sq = ((count_on_day - expected_if_uniform) ** 2) / expected_if_uniform
            confidence = min(0.99, 0.5 + (chi_sq / 10.0))
        else:
            confidence = 0.0
        
        probability = count_on_day / float(total_incidents)
        
        return {
            'day': day,
            'probability': probability,
            'confidence': confidence,
            'incident_count': count_on_day,
            'evidence': '{0} has {1}/{2} incidents ({3:.1f}%)'.format(
                day, count_on_day, total_incidents, 100.0 * probability
            )
        }
    
    def _get_all_day_risks(self, target):
        """Get risk for all 7 days."""
        day_names = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']
        risks = []
        
        for day_name in day_names:
            risk = self.get_day_of_week_risk(target, day_name)
            risks.append(risk)
        
        # Filter to high-risk days
        high_risk = [r for r in risks if r['confidence'] >= self.min_confidence]
        return sorted(high_risk, key=lambda x: x['probability'], reverse=True)
    
    def _count_incidents_by_day(self, incidents):
        """Count incidents grouped by day of week."""
        day_names = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']
        day_counts = defaultdict(int)
        
        for incident in incidents:
            try:
                first_seen = incident.get('first_seen')
                if isinstance(first_seen, str):
                    dt = datetime.fromisoformat(first_seen)
                else:
                    dt = first_seen
                
                day_of_week = dt.weekday()  # 0=Monday
                day_name = day_names[day_of_week]
                day_counts[day_name] += 1
            except Exception:
                pass
        
        return day_counts
    
    # =====================================================
    # COMPOSITE RISK WINDOW PREDICTION
    # =====================================================
    
    def predict_high_risk_window(self, target):
        """
        Find the highest-risk hour-of-day and day-of-week combination.
        
        Returns:
            Dict with hour_window, day_window, confidence, incident_count, evidence
        """
        # Get hour-of-day risks
        hour_risks = self._get_all_hour_risks(target)
        
        # Get day-of-week risks
        day_risks = self._get_all_day_risks(target)
        
        if not hour_risks or not day_risks:
            return {
                'hour_window': None,
                'day_window': None,
                'combined_confidence': 0.0,
                'incident_count': 0,
                'evidence': 'Insufficient pattern data'
            }
        
        # Combine highest hour and day risks
        top_hour = hour_risks[0]
        top_day = day_risks[0]
        
        # Combined confidence (geometric mean)
        combined_confidence = math.sqrt(top_hour['confidence'] * top_day['confidence'])
        
        # Format hour window as HH:00-HH:59
        hour_window = '{0:02d}:00-{0:02d}:59'.format(top_hour['hour'])
        day_window = top_day['day']
        
        # Total incidents in this window
        incident_count = top_hour['incident_count'] + top_day['incident_count']
        
        return {
            'hour_window': hour_window,
            'day_window': day_window,
            'combined_confidence': combined_confidence,
            'incident_count': incident_count,
            'hour_confidence': top_hour['confidence'],
            'day_confidence': top_day['confidence'],
            'evidence': 'Highest risk: {0} on {1} with combined confidence {2:.2f}'.format(
                hour_window, day_window, combined_confidence
            )
        }
    
    # =====================================================
    # NEXT FAILURE TIME ESTIMATE
    # =====================================================
    
    def predict_next_failure_window(self, target):
        """
        Predict when the next failure is likely to occur.
        
        Returns:
            Dict with next_window, hours_from_now, confidence, recommendations
        """
        now = datetime.utcnow()
        high_risk = self.predict_high_risk_window(target)
        
        if high_risk['hour_window'] is None:
            return {
                'next_window': None,
                'hours_from_now': None,
                'confidence': 0.0,
                'recommendations': ['Insufficient historical data for prediction']
            }
        
        # Parse hour window
        start_hour = int(high_risk['hour_window'].split(':')[0])
        day_name = high_risk['day_window']
        
        # Find next occurrence of this day
        day_names = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']
        target_day_index = day_names.index(day_name)
        current_day_index = now.weekday()
        
        days_until_target = (target_day_index - current_day_index) % 7
        if days_until_target == 0:
            # Same day - check if hour has passed
            if now.hour >= start_hour:
                days_until_target = 7  # Next week
        
        # Calculate exact time
        next_occurrence = now + timedelta(days=days_until_target)
        next_occurrence = next_occurrence.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        
        hours_from_now = (next_occurrence - now).total_seconds() / 3600.0
        
        return {
            'next_window': high_risk['hour_window'],
            'next_day': day_name,
            'hours_from_now': hours_from_now,
            'estimated_time': next_occurrence.isoformat(),
            'confidence': high_risk['combined_confidence'],
            'recommendations': [
                'Increase monitoring around {0} on {1}'.format(high_risk['hour_window'], day_name),
                'Consider preventive maintenance before this window',
                'Ensure on-call staff available during high-risk periods'
            ]
        }
    
    # =====================================================
    # OVERALL PREDICTION SUMMARY
    # =====================================================
    
    def predict_summary(self, target):
        """
        Get comprehensive failure prediction for a target.
        
        Returns:
            Dict with all prediction details
        """
        hour_risks = self._get_all_hour_risks(target)
        day_risks = self._get_all_day_risks(target)
        high_risk_window = self.predict_high_risk_window(target)
        next_failure = self.predict_next_failure_window(target)
        
        return {
            'target': target,
            'high_risk_hours': hour_risks[:3],  # Top 3 hours
            'high_risk_days': day_risks[:3],    # Top 3 days
            'primary_risk_window': high_risk_window,
            'next_predicted_failure': next_failure,
            'lookback_days': self.lookback_days,
            'prediction_confidence': high_risk_window['combined_confidence']
        }
