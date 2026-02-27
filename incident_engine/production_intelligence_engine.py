# incident_engine/production_intelligence_engine.py
"""
==============================================================
PRODUCTION INTELLIGENCE ENGINE (INDUSTRY-GRADE)
==============================================================

MANDATORY BACKEND LOGIC LAYERS (ALL IMPLEMENTED):

1. ROOT CAUSE FALLBACK (CRITICAL)
   - NEVER return "Unknown" if evidence exists
   - Medium-confidence inferred root cause enforced
   - Uses ORA frequency, burst repetition, severity dominance
   
2. ORA CODE → ABSTRACT CAUSE MAPPING
   - All ORA codes mapped to actionable DBA categories
   - e.g., ORA-600 → Internal engine instability
   
3. ACTION FALLBACK (NO "NO ACTIONS" EVER)
   - Risk-based fallback actions always present
   - DBA ALWAYS gets: Immediate actions, Priority, Urgency
   
4. TRUE DOWN vs CRITICAL SEPARATION
   - DOWN = STOP, SHUTDOWN, INSTANCE_TERMINATED
   - CRITICAL = DB running but unstable
   - Explicit separation enforced
   
5. WIDENING LOGIC (ANTI-FALSE-ZERO)
   - Auto-widen time window, severity, category
   - Always explain what was checked and why widening applied
   
6. SESSION / ENVIRONMENT MEMORY (GLOBAL STATE)
   - Highest risk database tracked
   - Dominant ORA codes tracked
   - Peak alert hours tracked
   - Future answers reference prior analysis

Python 3.6.8 compatible.
"""

import re
from collections import defaultdict
from datetime import datetime


