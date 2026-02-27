"""
DBA Knowledge Base - Phase 6 Component
========================================
Static, curated Oracle DBA knowledge layer.

This is READ-ONLY advisory knowledge:
- Oracle error patterns and meanings
- Data Guard / Standby patterns
- Common root causes (patching, IO, network, archive lag)
- What experienced DBAs typically check first

RULES:
- Knowledge is advisory only
- NEVER say "this is the exact fix"
- Always use "typically", "often", "commonly observed"
- Data from CSV always wins over knowledge
"""

from typing import Dict, List, Optional, Tuple


class OracleErrorKnowledge:
    """
    Curated Oracle error knowledge.
    Maps ORA codes to DBA-friendly explanations.
    """
    
    # Oracle Internal Errors
    INTERNAL_ERRORS = {
        'ORA-600': {
            'category': 'Internal Error',
            'severity': 'CRITICAL',
            'meaning': 'Internal Oracle kernel error - indicates a bug or corruption at the engine level',
            'common_causes': [
                'Oracle software bug',
                'Memory corruption',
                'Hardware issues (CPU, memory)',
                'Data block corruption',
                'Undo/redo corruption'
            ],
            'dba_first_checks': [
                'Check alert log for full error arguments',
                'Look for recent patching or upgrades',
                'Check for memory pressure on the host',
                'Review recent schema changes',
                'Check for storage issues'
            ],
            'typical_resolution': 'Usually requires Oracle Support analysis of the error arguments',
            'risk_level': 'HIGH',
            'production_impact': 'Can cause session crashes, instance crashes, or data corruption'
        },
        'ORA-7445': {
            'category': 'Internal Error',
            'severity': 'CRITICAL',
            'meaning': 'Operating system exception caught by Oracle - kernel signal error',
            'common_causes': [
                'Oracle code path hitting OS exception',
                'Memory access violation',
                'Stack overflow',
                'Hardware failure'
            ],
            'dba_first_checks': [
                'Check OS logs for hardware errors',
                'Review memory and CPU utilization',
                'Check for recent patches',
                'Look at trace files for stack trace'
            ],
            'typical_resolution': 'Often requires Oracle patch or OS-level investigation',
            'risk_level': 'HIGH',
            'production_impact': 'Can crash sessions or entire instance'
        }
    }
    
    # Network / Listener Errors
    NETWORK_ERRORS = {
        'ORA-12537': {
            'category': 'Network/Listener',
            'severity': 'WARNING',
            'meaning': 'TNS connection closed unexpectedly - network communication failure',
            'common_causes': [
                'Network instability',
                'Firewall dropping connections',
                'Listener restart',
                'Client timeout settings',
                'Load balancer issues'
            ],
            'dba_first_checks': [
                'Check listener status and logs',
                'Verify network connectivity',
                'Review firewall rules',
                'Check for recent network changes'
            ],
            'typical_resolution': 'Usually network infrastructure issue, not database',
            'risk_level': 'MEDIUM',
            'production_impact': 'Applications may experience connection drops'
        },
        'ORA-12541': {
            'category': 'Network/Listener',
            'severity': 'CRITICAL',
            'meaning': 'TNS no listener - the database listener is not running or unreachable',
            'common_causes': [
                'Listener not started',
                'Wrong port or hostname',
                'Listener crashed',
                'Network routing issue'
            ],
            'dba_first_checks': [
                'Verify listener is running (lsnrctl status)',
                'Check listener.ora configuration',
                'Verify network connectivity to listener port',
                'Check for listener log errors'
            ],
            'typical_resolution': 'Start or restart the listener, verify configuration',
            'risk_level': 'HIGH',
            'production_impact': 'No new connections can be established'
        },
        'ORA-03113': {
            'category': 'Network/Connection',
            'severity': 'WARNING',
            'meaning': 'End-of-file on communication channel - connection was lost',
            'common_causes': [
                'Instance crash',
                'Process killed',
                'Network interruption',
                'Firewall timeout',
                'Session killed by DBA'
            ],
            'dba_first_checks': [
                'Check if instance is still running',
                'Review alert log for errors',
                'Check network stability',
                'Look for session termination messages'
            ],
            'typical_resolution': 'Identify if instance crashed or network issue',
            'risk_level': 'MEDIUM',
            'production_impact': 'Existing connections may be dropped'
        }
    }
    
    # Space and Storage Errors
    SPACE_ERRORS = {
        'ORA-01653': {
            'category': 'Space/Storage',
            'severity': 'CRITICAL',
            'meaning': 'Unable to extend table - tablespace is full',
            'common_causes': [
                'Tablespace reached maxsize',
                'Datafile not autoextend',
                'Disk full',
                'Unexpected data growth'
            ],
            'dba_first_checks': [
                'Check tablespace usage percentages',
                'Verify disk space on storage',
                'Review datafile autoextend settings',
                'Identify growing segments'
            ],
            'typical_resolution': 'Add space to tablespace or enable autoextend',
            'risk_level': 'HIGH',
            'production_impact': 'Transactions will fail, applications blocked'
        },
        'ORA-01555': {
            'category': 'Undo/Consistency',
            'severity': 'WARNING',
            'meaning': 'Snapshot too old - undo data overwritten before query completed',
            'common_causes': [
                'Long-running queries',
                'Undersized undo tablespace',
                'High transaction volume',
                'Undo retention too low'
            ],
            'dba_first_checks': [
                'Check undo tablespace size',
                'Review undo_retention parameter',
                'Identify long-running queries',
                'Check undo usage statistics'
            ],
            'typical_resolution': 'Increase undo tablespace or retention, optimize queries',
            'risk_level': 'MEDIUM',
            'production_impact': 'Queries may fail, reports may be incomplete'
        }
    }
    
    # Data Guard / Standby Errors
    DATAGUARD_ERRORS = {
        'ORA-16816': {
            'category': 'Data Guard',
            'severity': 'CRITICAL',
            'meaning': 'Incorrect database role - operation attempted on wrong role',
            'common_causes': [
                'Running primary-only operation on standby',
                'Broker configuration mismatch',
                'Role transition incomplete'
            ],
            'dba_first_checks': [
                'Verify current database role',
                'Check Data Guard broker status',
                'Review switchover/failover history'
            ],
            'typical_resolution': 'Verify role and use appropriate commands',
            'risk_level': 'MEDIUM',
            'production_impact': 'Data Guard operations may fail'
        },
        'ORA-16766': {
            'category': 'Data Guard',
            'severity': 'CRITICAL',
            'meaning': 'Redo transport service not started on standby',
            'common_causes': [
                'Standby not in managed recovery',
                'Network issue to standby',
                'Archive destination misconfigured',
                'Standby apply stopped'
            ],
            'dba_first_checks': [
                'Check standby managed recovery status',
                'Verify archive log destinations',
                'Review Data Guard gap status',
                'Check network connectivity'
            ],
            'typical_resolution': 'Start managed recovery, verify network and configuration',
            'risk_level': 'HIGH',
            'production_impact': 'Standby falling behind, potential data loss risk'
        }
    }
    
    # Archive Log Errors
    ARCHIVELOG_ERRORS = {
        'ORA-00257': {
            'category': 'Archive Log',
            'severity': 'CRITICAL',
            'meaning': 'Archiver error - archive destination full or inaccessible',
            'common_causes': [
                'Archive destination disk full',
                'Archive destination offline',
                'RMAN backup failing to delete',
                'Rapid redo generation'
            ],
            'dba_first_checks': [
                'Check archive destination space',
                'Verify archiver process status',
                'Check RMAN backup completion',
                'Review archive log generation rate'
            ],
            'typical_resolution': 'Free archive destination space, fix backup chain',
            'risk_level': 'CRITICAL',
            'production_impact': 'Database will hang/freeze until resolved'
        }
    }
    
    @classmethod
    def get_all_errors(cls) -> Dict:
        """Get all known Oracle errors."""
        all_errors = {}
        all_errors.update(cls.INTERNAL_ERRORS)
        all_errors.update(cls.NETWORK_ERRORS)
        all_errors.update(cls.SPACE_ERRORS)
        all_errors.update(cls.DATAGUARD_ERRORS)
        all_errors.update(cls.ARCHIVELOG_ERRORS)
        return all_errors
    
    @classmethod
    def lookup_error(cls, error_code: str) -> Optional[Dict]:
        """
        Look up knowledge for a specific ORA error code.
        Returns None if error is not in knowledge base.
        """
        # Normalize error code
        code = error_code.upper().strip()
        if not code.startswith('ORA-'):
            code = f'ORA-{code}'
        
        return cls.get_all_errors().get(code)
    
    @classmethod
    def find_matching_errors(cls, text: str) -> List[Tuple[str, Dict]]:
        """
        Find all ORA errors mentioned in text and return their knowledge.
        """
        import re
        matches = []
        
        # Find all ORA-XXXXX patterns
        ora_pattern = r'ORA[-\s]?(\d+)'
        found = re.findall(ora_pattern, text, re.IGNORECASE)
        
        for code in found:
            full_code = f'ORA-{code}'
            knowledge = cls.lookup_error(full_code)
            if knowledge:
                matches.append((full_code, knowledge))
        
        return matches


