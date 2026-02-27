# anomaly/detector.py
"""
Statistical Anomaly Detection Engine for OEM Incident Intelligence System.

Uses z-score based detection with rolling windows to identify anomalies.
Detects when metrics deviate significantly from their historical baseline.

No machine learning - purely statistical.
Python 3.6 compatible.
"""

from datetime import datetime, timedelta
from collections import defaultdict
import math


class AnomalyDetector(object):
    """
    Detects metric anomalies using statistical methods.
    """
    
    def __init__(self, db, z_threshold=2.5, rolling_window_minutes=30):
        """
        Initialize anomaly detector.
        
        Args:
            db: Database instance (from storage.database)
            z_threshold: Z-score threshold for anomaly (default 2.5 = ~99.4th percentile)
            rolling_window_minutes: Calculate baseline over this window (default 30 min)
        """
        self.db = db
        self.z_threshold = z_threshold
        self.rolling_window_minutes = rolling_window_minutes
    
    # =====================================================
    # Z-SCORE CALCULATION
    # =====================================================
    
    def calculate_zscore(self, value, mean, stddev):
        """
        Calculate z-score for a value.
        
        z = (value - mean) / stddev
        
        Args:
            value: Observed value
            mean: Baseline mean
            stddev: Baseline standard deviation
        
        Returns:
            Z-score (float)
        """
        if stddev == 0:
            return 0.0  # Can't detect anomaly if no variation
        
        return (value - mean) / float(stddev)
    
    # =====================================================
    # BASELINE CALCULATION
    # =====================================================
    
    def get_metric_baseline(self, target, metric_name, lookback_hours=24):
        """
        Calculate baseline (mean, stddev) for a metric.
        
        Args:
            target: Database/target name
            metric_name: Metric name (e.g., 'CPU%', 'Memory%')
            lookback_hours: Days to look back (default 24 hours)
        
        Returns:
            Tuple: (mean, stddev, sample_count)
        """
        metrics = self.db.get_metrics(target=target, days=(lookback_hours / 24.0))
        
        # Filter to this metric
        values = []
        for metric in metrics:
            if metric.get('metric_name') == metric_name:
                try:
                    val = float(metric.get('value', 0))
                    values.append(val)
                except (ValueError, TypeError):
                    pass
        
        if len(values) < 2:
            return (0.0, 0.0, 0)  # Not enough data
        
        # Calculate mean
        mean = sum(values) / float(len(values))
        
        # Calculate standard deviation
        variance = sum([(x - mean) ** 2 for x in values]) / float(len(values))
        stddev = math.sqrt(variance)
        
        return (mean, stddev, len(values))
    
    # =====================================================
    # ROLLING WINDOW BASELINE
    # =====================================================
    
    def get_rolling_baseline(self, target, metric_name, minutes=30):
        """
        Get baseline from rolling time window.
        
        Args:
            target: Database/target
            metric_name: Metric name
            minutes: Window size (default 30 min)
        
        Returns:
            Tuple: (mean, stddev, sample_count)
        """
        metrics = self.db.get_metrics(target=target, days=1)
        
        # Filter to this metric and time window
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        values = []
        
        for metric in metrics:
            if metric.get('metric_name') == metric_name:
                try:
                    metric_time = metric.get('metric_time')
                    if isinstance(metric_time, str):
                        dt = datetime.fromisoformat(metric_time)
                    else:
                        dt = metric_time
                    
                    if dt >= cutoff:
                        val = float(metric.get('value', 0))
                        values.append(val)
                except (ValueError, TypeError):
                    pass
        
        if len(values) < 2:
            # Fall back to 24-hour baseline
            return self.get_metric_baseline(target, metric_name, lookback_hours=24)
        
        # Calculate statistics
        mean = sum(values) / float(len(values))
        variance = sum([(x - mean) ** 2 for x in values]) / float(len(values))
        stddev = math.sqrt(variance)
        
        return (mean, stddev, len(values))
    
    # =====================================================
    # ANOMALY DETECTION
    # =====================================================
    
    def is_anomaly(self, target, metric_name, value):
        """
        Check if a metric value is anomalous.
        
        Args:
            target: Database/target
            metric_name: Metric name
            value: Current metric value
        
        Returns:
            Tuple: (is_anomalous, z_score)
        """
        mean, stddev, samples = self.get_rolling_baseline(target, metric_name)
        
        if samples < 2:
            # Not enough data
            return (False, 0.0)
        
        z_score = abs(self.calculate_zscore(value, mean, stddev))
        is_anomalous = z_score > self.z_threshold
        
        return (is_anomalous, z_score)
    
    # =====================================================
    # BATCH ANOMALY DETECTION
    # =====================================================
    
    def detect_anomalies_for_target(self, target):
        """
        Detect all anomalies for a target's current metrics.
        
        Args:
            target: Database/target
        
        Returns:
            List of anomaly records
        """
        metrics = self.db.get_metrics(target=target, days=1)
        
        # Get latest value for each metric
        latest_by_metric = {}
        for metric in metrics:
            metric_name = metric.get('metric_name')
            metric_time = metric.get('metric_time')
            
            if metric_name not in latest_by_metric:
                latest_by_metric[metric_name] = metric
        
        anomalies = []
        
        for metric_name, metric in latest_by_metric.items():
            try:
                value = float(metric.get('value', 0))
                is_anomalous, z_score = self.is_anomaly(target, metric_name, value)
                
                if is_anomalous:
                    mean, stddev, samples = self.get_rolling_baseline(target, metric_name)
                    
                    # Determine severity
                    if z_score > 4.0:
                        severity = 'CRITICAL'
                    elif z_score > 3.0:
                        severity = 'HIGH'
                    else:
                        severity = 'MEDIUM'
                    
                    anomalies.append({
                        'target': target,
                        'metric_name': metric_name,
                        'anomaly_time': datetime.utcnow(),
                        'observed_value': value,
                        'baseline_value': mean,
                        'anomaly_score': z_score,
                        'severity': severity,
                        'evidence': 'Baseline: {0:.2f}, Current: {1:.2f}, Z-score: {2:.2f}'.format(
                            mean, value, z_score
                        )
                    })
            except (ValueError, TypeError):
                pass
        
        return anomalies
    
    # =====================================================
    # SAVE ANOMALIES TO DATABASE
    # =====================================================
    
    def detect_and_save_anomalies(self, target):
        """
        Detect anomalies for target and save to database.
        
        Args:
            target: Database/target
        
        Returns:
            Number of anomalies detected
        """
        anomalies = self.detect_anomalies_for_target(target)
        
        for anomaly in anomalies:
            self.db.insert_anomaly(
                target=anomaly['target'],
                metric_name=anomaly['metric_name'],
                anomaly_time=anomaly['anomaly_time'],
                anomaly_score=anomaly['anomaly_score'],
                baseline_value=anomaly['baseline_value'],
                observed_value=anomaly['observed_value'],
                severity=anomaly['severity']
            )
        
        return len(anomalies)
    
    # =====================================================
    # GLOBAL ANOMALY DETECTION
    # =====================================================
    
    def detect_all_anomalies(self):
        """
        Detect anomalies for all targets.
        
        Returns:
            Dictionary: {target: num_anomalies}
        """
        incidents = self.db.get_incidents(days=1)
        targets = set([inc.get('target') for inc in incidents])
        
        results = {}
        for target in targets:
            count = self.detect_and_save_anomalies(target)
            results[target] = count
            if count > 0:
                print("[ANOMALY] Detected {0} anomalies for {1}".format(count, target))
        
        return results
    
    # =====================================================
    # HISTORICAL ANOMALY ANALYSIS
    # =====================================================
    
    def retrospective_analysis(self, target, metric_name, days=7):
        """
        Perform retrospective anomaly analysis on historical data.
        
        Useful for understanding which metrics were abnormal during incidents.
        
        Args:
            target: Database/target
            metric_name: Metric to analyze
            days: How far back to look
        
        Returns:
            List of historical anomalies
        """
        metrics = self.db.get_metrics(target=target, days=days)
        
        # Filter to this metric
        values_with_time = []
        for metric in metrics:
            if metric.get('metric_name') == metric_name:
                try:
                    val = float(metric.get('value', 0))
                    metric_time = metric.get('metric_time')
                    if isinstance(metric_time, str):
                        dt = datetime.fromisoformat(metric_time)
                    else:
                        dt = metric_time
                    values_with_time.append((dt, val))
                except (ValueError, TypeError):
                    pass
        
        if len(values_with_time) < 2:
            return []
        
        # Calculate overall statistics
        values = [v for t, v in values_with_time]
        mean = sum(values) / float(len(values))
        variance = sum([(x - mean) ** 2 for x in values]) / float(len(values))
        stddev = math.sqrt(variance)
        
        # Identify anomalies
        anomalies = []
        for dt, value in values_with_time:
            z_score = abs(self.calculate_zscore(value, mean, stddev))
            
            if z_score > self.z_threshold:
                if z_score > 4.0:
                    severity = 'CRITICAL'
                elif z_score > 3.0:
                    severity = 'HIGH'
                else:
                    severity = 'MEDIUM'
                
                anomalies.append({
                    'timestamp': dt,
                    'value': value,
                    'z_score': z_score,
                    'severity': severity
                })
        
        return anomalies