class ORACodeMappingEngine:
    """
    LAYER 2: ORA CODE → ABSTRACT CAUSE MAPPING
    
    Maps specific ORA codes to actionable DBA categories.
    NEVER returns raw ORA codes without classification.
    """
    
    # Comprehensive ORA code mapping (production-grade)
    ORA_MAPPINGS = {
        # Internal Engine Errors
        "ORA-600": {
            "abstract_cause": "Internal Oracle engine instability",
            "category": "KERNEL",
            "severity": "CRITICAL",
            "actions": [
                "IMMEDIATE: Collect trace files from $ORACLE_BASE/diag/rdbms/",
                "Search My Oracle Support for ORA-600 with specific arguments",
                "Check if recent patches were applied or reverted",
                "Consider raising Oracle SR with trace files"
            ],
            "investigation_priority": "P1"
        },
        "ORA-00600": {
            "abstract_cause": "Internal Oracle engine instability",
            "category": "KERNEL",
            "severity": "CRITICAL",
            "actions": [
                "IMMEDIATE: Collect trace files from $ORACLE_BASE/diag/rdbms/",
                "Search My Oracle Support for ORA-600 with specific arguments",
                "Check if recent patches were applied or reverted",
                "Consider raising Oracle SR with trace files"
            ],
            "investigation_priority": "P1"
        },
        
        # Memory Corruption / Process Crash
        "ORA-7445": {
            "abstract_cause": "Memory corruption / process crash",
            "category": "MEMORY",
            "severity": "CRITICAL",
            "actions": [
                "IMMEDIATE: Check OS dmesg for kernel OOM or memory errors",
                "Review core dump in $ORACLE_BASE/diag/",
                "Verify memory limits (ulimit settings)",
                "Apply latest Oracle patches"
            ],
            "investigation_priority": "P1"
        },
        "ORA-07445": {
            "abstract_cause": "Memory corruption / process crash",
            "category": "MEMORY",
            "severity": "CRITICAL",
            "actions": [
                "IMMEDIATE: Check OS dmesg for kernel OOM or memory errors",
                "Review core dump in $ORACLE_BASE/diag/",
                "Verify memory limits (ulimit settings)",
                "Apply latest Oracle patches"
            ],
            "investigation_priority": "P1"
        },
        
        # Network / TNS Instability
        "ORA-12154": {
            "abstract_cause": "Network / TNS connection resolution failure",
            "category": "NETWORK",
            "severity": "HIGH",
            "actions": [
                "Verify tnsnames.ora configuration",
                "Test: tnsping <service_name>",
                "Check listener status: lsnrctl status",
                "Verify DNS resolution for host"
            ],
            "investigation_priority": "P2"
        },
        "ORA-12170": {
            "abstract_cause": "Network / TNS connection timeout",
            "category": "NETWORK",
            "severity": "HIGH",
            "actions": [
                "Check network connectivity between client and server",
                "Verify firewall rules for Oracle ports",
                "Review SQLNET.INBOUND_CONNECT_TIMEOUT",
                "Check listener log for connection attempts"
            ],
            "investigation_priority": "P2"
        },
        "ORA-12537": {
            "abstract_cause": "Network / TNS instability",
            "category": "NETWORK",
            "severity": "HIGH",
            "actions": [
                "Check listener status and restart if necessary",
                "Verify network stability (packet loss, latency)",
                "Review TNS configuration for timeouts",
                "Check for connection pool exhaustion"
            ],
            "investigation_priority": "P2"
        },
        "ORA-12541": {
            "abstract_cause": "Network / Listener not running",
            "category": "NETWORK",
            "severity": "CRITICAL",
            "actions": [
                "IMMEDIATE: Start listener - lsnrctl start",
                "Check listener.log for shutdown reason",
                "Verify listener.ora configuration",
                "Set up listener auto-restart"
            ],
            "investigation_priority": "P1"
        },
        
        # Storage Pressure
        "ORA-1652": {
            "abstract_cause": "Storage pressure - unable to extend temp segment",
            "category": "STORAGE",
            "severity": "HIGH",
            "actions": [
                "Add datafile to TEMP tablespace",
                "Identify sessions with large sorts",
                "Review PGA_AGGREGATE_TARGET setting",
                "Clean up orphaned temp segments"
            ],
            "investigation_priority": "P2"
        },
        "ORA-1653": {
            "abstract_cause": "Storage pressure - unable to extend table",
            "category": "STORAGE",
            "severity": "HIGH",
            "actions": [
                "Add datafile to tablespace or enable AUTOEXTEND",
                "Identify tablespace usage: SELECT * FROM dba_tablespace_usage_metrics",
                "Purge historical data if applicable",
                "Implement proactive space monitoring"
            ],
            "investigation_priority": "P2"
        },
        "ORA-1654": {
            "abstract_cause": "Storage pressure - unable to extend index",
            "category": "STORAGE",
            "severity": "HIGH",
            "actions": [
                "Add space to index tablespace",
                "Consider index rebuild with COMPRESS",
                "Review index sizing and partitioning",
                "Monitor tablespace growth rate"
            ],
            "investigation_priority": "P2"
        },
        "ORA-19815": {
            "abstract_cause": "Storage pressure - flash recovery area full",
            "category": "STORAGE",
            "severity": "CRITICAL",
            "actions": [
                "IMMEDIATE: Delete obsolete backups: RMAN> DELETE OBSOLETE",
                "Backup archive logs to tape/cloud",
                "Increase db_recovery_file_dest_size",
                "Review retention policy"
            ],
            "investigation_priority": "P1"
        },
        
        # Memory Pressure
        "ORA-4031": {
            "abstract_cause": "Memory pressure - shared pool exhaustion",
            "category": "MEMORY",
            "severity": "HIGH",
            "actions": [
                "Increase SHARED_POOL_SIZE or SGA_TARGET",
                "Identify cursor leaks: SELECT * FROM v$sqlarea WHERE parsing_schema_name NOT IN ('SYS')",
                "Pin frequently used packages: DBMS_SHARED_POOL.KEEP",
                "Enable cursor_sharing if hard parsing is excessive"
            ],
            "investigation_priority": "P2"
        },
        "ORA-04031": {
            "abstract_cause": "Memory pressure - shared pool exhaustion",
            "category": "MEMORY",
            "severity": "HIGH",
            "actions": [
                "Increase SHARED_POOL_SIZE or SGA_TARGET",
                "Identify cursor leaks: SELECT * FROM v$sqlarea WHERE parsing_schema_name NOT IN ('SYS')",
                "Pin frequently used packages: DBMS_SHARED_POOL.KEEP",
                "Enable cursor_sharing if hard parsing is excessive"
            ],
            "investigation_priority": "P2"
        },
        "ORA-4030": {
            "abstract_cause": "Memory pressure - process memory exhaustion",
            "category": "MEMORY",
            "severity": "HIGH",
            "actions": [
                "Increase PGA_AGGREGATE_TARGET",
                "Check for memory leaks in applications",
                "Review OS memory limits (ulimit)",
                "Monitor process memory: SELECT * FROM v$process"
            ],
            "investigation_priority": "P2"
        },
        
        # Data Guard / Replication
        "ORA-16014": {
            "abstract_cause": "Archive log destination issue",
            "category": "DATAGUARD",
            "severity": "CRITICAL",
            "actions": [
                "IMMEDIATE: Check archive dest status: SELECT * FROM v$archive_dest",
                "Verify network to standby database",
                "Clear any archive gaps",
                "Check standby redo log capacity"
            ],
            "investigation_priority": "P1"
        },
        "ORA-16058": {
            "abstract_cause": "Data Guard configuration error",
            "category": "DATAGUARD",
            "severity": "HIGH",
            "actions": [
                "Verify Data Guard configuration: DGMGRL> SHOW CONFIGURATION",
                "Check standby database status",
                "Review alert log on both primary and standby",
                "Reinitialize standby if necessary"
            ],
            "investigation_priority": "P2"
        },
        
        # Undo / Snapshot Issues
        "ORA-1555": {
            "abstract_cause": "Undo retention / snapshot too old",
            "category": "UNDO",
            "severity": "MEDIUM",
            "actions": [
                "Increase UNDO_RETENTION parameter",
                "Size UNDO tablespace appropriately",
                "Optimize long-running queries",
                "Implement query chunking for large reads"
            ],
            "investigation_priority": "P3"
        },
        
        # Instance Crash / Startup
        "ORA-1034": {
            "abstract_cause": "Database not available - instance not started",
            "category": "INSTANCE",
            "severity": "CRITICAL",
            "actions": [
                "IMMEDIATE: Check alert log for shutdown reason",
                "Attempt startup: sqlplus / as sysdba; STARTUP;",
                "If corrupt, check for RECOVER DATABASE need",
                "Escalate if instance won't start"
            ],
            "investigation_priority": "P1"
        },
        "ORA-01034": {
            "abstract_cause": "Database not available - instance not started",
            "category": "INSTANCE",
            "severity": "CRITICAL",
            "actions": [
                "IMMEDIATE: Check alert log for shutdown reason",
                "Attempt startup: sqlplus / as sysdba; STARTUP;",
                "If corrupt, check for RECOVER DATABASE need",
                "Escalate if instance won't start"
            ],
            "investigation_priority": "P1"
        },
        "ORA-1033": {
            "abstract_cause": "Database initialization/shutdown in progress",
            "category": "INSTANCE",
            "severity": "HIGH",
            "actions": [
                "Wait for operation to complete",
                "Monitor alert log for progress",
                "Check v$instance for status"
            ],
            "investigation_priority": "P2"
        }
    }
    
    # Category to abstract cause fallback
    CATEGORY_ABSTRACTS = {
        "INTERNAL_ERROR": "Internal Oracle engine instability",
        "MEMORY_ERROR": "Memory pressure (SGA/PGA)",
        "STORAGE_FULL": "Storage / tablespace capacity exhaustion",
        "TIMEOUT": "Connection timeout / network latency",
        "LISTENER_DOWN": "Network / listener disruption",
        "DATAGUARD_GAP": "Data Guard / replication instability",
        "PERFORMANCE": "Performance degradation",
        "ARCHIVELOG": "Archive log management issue",
        "TABLESPACE": "Tablespace capacity exhaustion"
    }
    
    @classmethod
    def get_mapping(cls, ora_code):
        """
        Get full mapping for an ORA code.
        
        Returns:
            Dict with abstract_cause, category, severity, actions, priority
        """
        if not ora_code:
            return None
        
        # Normalize the code
        code_upper = ora_code.upper().strip()
        
        # Direct match
        if code_upper in cls.ORA_MAPPINGS:
            return cls.ORA_MAPPINGS[code_upper]
        
        # Try with ORA- prefix variants
        if code_upper.startswith("ORA-"):
            base = code_upper.replace("ORA-", "ORA-0").lstrip("0") if len(code_upper) < 8 else code_upper
            for key in cls.ORA_MAPPINGS:
                if base in key or key in base:
                    return cls.ORA_MAPPINGS[key]
        
        # Try numeric extraction
        num_match = re.search(r'(\d+)', code_upper)
        if num_match:
            num = num_match.group(1)
            for key in cls.ORA_MAPPINGS:
                if num in key:
                    return cls.ORA_MAPPINGS[key]
        
        return None
    
    @classmethod
    def get_abstract_cause(cls, ora_code_or_category):
        """
        Get abstract cause for ORA code or category.
        
        RULE: NEVER return "Unknown" if any evidence exists.
        """
        if not ora_code_or_category:
            return "General system instability (investigation needed)"
        
        input_upper = ora_code_or_category.upper().strip()
        
        # Check ORA mapping
        mapping = cls.get_mapping(input_upper)
        if mapping:
            return mapping["abstract_cause"]
        
        # Check category mapping
        for cat, abstract in cls.CATEGORY_ABSTRACTS.items():
            if cat in input_upper or input_upper in cat:
                return abstract
        
        # Pattern-based inference
        if "ORA-600" in input_upper or "00600" in input_upper:
            return "Internal Oracle engine instability"
        elif "ORA-7445" in input_upper or "07445" in input_upper:
            return "Memory corruption / process crash"
        elif any(x in input_upper for x in ["TNS", "LISTENER", "1215", "1254"]):
            return "Network / listener disruption"
        elif any(x in input_upper for x in ["TABLESPACE", "STORAGE", "165", "ORA-01"]):
            return "Storage / tablespace capacity exhaustion"
        elif any(x in input_upper for x in ["MEMORY", "SGA", "PGA", "403"]):
            return "Memory pressure (SGA/PGA)"
        elif any(x in input_upper for x in ["DG", "STANDBY", "GUARD", "160"]):
            return "Data Guard / replication instability"
        elif "ARCHIVE" in input_upper:
            return "Archive log management issue"
        elif "INTERNAL" in input_upper:
            return "Internal Oracle engine instability"
        elif "TIMEOUT" in input_upper:
            return "Connection timeout / network latency"
        
        # Ultimate fallback - but NEVER "Unknown"
        return "Oracle operational issue (requires investigation)"
    
    @classmethod
    def get_actions_for_code(cls, ora_code):
        """
        Get recommended actions for an ORA code.
        
        RULE: NEVER return empty actions.
        """
        mapping = cls.get_mapping(ora_code)
        if mapping and mapping.get("actions"):
            return {
                "actions": mapping["actions"],
                "urgency": mapping.get("severity", "HIGH"),
                "priority": mapping.get("investigation_priority", "P2"),
                "source": "ORA code mapping"
            }
        
        # Fallback actions based on code pattern
        abstract = cls.get_abstract_cause(ora_code)
        return {
            "actions": [
                "Search My Oracle Support for {}".format(ora_code or "error"),
                "Review Oracle alert log for detailed context",
                "Check trace files in $ORACLE_BASE/diag/",
                "Monitor for recurrence and collect patterns"
            ],
            "urgency": "HIGH",
            "priority": "P2",
            "source": "Fallback (abstract: {})".format(abstract)
        }