class DataGuardKnowledge:
    """
    Curated Data Guard / Standby database knowledge.
    """
    
    STANDBY_PATTERNS = {
        'archive_gap': {
            'description': 'Gap between primary and standby archive logs',
            'common_causes': [
                'Network bandwidth limitation',
                'Standby apply process stopped',
                'Archive destination issues',
                'Heavy transaction load on primary'
            ],
            'warning_signs': [
                'Increasing apply lag',
                'Archive log shipping delays',
                'Standby alert messages',
                'Gap in sequence numbers'
            ],
            'typical_dba_actions': [
                'Check managed recovery status',
                'Monitor archive log shipping',
                'Review network throughput',
                'Verify standby space availability'
            ],
            'risk_if_ignored': 'Data loss exposure increases, longer recovery time'
        },
        'apply_lag': {
            'description': 'Standby is behind primary in applying changes',
            'common_causes': [
                'I/O bottleneck on standby',
                'CPU contention on standby',
                'Large transactions (batch loads)',
                'Standby recovery process issues'
            ],
            'warning_signs': [
                'v$dataguard_stats showing lag',
                'Alert log messages about lag',
                'Increasing SCN difference'
            ],
            'typical_dba_actions': [
                'Check standby I/O performance',
                'Monitor standby CPU usage',
                'Review parallel recovery settings',
                'Consider standby hardware capacity'
            ],
            'risk_if_ignored': 'Failover RPO increases, potential data loss'
        },
        'switchover_readiness': {
            'description': 'Ability to perform planned role transition',
            'checks_required': [
                'No archive gaps',
                'Apply lag within tolerance',
                'Both databases healthy',
                'Broker configuration valid'
            ],
            'common_blockers': [
                'Pending archive logs',
                'MRP process not running',
                'Configuration warnings',
                'Network connectivity issues'
            ]
        }
    }
    
    @classmethod
    def get_standby_pattern(cls, pattern_name: str) -> Optional[Dict]:
        """Get knowledge about a specific standby pattern."""
        return cls.STANDBY_PATTERNS.get(pattern_name.lower().replace(' ', '_'))


