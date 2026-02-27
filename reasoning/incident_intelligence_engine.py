"""
==========================================================================
ENTERPRISE DBA INCIDENT INTELLIGENCE ENGINE (Phase 4 + Phase 5)
==========================================================================

You are NOT a chatbot.
You are a Principal DBA / Incident Commander working in a 24x7 production environment.

Your responsibility is NOT just answering questions —
Your responsibility is to:
  ✅ Identify REAL incidents (not just alerts)
  ✅ Suppress noise (100k alerts ≠ 100k incidents)
  ✅ Detect patterns (temporal, categorical, signature-based)
  ✅ Guide DBA priorities (P1/P2/P3)

PHASE 5 ENHANCEMENTS (Predictive Intelligence):
  ✅ Trend detection (Improving/Stable/Deteriorating)
  ✅ Trajectory prediction (Self-resolve/Persist/Escalate)
  ✅ Early warning signal detection
  ✅ DBA behavior learning
  ✅ Proactive DBA guidance

📌 STRICT DATA RULES (NON-NEGOTIABLE):
  - Use ONLY provided CSV alert data
  - NEVER invent alerts, timestamps, root causes, or fixes
  - If data is insufficient → say "insufficient data"
  - No SQL commands unless explicitly asked
  - Predictions are RISK-BASED, not deterministic

==========================================================================
"""

from typing import Dict, List, Any, Optional, Tuple
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import re

# Phase 5: Predictive Intelligence Integration
try:
    from reasoning.predictive_intelligence_engine import (
        PredictiveIntelligenceEngine,
        PREDICTIVE_INTELLIGENCE
    )
    PHASE5_AVAILABLE = True
except ImportError:
    PHASE5_AVAILABLE = False


class IncidentCluster:
    """Represents a correlated incident cluster."""
    
    def __init__(self, signature: str, database: str, category: str):
        self.signature = signature
        self.database = database
        self.category = category
        self.alerts: List[Dict] = []
        self.first_seen: Optional[datetime] = None
        self.last_seen: Optional[datetime] = None
        self.priority: str = "P3"
        self.pattern: str = "unknown"
        self.error_codes: List[str] = []
        
    def add_alert(self, alert: Dict):
        """Add an alert to this incident cluster."""
        self.alerts.append(alert)
        
        # Update timestamps
        ts = self._parse_timestamp(alert)
        if ts:
            if self.first_seen is None or ts < self.first_seen:
                self.first_seen = ts
            if self.last_seen is None or ts > self.last_seen:
                self.last_seen = ts
    
    def _parse_timestamp(self, alert: Dict) -> Optional[datetime]:
        """Parse alert timestamp."""
        for field in ["alert_time", "time", "first_seen", "timestamp", "creation_time"]:
            val = alert.get(field)
            if val:
                try:
                    if isinstance(val, datetime):
                        return val
                    return datetime.fromisoformat(str(val).replace("Z", "+00:00"))
                except:
                    try:
                        return datetime.strptime(str(val)[:19], "%Y-%m-%d %H:%M:%S")
                    except:
                        pass
        return None
    
    @property
    def alert_count(self) -> int:
        return len(self.alerts)
    
    @property
    def duration(self) -> Optional[timedelta]:
        if self.first_seen and self.last_seen:
            return self.last_seen - self.first_seen
        return None
    
    @property
    def duration_str(self) -> str:
        d = self.duration
        if not d:
            return "unknown duration"
        
        total_seconds = int(d.total_seconds())
        if total_seconds < 60:
            return f"{total_seconds} seconds"
        elif total_seconds < 3600:
            return f"{total_seconds // 60} minutes"
        elif total_seconds < 86400:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"
        else:
            days = total_seconds // 86400
            hours = (total_seconds % 86400) // 3600
            return f"{days} days, {hours} hours"