class RootCauseFallbackEngine:
    """
    LAYER 1: ROOT CAUSE FALLBACK (CRITICAL)
    
    RULES:
    - Root cause may be INFERRED, but NEVER Unknown if evidence exists
    - Use ORA frequency, burst repetition, severity dominance, temporal clustering
    - If evidence > threshold → FORCE inferred root cause
    """
    
    # Minimum evidence thresholds (STRICT CONFIDENCE RULES)
    MIN_FREQUENCY_FOR_INFERENCE = 10  # At least 10 occurrences
    
    # =====================================================
    # MANDATORY CONFIDENCE SCORING RULES
    # =====================================================
    # If evidence_score >= 0.80 → HIGH confidence
    # If evidence_score >= 0.60 → MEDIUM confidence (inferred)
    # If evidence_score >= 0.30 → LOW confidence (patterns exist)
    # Below 0.30 with patterns → Still infer, mark UNKNOWN not allowed
    #
    # ORA-600/INTERNAL_ERROR with high volume MUST NOT be UNKNOWN
    # =====================================================
    MIN_SCORE_FOR_HIGH_CONFIDENCE = 0.80
    MIN_SCORE_FOR_MEDIUM_CONFIDENCE = 0.60
    MIN_SCORE_FOR_LOW_INFERENCE = 0.30
    
    @classmethod
    def infer_root_cause(cls, alerts, target=None):
        """
        Infer root cause with confidence levels.
        
        Returns:
            Dict with:
            - root_cause: The inferred root cause
            - abstract_cause: DBA-actionable category
            - confidence: HIGH/MEDIUM/LOW
            - evidence: List of evidence points
            - score_breakdown: Detailed scoring
        
        RULE: NEVER return "Unknown" if any patterns exist
        """
        if not alerts:
            return {
                "root_cause": "No alert data available",
                "abstract_cause": "Data unavailable",
                "confidence": "NONE",
                "evidence": [],
                "score_breakdown": {}
            }
        
        # Filter by target if specified
        if target:
            target_upper = target.upper()
            alerts = [a for a in alerts if 
                     (a.get("target_name") or a.get("target") or "").upper() == target_upper or
                     target_upper in (a.get("target_name") or a.get("target") or "").upper()]
        
        if not alerts:
            return {
                "root_cause": "No alerts for specified target",
                "abstract_cause": "Target not found in data",
                "confidence": "NONE",
                "evidence": ["Target '{}' has 0 alerts in dataset".format(target)],
                "score_breakdown": {}
            }
        
        # Score all error types
        error_scores = defaultdict(lambda: {
            "count": 0,
            "critical_count": 0,
            "timestamps": [],
            "messages": []
        })
        
        for alert in alerts:
            msg = alert.get("message") or alert.get("msg_text") or ""
            issue_type = alert.get("issue_type") or "INTERNAL_ERROR"
            severity = (alert.get("severity") or "").upper()
            
            # Extract ORA code
            ora_match = re.search(r'ORA-?\d+', msg, re.IGNORECASE)
            error_key = ora_match.group(0).upper() if ora_match else issue_type
            
            error_scores[error_key]["count"] += 1
            if severity == "CRITICAL":
                error_scores[error_key]["critical_count"] += 1
            
            # Extract timestamp
            ts = alert.get("collection_timestamp") or alert.get("timestamp") or alert.get("time")
            if ts:
                error_scores[error_key]["timestamps"].append(ts)
            
            error_scores[error_key]["messages"].append(msg[:100])
        
        if not error_scores:
            return {
                "root_cause": "No error patterns detected",
                "abstract_cause": "General system instability",
                "confidence": "LOW",
                "evidence": ["Analyzed {} alerts but no clear pattern emerged".format(len(alerts))],
                "score_breakdown": {}
            }
        
        # Compute comprehensive scores
        total_alerts = len(alerts)
        scored_causes = []
        
        for error_key, data in error_scores.items():
            count = data["count"]
            critical_count = data["critical_count"]
            
            # 1. Frequency score (0-1)
            frequency_score = count / total_alerts
            
            # 2. Severity dominance (0-1)
            severity_score = critical_count / max(count, 1)
            
            # 3. Burst density (0-1) - are occurrences clustered?
            burst_score = cls._compute_burst_score(data["timestamps"])
            
            # 4. Repetition score (0-1) - raw count impact
            repetition_score = min(count / 1000, 1.0)
            
            # Weighted total
            total_score = (
                frequency_score * 0.35 +
                severity_score * 0.25 +
                burst_score * 0.20 +
                repetition_score * 0.20
            )
            
            scored_causes.append({
                "error_type": error_key,
                "count": count,
                "critical_count": critical_count,
                "total_score": total_score,
                "breakdown": {
                    "frequency": round(frequency_score, 3),
                    "severity": round(severity_score, 3),
                    "burst": round(burst_score, 3),
                    "repetition": round(repetition_score, 3)
                }
            })
        
        # Sort by score
        scored_causes.sort(key=lambda x: x["total_score"], reverse=True)
        top_cause = scored_causes[0]
        
        # =====================================================
        # STRICT CONFIDENCE DETERMINATION (MANDATORY)
        # =====================================================
        # evidence_score >= 0.80 → HIGH confidence (computed)
        # evidence_score >= 0.60 → MEDIUM confidence (inferred)
        # evidence_score >= 0.30 → LOW confidence (patterns found)
        # Below 0.30 but patterns → Still report, never UNKNOWN
        #
        # Special rule: ORA-600/INTERNAL_ERROR with count >= 100
        # MUST be at least MEDIUM confidence, never UNKNOWN
        # =====================================================
        top_score = top_cause["total_score"]
        top_count = top_cause["count"]
        error_type = top_cause["error_type"].upper()
        
        # Force HIGH for dominant patterns
        if top_score >= cls.MIN_SCORE_FOR_HIGH_CONFIDENCE:
            confidence = "HIGH"
        elif top_score >= cls.MIN_SCORE_FOR_MEDIUM_CONFIDENCE:
            confidence = "MEDIUM"
        elif top_score >= cls.MIN_SCORE_FOR_LOW_INFERENCE or top_count >= cls.MIN_FREQUENCY_FOR_INFERENCE:
            confidence = "LOW"
        else:
            # Still have patterns - never return UNKNOWN
            confidence = "LOW"
        
        # CRITICAL FIX: ORA-600/INTERNAL_ERROR with high volume MUST be at least MEDIUM
        if ("ORA-600" in error_type or "00600" in error_type or "INTERNAL" in error_type):
            if top_count >= 100:
                confidence = "HIGH" if top_score >= 0.50 else "MEDIUM"
            elif top_count >= 10:
                confidence = "MEDIUM" if confidence == "LOW" else confidence
        
        # Get abstract cause
        abstract = ORACodeMappingEngine.get_abstract_cause(top_cause["error_type"])
        
        # Build evidence
        evidence = []
        if top_cause["count"] >= 100:
            evidence.append("{:,} occurrences of {} (dominant pattern)".format(top_cause["count"], top_cause["error_type"]))
        elif top_cause["count"] >= 10:
            evidence.append("{:,} occurrences of {} (repeated pattern)".format(top_cause["count"], top_cause["error_type"]))
        
        if top_cause["critical_count"] > 0:
            evidence.append("{:,} CRITICAL-severity instances".format(top_cause["critical_count"]))
        
        if top_cause["breakdown"]["burst"] > 0.5:
            evidence.append("Burst pattern detected (clustered in time)")
        
        if top_cause["breakdown"]["frequency"] > 0.3:
            evidence.append("High frequency ({:.1f}% of all alerts)".format(top_cause["breakdown"]["frequency"] * 100))
        
        return {
            "root_cause": top_cause["error_type"],
            "abstract_cause": abstract,
            "confidence": confidence,
            "evidence": evidence,
            "score_breakdown": top_cause["breakdown"],
            "total_score": top_cause["total_score"],
            "all_causes": scored_causes[:5],  # Top 5 for context
            "label": "Root Cause: {} ({} Confidence)".format(
                "COMPUTED" if confidence == "HIGH" else "INFERRED",
                confidence
            )
        }
    
    @classmethod
    def _compute_burst_score(cls, timestamps):
        """Compute burst density score from timestamps."""
        if not timestamps or len(timestamps) < 2:
            return 0.3  # Default
        
        # Try to parse timestamps
        parsed = []
        for ts in timestamps[:100]:  # Limit for performance
            if isinstance(ts, datetime):
                parsed.append(ts)
            elif isinstance(ts, str):
                for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%d-%b-%y %I.%M.%S.%f %p"]:
                    try:
                        parsed.append(datetime.strptime(ts[:19], fmt[:min(len(ts), len(fmt))]))
                        break
                    except:
                        pass
        
        if len(parsed) < 2:
            return 0.3
        
        parsed.sort()
        gaps = [(parsed[i+1] - parsed[i]).total_seconds() 
               for i in range(len(parsed)-1)]
        
        avg_gap = sum(gaps) / len(gaps) if gaps else 3600
        
        # Short gap = high burst
        return min(3600 / max(avg_gap, 1), 1.0)