class CommonRootCauses:
    """
    Curated knowledge about common root causes.
    What experienced DBAs have learned over years.
    """
    
    CATEGORIES = {
        'patching': {
            'description': 'Issues related to Oracle patches and upgrades',
            'typical_symptoms': [
                'ORA-600 errors after patch',
                'New ORA-7445 errors',
                'Performance degradation',
                'Query plan changes'
            ],
            'dba_investigation': [
                'Compare patch history with error timing',
                'Check for known patch bugs',
                'Review Oracle support notes'
            ],
            'advisory': 'Patching is often associated with new internal errors'
        },
        'io_issues': {
            'description': 'Storage and I/O related problems',
            'typical_symptoms': [
                'Slow query performance',
                'Checkpoint not complete warnings',
                'Recovery taking long time',
                'High db file sequential read waits'
            ],
            'dba_investigation': [
                'Check storage latency metrics',
                'Review I/O statistics in AWR',
                'Verify storage array health',
                'Check for multipath issues'
            ],
            'advisory': 'I/O issues often manifest as slow performance first'
        },
        'network': {
            'description': 'Network infrastructure problems',
            'typical_symptoms': [
                'ORA-12537 connection drops',
                'ORA-03113 end of file errors',
                'Intermittent connection failures',
                'Data Guard lag spikes'
            ],
            'dba_investigation': [
                'Check network latency and packet loss',
                'Review firewall and load balancer logs',
                'Verify DNS resolution',
                'Test connectivity to all nodes'
            ],
            'advisory': 'Network issues are often mistaken for database problems'
        },
        'memory_pressure': {
            'description': 'Host or Oracle memory issues',
            'typical_symptoms': [
                'ORA-4031 shared pool errors',
                'Excessive paging',
                'SGA resize messages',
                'Process memory errors'
            ],
            'dba_investigation': [
                'Check host memory utilization',
                'Review SGA/PGA allocation',
                'Look for memory leaks',
                'Check for oversized cursors'
            ],
            'advisory': 'Memory issues can cause unpredictable behavior'
        },
        'space_exhaustion': {
            'description': 'Disk or tablespace space running out',
            'typical_symptoms': [
                'ORA-01653 unable to extend',
                'ORA-00257 archiver stuck',
                'Slow or hung transactions',
                'Backup failures'
            ],
            'dba_investigation': [
                'Check tablespace usage',
                'Review disk space on all mounts',
                'Check archive log destination',
                'Review segment growth trends'
            ],
            'advisory': 'Space issues can cause sudden outages without warning'
        }
    }
    
    @classmethod
    def get_root_cause(cls, category: str) -> Optional[Dict]:
        """Get knowledge about a root cause category."""
        return cls.CATEGORIES.get(category.lower().replace(' ', '_'))
    
    @classmethod
    def find_matching_causes(cls, symptoms: List[str]) -> List[str]:
        """
        Given symptoms, suggest possible root cause categories.
        Returns list of category names that might be relevant.
        """
        matches = []
        symptoms_lower = [s.lower() for s in symptoms]
        
        for category, info in cls.CATEGORIES.items():
            for symptom in info['typical_symptoms']:
                if any(s in symptom.lower() for s in symptoms_lower):
                    if category not in matches:
                        matches.append(category)
                    break
        
        return matches


