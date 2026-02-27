"""
HYPOTHESIS ENGINE

Purpose:
    Generates ranked hypotheses from symptoms.
    A DBA doesn't jump to conclusions - they form hypotheses and test them.

Algorithm:
    1. Extract symptoms from alerts/metrics
    2. Match symptoms against known issue patterns
    3. Generate probability-weighted hypotheses
    4. Rank by evidence strength

Function Signatures:
    generate_hypotheses(symptoms: List[Dict]) -> List[Hypothesis]
    test_hypothesis(hypothesis: Hypothesis, evidence: List[Dict]) -> TestResult
    rank_hypotheses(hypotheses: List[Hypothesis]) -> List[RankedHypothesis]

Example Output:
    {
        "hypotheses": [
            {
                "id": "H1",
                "title": "Tablespace exhaustion causing write failures",
                "probability": 0.85,
                "evidence_for": ["ORA-1653 in 23 alerts", "Storage at 97%"],
                "evidence_against": ["No archive log issues"],
                "required_tests": ["Check DBA_FREE_SPACE", "Verify autoextend"]
            }
        ]
    }
"""

from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import re


class HypothesisEngine:
    """
    Generates and tests hypotheses like an experienced DBA.
    """
    
    # Known issue patterns mapped to hypotheses
    SYMPTOM_PATTERNS = {
        "TABLESPACE_EXHAUSTION": {
            "symptoms": ["ORA-1653", "ORA-1652", "ORA-1654", "tablespace", "storage full", "cannot extend"],
            "weight": 1.0,
            "tests": [
                "SELECT tablespace_name, ROUND((used_space/max_size)*100,2) pct FROM DBA_TABLESPACE_USAGE_METRICS",
                "Check datafile autoextend: DBA_DATA_FILES",
                "Identify largest segments: DBA_SEGMENTS ORDER BY bytes DESC"
            ]
        },
        "UNDO_PRESSURE": {
            "symptoms": ["ORA-1555", "ORA-30036", "snapshot too old", "undo", "rollback"],
            "weight": 0.95,
            "tests": [
                "SELECT * FROM V$UNDOSTAT ORDER BY BEGIN_TIME DESC",
                "Check UNDO_RETENTION parameter",
                "Identify long-running transactions"
            ]
        },
        "MEMORY_EXHAUSTION": {
            "symptoms": ["ORA-4031", "shared pool", "memory", "pga", "sga", "cannot allocate"],
            "weight": 0.9,
            "tests": [
                "SELECT * FROM V$SHARED_POOL_ADVICE",
                "SELECT * FROM V$PGA_TARGET_ADVICE",
                "Check V$LIBRARYCACHE for reloads"
            ]
        },
        "INTERNAL_ERROR": {
            "symptoms": ["ORA-600", "ORA-7445", "internal error", "kernel"],
            "weight": 1.0,
            "tests": [
                "Extract error arguments from alert log",
                "Search My Oracle Support (MOS) for bug ID",
                "Check Oracle patch level"
            ]
        },
        "NETWORK_ISSUE": {
            "symptoms": ["ORA-12170", "ORA-12154", "TNS", "listener", "connection", "timeout", "network"],
            "weight": 0.85,
            "tests": [
                "lsnrctl status",
                "tnsping <service_name>",
                "Check listener.log for errors"
            ]
        },
        "DATAGUARD_LAG": {
            "symptoms": ["apply lag", "standby", "data guard", "replication", "sync"],
            "weight": 0.9,
            "tests": [
                "DGMGRL> SHOW CONFIGURATION",
                "SELECT * FROM V$DATAGUARD_STATS",
                "Check network bandwidth to standby"
            ]
        },
        "CPU_SATURATION": {
            "symptoms": ["cpu", "load", "runaway", "parallel", "resource"],
            "weight": 0.8,
            "tests": [
                "Check V$SESSION for high CPU sessions",
                "Review V$SQL for high CPU queries",
                "Check Resource Manager configuration"
            ]
        },
        "LOCK_CONTENTION": {
            "symptoms": ["enqueue", "lock", "blocked", "deadlock", "waiting", "ORA-60"],
            "weight": 0.85,
            "tests": [
                "SELECT * FROM V$LOCK WHERE BLOCK=1",
                "Check DBA_BLOCKERS view",
                "Review V$SESSION_WAIT for lock waits"
            ]
        },
        "IO_BOTTLENECK": {
            "symptoms": ["i/o", "disk", "read", "write", "latency", "storage"],
            "weight": 0.75,
            "tests": [
                "Check V$FILESTAT for I/O distribution",
                "Review V$SYSTEM_EVENT for I/O waits",
                "Check ASM disk group performance"
            ]
        },
        "ARCHIVE_LOG_ISSUE": {
            "symptoms": ["archiver", "ORA-257", "archive", "FRA", "flash recovery"],
            "weight": 0.95,
            "tests": [
                "Check V$FLASH_RECOVERY_AREA_USAGE",
                "Verify archive destination space",
                "Check LOG_ARCHIVE_DEST status"
            ]
        }
    }
    
    def __init__(self):
        """Initialize hypothesis engine."""
        self.hypothesis_cache = {}
        self.test_results = {}
    
    def generate_hypotheses(self, 
                           alerts: List[Dict],
                           metrics: List[Dict] = None,
                           target: str = None) -> List[Dict]:
        """
        Generate hypotheses from symptoms.
        
        Args:
            alerts: List of alert dictionaries
            metrics: Optional list of metric dictionaries
            target: Optional target database filter
            
        Returns:
            List of hypothesis dictionaries, ranked by probability
        """
        if not alerts:
            return []
        
        # Filter by target if specified - STRICT EXACT MATCHING
        if target:
            target_upper = target.upper()
            alerts = [a for a in alerts 
                     if (a.get("target") or a.get("target_name") or "").upper() == target_upper]
        
        # Extract symptoms from alerts
        symptoms = self._extract_symptoms(alerts)
        
        # Match against known patterns
        matches = self._match_patterns(symptoms)
        
        # Generate hypotheses with evidence
        hypotheses = []
        for pattern_name, match_data in matches.items():
            hypothesis = self._build_hypothesis(
                pattern_name, 
                match_data, 
                symptoms,
                alerts
            )
            hypotheses.append(hypothesis)
        
        # Add metrics-based hypotheses
        if metrics:
            metric_hypotheses = self._generate_metric_hypotheses(metrics, target)
            hypotheses.extend(metric_hypotheses)
        
        # Rank by probability
        hypotheses = sorted(hypotheses, key=lambda h: h["probability"], reverse=True)
        
        # Assign IDs
        for i, h in enumerate(hypotheses, 1):
            h["id"] = "H{}".format(i)
        
        return hypotheses[:10]  # Top 10 hypotheses
    
    def _extract_symptoms(self, alerts: List[Dict]) -> Dict:
        """Extract symptoms from alert messages."""
        symptoms = {
            "ora_codes": Counter(),
            "keywords": Counter(),
            "severity_counts": Counter(),
            "targets": Counter(),
            "raw_messages": []
        }
        
        for alert in alerts:
            message = (alert.get("message") or alert.get("alert_message") or "").upper()
            severity = (alert.get("severity") or alert.get("alert_state") or "INFO").upper()
            target = (alert.get("target") or alert.get("target_name") or "UNKNOWN").upper()
            
            # Extract ORA codes
            ora_matches = re.findall(r'ORA-(\d+)', message)
            for code in ora_matches:
                symptoms["ora_codes"]["ORA-" + code] += 1
            
            # Extract keywords
            keywords = ["tablespace", "memory", "cpu", "disk", "listener", 
                       "timeout", "connection", "lag", "standby", "lock",
                       "deadlock", "archive", "undo", "rollback", "internal"]
            for kw in keywords:
                if kw in message.lower():
                    symptoms["keywords"][kw] += 1
            
            symptoms["severity_counts"][severity] += 1
            symptoms["targets"][target] += 1
            symptoms["raw_messages"].append(message)
        
        return symptoms
    
    def _match_patterns(self, symptoms: Dict) -> Dict[str, Dict]:
        """Match symptoms against known patterns."""
        matches = {}
        
        for pattern_name, pattern_data in self.SYMPTOM_PATTERNS.items():
            match_score = 0
            evidence = []
            
            for symptom in pattern_data["symptoms"]:
                # Check ORA codes
                if symptom.startswith("ORA-"):
                    if symptom in symptoms["ora_codes"]:
                        count = symptoms["ora_codes"][symptom]
                        match_score += count * 10
                        evidence.append("{} found {} times".format(symptom, count))
                else:
                    # Check keywords
                    if symptom.lower() in symptoms["keywords"]:
                        count = symptoms["keywords"][symptom.lower()]
                        match_score += count * 2
                        evidence.append("'{}' keyword in {} alerts".format(symptom, count))
                    
                    # Check raw messages
                    for msg in symptoms["raw_messages"]:
                        if symptom.upper() in msg:
                            match_score += 1
            
            if match_score > 0:
                matches[pattern_name] = {
                    "score": match_score,
                    "weight": pattern_data["weight"],
                    "evidence": evidence,
                    "tests": pattern_data["tests"]
                }
        
        return matches
    
    def _build_hypothesis(self, 
                         pattern_name: str, 
                         match_data: Dict,
                         symptoms: Dict,
                         alerts: List[Dict]) -> Dict:
        """Build a complete hypothesis from pattern match."""
        
        # Calculate probability based on evidence strength
        max_score = 100  # Normalize against max possible
        raw_probability = min(match_data["score"] / max_score, 0.99)
        weighted_probability = raw_probability * match_data["weight"]
        
        # Build evidence against (what doesn't fit)
        evidence_against = []
        if pattern_name == "TABLESPACE_EXHAUSTION":
            if symptoms["keywords"].get("archive", 0) == 0:
                evidence_against.append("No archive log issues observed")
        elif pattern_name == "MEMORY_EXHAUSTION":
            if symptoms["keywords"].get("cpu", 0) > symptoms["keywords"].get("memory", 0):
                evidence_against.append("CPU issues more prominent than memory")
        
        # Add severity context
        if symptoms["severity_counts"].get("CRITICAL", 0) > 10:
            weighted_probability = min(weighted_probability * 1.2, 0.99)
        
        # Build hypothesis title
        titles = {
            "TABLESPACE_EXHAUSTION": "Tablespace space exhaustion causing allocation failures",
            "UNDO_PRESSURE": "Undo tablespace pressure causing transaction failures",
            "MEMORY_EXHAUSTION": "Shared pool/PGA memory exhaustion",
            "INTERNAL_ERROR": "Oracle internal bug or memory corruption",
            "NETWORK_ISSUE": "Network/listener connectivity problems",
            "DATAGUARD_LAG": "Data Guard synchronization lag",
            "CPU_SATURATION": "CPU resource saturation",
            "LOCK_CONTENTION": "Database lock contention",
            "IO_BOTTLENECK": "Storage I/O performance bottleneck",
            "ARCHIVE_LOG_ISSUE": "Archive log destination space/accessibility"
        }
        
        return {
            "pattern": pattern_name,
            "title": titles.get(pattern_name, pattern_name.replace("_", " ").title()),
            "probability": round(weighted_probability, 2),
            "evidence_for": match_data["evidence"][:5],
            "evidence_against": evidence_against[:3],
            "required_tests": match_data["tests"],
            "severity_context": dict(symptoms["severity_counts"]),
            "affected_targets": [t for t, c in symptoms["targets"].most_common(3)]
        }
    
    def _generate_metric_hypotheses(self, 
                                   metrics: List[Dict], 
                                   target: str = None) -> List[Dict]:
        """Generate hypotheses from metric anomalies."""
        hypotheses = []
        
        # Group metrics by type
        metric_values = defaultdict(list)
        for m in metrics:
            name = (m.get("metric_name") or m.get("name") or "unknown").lower()
            try:
                value = float(m.get("metric_value") or m.get("value") or 0)
                metric_values[name].append(value)
            except (ValueError, TypeError):
                continue
        
        # Check for anomalies
        for name, values in metric_values.items():
            if not values:
                continue
            
            avg_value = sum(values) / len(values)
            max_value = max(values)
            
            if "cpu" in name and max_value > 85:
                hypotheses.append({
                    "pattern": "CPU_FROM_METRICS",
                    "title": "High CPU utilization detected",
                    "probability": min(max_value / 100, 0.95),
                    "evidence_for": ["CPU peaked at {}%".format(round(max_value, 1)),
                                    "Average CPU: {}%".format(round(avg_value, 1))],
                    "evidence_against": [],
                    "required_tests": ["Identify top CPU consumers", "Check parallel query activity"],
                    "severity_context": {"HIGH": 1 if max_value > 90 else 0},
                    "affected_targets": [target] if target else []
                })
            
            if "memory" in name and max_value > 90:
                hypotheses.append({
                    "pattern": "MEMORY_FROM_METRICS",
                    "title": "Memory pressure detected from metrics",
                    "probability": min(max_value / 100, 0.95),
                    "evidence_for": ["Memory usage peaked at {}%".format(round(max_value, 1))],
                    "evidence_against": [],
                    "required_tests": ["Check SGA/PGA allocation", "Review memory advisors"],
                    "severity_context": {"HIGH": 1 if max_value > 95 else 0},
                    "affected_targets": [target] if target else []
                })
            
            if ("storage" in name or "tablespace" in name) and max_value > 85:
                hypotheses.append({
                    "pattern": "STORAGE_FROM_METRICS",
                    "title": "Storage capacity warning from metrics",
                    "probability": min(max_value / 100, 0.90),
                    "evidence_for": ["Storage at {}%".format(round(max_value, 1))],
                    "evidence_against": [],
                    "required_tests": ["Check tablespace free space", "Review autoextend settings"],
                    "severity_context": {"WARNING": 1},
                    "affected_targets": [target] if target else []
                })
        
        return hypotheses
    
    def test_hypothesis(self, 
                       hypothesis: Dict, 
                       additional_evidence: List[Dict]) -> Dict:
        """
        Test a hypothesis against additional evidence.
        
        Args:
            hypothesis: Hypothesis dictionary
            additional_evidence: New alerts or metrics to test against
            
        Returns:
            Test result with updated probability
        """
        if not additional_evidence:
            return {
                "hypothesis_id": hypothesis.get("id"),
                "status": "UNTESTABLE",
                "message": "No additional evidence provided",
                "updated_probability": hypothesis["probability"]
            }
        
        # Extract symptoms from new evidence
        symptoms = self._extract_symptoms(additional_evidence)
        
        # Check if new evidence supports or refutes
        support_count = 0
        refute_count = 0
        new_evidence = []
        
        pattern = hypothesis.get("pattern", "")
        if pattern in self.SYMPTOM_PATTERNS:
            for symptom in self.SYMPTOM_PATTERNS[pattern]["symptoms"]:
                if symptom.startswith("ORA-"):
                    if symptom in symptoms["ora_codes"]:
                        support_count += symptoms["ora_codes"][symptom]
                        new_evidence.append("SUPPORTS: {} found".format(symptom))
                elif symptom.lower() in symptoms["keywords"]:
                    support_count += symptoms["keywords"][symptom.lower()]
                    new_evidence.append("SUPPORTS: '{}' found".format(symptom))
        
        # Adjust probability
        original_prob = hypothesis["probability"]
        if support_count > refute_count:
            adjustment = min(0.1 * (support_count - refute_count), 0.2)
            new_prob = min(original_prob + adjustment, 0.99)
            status = "SUPPORTED"
        elif refute_count > support_count:
            adjustment = min(0.1 * (refute_count - support_count), 0.3)
            new_prob = max(original_prob - adjustment, 0.05)
            status = "REFUTED"
        else:
            new_prob = original_prob
            status = "INCONCLUSIVE"
        
        return {
            "hypothesis_id": hypothesis.get("id"),
            "status": status,
            "support_count": support_count,
            "refute_count": refute_count,
            "new_evidence": new_evidence,
            "original_probability": original_prob,
            "updated_probability": round(new_prob, 2)
        }
    
    def rank_hypotheses(self, hypotheses: List[Dict]) -> List[Dict]:
        """
        Rank hypotheses by multiple factors.
        
        Args:
            hypotheses: List of hypothesis dictionaries
            
        Returns:
            Sorted list with rank information
        """
        for h in hypotheses:
            # Composite score
            prob_score = h["probability"] * 40
            evidence_score = min(len(h.get("evidence_for", [])) * 5, 20)
            severity_score = (h.get("severity_context", {}).get("CRITICAL", 0) * 30 +
                            h.get("severity_context", {}).get("HIGH", 0) * 10)
            
            h["composite_score"] = round(prob_score + evidence_score + severity_score, 2)
        
        ranked = sorted(hypotheses, key=lambda h: h["composite_score"], reverse=True)
        
        for i, h in enumerate(ranked, 1):
            h["rank"] = i
            h["confidence_level"] = (
                "HIGH" if h["probability"] > 0.7 else
                "MEDIUM" if h["probability"] > 0.4 else
                "LOW"
            )
        
        return ranked