class ActionFallbackEngine:
    """
    LAYER 3: ACTION FALLBACK (NO "NO ACTIONS" EVER)
    
    RULE: "No actions mapped" is STRICTLY FORBIDDEN
    
    Fallback hierarchy:
    1. ORA code-specific actions
    2. Abstract cause-based actions
    3. Risk-based fallback actions (volume, severity, time)
    4. Ultimate fallback (general DBA checklist)
    """
    
    # Risk-based action templates
    RISK_ACTIONS = {
        "CRITICAL": {
            "urgency": "CRITICAL",
            "priority": "P1",
            "actions": [
                "IMMEDIATE: Assign dedicated DBA for real-time monitoring",
                "Triage and prioritize CRITICAL alerts by impact",
                "Prepare escalation to senior DBA/management",
                "Document current state for incident report",
                "Consider initiating incident bridge if multiple systems affected"
            ]
        },
        "HIGH": {
            "urgency": "HIGH",
            "priority": "P2",
            "actions": [
                "Review alert log for recent errors: tail -100 alert_*.log",
                "Check database status: SELECT STATUS FROM v$instance",
                "Monitor tablespace usage: SELECT * FROM dba_tablespace_usage_metrics",
                "Verify listener status: lsnrctl status"
            ]
        },
        "MEDIUM": {
            "urgency": "MEDIUM",
            "priority": "P3",
            "actions": [
                "Schedule investigation during next maintenance window",
                "Review historical patterns for this error",
                "Check My Oracle Support for known issues",
                "Document findings for change review"
            ]
        },
        "LOW": {
            "urgency": "LOW",
            "priority": "P4",
            "actions": [
                "Add to monitoring watchlist",
                "Review during weekly health check",
                "Document for trending analysis"
            ]
        }
    }
    
    # Pattern-based action templates
    PATTERN_ACTIONS = {
        "burst": {
            "description": "Burst pattern detected - clustered failures",
            "actions": [
                "IMMEDIATE: Check for batch jobs or scheduled tasks during burst window",
                "Review AWR/ASH reports for the burst period",
                "Analyze resource contention during peak",
                "Consider load balancing or job rescheduling"
            ],
            "urgency": "HIGH"
        },
        "repeating": {
            "description": "Repeating pattern detected - recurring failures",
            "actions": [
                "Identify trigger for recurring failures",
                "Check cron/scheduler for jobs at failure times",
                "Review application connection patterns",
                "Search MOS for known issues with this pattern"
            ],
            "urgency": "HIGH"
        },
        "sustained": {
            "description": "Sustained issue - chronic instability",
            "actions": [
                "Review alert log chronologically for root trigger",
                "Check for recent configuration changes",
                "Verify hardware health (CPU, memory, disk)",
                "Plan proactive remediation during maintenance"
            ],
            "urgency": "MEDIUM"
        }
    }
    
    @classmethod
    def get_actions(cls, root_cause_result, risk_level="MEDIUM", temporal_pattern=None):
        """
        Get comprehensive actions. NEVER returns empty.
        
        Args:
            root_cause_result: Result from RootCauseFallbackEngine
            risk_level: CRITICAL/HIGH/MEDIUM/LOW
            temporal_pattern: burst/repeating/sustained
        
        Returns:
            List of action groups, each with cause, actions, urgency, priority
        """
        actions = []
        
        # 1. Root cause-specific actions
        if root_cause_result and root_cause_result.get("root_cause"):
            ora_code = root_cause_result["root_cause"]
            ora_actions = ORACodeMappingEngine.get_actions_for_code(ora_code)
            
            actions.append({
                "cause": ora_code,
                "abstract_cause": root_cause_result.get("abstract_cause", ""),
                "confidence": root_cause_result.get("confidence", "MEDIUM"),
                "actions": ora_actions["actions"],
                "urgency": ora_actions["urgency"],
                "priority": ora_actions["priority"],
                "source": ora_actions.get("source", "ORA mapping")
            })
        
        # 2. Pattern-based actions
        if temporal_pattern and temporal_pattern in cls.PATTERN_ACTIONS:
            pattern_template = cls.PATTERN_ACTIONS[temporal_pattern]
            actions.append({
                "cause": pattern_template["description"],
                "abstract_cause": "Temporal pattern",
                "confidence": "MEDIUM",
                "actions": pattern_template["actions"],
                "urgency": pattern_template["urgency"],
                "priority": "P2",
                "source": "Pattern analysis"
            })
        
        # 3. Risk-based fallback if needed
        if not actions or risk_level in ["CRITICAL", "HIGH"]:
            risk_template = cls.RISK_ACTIONS.get(risk_level, cls.RISK_ACTIONS["MEDIUM"])
            actions.append({
                "cause": "Risk Level: {}".format(risk_level),
                "abstract_cause": "Alert volume and severity",
                "confidence": "HIGH",
                "actions": risk_template["actions"],
                "urgency": risk_template["urgency"],
                "priority": risk_template["priority"],
                "source": "Risk assessment"
            })
        
        # 4. Ultimate fallback - ALWAYS have actions
        if not actions:
            actions.append({
                "cause": "General Database Health",
                "abstract_cause": "Baseline investigation",
                "confidence": "LOW",
                "actions": [
                    "Review Oracle alert log: tail -100 $ORACLE_BASE/diag/rdbms/*/*/trace/alert_*.log",
                    "Check listener status: lsnrctl status",
                    "Monitor tablespace: SELECT * FROM dba_tablespace_usage_metrics",
                    "Verify instance: SELECT STATUS, DATABASE_STATUS FROM v$instance"
                ],
                "urgency": "MEDIUM",
                "priority": "P3",
                "source": "Fallback checklist"
            })
        
        return actions