class DBAFirstChecks:
    """
    What experienced DBAs check first for different situations.
    This represents human DBA intuition and practice.
    """
    
    SITUATION_CHECKS = {
        'high_alert_volume': {
            'first_checks': [
                'Is this a known maintenance window?',
                'Was there a recent change or deployment?',
                'Is this one database or multiple?',
                'Is this one error type or many?'
            ],
            'interpretation': 'High alert volume usually indicates either a real incident or an expected event',
            'key_questions': [
                'When did the volume increase?',
                'Is there a pattern (time, database, error type)?',
                'Are related systems affected?'
            ]
        },
        'internal_errors': {
            'first_checks': [
                'Check the full ORA-600 arguments in alert log',
                'Look for recent patches or upgrades',
                'Is this a new error or recurring?',
                'Is it affecting multiple sessions?'
            ],
            'interpretation': 'Internal errors usually indicate Oracle bugs or corruption',
            'key_questions': [
                'What operation triggered it?',
                'Is it reproducible?',
                'What was the impact on the session?'
            ]
        },
        'standby_issues': {
            'first_checks': [
                'Is managed recovery running?',
                'What is the current lag?',
                'Are archive logs shipping?',
                'Is there a network issue?'
            ],
            'interpretation': 'Standby issues often relate to network or apply process',
            'key_questions': [
                'When did the lag start?',
                'What is the lag trend (stable or growing)?',
                'Are there any alerts on the primary?'
            ]
        },
        'performance_degradation': {
            'first_checks': [
                'Check for resource waits (CPU, I/O, memory)',
                'Look for blocking sessions',
                'Review recent execution plan changes',
                'Check for missing statistics'
            ],
            'interpretation': 'Performance issues usually have specific wait events',
            'key_questions': [
                'Which queries or operations are slow?',
                'When did it start?',
                'What changed recently?'
            ]
        },
        'connection_issues': {
            'first_checks': [
                'Is the listener running?',
                'Can you connect locally?',
                'Check network connectivity',
                'Review connection pool settings'
            ],
            'interpretation': 'Connection issues are usually listener or network related',
            'key_questions': [
                'Are all applications affected?',
                'Is it intermittent or constant?',
                'Any recent network changes?'
            ]
        }
    }
    
    @classmethod
    def get_first_checks(cls, situation: str) -> Optional[Dict]:
        """Get first checks for a situation."""
        return cls.SITUATION_CHECKS.get(situation.lower().replace(' ', '_'))
    
    @classmethod
    def get_checks_for_errors(cls, error_types: List[str]) -> Dict:
        """Get first checks based on error types present."""
        checks = {}
        
        for error in error_types:
            error_lower = error.lower()
            
            if 'ora-600' in error_lower or 'ora-7445' in error_lower or 'internal' in error_lower:
                checks['internal_errors'] = cls.SITUATION_CHECKS['internal_errors']
            
            if 'standby' in error_lower or 'dataguard' in error_lower or 'data guard' in error_lower:
                checks['standby_issues'] = cls.SITUATION_CHECKS['standby_issues']
            
            if 'ora-12' in error_lower or 'connection' in error_lower or 'listener' in error_lower:
                checks['connection_issues'] = cls.SITUATION_CHECKS['connection_issues']
        
        return checks


