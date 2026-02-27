# learning/pattern_engine.py
"""
Pattern Learning Engine for OEM Incident Intelligence System.

Detects recurring patterns in incidents:
- Day-of-week patterns (e.g., "Mondays fail more often")
- Hour-of-day patterns (e.g., "2-4 AM failures")
- Alert combination patterns (e.g., "CPU + Memory failures together")
- Target-specific patterns (e.g., "This DB always fails Mondays")

Statistical only - no machine learning.
Python 3.6 compatible.
"""

from datetime import datetime, timedelta
from collections import defaultdict
import math


class PatternEngine(object):
    """
    Learns recurring patterns from historical incidents.
    """
    
    def __init__(self, db, min_confidence=0.60, lookback_days=60):
        """
        Initialize pattern engine.
        
        Args:
            db: Database instance (from storage.database)
            min_confidence: Minimum confidence to consider pattern real (0.0-1.0)
            lookback_days: How far back to analyze (default 60 days)
        """
        self.db = db
        self.min_confidence = min_confidence
        self.lookback_days = lookback_days
    
    # =====================================================
    # DAY-OF-WEEK PATTERNS
    # =====================================================
    
    def detect_day_of_week_patterns(self, target=None):
        """
        Detect if target has patterns tied to day of week.
        
        Returns:
            List of patterns like {"day": "MONDAY", "confidence": 0.85, "count": 12}
        """
        incidents = self.db.get_incidents(target=target, days=self.lookback_days)
        if not incidents:
            return []
        
        # Group by day of week
        day_counts = defaultdict(int)
        total_incidents = 0
        
        day_names = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']
        
        for incident in incidents:
            try:
                # Parse incident timestamp
                first_seen = incident.get('first_seen')
                if isinstance(first_seen, str):
                    dt = datetime.fromisoformat(first_seen)
                else:
                    dt = first_seen
                
                day_of_week = dt.weekday()  # 0=Monday, 6=Sunday
                day_name = day_names[day_of_week]
                
                day_counts[day_name] += 1
                total_incidents += 1
            except Exception as e:
                pass
        
        if total_incidents == 0:
            return []
        
        # Calculate confidence: is this day significantly overrepresented?
        # Expected if uniform: total_incidents / 7
        expected = total_incidents / 7.0
        patterns = []
        
        for day_name in day_names:
            observed = day_counts[day_name]
            
            # Chi-square test for significance
            if observed > 0:
                chi_sq = ((observed - expected) ** 2) / expected
                # Simple heuristic: if significantly above average
                if observed > expected * 1.2:  # 20% above average
                    confidence = min(0.99, 0.5 + (chi_sq / 10.0))  # Scale chi-sq to confidence
                    patterns.append({
                        'pattern_type': 'DAY_OF_WEEK',
                        'pattern_value': day_name,
                        'incident_count': observed,
                        'confidence': confidence,
                        'evidence': 'Incidents on {0}: {1}/{2} ({3:.1f}%)'.format(
                            day_name, observed, total_incidents, 
                            100.0 * observed / total_incidents
                        )
                    })
        
        return patterns
    
    # =====================================================
    # HOUR-OF-DAY PATTERNS
    # =====================================================
    
    def detect_hour_of_day_patterns(self, target=None):
        """
        Detect if target has patterns tied to hour of day.
        
        Returns:
            List of patterns like {"hour": "02-04", "confidence": 0.75, "count": 8}
        """
        incidents = self.db.get_incidents(target=target, days=self.lookback_days)
        if not incidents:
            return []
        
        # Group by hour (4-hour windows for statistical significance)
        hour_windows = [
            ('00-04', [0, 1, 2, 3]),
            ('04-08', [4, 5, 6, 7]),
            ('08-12', [8, 9, 10, 11]),
            ('12-16', [12, 13, 14, 15]),
            ('16-20', [16, 17, 18, 19]),
            ('20-24', [20, 21, 22, 23])
        ]
        
        window_counts = defaultdict(int)
        total_incidents = 0
        
        for incident in incidents:
            try:
                first_seen = incident.get('first_seen')
                if isinstance(first_seen, str):
                    dt = datetime.fromisoformat(first_seen)
                else:
                    dt = first_seen
                
                hour = dt.hour
                
                for window_label, hours in hour_windows:
                    if hour in hours:
                        window_counts[window_label] += 1
                        break
                
                total_incidents += 1
            except Exception as e:
                pass
        
        if total_incidents == 0:
            return []
        
        # Calculate confidence
        expected = total_incidents / 6.0  # 6 windows
        patterns = []
        
        for window_label, _ in hour_windows:
            observed = window_counts[window_label]
            
            if observed > expected * 1.2:  # 20% above average
                chi_sq = ((observed - expected) ** 2) / expected
                confidence = min(0.99, 0.5 + (chi_sq / 10.0))
                patterns.append({
                    'pattern_type': 'HOUR_OF_DAY',
                    'pattern_value': window_label,
                    'incident_count': observed,
                    'confidence': confidence,
                    'evidence': 'Incidents between {0} hours: {1}/{2} ({3:.1f}%)'.format(
                        window_label, observed, total_incidents,
                        100.0 * observed / total_incidents
                    )
                })
        
        return patterns
    
    # =====================================================
    # ALERT COMBINATION PATTERNS
    # =====================================================
    
    def detect_alert_combination_patterns(self, target=None):
        """
        Detect which alert messages often occur together.
        
        Returns:
            List of patterns like {"alerts": ["CPU", "Memory"], "confidence": 0.80}
        """
        alerts = self.db.get_alerts(target=target, days=self.lookback_days)
        if not alerts:
            return []
        
        # Group alerts into 10-minute buckets
        buckets = defaultdict(lambda: defaultdict(int))  # timestamp -> {message -> count}
        
        for alert in alerts:
            try:
                alert_time = alert.get('alert_time')
                if isinstance(alert_time, str):
                    dt = datetime.fromisoformat(alert_time)
                else:
                    dt = alert_time
                
                # Round to 10-minute bucket
                bucket_time = dt.replace(minute=(dt.minute // 10) * 10, second=0, microsecond=0)
                message = alert.get('message', '').lower()
                
                buckets[bucket_time][message] += 1
            except Exception as e:
                pass
        
        # Find frequently co-occurring alerts
        combinations = defaultdict(int)
        
        for bucket in buckets.values():
            messages = sorted([msg for msg in bucket.keys()])
            
            # For small buckets, just count pair co-occurrences
            for i in range(len(messages)):
                for j in range(i + 1, len(messages)):
                    pair = tuple(sorted([messages[i], messages[j]]))
                    combinations[pair] += 1
        
        # Convert to patterns
        patterns = []
        total_buckets = len(buckets)
        
        for (msg1, msg2), count in combinations.items():
            if count >= 2:  # At least 2 co-occurrences
                confidence = count / float(total_buckets)
                if confidence >= self.min_confidence:
                    patterns.append({
                        'pattern_type': 'ALERT_COMBINATION',
                        'pattern_value': '{0} + {1}'.format(msg1[:20], msg2[:20]),
                        'incident_count': count,
                        'confidence': confidence,
                        'evidence': 'Co-occurred {0} times in {1} observation periods'.format(
                            count, total_buckets
                        )
                    })
        
        return patterns
    
    # =====================================================
    # TARGET-SPECIFIC PATTERNS
    # =====================================================
    
    def detect_target_patterns(self, target):
        """
        Detect all patterns specific to a single target.
        
        Returns:
            Dictionary with day, hour, and combination patterns
        """
        if not target:
            return {}
        
        return {
            'day_of_week': self.detect_day_of_week_patterns(target=target),
            'hour_of_day': self.detect_hour_of_day_patterns(target=target),
            'alert_combinations': self.detect_alert_combination_patterns(target=target)
        }
    
    # =====================================================
    # SAVE PATTERNS TO DATABASE
    # =====================================================
    
    def learn_patterns_for_target(self, target):
        """
        Learn all patterns for a target and save to database.
        
        Args:
            target: Database/target name
        
        Returns:
            Number of patterns saved
        """
        patterns_data = self.detect_target_patterns(target)
        count = 0
        
        for category in ['day_of_week', 'hour_of_day', 'alert_combinations']:
            for pattern in patterns_data.get(category, []):
                if pattern['confidence'] >= self.min_confidence:
                    self.db.insert_pattern(
                        target=target,
                        pattern_type=pattern['pattern_type'],
                        pattern_value=pattern['pattern_value'],
                        incident_count=pattern['incident_count'],
                        confidence=pattern['confidence'],
                        evidence=pattern['evidence']
                    )
                    count += 1
        
        return count
    
    # =====================================================
    # GLOBAL PATTERN LEARNING
    # =====================================================
    
    def learn_all_patterns(self):
        """
        Learn patterns for all targets in database.
        
        Returns:
            Dictionary: {target: num_patterns_learned}
        """
        incidents = self.db.get_incidents(days=self.lookback_days)
        targets = set([inc.get('target') for inc in incidents])
        
        results = {}
        for target in targets:
            count = self.learn_patterns_for_target(target)
            results[target] = count
            print("[PATTERN] Learned {0} patterns for {1}".format(count, target))
        
        return results
