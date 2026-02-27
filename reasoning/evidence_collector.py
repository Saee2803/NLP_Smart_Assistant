"""
EVIDENCE COLLECTOR

Purpose:
    Gathers and validates evidence to support or refute hypotheses.
    DBAs don't guess - they collect evidence from multiple sources.

Algorithm:
    1. For each hypothesis, identify required evidence types
    2. Query relevant data sources (alerts, metrics, logs)
    3. Score evidence strength (strong/weak/contradictory)
    4. Build evidence chain for root cause determination

Function Signatures:
    collect_evidence(hypothesis: Dict, data_sources: Dict) -> EvidencePackage
    validate_evidence(evidence: List[Dict]) -> ValidationResult
    build_evidence_chain(cause: str, alerts: List) -> EvidenceChain

Example Output:
    {
        "hypothesis_id": "H1",
        "evidence_strength": "STRONG",
        "evidence_items": [
            {"source": "alerts", "item": "ORA-1653 in 47 alerts", "weight": 0.9},
            {"source": "metrics", "item": "Storage at 98.7%", "weight": 0.95}
        ],
        "contradictions": [],
        "confidence_boost": 0.15
    }
"""

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import re


class EvidenceCollector:
    """
    Collects and validates evidence like a DBA building a case.
    """
    
    # Evidence type definitions
    EVIDENCE_TYPES = {
        "TABLESPACE_EXHAUSTION": {
            "primary": ["ORA-1653", "ORA-1652", "storage%", "tablespace_usage"],
            "secondary": ["segment_growth", "autoextend_disabled"],
            "contradictory": ["recent_cleanup", "space_added"]
        },
        "MEMORY_EXHAUSTION": {
            "primary": ["ORA-4031", "shared_pool%", "pga_usage%"],
            "secondary": ["library_cache_misses", "hard_parses"],
            "contradictory": ["memory_increase", "flush_success"]
        },
        "INTERNAL_ERROR": {
            "primary": ["ORA-600", "ORA-7445"],
            "secondary": ["trace_file", "core_dump"],
            "contradictory": ["known_bug_patched"]
        },
        "CPU_SATURATION": {
            "primary": ["cpu%", "load_average"],
            "secondary": ["parallel_queries", "runaway_sessions"],
            "contradictory": ["cpu_normal_after"]
        },
        "NETWORK_ISSUE": {
            "primary": ["ORA-12170", "TNS-", "listener_down"],
            "secondary": ["connection_timeouts", "network_latency"],
            "contradictory": ["listener_up", "connections_restored"]
        }
    }
    
    # Evidence weight by source
    SOURCE_WEIGHTS = {
        "ora_error": 0.95,      # ORA codes are strong evidence
        "metric_threshold": 0.85, # Metrics above threshold
        "metric_trend": 0.70,    # Metric trends
        "alert_count": 0.80,     # Alert frequency
        "time_correlation": 0.75, # Events close in time
        "pattern_match": 0.60,   # Pattern recognition
        "historical": 0.50       # Historical occurrence
    }
    
    def __init__(self):
        """Initialize evidence collector."""
        self.collected_evidence = {}
        self.evidence_cache = {}
    
    def collect_evidence(self,
                        hypothesis: Dict,
                        alerts: List[Dict],
                        metrics: List[Dict] = None,
                        target: str = None) -> Dict:
        """
        Collect evidence for a hypothesis.
        
        Args:
            hypothesis: Hypothesis dictionary to collect evidence for
            alerts: List of alert dictionaries
            metrics: Optional list of metric dictionaries
            target: Optional target filter
            
        Returns:
            Evidence package dictionary
        """
        pattern = hypothesis.get("pattern", "")
        evidence_items = []
        contradictions = []
        
        # Filter by target
        if target:
            target_upper = target.upper()
            alerts = [a for a in alerts 
                     if target_upper in (a.get("target") or a.get("target_name") or "").upper()]
            if metrics:
                metrics = [m for m in metrics 
                          if target_upper in (m.get("target") or "").upper()]
        
        # 1. Collect ORA code evidence
        ora_evidence = self._collect_ora_evidence(alerts, pattern)
        evidence_items.extend(ora_evidence)
        
        # 2. Collect metric evidence
        if metrics:
            metric_evidence = self._collect_metric_evidence(metrics, pattern)
            evidence_items.extend(metric_evidence)
        
        # 3. Collect frequency evidence
        freq_evidence = self._collect_frequency_evidence(alerts, pattern)
        evidence_items.extend(freq_evidence)
        
        # 4. Collect time correlation evidence
        time_evidence = self._collect_time_correlation(alerts)
        evidence_items.extend(time_evidence)
        
        # 5. Check for contradictions
        contradictions = self._find_contradictions(alerts, metrics, pattern)
        
        # Calculate evidence strength
        total_weight = sum(e.get("weight", 0.5) for e in evidence_items)
        contradiction_penalty = len(contradictions) * 0.1
        
        if total_weight > 2.0 and len(contradictions) == 0:
            strength = "STRONG"
            confidence_boost = 0.15
        elif total_weight > 1.0:
            strength = "MODERATE"
            confidence_boost = 0.08 - contradiction_penalty
        elif total_weight > 0.5:
            strength = "WEAK"
            confidence_boost = 0.03 - contradiction_penalty
        else:
            strength = "INSUFFICIENT"
            confidence_boost = -0.05
        
        return {
            "hypothesis_id": hypothesis.get("id"),
            "hypothesis_pattern": pattern,
            "evidence_strength": strength,
            "evidence_items": evidence_items,
            "contradictions": contradictions,
            "total_weight": round(total_weight, 2),
            "confidence_boost": round(confidence_boost, 2),
            "evidence_count": len(evidence_items)
        }
    
    def _collect_ora_evidence(self, alerts: List[Dict], pattern: str) -> List[Dict]:
        """Collect ORA error code evidence."""
        evidence = []
        ora_counts = Counter()
        
        for alert in alerts:
            message = (alert.get("message") or alert.get("alert_message") or "").upper()
            ora_matches = re.findall(r'ORA-(\d+)', message)
            for code in ora_matches:
                ora_counts["ORA-" + code] += 1
        
        # Map ORA codes to evidence
        ora_relevance = {
            "TABLESPACE_EXHAUSTION": ["ORA-1653", "ORA-1652", "ORA-1654", "ORA-1688"],
            "MEMORY_EXHAUSTION": ["ORA-4031", "ORA-4030"],
            "INTERNAL_ERROR": ["ORA-600", "ORA-7445"],
            "NETWORK_ISSUE": ["ORA-12170", "ORA-12154", "ORA-12541"],
            "UNDO_PRESSURE": ["ORA-1555", "ORA-30036"],
            "LOCK_CONTENTION": ["ORA-60", "ORA-54"]
        }
        
        relevant_codes = ora_relevance.get(pattern, [])
        
        for code, count in ora_counts.items():
            is_relevant = code in relevant_codes
            weight = self.SOURCE_WEIGHTS["ora_error"] if is_relevant else 0.3
            
            evidence.append({
                "source": "ora_error",
                "item": "{} occurred {} times".format(code, count),
                "weight": weight * (1 + min(count / 100, 1)),  # Scale by frequency
                "relevance": "PRIMARY" if is_relevant else "SECONDARY",
                "code": code,
                "count": count
            })
        
        return evidence
    
    def _collect_metric_evidence(self, metrics: List[Dict], pattern: str) -> List[Dict]:
        """Collect metric threshold and trend evidence."""
        evidence = []
        metric_values = defaultdict(list)
        
        # Group metrics
        for m in metrics:
            name = (m.get("metric_name") or m.get("name") or "unknown").lower()
            try:
                value = float(m.get("metric_value") or m.get("value") or 0)
                metric_values[name].append(value)
            except (ValueError, TypeError):
                continue
        
        # Thresholds by pattern
        thresholds = {
            "TABLESPACE_EXHAUSTION": {"storage": 85, "tablespace": 85},
            "MEMORY_EXHAUSTION": {"memory": 85, "pga": 90, "sga": 90},
            "CPU_SATURATION": {"cpu": 80, "load": 4.0},
            "IO_BOTTLENECK": {"io_latency": 20, "iops": 1000}
        }
        
        pattern_thresholds = thresholds.get(pattern, {})
        
        for name, values in metric_values.items():
            if not values:
                continue
            
            max_val = max(values)
            avg_val = sum(values) / len(values)
            
            # Check against thresholds
            for threshold_key, threshold_val in pattern_thresholds.items():
                if threshold_key in name:
                    if max_val > threshold_val:
                        evidence.append({
                            "source": "metric_threshold",
                            "item": "{} peaked at {} (threshold: {})".format(
                                name, round(max_val, 1), threshold_val),
                            "weight": self.SOURCE_WEIGHTS["metric_threshold"],
                            "metric_name": name,
                            "value": max_val,
                            "threshold": threshold_val
                        })
            
            # Check for trends
            if len(values) >= 5:
                trend = self._calculate_trend(values)
                if trend["direction"] == "INCREASING" and trend["slope"] > 0.1:
                    evidence.append({
                        "source": "metric_trend",
                        "item": "{} showing increasing trend (slope: {})".format(
                            name, round(trend["slope"], 3)),
                        "weight": self.SOURCE_WEIGHTS["metric_trend"],
                        "metric_name": name,
                        "trend_direction": trend["direction"]
                    })
        
        return evidence
    
    def _calculate_trend(self, values: List[float]) -> Dict:
        """Calculate trend direction and slope."""
        if len(values) < 2:
            return {"direction": "STABLE", "slope": 0}
        
        # Simple linear regression
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n
        
        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        slope = numerator / denominator if denominator > 0 else 0
        
        if slope > 0.05:
            direction = "INCREASING"
        elif slope < -0.05:
            direction = "DECREASING"
        else:
            direction = "STABLE"
        
        return {"direction": direction, "slope": slope}
    
    def _collect_frequency_evidence(self, alerts: List[Dict], pattern: str) -> List[Dict]:
        """Collect frequency-based evidence."""
        evidence = []
        
        # Count alerts by type
        type_counts = Counter()
        severity_counts = Counter()
        
        for alert in alerts:
            alert_type = (alert.get("issue_type") or alert.get("alert_type") or "UNKNOWN").upper()
            severity = (alert.get("severity") or alert.get("alert_state") or "INFO").upper()
            type_counts[alert_type] += 1
            severity_counts[severity] += 1
        
        # High frequency is evidence
        total = len(alerts)
        if total > 100:
            evidence.append({
                "source": "alert_count",
                "item": "{:,} total alerts in dataset".format(total),
                "weight": self.SOURCE_WEIGHTS["alert_count"] * min(total / 1000, 1.5),
                "count": total
            })
        
        # CRITICAL count
        critical_count = severity_counts.get("CRITICAL", 0)
        if critical_count > 10:
            evidence.append({
                "source": "alert_count",
                "item": "{} CRITICAL severity alerts".format(critical_count),
                "weight": self.SOURCE_WEIGHTS["alert_count"] * 1.2,
                "severity": "CRITICAL",
                "count": critical_count
            })
        
        # Type-specific evidence
        relevant_types = {
            "TABLESPACE_EXHAUSTION": ["INTERNAL_ERROR", "STORAGE"],
            "MEMORY_EXHAUSTION": ["MEMORY", "OOM"],
            "INTERNAL_ERROR": ["INTERNAL_ERROR", "CRASH"]
        }
        
        for relevant_type in relevant_types.get(pattern, []):
            if relevant_type in type_counts:
                count = type_counts[relevant_type]
                evidence.append({
                    "source": "alert_count",
                    "item": "{} {} type alerts".format(count, relevant_type),
                    "weight": self.SOURCE_WEIGHTS["alert_count"],
                    "type": relevant_type,
                    "count": count
                })
        
        return evidence
    
    def _collect_time_correlation(self, alerts: List[Dict]) -> List[Dict]:
        """Collect time correlation evidence."""
        evidence = []
        
        # Parse timestamps
        times = []
        for alert in alerts:
            time_str = alert.get("alert_time") or alert.get("time") or ""
            try:
                dt = datetime.strptime(str(time_str)[:19], "%Y-%m-%dT%H:%M:%S")
                times.append(dt)
            except:
                continue
        
        if len(times) < 2:
            return evidence
        
        times.sort()
        
        # Check for burst patterns (many alerts in short window)
        burst_window = timedelta(minutes=5)
        burst_counts = []
        
        i = 0
        while i < len(times):
            window_end = times[i] + burst_window
            count = 1
            j = i + 1
            while j < len(times) and times[j] <= window_end:
                count += 1
                j += 1
            
            if count >= 10:
                burst_counts.append({
                    "time": times[i],
                    "count": count
                })
            i = j if j > i + 1 else i + 1
        
        if burst_counts:
            max_burst = max(burst_counts, key=lambda b: b["count"])
            evidence.append({
                "source": "time_correlation",
                "item": "Alert burst: {} alerts in 5 minutes at {}".format(
                    max_burst["count"], max_burst["time"].strftime("%H:%M")),
                "weight": self.SOURCE_WEIGHTS["time_correlation"],
                "burst_count": max_burst["count"]
            })
        
        return evidence
    
    def _find_contradictions(self, 
                            alerts: List[Dict],
                            metrics: List[Dict],
                            pattern: str) -> List[Dict]:
        """Find evidence that contradicts the hypothesis."""
        contradictions = []
        
        # Check for recovery indicators
        for alert in alerts:
            severity = (alert.get("severity") or "").upper()
            message = (alert.get("message") or "").upper()
            
            if severity == "CLEAR" or "RESOLVED" in message or "RECOVERED" in message:
                contradictions.append({
                    "item": "Recovery indicator: {}".format(severity),
                    "impact": "Suggests issue may be transient"
                })
                break  # One is enough
        
        # Pattern-specific contradictions
        if pattern == "TABLESPACE_EXHAUSTION" and metrics:
            for m in metrics:
                name = (m.get("metric_name") or "").lower()
                if "storage" in name or "tablespace" in name:
                    try:
                        value = float(m.get("metric_value") or 0)
                        if value < 50:
                            contradictions.append({
                                "item": "Storage at {}% - not critically full".format(value),
                                "impact": "May indicate cleanup occurred"
                            })
                            break
                    except:
                        pass
        
        return contradictions[:3]  # Limit contradictions
    
    def validate_evidence(self, evidence_items: List[Dict]) -> Dict:
        """
        Validate collected evidence.
        
        Args:
            evidence_items: List of evidence dictionaries
            
        Returns:
            Validation result
        """
        if not evidence_items:
            return {
                "valid": False,
                "reason": "No evidence provided",
                "quality_score": 0
            }
        
        # Count by source type
        source_counts = Counter(e.get("source") for e in evidence_items)
        
        # Check for diversity (multiple source types is better)
        diversity = len(source_counts)
        
        # Check for primary evidence
        has_primary = any(e.get("relevance") == "PRIMARY" for e in evidence_items)
        
        # Calculate quality score
        total_weight = sum(e.get("weight", 0.5) for e in evidence_items)
        diversity_bonus = diversity * 0.1
        primary_bonus = 0.2 if has_primary else 0
        
        quality_score = min(total_weight + diversity_bonus + primary_bonus, 1.0)
        
        return {
            "valid": quality_score > 0.3,
            "quality_score": round(quality_score, 2),
            "evidence_count": len(evidence_items),
            "source_diversity": diversity,
            "has_primary_evidence": has_primary,
            "recommendation": (
                "Evidence sufficient for conclusion" if quality_score > 0.6 else
                "Gather more evidence before concluding"
            )
        }
    
    def build_evidence_chain(self, 
                            root_cause: str,
                            alerts: List[Dict],
                            metrics: List[Dict] = None) -> Dict:
        """
        Build complete evidence chain for a root cause.
        
        Args:
            root_cause: The root cause to build chain for
            alerts: Alert data
            metrics: Optional metric data
            
        Returns:
            Complete evidence chain
        """
        # Map root cause to pattern
        cause_to_pattern = {
            "INTERNAL_DATABASE_ERROR": "INTERNAL_ERROR",
            "STORAGE_CAPACITY": "TABLESPACE_EXHAUSTION",
            "MEMORY_PRESSURE": "MEMORY_EXHAUSTION",
            "CPU_RESOURCE": "CPU_SATURATION",
            "NETWORK_CONNECTIVITY": "NETWORK_ISSUE"
        }
        
        pattern = cause_to_pattern.get(root_cause, root_cause)
        
        # Create dummy hypothesis for evidence collection
        hypothesis = {"pattern": pattern, "id": "CHAIN"}
        
        # Collect all evidence
        evidence_package = self.collect_evidence(hypothesis, alerts, metrics)
        
        # Build the chain
        chain_links = []
        
        # Primary evidence (direct indicators)
        primary = [e for e in evidence_package["evidence_items"] 
                  if e.get("relevance") == "PRIMARY" or e.get("weight", 0) > 0.8]
        if primary:
            chain_links.append({
                "level": "PRIMARY",
                "description": "Direct error indicators",
                "items": primary[:5]
            })
        
        # Secondary evidence (corroborating)
        secondary = [e for e in evidence_package["evidence_items"]
                    if e not in primary and e.get("weight", 0) > 0.5]
        if secondary:
            chain_links.append({
                "level": "SECONDARY",
                "description": "Corroborating evidence",
                "items": secondary[:5]
            })
        
        # Contextual evidence
        contextual = [e for e in evidence_package["evidence_items"]
                     if e not in primary and e not in secondary]
        if contextual:
            chain_links.append({
                "level": "CONTEXTUAL",
                "description": "Supporting context",
                "items": contextual[:5]
            })
        
        return {
            "root_cause": root_cause,
            "pattern": pattern,
            "chain_strength": evidence_package["evidence_strength"],
            "chain_links": chain_links,
            "contradictions": evidence_package["contradictions"],
            "total_evidence_items": evidence_package["evidence_count"],
            "confidence": (
                "HIGH" if evidence_package["evidence_strength"] == "STRONG" else
                "MEDIUM" if evidence_package["evidence_strength"] == "MODERATE" else
                "LOW"
            )
        }