class DownVsCriticalEngine:
    """
    LAYER 4: TRUE DOWN vs CRITICAL SEPARATION
    
    DOWN = STOP, SHUTDOWN, INSTANCE TERMINATED, ORA-01034, ORA-01033
    CRITICAL = DB running but unstable (high CRITICAL alerts)
    
    RULE: If no DOWN events, explicitly state: RUNNING but UNSTABLE
    """
    
    # DOWN indicators (database truly not running)
    DOWN_KEYWORDS = [
        "STOP", "DB_DOWN", "INSTANCE_TERMINATED", "SHUTDOWN",
        "INSTANCE TERMINATED", "DATABASE DOWN", "ORA-01034",
        "ORA-01033", "ORACLE NOT AVAILABLE", "MOUNT EXCLUSIVE",
        "SYSTEM CRASH", "ABORT", "IMMEDIATE SHUTDOWN"
    ]
    
    @classmethod
    def analyze(cls, alerts, target=None):
        """
        Analyze alerts to determine TRUE DOWN vs CRITICAL status.
        
        Returns:
            Dict with:
            - status: DOWN / CRITICAL_BUT_RUNNING / RUNNING
            - down_count: Number of true DOWN events
            - critical_count: Number of CRITICAL (but not DOWN) alerts
            - explanation: Human-readable explanation
            - down_samples: Sample DOWN alerts
        """
        down_alerts = []
        critical_alerts = []
        warning_alerts = []
        
        for alert in alerts:
            # Filter by target if specified
            if target:
                alert_target = (alert.get("target") or alert.get("target_name") or "").upper()
                if target.upper() not in alert_target and alert_target not in target.upper():
                    continue
            
            msg = (alert.get("message") or alert.get("msg_text") or "").upper()
            severity = (alert.get("severity") or "").upper()
            
            # Check for DOWN indicators
            is_down = False
            for kw in cls.DOWN_KEYWORDS:
                if kw in msg:
                    is_down = True
                    down_alerts.append(alert)
                    break
            
            if not is_down:
                if severity == "CRITICAL":
                    critical_alerts.append(alert)
                elif severity == "WARNING":
                    warning_alerts.append(alert)
        
        # Determine status
        if down_alerts:
            status = "DOWN"
            explanation = "⛔ CONFIRMED DOWN: {} instance(s) show TRUE DOWN indicators (STOP/SHUTDOWN/TERMINATED)".format(
                len(down_alerts)
            )
        elif critical_alerts:
            status = "CRITICAL_BUT_RUNNING"
            explanation = "⚠️ RUNNING but UNSTABLE: {} CRITICAL alerts but NO DOWN events. Database is operational but degraded.".format(
                len(critical_alerts)
            )
        else:
            status = "RUNNING"
            explanation = "✅ RUNNING: No DOWN or CRITICAL alerts. {} WARNING alerts present.".format(
                len(warning_alerts)
            )
        
        return {
            "status": status,
            "is_truly_down": len(down_alerts) > 0,
            "is_critical_but_running": len(down_alerts) == 0 and len(critical_alerts) > 0,
            "is_stable": len(down_alerts) == 0 and len(critical_alerts) == 0,
            "down_count": len(down_alerts),
            "critical_count": len(critical_alerts),
            "warning_count": len(warning_alerts),
            "explanation": explanation,
            "down_samples": down_alerts[:3],
            "critical_samples": critical_alerts[:3]
        }