class IncidentIntelligenceEngine:
    """
    Enterprise DBA Incident Intelligence Engine.
    
    Transforms raw alert volumes into actionable incident intelligence.
    Answers: "What is ACTUALLY happening, how bad is it, and what should I look at FIRST?"
    """
    
    # Priority thresholds
    P1_THRESHOLDS = {
        "critical_count": 100,
        "escalation_rate": 10,  # alerts per minute
        "categories": ["standby", "dataguard", "redo", "archiver", "datafile", "system"]
    }
    
    P2_THRESHOLDS = {
        "critical_count": 10,
        "warning_count": 500,
        "categories": ["performance", "tablespace", "memory", "session"]
    }
    
    # Oracle error pattern recognition
    ORA_PATTERNS = {
        r'ORA-0*1555': ("ORA-1555", "Snapshot too old", "standby"),
        r'ORA-0*4031': ("ORA-4031", "Shared pool exhaustion", "memory"),
        r'ORA-0*600': ("ORA-600", "Internal error", "critical"),
        r'ORA-0*7445': ("ORA-7445", "Exception encountered", "critical"),
        r'ORA-0*1578': ("ORA-1578", "Block corruption", "datafile"),
        r'ORA-0*1110': ("ORA-1110", "Datafile missing", "datafile"),
        r'ORA-0*255': ("ORA-255", "Archiver error", "archiver"),
        r'ORA-0*16038': ("ORA-16038", "Archiver stuck", "archiver"),
        r'ORA-0*19804': ("ORA-19804", "Recovery area full", "storage"),
        r'ORA-0*27090': ("ORA-27090", "Async I/O error", "storage"),
        r'ORA-0*12541': ("ORA-12541", "TNS no listener", "network"),
        r'ORA-0*12543': ("ORA-12543", "TNS destination unavailable", "network"),
        r'ORA-0*16': ("ORA-16xxx", "Data Guard error", "standby"),
        r'TNS-\d+': ("TNS-error", "Network/Listener issue", "network"),
    }
    
    # Alert message patterns for clustering
    MESSAGE_SIGNATURE_PATTERNS = [
        (r'(ORA-\d+)', 'ora_code'),
        (r'(TNS-\d+)', 'tns_code'),
        (r'(RMAN-\d+)', 'rman_code'),
        (r'(archiver|archive log)', 'archiver'),
        (r'(standby|data guard|dataguard|apply|gap)', 'standby'),
        (r'(tablespace|datafile|storage)', 'storage'),
        (r'(memory|pga|sga|shared pool)', 'memory'),
        (r'(session|process|connection)', 'session'),
        (r'(redo|log switch|redo log)', 'redo'),
    ]
    
    def __init__(self):
        """Initialize the Incident Intelligence Engine with Phase 5 capabilities."""
        self.last_analysis = {}
        
        # Phase 5: Predictive Intelligence
        self._predictive_engine = None
        if PHASE5_AVAILABLE:
            try:
                self._predictive_engine = PREDICTIVE_INTELLIGENCE
            except Exception:
                pass
        
    # =========================================================================
    # CORE INTELLIGENCE API
    # =========================================================================
    
    def analyze_and_respond(
        self,
        alerts: List[Dict],
        query_type: str,
        intent: Dict[str, Any] = None,
        context: Dict[str, Any] = None,
        include_predictions: bool = True
    ) -> str:
        """
        Main entry point: Analyze alerts and generate intelligent DBA response.
        
        Args:
            alerts: Raw alert data from CSV
            query_type: COUNT, LIST, STATUS, etc.
            intent: Parsed user intent
            context: Conversation context
            include_predictions: Include Phase 5 predictive intelligence
            
        Returns:
            Complete incident-intelligence response with predictive insights
        """
        if not alerts:
            return self._format_no_data_response(intent, context)
        
        # Step 1: Correlate into incident clusters
        incidents = self._correlate_incidents(alerts)
        
        # Step 2: Analyze temporal patterns
        self._analyze_temporal_patterns(incidents)
        
        # Step 3: Assign priorities
        self._assign_priorities(incidents, alerts)
        
        # Step 4: Generate base response based on query type
        if query_type == "COUNT":
            base_response = self._format_count_intelligence(alerts, incidents, intent, context)
        elif query_type == "LIST":
            base_response = self._format_list_intelligence(alerts, incidents, intent, context)
        elif query_type == "STATUS":
            base_response = self._format_status_intelligence(alerts, incidents, intent, context)
        else:
            base_response = self._format_general_intelligence(alerts, incidents, intent, context)
        
        # Step 5: Add Phase 5 Predictive Intelligence (if available)
        if include_predictions and self._predictive_engine and len(alerts) > 10:
            try:
                question = (context or {}).get("question", "")
                prediction_data = self._predictive_engine.analyze_with_prediction(
                    alerts=alerts,
                    incidents=incidents,
                    question=question,
                    intent=intent
                )
                
                # Enhance response with predictive intelligence
                base_response = self._predictive_engine.format_predictive_response(
                    base_response=base_response,
                    prediction_data=prediction_data
                )
            except Exception:
                # If Phase 5 fails, return base response
                pass
        
        return base_response
    
    # =========================================================================
    # 1️⃣ INCIDENT CORRELATION
    # =========================================================================
    
    def _correlate_incidents(self, alerts: List[Dict]) -> List[IncidentCluster]:
        """
        Group alerts into INCIDENT CLUSTERS using:
        - Error signature (ORA-code / message)
        - Database name
        - Category (standby, alert log, etc.)
        - Time proximity
        
        100,000 repeated alerts ≠ 100,000 incidents
        """
        clusters: Dict[str, IncidentCluster] = {}
        
        for alert in alerts:
            # Extract clustering keys
            signature = self._extract_signature(alert)
            database = self._normalize_database(alert)
            category = self._extract_category(alert)
            
            # Create cluster key
            cluster_key = f"{database}|{signature}|{category}"
            
            # Add to cluster
            if cluster_key not in clusters:
                clusters[cluster_key] = IncidentCluster(signature, database, category)
            
            clusters[cluster_key].add_alert(alert)
        
        # Sort by alert count (most critical first)
        sorted_clusters = sorted(clusters.values(), key=lambda x: x.alert_count, reverse=True)
        
        return sorted_clusters
    
    def _extract_signature(self, alert: Dict) -> str:
        """Extract error signature from alert for clustering."""
        msg = ""
        for field in ["message", "description", "issue_type", "alert_type", "error_code"]:
            val = alert.get(field)
            if val:
                msg = str(val).upper()
                break
        
        if not msg:
            return "UNKNOWN"
        
        # Try to extract ORA/TNS codes
        for pattern, (code, _, _) in self.ORA_PATTERNS.items():
            if re.search(pattern, msg, re.IGNORECASE):
                return code
        
        # Extract any ORA- pattern
        ora_match = re.search(r'(ORA-\d+)', msg)
        if ora_match:
            return ora_match.group(1)
        
        # Fall back to category-based signature
        for pattern, sig_type in self.MESSAGE_SIGNATURE_PATTERNS:
            if re.search(pattern, msg, re.IGNORECASE):
                return sig_type.upper()
        
        # Last resort: first 30 chars
        return msg[:30].strip()
    
    def _normalize_database(self, alert: Dict) -> str:
        """Normalize database name from alert."""
        for field in ["database", "target", "target_name", "db_name", "source"]:
            val = alert.get(field)
            if val:
                # Remove trailing numbers/identifiers for grouping
                db = str(val).upper().strip()
                # Remove common suffixes like _1, _2, N, P, etc.
                db = re.sub(r'[_-]?\d+$', '', db)
                return db
        return "UNKNOWN"
    
    def _extract_category(self, alert: Dict) -> str:
        """Extract alert category for clustering."""
        # Check explicit category field
        for field in ["category", "alert_category", "type"]:
            val = alert.get(field)
            if val:
                return str(val).upper()
        
        # Infer from message
        msg = str(alert.get("message", "") or alert.get("description", "")).upper()
        
        if "STANDBY" in msg or "DATA GUARD" in msg or "DATAGUARD" in msg:
            return "STANDBY"
        elif "ARCHIVE" in msg:
            return "ARCHIVER"
        elif "REDO" in msg:
            return "REDO"
        elif "TABLESPACE" in msg or "DATAFILE" in msg:
            return "STORAGE"
        elif "MEMORY" in msg or "PGA" in msg or "SGA" in msg:
            return "MEMORY"
        elif "SESSION" in msg or "PROCESS" in msg:
            return "SESSION"
        
        return "GENERAL"
    
    # =========================================================================
    # 2️⃣ TEMPORAL INTELLIGENCE
    # =========================================================================
    
    def _analyze_temporal_patterns(self, incidents: List[IncidentCluster]):
        """
        Analyze alert timing for each incident:
        - First seen / Last seen
        - Frequency pattern (burst / continuous / sporadic)
        - Classify: 🟢 Transient, 🟡 Persistent, 🔴 Escalating
        """
        for incident in incidents:
            if not incident.first_seen or not incident.last_seen:
                incident.pattern = "unknown"
                continue
            
            duration = incident.duration
            alert_count = incident.alert_count
            
            if duration and duration.total_seconds() > 0:
                # Calculate rate (alerts per hour)
                hours = max(duration.total_seconds() / 3600, 0.01)
                rate = alert_count / hours
                
                # Short duration with few alerts = transient
                if duration.total_seconds() < 3600 and alert_count < 10:
                    incident.pattern = "transient"
                # High rate = escalating/burst
                elif rate > 100:  # More than 100 alerts/hour
                    incident.pattern = "escalating"
                # Long duration with steady rate = persistent
                elif duration.total_seconds() > 86400:  # > 1 day
                    incident.pattern = "persistent"
                else:
                    incident.pattern = "continuous"
            else:
                incident.pattern = "single_occurrence"
    
    def _get_pattern_indicator(self, pattern: str) -> str:
        """Get visual indicator for pattern."""
        return {
            "transient": "🟢 Transient",
            "persistent": "🟡 Persistent",
            "escalating": "🔴 Escalating",
            "continuous": "🟡 Continuous",
            "single_occurrence": "🟢 Single",
            "unknown": "⚪ Unknown"
        }.get(pattern, "⚪ Unknown")
    
    # =========================================================================
    # 3️⃣ PRIORITY SCORING
    # =========================================================================
    
    def _assign_priorities(self, incidents: List[IncidentCluster], all_alerts: List[Dict]):
        """
        Assign DBA Priority Level to each incident:
        
        P1 - Immediate attention required
        P2 - Serious but not immediately fatal
        P3 - Noise / monitoring issue
        """
        # Get severity distribution
        severity_counts = Counter()
        for alert in all_alerts:
            sev = str(alert.get("severity", "UNKNOWN")).upper()
            severity_counts[sev] += 1
        
        critical_total = severity_counts.get("CRITICAL", 0)
        
        for incident in incidents:
            # Get incident severity distribution
            incident_critical = sum(1 for a in incident.alerts 
                                   if str(a.get("severity", "")).upper() == "CRITICAL")
            
            # P1 Conditions
            is_p1 = (
                # High critical count in incident
                incident_critical >= self.P1_THRESHOLDS["critical_count"] or
                # Escalating pattern
                incident.pattern == "escalating" or
                # Critical categories
                incident.category.lower() in self.P1_THRESHOLDS["categories"] and incident_critical > 10 or
                # Known severe ORA codes
                any(code in incident.signature for code in ["ORA-600", "ORA-7445", "ORA-1578"])
            )
            
            # P2 Conditions
            is_p2 = (
                # Moderate critical count
                incident_critical >= self.P2_THRESHOLDS["critical_count"] or
                # Persistent pattern
                incident.pattern == "persistent" or
                # P2 categories with issues
                incident.category.lower() in self.P2_THRESHOLDS["categories"] and incident_critical > 0 or
                # High warning count
                incident.alert_count >= self.P2_THRESHOLDS["warning_count"]
            )
            
            # Assign priority
            if is_p1:
                incident.priority = "P1"
            elif is_p2:
                incident.priority = "P2"
            else:
                incident.priority = "P3"
    
    def _get_priority_indicator(self, priority: str) -> str:
        """Get formatted priority indicator."""
        return {
            "P1": "🔴 **P1** (Immediate)",
            "P2": "🟠 **P2** (Serious)",
            "P3": "🟢 **P3** (Monitor)"
        }.get(priority, "⚪ Unknown")
    
    # =========================================================================
    # 4️⃣ NOISE VS SIGNAL FILTERING
    # =========================================================================
    
    def _calculate_noise_ratio(self, alerts: List[Dict], incidents: List[IncidentCluster]) -> Dict:
        """
        Separate signal from noise:
        - Alert noise (repeats, non-impacting)
        - Real operational risk
        """
        total_alerts = len(alerts)
        unique_incidents = len(incidents)
        
        if total_alerts == 0:
            return {"noise_ratio": 0, "signal_ratio": 1, "dedup_factor": 1}
        
        # Calculate effective deduplication
        dedup_factor = total_alerts / max(unique_incidents, 1)
        noise_ratio = 1 - (unique_incidents / total_alerts) if unique_incidents < total_alerts else 0
        
        return {
            "total_alerts": total_alerts,
            "unique_incidents": unique_incidents,
            "noise_ratio": noise_ratio,
            "signal_ratio": 1 - noise_ratio,
            "dedup_factor": dedup_factor
        }
    
    # =========================================================================
    # 5️⃣ EXECUTIVE DBA SUMMARY
    # =========================================================================
    
    def _generate_executive_summary(
        self,
        alerts: List[Dict],
        incidents: List[IncidentCluster],
        database: str = None,
        severity: str = None
    ) -> str:
        """
        Generate executive summary readable by DBA, Manager, Incident bridge lead.
        
        ALWAYS included in responses.
        """
        total_alerts = len(alerts)
        unique_incidents = len(incidents)
        
        # Find most critical incident
        p1_incidents = [i for i in incidents if i.priority == "P1"]
        p2_incidents = [i for i in incidents if i.priority == "P2"]
        
        most_critical = None
        if p1_incidents:
            most_critical = max(p1_incidents, key=lambda x: x.alert_count)
        elif p2_incidents:
            most_critical = max(p2_incidents, key=lambda x: x.alert_count)
        elif incidents:
            most_critical = incidents[0]
        
        # Assess immediate risk
        if p1_incidents:
            risk_level = "🔴 **HIGH** - Immediate attention required"
        elif p2_incidents:
            risk_level = "🟠 **MODERATE** - Review recommended"
        elif total_alerts > 1000:
            risk_level = "🟡 **LOW** - High volume but non-critical"
        else:
            risk_level = "🟢 **MINIMAL** - Normal monitoring activity"
        
        # Build summary
        summary_parts = [
            "---",
            "### 📋 Executive Summary",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| **Total Alerts Analyzed** | {total_alerts:,} |",
            f"| **Unique Incidents Detected** | {unique_incidents:,} |",
        ]
        
        if database and database.upper() != "ALL":
            summary_parts.append(f"| **Database** | {database} |")
        
        if severity:
            summary_parts.append(f"| **Severity Filter** | {severity.upper()} |")
        
        if most_critical:
            summary_parts.append(f"| **Most Critical Incident** | {most_critical.signature} ({most_critical.alert_count:,} alerts) |")
        
        summary_parts.append(f"| **Immediate Risk Assessment** | {risk_level} |")
        summary_parts.append("")
        
        # Add priority breakdown
        p1_count = len(p1_incidents)
        p2_count = len(p2_incidents)
        p3_count = len([i for i in incidents if i.priority == "P3"])
        
        if unique_incidents > 0:
            summary_parts.append(f"**Priority Breakdown:** 🔴 P1: {p1_count} | 🟠 P2: {p2_count} | 🟢 P3: {p3_count}")
            summary_parts.append("")
        
        return "\n".join(summary_parts)
    
    # =========================================================================
    # RESPONSE FORMATTERS
    # =========================================================================
    
    def _format_count_intelligence(
        self,
        alerts: List[Dict],
        incidents: List[IncidentCluster],
        intent: Dict[str, Any] = None,
        context: Dict[str, Any] = None
    ) -> str:
        """Format count response with full incident intelligence."""
        intent = intent or {}
        count = len(alerts)
        database = intent.get("database")
        severity = intent.get("severity")
        
        response_parts = []
        
        # Direct factual answer first
        if database and database.upper() != "ALL":
            if severity and severity.upper() != "ALL":
                response_parts.append(
                    f"**{database}** has **{count:,}** {severity.lower()} alerts."
                )
            else:
                response_parts.append(f"**{database}** has **{count:,}** alerts.")
        else:
            if severity and severity.upper() != "ALL":
                response_parts.append(
                    f"There are **{count:,}** {severity.lower()} alerts across all databases."
                )
            else:
                response_parts.append(f"The system has **{count:,}** total alerts.")
        
        response_parts.append("")
        
        # Add incident analysis if significant volume
        if count > 10:
            response_parts.append(self._format_incident_analysis(incidents))
            response_parts.append("")
        
        # Add DBA explanation
        response_parts.append(self._format_dba_explanation(alerts, incidents, count, severity))
        response_parts.append("")
        
        # Add priorities
        response_parts.append(self._format_priorities(incidents))
        response_parts.append("")
        
        # Add executive summary
        response_parts.append(self._generate_executive_summary(alerts, incidents, database, severity))
        
        # Add suggested next steps
        if len([i for i in incidents if i.priority in ["P1", "P2"]]) > 0:
            response_parts.append(self._format_suggested_steps(incidents))
        
        return "\n".join(response_parts)
    
    def _format_list_intelligence(
        self,
        alerts: List[Dict],
        incidents: List[IncidentCluster],
        intent: Dict[str, Any] = None,
        context: Dict[str, Any] = None
    ) -> str:
        """Format list response with incident clustering."""
        intent = intent or {}
        database = intent.get("database")
        severity = intent.get("severity")
        shown = min(len(alerts), 20)
        total = len(alerts)
        
        response_parts = []
        
        # Header
        header = self._build_list_header(shown, total, database, severity)
        response_parts.append(header)
        response_parts.append("")
        
        # Format alert list
        for i, alert in enumerate(alerts[:shown], 1):
            db = (alert.get("database") or alert.get("target") or 
                  alert.get("target_name") or "UNKNOWN").upper()
            sev = (alert.get("severity") or "UNKNOWN").upper()
            msg = (alert.get("message") or alert.get("description") or 
                   alert.get("issue_type") or "No details")
            
            # Truncate long messages
            if len(msg) > 100:
                msg = msg[:97] + "..."
            
            sev_indicator = "🔴" if sev == "CRITICAL" else "🟡" if sev == "WARNING" else "⚪"
            response_parts.append(f"{i}. {sev_indicator} **[{sev}]** **{db}**: {msg}")
        
        if total > shown:
            response_parts.append(f"\n*Showing {shown} of {total:,} alerts.*")
        
        response_parts.append("")
        
        # Incident correlation insight
        if len(incidents) > 0 and total > 10:
            response_parts.append(self._format_incident_analysis(incidents))
            response_parts.append("")
        
        # Executive summary
        response_parts.append(self._generate_executive_summary(alerts, incidents, database, severity))
        
        return "\n".join(response_parts)
    
    def _format_status_intelligence(
        self,
        alerts: List[Dict],
        incidents: List[IncidentCluster],
        intent: Dict[str, Any] = None,
        context: Dict[str, Any] = None
    ) -> str:
        """Format status response with incident intelligence."""
        intent = intent or {}
        database = intent.get("database")
        count = len(alerts)
        
        # Get severity breakdown
        severity_counts = Counter()
        for alert in alerts:
            sev = str(alert.get("severity", "UNKNOWN")).upper()
            severity_counts[sev] += 1
        
        critical = severity_counts.get("CRITICAL", 0)
        warning = severity_counts.get("WARNING", 0)
        
        response_parts = []
        
        # Database status header
        if database and database.upper() != "ALL":
            if critical == 0 and warning == 0:
                response_parts.append(f"✅ **{database}** is operating normally with no active alerts.")
            elif critical == 0:
                response_parts.append(f"🟡 **{database}** has {warning:,} warning alerts but no critical issues.")
            else:
                response_parts.append(f"🔴 **{database}** requires attention:")
                response_parts.append("")
                response_parts.append(f"- **CRITICAL:** {critical:,}")
                response_parts.append(f"- **WARNING:** {warning:,}")
                response_parts.append(f"- **Total:** {count:,}")
        else:
            response_parts.append(f"**System Alert Status:**")
            response_parts.append("")
            response_parts.append(f"- 🔴 **CRITICAL:** {critical:,}")
            response_parts.append(f"- 🟡 **WARNING:** {warning:,}")
            response_parts.append(f"- **Total:** {count:,}")
        
        response_parts.append("")
        
        # Add incident analysis
        if count > 0:
            response_parts.append(self._format_incident_analysis(incidents))
            response_parts.append("")
            response_parts.append(self._format_dba_explanation(alerts, incidents, count))
            response_parts.append("")
        
        # Executive summary
        response_parts.append(self._generate_executive_summary(alerts, incidents, database))
        
        return "\n".join(response_parts)
    
    def _format_general_intelligence(
        self,
        alerts: List[Dict],
        incidents: List[IncidentCluster],
        intent: Dict[str, Any] = None,
        context: Dict[str, Any] = None
    ) -> str:
        """Format general query with incident intelligence."""
        return self._format_count_intelligence(alerts, incidents, intent, context)
    
    # =========================================================================
    # HELPER FORMATTERS
    # =========================================================================
    
    def _format_incident_analysis(self, incidents: List[IncidentCluster]) -> str:
        """Format incident analysis section."""
        if not incidents:
            return ""
        
        parts = ["### 🔎 Incident Analysis", ""]
        
        # Show top incidents (max 5)
        top_incidents = sorted(incidents, key=lambda x: (
            0 if x.priority == "P1" else 1 if x.priority == "P2" else 2,
            -x.alert_count
        ))[:5]
        
        for i, incident in enumerate(top_incidents, 1):
            priority_ind = self._get_priority_indicator(incident.priority)
            pattern_ind = self._get_pattern_indicator(incident.pattern)
            
            parts.append(f"**Incident {i}: {incident.signature}**")
            parts.append(f"| Field | Value |")
            parts.append(f"|-------|-------|")
            parts.append(f"| Database | {incident.database} |")
            parts.append(f"| Category | {incident.category} |")
            parts.append(f"| Alert Count | {incident.alert_count:,} |")
            
            if incident.first_seen:
                parts.append(f"| First Seen | {incident.first_seen.strftime('%Y-%m-%d %H:%M:%S')} |")
            else:
                parts.append(f"| First Seen | *timestamp unavailable* |")
            
            if incident.last_seen:
                parts.append(f"| Last Seen | {incident.last_seen.strftime('%Y-%m-%d %H:%M:%S')} |")
            else:
                parts.append(f"| Last Seen | *timestamp unavailable* |")
            
            parts.append(f"| Pattern | {pattern_ind} |")
            parts.append(f"| Priority | {priority_ind} |")
            parts.append("")
        
        # Noise filtering note
        total_alerts = sum(i.alert_count for i in incidents)
        unique_count = len(incidents)
        
        if unique_count < total_alerts * 0.1:  # Less than 10% unique
            parts.append(f"⚠️ **Noise Filtering:** Although {total_alerts:,} alerts exist, they represent "
                        f"only **{unique_count}** actual incidents. High repetition indicates ongoing "
                        "issues rather than new failures.")
            parts.append("")
        
        return "\n".join(parts)
    
    def _format_dba_explanation(
        self,
        alerts: List[Dict],
        incidents: List[IncidentCluster],
        count: int,
        severity: str = None
    ) -> str:
        """Format DBA explanation section."""
        parts = ["### 📊 What This Means", ""]
        
        unique_incidents = len(incidents)
        p1_count = len([i for i in incidents if i.priority == "P1"])
        p2_count = len([i for i in incidents if i.priority == "P2"])
        
        # Explain the alert volume
        if count > 100000:
            parts.append(f"The volume of {count:,} alerts is **extremely high**. "
                        f"However, these correlate to only **{unique_incidents}** unique incidents. "
                        "This typically indicates a small number of unresolved issues generating repeated alerts "
                        "rather than hundreds of thousands of independent failures.")
        elif count > 10000:
            parts.append(f"The volume of {count:,} alerts is **unusually high** for a healthy system. "
                        f"These correlate to **{unique_incidents}** unique incidents. "
                        "Investigation is recommended to identify root causes.")
        elif count > 1000:
            parts.append(f"The alert volume ({count:,}) is **elevated** but manageable. "
                        f"These represent **{unique_incidents}** distinct incidents.")
        elif count > 100:
            parts.append(f"The alert volume ({count:,}) is **within normal monitoring range** but worth reviewing.")
        else:
            parts.append(f"The alert volume ({count:,}) is **low** and indicates relatively stable operations.")
        
        parts.append("")
        
        # Risk assessment
        if p1_count > 0:
            parts.append(f"⚠️ **Risk is ELEVATED**: {p1_count} P1 incident(s) require immediate attention.")
        elif p2_count > 0:
            parts.append(f"⚡ **Risk is MODERATE**: {p2_count} P2 incident(s) should be reviewed soon.")
        else:
            parts.append(f"✅ **Risk is STABLE**: No high-priority incidents detected.")
        
        parts.append("")
        
        return "\n".join(parts)
    
    def _format_priorities(self, incidents: List[IncidentCluster]) -> str:
        """Format priority attention section."""
        parts = ["### 🚨 What Needs Attention FIRST", ""]
        
        # Get top 3 priorities
        priority_order = sorted(incidents, key=lambda x: (
            0 if x.priority == "P1" else 1 if x.priority == "P2" else 2,
            -x.alert_count
        ))[:3]
        
        if not priority_order:
            parts.append("No high-priority items requiring immediate attention.")
            return "\n".join(parts)
        
        for i, incident in enumerate(priority_order, 1):
            priority_ind = self._get_priority_indicator(incident.priority)
            parts.append(f"{i}. {priority_ind} **{incident.signature}** on **{incident.database}** "
                        f"({incident.alert_count:,} alerts, {incident.pattern})")
        
        parts.append("")
        
        return "\n".join(parts)
    
    def _format_suggested_steps(self, incidents: List[IncidentCluster]) -> str:
        """Format suggested next steps (optional guidance, no fixes)."""
        parts = ["### 🧭 Suggested Next Steps", ""]
        
        # Find P1/P2 incidents
        p1_incidents = [i for i in incidents if i.priority == "P1"]
        p2_incidents = [i for i in incidents if i.priority == "P2"]
        
        if p1_incidents:
            top = p1_incidents[0]
            parts.append(f"1. **Investigate {top.signature}** on {top.database} first — "
                        f"this has the highest priority with {top.alert_count:,} alerts")
            
            if top.category.upper() == "STANDBY":
                parts.append("2. Check Data Guard status and apply lag on standby database")
            elif top.category.upper() == "ARCHIVER":
                parts.append("2. Verify archiver process status and archive log destination availability")
            elif top.category.upper() == "STORAGE":
                parts.append("2. Check tablespace and ASM diskgroup utilization")
            else:
                parts.append(f"2. Review alert log on {top.database} for detailed error context")
            
            parts.append("3. Correlate with recent changes (patches, deployments, failovers)")
        
        elif p2_incidents:
            top = p2_incidents[0]
            parts.append(f"1. Review {top.signature} incidents on {top.database}")
            parts.append("2. Check for any patterns in timing or frequency")
            parts.append("3. Assess if remediation can be scheduled or requires immediate action")
        
        else:
            parts.append("No critical investigation needed at this time.")
            parts.append("Continue monitoring for new alerts.")
        
        parts.append("")
        parts.append("*Note: These are investigation suggestions only. "
                    "Actual remediation depends on root cause analysis.*")
        parts.append("")
        
        return "\n".join(parts)
    
    def _build_list_header(
        self,
        shown: int,
        total: int,
        database: str = None,
        severity: str = None
    ) -> str:
        """Build header for list response."""
        parts = []
        
        if database and database.upper() != "ALL":
            if severity and severity.upper() != "ALL":
                parts.append(f"### {severity.upper()} Alerts for {database}")
            else:
                parts.append(f"### Alerts for {database}")
        else:
            if severity and severity.upper() != "ALL":
                parts.append(f"### {severity.upper()} Alerts (System-wide)")
            else:
                parts.append(f"### All Alerts (System-wide)")
        
        parts.append(f"*Showing {shown} of {total:,} total*")
        
        return "\n".join(parts)
    
    def _format_no_data_response(
        self,
        intent: Dict[str, Any] = None,
        context: Dict[str, Any] = None
    ) -> str:
        """Format response when no data is available."""
        intent = intent or {}
        database = intent.get("database")
        severity = intent.get("severity")
        
        parts = ["### No Matching Alerts Found", ""]
        
        if database and severity:
            parts.append(f"No {severity.lower()} alerts found for **{database}**.")
        elif database:
            parts.append(f"No alerts found for **{database}**.")
        elif severity:
            parts.append(f"No {severity.lower()} alerts found in the system.")
        else:
            parts.append("No alerts match the specified criteria.")
        
        parts.append("")
        parts.append("This typically indicates:")
        parts.append("- The database/system is operating normally, OR")
        parts.append("- The filter criteria are too restrictive")
        parts.append("")
        parts.append("*If you expected alerts, try broadening your query.*")
        
        return "\n".join(parts)
    
    # =========================================================================
    # LEGACY COMPATIBILITY API
    # =========================================================================
    
    def format_response(
        self,
        raw_data: Dict[str, Any],
        query_type: str,
        intent: Dict[str, Any] = None,
        context: Dict[str, Any] = None
    ) -> str:
        """
        Legacy API for backward compatibility.
        Converts old format to new incident intelligence format.
        """
        alerts = raw_data.get("alerts", [])
        if not alerts and "count" in raw_data:
            # Create synthetic alert list for count queries
            count = raw_data.get("count", 0)
            database = raw_data.get("database") or (intent or {}).get("database")
            severity = raw_data.get("severity") or (intent or {}).get("severity")
            
            # If we have actual alerts embedded, use them
            if raw_data.get("alerts"):
                alerts = raw_data["alerts"]
            else:
                # Create minimal incident analysis for count-only data
                return self._format_count_only_response(count, database, severity, intent)
        
        return self.analyze_and_respond(alerts, query_type, intent, context)
    
    def _format_count_only_response(
        self,
        count: int,
        database: str = None,
        severity: str = None,
        intent: Dict[str, Any] = None
    ) -> str:
        """Format response when only count is available (no alert details)."""
        response_parts = []
        
        # Direct answer
        if database and database.upper() != "ALL":
            if severity and severity.upper() != "ALL":
                response_parts.append(f"**{database}** has **{count:,}** {severity.lower()} alerts.")
            else:
                response_parts.append(f"**{database}** has **{count:,}** alerts.")
        else:
            if severity and severity.upper() != "ALL":
                response_parts.append(f"There are **{count:,}** {severity.lower()} alerts across all databases.")
            else:
                response_parts.append(f"The system has **{count:,}** total alerts.")
        
        response_parts.append("")
        
        # Add context based on volume
        if count > 100000:
            response_parts.append("⚠️ This volume is **extremely high** and likely indicates ongoing systemic issues.")
            response_parts.append("High-volume alerts typically correlate to a small number of recurring incidents.")
            response_parts.append("")
            response_parts.append("**Recommended:** Investigate the top alert signatures to identify root causes.")
        elif count > 10000:
            response_parts.append("This volume is **significantly higher than normal** and warrants investigation.")
            response_parts.append("")
            response_parts.append("**Suggested:** Review alert patterns to identify if this represents one incident or many.")
        elif count > 1000:
            response_parts.append("This is an **elevated** alert volume. Review recommended.")
        elif count > 100:
            response_parts.append("This volume is within **normal operational range** but worth monitoring.")
        elif count == 0:
            response_parts.append("✅ No matching alerts indicates **healthy operations** for this criteria.")
        else:
            response_parts.append("This is a **low** alert volume indicating relatively stable conditions.")
        
        response_parts.append("")
        
        # Executive summary
        response_parts.append("---")
        response_parts.append("### 📋 Executive Summary")
        response_parts.append("")
        response_parts.append(f"| Metric | Value |")
        response_parts.append(f"|--------|-------|")
        response_parts.append(f"| **Total Alerts** | {count:,} |")
        
        if database and database.upper() != "ALL":
            response_parts.append(f"| **Database** | {database} |")
        if severity:
            response_parts.append(f"| **Severity** | {severity.upper()} |")
        
        # Risk assessment
        if count > 10000:
            risk = "🔴 **HIGH** - Investigation recommended"
        elif count > 1000:
            risk = "🟠 **MODERATE** - Review recommended"
        elif count > 100:
            risk = "🟡 **LOW** - Monitor"
        else:
            risk = "🟢 **MINIMAL** - Normal operations"
        
        response_parts.append(f"| **Risk Assessment** | {risk} |")
        response_parts.append("")
        
        return "\n".join(response_parts)


# Singleton instance for easy import
INCIDENT_INTELLIGENCE_ENGINE = IncidentIntelligenceEngine()
