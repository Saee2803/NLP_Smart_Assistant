from datetime import timedelta, datetime
from collections import defaultdict
from data_engine.target_normalizer import TargetNormalizer


class MetricAlertValidator:
    """
    Validates whether alerts are supported by metric evidence
    
    PRODUCTION OPTIMIZATION:
    - Pre-indexes metrics by (target, time_bucket) for O(1) lookup
    - Reduces validation from O(N×M) to O(N) where N=alerts, M=metrics
    - Handles 650k+ alerts efficiently
    """

    CPU_THRESHOLD = 85
    MEMORY_THRESHOLD = 80
    STORAGE_THRESHOLD = 80
    
    # Time bucket size for indexing (5 minutes)
    BUCKET_MINUTES = 5

    def __init__(self, alerts, metrics):
        self.alerts = alerts
        self.metrics = metrics
        
        # PERFORMANCE FIX: Build metric index once at initialization
        print("[*] Building metric index for fast validation...")
        self.metric_index = self._build_metric_index()
        print("[OK] Metric index built: {0} targets indexed".format(len(self.metric_index)))

    # -------------------------------------------------
    # PERFORMANCE FIX: PRE-INDEX METRICS
    # -------------------------------------------------
    def _build_metric_index(self):
        """
        Build time-bucketed index: {normalized_target: {bucket_key: [metrics]}}
        This changes O(N×M) validation to O(N) with fast lookups.
        
        Bucket size = 5 minutes
        Alert window = ±15 minutes (so we check 6 buckets per alert)
        """
        index = defaultdict(lambda: defaultdict(list))
        
        for m in self.metrics:
            if not m:
                continue
            
            m_time = m.get("time")
            m_target = m.get("target")
            
            if not m_time or not m_target:
                continue
            
            # Normalize target for consistent lookup
            norm_target = TargetNormalizer.normalize(m_target)
            if not norm_target:
                continue
            
            # Calculate time bucket (rounds down to nearest 5-minute interval)
            bucket_key = self._get_time_bucket(m_time)
            
            # Add to index
            index[norm_target][bucket_key].append(m)
        
        return index

    def _get_time_bucket(self, dt):
        """
        Convert datetime to 5-minute bucket key.
        Example: 10:07 -> 10:05, 10:12 -> 10:10
        """
        if not isinstance(dt, datetime):
            return None
        
        # Round down to nearest 5-minute interval
        minutes = (dt.hour * 60 + dt.minute) // self.BUCKET_MINUTES * self.BUCKET_MINUTES
        bucket_hour = minutes // 60
        bucket_min = minutes % 60
        
        return dt.replace(hour=bucket_hour, minute=bucket_min, second=0, microsecond=0)

    def _get_relevant_buckets(self, alert_time):
        """
        Get all time buckets that overlap with alert window (±15 minutes).
        With 5-minute buckets, we need to check 6 buckets total.
        """
        if not isinstance(alert_time, datetime):
            return []
        
        buckets = []
        
        # Check buckets from -20 to +20 minutes (to cover ±15 min window)
        for offset_minutes in range(-20, 25, self.BUCKET_MINUTES):
            check_time = alert_time + timedelta(minutes=offset_minutes)
            bucket = self._get_time_bucket(check_time)
            if bucket and bucket not in buckets:
                buckets.append(bucket)
        
        return buckets

    # -------------------------------------------------
    # MAIN VALIDATION (OPTIMIZED)
    # -------------------------------------------------
    def validate(self):
        """
        Validate all alerts using indexed metric lookup.
        Progress logging every 50k alerts.
        """
        validated = []
        total = len(self.alerts)
        
        print("[*] Validating {0} alerts against indexed metrics...".format(total))
        
        for idx, alert in enumerate(self.alerts):
            result = self._validate_alert(alert)
            validated.append(result)
            
            # Progress indicator
            if (idx + 1) % 50000 == 0:
                print("[*] Validated {0}/{1} alerts...".format(idx + 1, total))

        return validated

    # -------------------------------------------------
    # SINGLE ALERT VALIDATION (OPTIMIZED)
    # -------------------------------------------------
    def _validate_alert(self, alert):
        alert_time = alert.get("time")
        target = alert.get("target")

        if not alert_time or not target:
            return self._result(alert, False, ["Missing time or target"])

        window_start = alert_time - timedelta(minutes=15)
        window_end = alert_time + timedelta(minutes=5)

        # Normalize target for index lookup
        norm_target = TargetNormalizer.normalize(target)
        if not norm_target:
            return self._result(alert, False, ["Invalid target"])

        # PERFORMANCE FIX: Use indexed lookup instead of linear scan
        related_metrics = []
        
        if norm_target in self.metric_index:
            # Get relevant time buckets
            buckets = self._get_relevant_buckets(alert_time)
            
            # Collect metrics from relevant buckets
            for bucket in buckets:
                if bucket in self.metric_index[norm_target]:
                    for m in self.metric_index[norm_target][bucket]:
                        m_time = m.get("time")
                        if m_time and window_start <= m_time <= window_end:
                            related_metrics.append(m)

        reasons = []

        for m in related_metrics:
            name = (m.get("metric") or "").lower()
            value = m.get("value", 0)

            if "cpu" in name and value >= self.CPU_THRESHOLD:
                reasons.append("High CPU ({0}%)".format(int(value)))

            if "memory" in name and value >= self.MEMORY_THRESHOLD:
                reasons.append("High memory usage ({0}%)".format(int(value)))

            if "disk" in name or "storage" in name:
                if value >= self.STORAGE_THRESHOLD:
                    reasons.append("Storage pressure ({0}%)".format(int(value)))

        is_valid = bool(reasons)

        # -------------------------------------------------
        # PRODUCTION FALLBACK: Alert Pattern Validation
        # -------------------------------------------------
        # If metric evidence is sparse but alert is CRITICAL,
        # check for high-frequency alert pattern
        if not is_valid and alert.get("severity") == "CRITICAL":
            pattern_detected = self._detect_alert_pattern(target, alert_time)
            if pattern_detected:
                is_valid = True
                reasons = ["SUPPORTED_BY_ALERT_PATTERN: Metric data unavailable, but high-frequency critical alert pattern detected"]

        if not reasons:
            reasons.append("No abnormal metrics found")

        return self._result(alert, is_valid, reasons)

    # -------------------------------------------------
    # PRODUCTION FALLBACK: ALERT PATTERN DETECTION
    # -------------------------------------------------
    def _detect_alert_pattern(self, target, alert_time):
        """
        Detect if there's a high-frequency CRITICAL alert pattern.
        Returns True if >= 3 CRITICAL alerts in last 24 hours for same target.
        """
        if not alert_time or not target:
            return False

        lookback_start = alert_time - timedelta(hours=24)

        critical_count = 0
        for a in self.alerts:
            a_time = a.get("time")
            a_target = a.get("target")
            a_severity = a.get("severity")

            if (a_time and a_severity == "CRITICAL" and
                lookback_start <= a_time <= alert_time and
                TargetNormalizer.equals(a_target, target)):
                critical_count += 1

        return critical_count >= 3

    # -------------------------------------------------
    # FORMAT OUTPUT
    # -------------------------------------------------
    def _result(self, alert, valid, reasons):
        return {
            "alert_time": alert.get("time"),
            "target": alert.get("target"),
            "severity": alert.get("severity"),
            "message": alert.get("message"),
            "metric_supported": valid,
            "reasons": reasons
        }