class WideningEngine:
    """
    LAYER 5: WIDENING LOGIC (ANTI-FALSE-ZERO)
    
    If any strict filter returns 0 rows:
    - Automatically widen time window, severity, category
    - Always explain: What was checked, Why widening applied, Alternative risk
    """
    
    @classmethod
    def widen_query(cls, original_result, alerts, criteria):
        """
        Apply widening logic if original query returned 0 results.
        
        Args:
            original_result: The empty/insufficient result
            alerts: All available alerts
            criteria: Dict with original criteria (target, time_range, severity, etc.)
        
        Returns:
            Widened result with explanation
        """
        widening_steps = []
        widened_alerts = []
        
        target = criteria.get("target")
        time_range = criteria.get("time_range")
        severity = criteria.get("severity")
        
        # Step 1: Widen target matching
        if target:
            # Try fuzzy match
            target_upper = target.upper()
            for alert in alerts:
                alert_target = (alert.get("target") or alert.get("target_name") or "").upper()
                # Substring match
                if target_upper in alert_target or alert_target in target_upper:
                    widened_alerts.append(alert)
            
            if not widened_alerts:
                # Try character similarity
                for alert in alerts:
                    alert_target = (alert.get("target") or alert.get("target_name") or "").upper()
                    common = len(set(target_upper) & set(alert_target))
                    total = len(set(target_upper) | set(alert_target))
                    if total > 0 and common / total > 0.5:
                        widened_alerts.append(alert)
                widening_steps.append("Fuzzy-matched target '{}' (exact match not found)".format(target))
        
        # Step 2: Widen time range if empty
        if not widened_alerts and time_range:
            widening_steps.append("Time range {}:00-{}:00 returned 0 alerts".format(
                time_range.get("start_hour", 0), time_range.get("end_hour", 24)
            ))
            # Use all alerts
            widened_alerts = alerts
            widening_steps.append("Widened to full time range")
        
        # Step 3: Widen severity if filtering
        if not widened_alerts and severity:
            widening_steps.append("Severity '{}' returned 0 alerts".format(severity))
            widened_alerts = alerts
            widening_steps.append("Widened to all severities")
        
        # Final fallback
        if not widened_alerts:
            widened_alerts = alerts
            widening_steps.append("Applied maximum widening - showing all available data")
        
        # Compute alternative summary
        alt_summary = cls._compute_alternative_summary(widened_alerts)
        
        return {
            "widening_applied": True,
            "widening_steps": widening_steps,
            "widened_result_count": len(widened_alerts),
            "widened_alerts": widened_alerts,
            "alternative_summary": alt_summary,
            "explanation": "Original query returned insufficient results. {}".format(
                " → ".join(widening_steps)
            )
        }
    
    @classmethod
    def _compute_alternative_summary(cls, alerts):
        """Compute summary of widened results."""
        if not alerts:
            return {"error": "No data available even after widening"}
        
        # Group by target
        by_target = defaultdict(int)
        by_severity = defaultdict(int)
        
        for alert in alerts:
            target = (alert.get("target") or alert.get("target_name") or "UNKNOWN").upper()
            severity = (alert.get("severity") or "INFO").upper()
            by_target[target] += 1
            by_severity[severity] += 1
        
        top_targets = sorted(by_target.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "total_alerts": len(alerts),
            "top_targets": [{"name": t[0], "count": t[1]} for t in top_targets],
            "severity_distribution": dict(by_severity),
            "suggested_target": top_targets[0][0] if top_targets else None
        }