class DBAKnowledgeBase:
    """
    Master DBA Knowledge Base - Phase 6 Component.
    
    Aggregates all curated DBA knowledge:
    - Oracle error knowledge
    - Data Guard patterns
    - Common root causes
    - DBA first checks
    
    RULES:
    - This is ADVISORY knowledge only
    - Always use uncertainty language
    - Never guarantee outcomes
    - Data from CSV always wins
    """
    
    def __init__(self):
        self.oracle_errors = OracleErrorKnowledge()
        self.dataguard = DataGuardKnowledge()
        self.root_causes = CommonRootCauses()
        self.first_checks = DBAFirstChecks()
    
    def lookup_ora_error(self, error_code: str) -> Optional[Dict]:
        """Look up knowledge for an ORA error."""
        return OracleErrorKnowledge.lookup_error(error_code)
    
    def find_errors_in_text(self, text: str) -> List[Tuple[str, Dict]]:
        """Find and return knowledge for all ORA errors in text."""
        return OracleErrorKnowledge.find_matching_errors(text)
    
    def get_standby_knowledge(self, pattern: str) -> Optional[Dict]:
        """Get Data Guard / standby pattern knowledge."""
        return DataGuardKnowledge.get_standby_pattern(pattern)
    
    def get_root_cause_knowledge(self, category: str) -> Optional[Dict]:
        """Get root cause category knowledge."""
        return CommonRootCauses.get_root_cause(category)
    
    def get_first_checks(self, situation: str) -> Optional[Dict]:
        """Get what a DBA would check first."""
        return DBAFirstChecks.get_first_checks(situation)
    
    def get_advisory_for_alert_type(self, alert_message: str) -> Dict:
        """
        Get advisory knowledge for an alert message.
        Returns structured advisory information.
        """
        advisory = {
            'has_knowledge': False,
            'ora_errors': [],
            'typical_meaning': None,
            'common_causes': [],
            'dba_first_checks': [],
            'risk_level': None,
            'advisory_language': []
        }
        
        # Check for ORA errors
        errors = self.find_errors_in_text(alert_message)
        if errors:
            advisory['has_knowledge'] = True
            advisory['ora_errors'] = errors
            
            # Use first error as primary
            code, knowledge = errors[0]
            advisory['typical_meaning'] = knowledge.get('meaning')
            advisory['common_causes'] = knowledge.get('common_causes', [])
            advisory['dba_first_checks'] = knowledge.get('dba_first_checks', [])
            advisory['risk_level'] = knowledge.get('risk_level')
            
            # Build advisory language
            advisory['advisory_language'] = [
                f"This error ({code}) typically indicates {knowledge.get('meaning', 'an Oracle issue')}",
                f"Common causes often include: {', '.join(knowledge.get('common_causes', ['various factors'])[:3])}",
                f"Experienced DBAs usually check: {knowledge.get('dba_first_checks', ['alert logs'])[0]}"
            ]
        
        # Check for standby-related keywords
        standby_keywords = ['standby', 'data guard', 'dataguard', 'mrp', 'apply', 'redo']
        if any(kw in alert_message.lower() for kw in standby_keywords):
            advisory['has_knowledge'] = True
            sg_knowledge = self.get_standby_knowledge('archive_gap')
            if sg_knowledge:
                advisory['advisory_language'].append(
                    "Data Guard issues commonly involve archive shipping or apply lag"
                )
        
        return advisory
    
    def format_human_advisory(self, alert_type: str, alert_count: int = 0) -> str:
        """
        Format advisory knowledge in human DBA language.
        Uses uncertainty language as required.
        """
        advisory = self.get_advisory_for_alert_type(alert_type)
        
        if not advisory['has_knowledge']:
            return ""
        
        lines = []
        lines.append("### 🧠 DBA Knowledge Context")
        lines.append("")
        
        if advisory['typical_meaning']:
            lines.append(f"**What this typically means:** {advisory['typical_meaning']}")
            lines.append("")
        
        if advisory['common_causes']:
            lines.append("**Common causes (from experience):**")
            for cause in advisory['common_causes'][:3]:
                lines.append(f"- {cause}")
            lines.append("")
        
        if advisory['dba_first_checks']:
            lines.append("**What DBAs usually check first:**")
            for check in advisory['dba_first_checks'][:3]:
                lines.append(f"- {check}")
            lines.append("")
        
        if advisory['risk_level']:
            lines.append(f"**Typical risk level:** {advisory['risk_level']}")
            lines.append("")
        
        lines.append("*Note: This is advisory information based on common patterns. "
                    "Actual root cause may vary.*")
        
        return "\n".join(lines)


# Singleton instance
DBA_KNOWLEDGE_BASE = DBAKnowledgeBase()