class SessionMemoryEngine:
    """
    LAYER 6: SESSION / ENVIRONMENT MEMORY (GLOBAL STATE)
    
    Maintains persistent memory:
    - Highest risk database
    - Dominant ORA codes
    - Peak alert hours
    - Known unstable systems
    
    Enables responses like: "Based on earlier analysis..."
    
    PRODUCTION RULES:
    1. Once root cause is identified, LOCK it for session
    2. Once highest risk DB is identified, LOCK it
    3. Once peak hour is computed, LOCK it
    4. Session context MUST be included in responses
    """
    
    # Singleton state
    _state = {
        "highest_risk_database": None,
        "highest_risk_score": 0,
        "dominant_ora_codes": [],
        "peak_alert_hour": None,
        "unstable_systems": [],
        "last_root_cause": None,
        "last_abstract_cause": None,
        "risk_posture": None,
        "question_count": 0,
        "analysis_history": [],
        # PRODUCTION: Locked values for session consistency
        "locked_root_cause": None,
        "locked_root_cause_db": {},  # db -> locked root cause
        "locked_highest_risk_db": None,
        "locked_peak_hour": None
    }
    
    @classmethod
    def update(cls, **kwargs):
        """Update session memory with new findings."""
        for key, value in kwargs.items():
            if key in cls._state and value is not None:
                cls._state[key] = value
        cls._state["question_count"] += 1
    
    @classmethod
    def add_ora_code(cls, ora_code):
        """Track dominant ORA code."""
        if ora_code and ora_code not in cls._state["dominant_ora_codes"]:
            cls._state["dominant_ora_codes"].insert(0, ora_code)
            cls._state["dominant_ora_codes"] = cls._state["dominant_ora_codes"][:5]
    
    @classmethod
    def set_highest_risk(cls, database, score):
        """Set highest risk database if score is higher.
        
        PRODUCTION: Lock highest risk DB once identified.
        """
        if score > cls._state["highest_risk_score"]:
            cls._state["highest_risk_database"] = database
            cls._state["highest_risk_score"] = score
            # Lock for session consistency
            if not cls._state.get("locked_highest_risk_db"):
                cls._state["locked_highest_risk_db"] = database
    
    @classmethod
    def lock_root_cause(cls, root_cause, db_name=None):
        """
        PRODUCTION: Lock root cause for session consistency.
        
        Once a dominant root cause is identified, LOCK it.
        Do NOT alternate between OTHER/UNKNOWN/INTERNAL_ERROR.
        """
        if not root_cause:
            return
        
        invalid_causes = ["OTHER", "UNKNOWN", "Unknown", "N/A", None, ""]
        if root_cause in invalid_causes:
            return
        
        # Lock global root cause
        if not cls._state.get("locked_root_cause"):
            cls._state["locked_root_cause"] = root_cause
        
        # Lock for specific database
        if db_name:
            db_upper = db_name.upper()
            if db_upper not in cls._state.get("locked_root_cause_db", {}):
                cls._state["locked_root_cause_db"][db_upper] = root_cause
    
    @classmethod
    def get_locked_root_cause(cls, db_name=None):
        """Get locked root cause for session or specific database."""
        if db_name:
            db_upper = db_name.upper()
            db_locked = cls._state.get("locked_root_cause_db", {}).get(db_upper)
            if db_locked:
                return db_locked
        
        return cls._state.get("locked_root_cause")
    
    @classmethod
    def lock_peak_hour(cls, hour):
        """Lock peak alert hour for session consistency."""
        if hour is not None and cls._state.get("locked_peak_hour") is None:
            cls._state["locked_peak_hour"] = hour
            cls._state["peak_alert_hour"] = hour
    
    @classmethod
    def add_unstable_system(cls, system_name):
        """Track unstable system."""
        if system_name and system_name not in cls._state["unstable_systems"]:
            cls._state["unstable_systems"].append(system_name)
            cls._state["unstable_systems"] = cls._state["unstable_systems"][:10]
    
    @classmethod
    def record_analysis(cls, analysis_result):
        """Record analysis in history."""
        entry = {
            "question_number": cls._state["question_count"],
            "target": analysis_result.get("target"),
            "root_cause": analysis_result.get("root_cause"),
            "confidence": analysis_result.get("confidence")
        }
        cls._state["analysis_history"].append(entry)
        if len(cls._state["analysis_history"]) > 20:
            cls._state["analysis_history"] = cls._state["analysis_history"][-20:]
    
    @classmethod
    def get_context_phrase(cls):
        """
        Build context phrase for follow-up questions.
        
        PRODUCTION RULE: Use locked values for consistency.
        Responses MUST say "Based on earlier analysis..." when applicable.
        
        Returns string like: "Based on earlier analysis: highest risk DB is X, ..."
        """
        if cls._state["question_count"] == 0:
            return None
        
        parts = []
        
        # Use locked highest risk DB for consistency
        highest_risk = cls._state.get("locked_highest_risk_db") or cls._state.get("highest_risk_database")
        if highest_risk:
            parts.append("highest risk database is {}".format(highest_risk))
        
        # Use locked root cause for consistency
        locked_rc = cls._state.get("locked_root_cause")
        if locked_rc:
            parts.append("primary issue identified as {}".format(locked_rc))
        elif cls._state["last_abstract_cause"]:
            parts.append("primary issue identified as {}".format(cls._state["last_abstract_cause"]))
        elif cls._state["last_root_cause"]:
            parts.append("root cause is {}".format(cls._state["last_root_cause"]))
        
        if cls._state["dominant_ora_codes"]:
            parts.append("dominant ORA codes are {}".format(", ".join(cls._state["dominant_ora_codes"][:2])))
        
        # Use locked peak hour for consistency
        peak_hour = cls._state.get("locked_peak_hour") or cls._state.get("peak_alert_hour")
        if peak_hour is not None:
            parts.append("peak alert hour at {}:00".format(peak_hour))
        
        if cls._state["risk_posture"]:
            parts.append("overall risk is {}".format(cls._state["risk_posture"]))
        
        if parts:
            return "Based on earlier analysis: " + ", ".join(parts) + "."
        return None
    
    @classmethod
    def get_state(cls):
        """Get full session state."""
        return cls._state.copy()
    
    @classmethod
    def reset(cls):
        """Reset session state."""
        cls._state = {
            "highest_risk_database": None,
            "highest_risk_score": 0,
            "dominant_ora_codes": [],
            "peak_alert_hour": None,
            "unstable_systems": [],
            "last_root_cause": None,
            "last_abstract_cause": None,
            "risk_posture": None,
            "question_count": 0,
            "analysis_history": [],
            # PRODUCTION: Reset locked values
            "locked_root_cause": None,
            "locked_root_cause_db": {},
            "locked_highest_risk_db": None,
            "locked_peak_hour": None
        }


class ProductionResponseFormatter:
    """
    Response formatter that enforces the MANDATORY response format.
    
    Every response MUST include:
    - Summary
    - What was checked
    - What was found
    - What it means
    - What to do now
    - Confidence
    """
    
    @classmethod
    def format(cls, summary, checked, found, meaning, action, confidence="MEDIUM",
               target=None, widening_note=None, evidence=None, prior_context=None):
        """
        Format response in strict production format.
        
        RULE: Every section is MANDATORY.
        """
        parts = []
        
        # Summary
        parts.append("🔹 **Summary**")
        parts.append(summary or "Analysis completed")
        parts.append("")
        
        # What was checked
        parts.append("🔍 **What was checked**")
        parts.append(checked or "Standard diagnostic checks performed")
        parts.append("")
        
        # What was found
        parts.append("📊 **What was found**")
        parts.append(found or "See details below")
        parts.append("")
        
        # What it means
        parts.append("🧠 **What it means**")
        parts.append(meaning or "See analysis above")
        parts.append("")
        
        # What to do now (NEVER EMPTY)
        parts.append("🛠️ **What to do now**")
        if isinstance(action, list):
            for i, act in enumerate(action, 1):
                if isinstance(act, dict):
                    parts.append("**{}. For {}:**".format(i, act.get("cause", "Issue")))
                    for step in act.get("actions", []):
                        parts.append("   {}. {}".format(i, step))
                    parts.append("   Urgency: {}".format(act.get("urgency", "MEDIUM")))
                else:
                    parts.append("{}. {}".format(i, act))
        else:
            parts.append(action or "Continue monitoring")
        parts.append("")
        
        # Confidence
        confidence_str = confidence if isinstance(confidence, str) else "{:.0f}%".format(confidence * 100) if confidence else "MEDIUM"
        parts.append("**Confidence:** {}".format(confidence_str))
        
        # Optional: Prior context
        if prior_context:
            parts.append("")
            parts.append("📝 {}".format(prior_context))
        
        # Optional: Widening note
        if widening_note:
            parts.append("")
            parts.append("⚠️ Note: {}".format(widening_note))
        
        return "\n".join(parts)


# =============================================================================
# MAIN ORCHESTRATOR
# =============================================================================

class ProductionIntelligenceOrchestrator:
    """
    Main orchestrator that wires all production intelligence layers together.
    
    This is the entry point for production-grade analysis.
    """
    
    def __init__(self):
        self.ora_engine = ORACodeMappingEngine()
        self.root_cause_engine = RootCauseFallbackEngine()
        self.action_engine = ActionFallbackEngine()
        self.down_critical_engine = DownVsCriticalEngine()
        self.widening_engine = WideningEngine()
        self.session = SessionMemoryEngine()
        self.formatter = ProductionResponseFormatter()
    
    def analyze(self, question, alerts, target=None):
        """
        Perform production-grade analysis.
        
        Returns:
            Fully formatted response with all mandatory sections.
        """
        # 1. Get session context
        prior_context = self.session.get_context_phrase()
        
        # 2. Infer root cause (NEVER Unknown)
        root_cause_result = self.root_cause_engine.infer_root_cause(alerts, target)
        
        # 3. Determine DOWN vs CRITICAL
        down_status = self.down_critical_engine.analyze(alerts, target)
        
        # 4. Compute risk level
        risk_level = self._compute_risk_level(alerts, target, root_cause_result)
        
        # 5. Detect temporal pattern
        temporal_pattern = self._detect_temporal_pattern(root_cause_result)
        
        # 6. Get actions (NEVER empty)
        actions = self.action_engine.get_actions(
            root_cause_result, risk_level, temporal_pattern
        )
        
        # 7. Update session memory
        self._update_session(target, root_cause_result, risk_level, down_status)
        
        # 8. Build response
        return {
            "root_cause": root_cause_result,
            "down_status": down_status,
            "risk_level": risk_level,
            "temporal_pattern": temporal_pattern,
            "actions": actions,
            "prior_context": prior_context,
            "session_state": self.session.get_state()
        }
    
    def _compute_risk_level(self, alerts, target, root_cause_result):
        """Compute risk level based on evidence."""
        if not alerts:
            return "UNKNOWN"
        
        # Filter by target if specified
        if target:
            target_upper = target.upper()
            alerts = [a for a in alerts if 
                     target_upper in (a.get("target") or a.get("target_name") or "").upper()]
        
        total = len(alerts)
        critical = sum(1 for a in alerts if (a.get("severity") or "").upper() == "CRITICAL")
        
        critical_ratio = critical / max(total, 1)
        confidence_score = root_cause_result.get("total_score", 0)
        
        if critical > 10000 or critical_ratio > 0.5:
            return "CRITICAL"
        elif critical > 1000 or critical_ratio > 0.2:
            return "HIGH"
        elif critical > 100 or critical_ratio > 0.1:
            return "ELEVATED"
        else:
            return "MODERATE"
    
    def _detect_temporal_pattern(self, root_cause_result):
        """Detect temporal pattern from scoring."""
        if not root_cause_result or not root_cause_result.get("score_breakdown"):
            return "sustained"
        
        bd = root_cause_result["score_breakdown"]
        
        if bd.get("burst", 0) > 0.5:
            return "burst"
        elif bd.get("repetition", 0) > 0.5:
            return "repeating"
        else:
            return "sustained"
    
    def _update_session(self, target, root_cause_result, risk_level, down_status):
        """Update session memory with findings."""
        # Update root cause
        if root_cause_result:
            rc = root_cause_result.get("root_cause")
            ac = root_cause_result.get("abstract_cause")
            
            self.session.update(
                last_root_cause=rc,
                last_abstract_cause=ac,
                risk_posture=risk_level
            )
            
            if rc and rc.startswith("ORA-"):
                self.session.add_ora_code(rc.split()[0])
        
        # Update risk tracking
        if target and root_cause_result:
            score = root_cause_result.get("total_score", 0)
            self.session.set_highest_risk(target, score)
        
        # Track unstable systems
        if down_status.get("is_critical_but_running") and target:
            self.session.add_unstable_system(target)
        
        # Record analysis
        self.session.record_analysis({
            "target": target,
            "root_cause": root_cause_result.get("root_cause") if root_cause_result else None,
            "confidence": root_cause_result.get("confidence") if root_cause_result else None
        })


# Global orchestrator instance
PRODUCTION_INTELLIGENCE = ProductionIntelligenceOrchestrator()
