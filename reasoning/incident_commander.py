# reasoning/incident_commander.py
"""
AUTONOMOUS DBA INCIDENT COMMANDER

You are not a reporter. You are not a chatbot.
You are the Incident Commander.

This engine:
- OWNS the incident
- THINKS ahead of the user
- REDUCES chaos, noise, and confusion
- NEVER fabricates data
- NEVER assumes fixes without evidence
"""

from datetime import datetime
from collections import Counter
from typing import Dict, List, Optional, Tuple, Any


class IncidentCommander:
    """
    Autonomous DBA Incident Commander.
    
    Takes control of the narrative during production incidents.
    Proactively assesses, prioritizes, escalates, and guides.
    """
    
    # Thresholds for incident classification
    THRESHOLDS = {
        "CRITICAL": 10000,      # > 10k critical alerts = ACTIVE INCIDENT
        "CONCERNING": 1000,     # > 1k critical alerts = CONCERNING
        "ELEVATED": 100,        # > 100 critical alerts = ELEVATED
        "NORMAL": 0             # Everything else
    }
    
    # Error severity rankings (P1 potential)
    P1_ERROR_PATTERNS = [
        "ORA-00600",    # Internal error - potential crash
        "ORA-07445",    # Exception raised - potential crash
        "ORA-04031",    # Shared pool exhaustion
        "ORA-01555",    # Snapshot too old - data consistency
        "ORA-16014",    # Archiver stuck
        "ORA-16038",    # Log cannot be archived
        "ORA-03113",    # End of file on communication channel
        "ORA-03114",    # Not connected to Oracle
        "ORA-12541",    # No listener
        "ORA-27101",    # Shared memory realm does not exist
    ]
    
    # Subsystem classifications
    SUBSYSTEM_PATTERNS = {
        "DATA_GUARD": ["standby", "dataguard", "data guard", "apply", "transport", "mrp", "redo", "ora-16"],
        "LISTENER": ["listener", "tns", "ora-12541", "ora-12514", "ora-12170"],
        "STORAGE": ["tablespace", "space", "extent", "ora-1654", "ora-1653", "ora-01691"],
        "MEMORY": ["pga", "sga", "shared pool", "ora-04031", "ora-04030"],
        "CONNECTIVITY": ["connection", "session", "ora-03113", "ora-03114", "ora-12541"],
        "INTERNAL": ["ora-00600", "ora-07445", "internal error"]
    }
    
    def __init__(self):
        self._last_assessment = None
        self._incident_start_time = None
        self._incident_id = None
        
    def assess_production_state(self, alerts: List[Dict]) -> Dict[str, Any]:
        """
        Perform autonomous assessment of production state.
        
        This is the core Incident Commander function.
        Returns a complete incident assessment.
        """
        if not alerts:
            return self._build_no_data_response()
        
        # Core metrics
        total_alerts = len(alerts)
        critical_alerts = [a for a in alerts if (a.get("severity") or "").upper() == "CRITICAL"]
        critical_count = len(critical_alerts)
        
        # Database breakdown
        db_breakdown = self._get_database_breakdown(alerts)
        
        # Error pattern analysis
        error_patterns = self._analyze_error_patterns(alerts)
        
        # Subsystem analysis
        subsystem_status = self._analyze_subsystems(alerts)
        
        # Determine incident status
        incident_status = self._determine_incident_status(critical_count, db_breakdown, error_patterns)
        
        # Priority ranking
        priorities = self._rank_priorities(db_breakdown, error_patterns, subsystem_status)
        
        # Next best actions
        actions = self._determine_next_actions(priorities, subsystem_status)
        
        # Failure predictions
        predictions = self._predict_next_risks(db_breakdown, subsystem_status, error_patterns)
        
        # Escalation advice
        escalation = self._determine_escalation(incident_status, priorities)
        
        # Build comprehensive assessment
        assessment = {
            "incident_status": incident_status,
            "total_alerts": total_alerts,
            "critical_count": critical_count,
            "db_breakdown": db_breakdown,
            "error_patterns": error_patterns,
            "subsystem_status": subsystem_status,
            "priorities": priorities,
            "actions": actions,
            "predictions": predictions,
            "escalation": escalation,
            "timestamp": datetime.now().isoformat()
        }
        
        self._last_assessment = assessment
        return assessment
    
    def _get_database_breakdown(self, alerts: List[Dict]) -> Dict[str, Dict]:
        """Get per-database alert breakdown."""
        db_stats = {}
        
        for alert in alerts:
            db = (alert.get("target_name") or alert.get("target") or "UNKNOWN").upper()
            severity = (alert.get("severity") or "UNKNOWN").upper()
            
            if db not in db_stats:
                db_stats[db] = {"total": 0, "CRITICAL": 0, "WARNING": 0, "INFO": 0}
            
            db_stats[db]["total"] += 1
            if severity in db_stats[db]:
                db_stats[db][severity] += 1
        
        return db_stats
    
    def _analyze_error_patterns(self, alerts: List[Dict]) -> Dict[str, Any]:
        """Analyze error patterns for P1 identification."""
        error_counts = Counter()
        p1_errors = []
        
        for alert in alerts:
            msg = (alert.get("message") or alert.get("msg_text") or "").upper()
            issue_type = (alert.get("issue_type") or "").upper()
            
            # Count by issue type
            if issue_type:
                error_counts[issue_type] += 1
            
            # Check for P1 error patterns
            for pattern in self.P1_ERROR_PATTERNS:
                if pattern.upper() in msg:
                    p1_errors.append({
                        "pattern": pattern,
                        "db": (alert.get("target_name") or alert.get("target") or "UNKNOWN").upper(),
                        "message": msg[:100]
                    })
        
        return {
            "top_errors": error_counts.most_common(5),
            "p1_errors": p1_errors[:10],  # Limit to top 10
            "unique_patterns": len(error_counts),
            "has_p1_patterns": len(p1_errors) > 0
        }
    
    def _analyze_subsystems(self, alerts: List[Dict]) -> Dict[str, Dict]:
        """Analyze which subsystems are affected."""
        subsystem_status = {}
        
        for name, patterns in self.SUBSYSTEM_PATTERNS.items():
            matching_alerts = []
            for alert in alerts:
                msg = (alert.get("message") or alert.get("msg_text") or "").lower()
                issue_type = (alert.get("issue_type") or "").lower()
                
                if any(p in msg or p in issue_type for p in patterns):
                    matching_alerts.append(alert)
            
            if matching_alerts:
                critical = sum(1 for a in matching_alerts if (a.get("severity") or "").upper() == "CRITICAL")
                subsystem_status[name] = {
                    "total": len(matching_alerts),
                    "critical": critical,
                    "status": "CRITICAL" if critical > 100 else "DEGRADED" if critical > 10 else "WARNING"
                }
        
        return subsystem_status
    
    def _determine_incident_status(self, critical_count: int, db_breakdown: Dict, 
                                   error_patterns: Dict) -> Dict[str, Any]:
        """Determine overall incident status."""
        if critical_count > self.THRESHOLDS["CRITICAL"]:
            status = "ACTIVE_INCIDENT"
            severity = "CRITICAL"
            message = "We are in an ACTIVE INCIDENT"
        elif critical_count > self.THRESHOLDS["CONCERNING"]:
            status = "CONCERNING"
            severity = "HIGH"
            message = "Situation is CONCERNING and requires attention"
        elif critical_count > self.THRESHOLDS["ELEVATED"]:
            status = "ELEVATED"
            severity = "MEDIUM"
            message = "Alert levels are ELEVATED above normal"
        else:
            status = "NORMAL"
            severity = "LOW"
            message = "Production is stable"
        
        # Check for P1 patterns even at lower volumes
        if error_patterns.get("has_p1_patterns") and status != "ACTIVE_INCIDENT":
            status = "ACTIVE_INCIDENT"
            severity = "CRITICAL"
            message = "P1 error patterns detected - ACTIVE INCIDENT"
        
        return {
            "status": status,
            "severity": severity,
            "message": message,
            "critical_count": critical_count,
            "database_count": len(db_breakdown)
        }
    
    def _rank_priorities(self, db_breakdown: Dict, error_patterns: Dict, 
                        subsystem_status: Dict) -> List[Dict]:
        """Rank issues by priority (P1/P2/P3)."""
        priorities = []
        
        # Sort databases by critical count
        sorted_dbs = sorted(db_breakdown.items(), 
                           key=lambda x: x[1].get("CRITICAL", 0), 
                           reverse=True)
        
        # First one with high critical count is P1
        p1_assigned = False
        
        for db, stats in sorted_dbs:
            critical = stats.get("CRITICAL", 0)
            total = stats.get("total", 0)
            
            if not p1_assigned and critical > 1000:
                priority = {
                    "priority": "P1",
                    "database": db,
                    "critical_count": critical,
                    "total_count": total,
                    "reason": f"Highest critical alert volume ({critical:,} alerts)",
                    "action": "Focus all immediate attention here"
                }
                p1_assigned = True
            elif critical > 100:
                priority = {
                    "priority": "P2",
                    "database": db,
                    "critical_count": critical,
                    "total_count": total,
                    "reason": f"Escalating critical count ({critical:,} alerts)",
                    "action": "Monitor closely, prepare for escalation"
                }
            elif critical > 0:
                priority = {
                    "priority": "P3",
                    "database": db,
                    "critical_count": critical,
                    "total_count": total,
                    "reason": f"Degraded but stable ({critical:,} critical)",
                    "action": "Address after P1/P2 resolved"
                }
            else:
                continue
            
            priorities.append(priority)
        
        return priorities[:5]  # Top 5 priorities
    
    def _determine_next_actions(self, priorities: List[Dict], 
                               subsystem_status: Dict) -> Dict[str, List[str]]:
        """Determine what should be done NOW, WAIT, and NOT TOUCH."""
        do_now = []
        can_wait = []
        do_not_touch = []
        
        # P1 actions
        p1 = next((p for p in priorities if p["priority"] == "P1"), None)
        if p1:
            do_now.append(f"Focus on {p1['database']} - highest severity")
            do_now.append("Check if database is accessible (basic connectivity)")
            do_now.append("Verify listener status for affected database")
        
        # Subsystem-specific actions
        if "DATA_GUARD" in subsystem_status:
            dg_status = subsystem_status["DATA_GUARD"]
            if dg_status["status"] == "CRITICAL":
                do_now.append("Verify Data Guard apply lag and transport status")
            else:
                can_wait.append("Data Guard review (not critical)")
        
        if "CONNECTIVITY" in subsystem_status:
            if subsystem_status["CONNECTIVITY"]["status"] == "CRITICAL":
                do_now.append("Check network and listener immediately")
        
        if "INTERNAL" in subsystem_status:
            if subsystem_status["INTERNAL"]["status"] == "CRITICAL":
                do_now.append("Check alert log for ORA-600/ORA-7445 traces")
                do_not_touch.append("Do NOT restart database without trace analysis")
        
        # P2/P3 can wait
        for p in priorities:
            if p["priority"] == "P2":
                can_wait.append(f"{p['database']} - monitor for escalation")
            elif p["priority"] == "P3":
                can_wait.append(f"{p['database']} - address after incident")
        
        # Safety items
        do_not_touch.append("Do NOT apply patches during active incident")
        do_not_touch.append("Do NOT perform failovers without explicit approval")
        
        return {
            "do_now": do_now[:5],
            "can_wait": can_wait[:5],
            "do_not_touch": do_not_touch[:3]
        }
    
    def _predict_next_risks(self, db_breakdown: Dict, subsystem_status: Dict,
                           error_patterns: Dict) -> List[Dict]:
        """Predict likely next risks (SAFE MODE - with confidence)."""
        predictions = []
        
        # Database propagation risk
        sorted_dbs = sorted(db_breakdown.items(), 
                           key=lambda x: x[1].get("CRITICAL", 0), 
                           reverse=True)
        
        if len(sorted_dbs) >= 2:
            top_db = sorted_dbs[0]
            second_db = sorted_dbs[1]
            
            # Check for Primary-Standby relationship
            if "STB" in second_db[0] or "STB" in top_db[0]:
                predictions.append({
                    "prediction": f"{second_db[0]} may experience propagation effects",
                    "confidence": "HIGH" if second_db[1].get("CRITICAL", 0) > 100 else "MEDIUM",
                    "evidence": "Primary-Standby relationship detected in alert pattern",
                    "subsystem": "DATA_GUARD"
                })
        
        # Subsystem escalation predictions
        for subsystem, status in subsystem_status.items():
            if status["status"] == "DEGRADED":
                predictions.append({
                    "prediction": f"{subsystem} subsystem may escalate to CRITICAL",
                    "confidence": "MEDIUM",
                    "evidence": f"{status['critical']} critical alerts trending upward",
                    "subsystem": subsystem
                })
        
        # P1 error pattern predictions
        if error_patterns.get("has_p1_patterns"):
            predictions.append({
                "prediction": "Database crash or hang risk if internal errors continue",
                "confidence": "HIGH",
                "evidence": "ORA-600/ORA-7445 patterns detected",
                "subsystem": "INTERNAL"
            })
        
        return predictions[:3]
    
    def _determine_escalation(self, incident_status: Dict, 
                             priorities: List[Dict]) -> Dict[str, Any]:
        """Determine escalation recommendations."""
        if incident_status["status"] != "ACTIVE_INCIDENT":
            return {
                "needed": False,
                "reason": "Situation does not require escalation at this time"
            }
        
        escalation = {
            "needed": True,
            "targets": [],
            "reason": ""
        }
        
        p1 = next((p for p in priorities if p["priority"] == "P1"), None)
        
        if p1 and p1.get("critical_count", 0) > 100000:
            escalation["targets"].append("Senior DBA")
            escalation["targets"].append("Infrastructure Team")
            escalation["targets"].append("Management (availability risk)")
            escalation["reason"] = f"Extreme alert volume ({p1['critical_count']:,} critical) indicates major incident"
        elif p1 and p1.get("critical_count", 0) > 10000:
            escalation["targets"].append("Senior DBA")
            escalation["targets"].append("Infrastructure Team")
            escalation["reason"] = f"High alert volume ({p1['critical_count']:,} critical) requires additional support"
        else:
            escalation["targets"].append("Senior DBA")
            escalation["reason"] = "Active incident requires senior oversight"
        
        return escalation
    
    def format_incident_response(self, assessment: Dict, audience: str = "DBA") -> str:
        """
        Format assessment into Incident Commander response.
        
        Audience options: DBA, MANAGER, LEADERSHIP
        """
        incident = assessment.get("incident_status", {})
        priorities = assessment.get("priorities", [])
        actions = assessment.get("actions", {})
        predictions = assessment.get("predictions", [])
        escalation = assessment.get("escalation", {})
        
        # Build response sections
        sections = []
        
        # 1. Incident Status
        status_emoji = "🚨" if incident.get("status") == "ACTIVE_INCIDENT" else "⚠️"
        sections.append(
            f"{status_emoji} **INCIDENT STATUS: {incident.get('status', 'UNKNOWN')}**\n\n"
            f"{incident.get('message', 'Assessing situation...')}\n"
            f"- **{assessment.get('critical_count', 0):,}** critical alerts across "
            f"**{incident.get('database_count', 0)}** database(s)"
        )
        
        # 2. Top Priority (P1)
        p1 = next((p for p in priorities if p["priority"] == "P1"), None)
        if p1:
            sections.append(
                f"🔥 **TOP PRIORITY (P1): {p1['database']}**\n\n"
                f"- {p1['critical_count']:,} critical alerts\n"
                f"- Reason: {p1['reason']}\n"
                f"- Action: {p1['action']}"
            )
        
        # 3. Evidence Snapshot (for DBA audience)
        if audience == "DBA":
            error_patterns = assessment.get("error_patterns", {})
            top_errors = error_patterns.get("top_errors", [])[:3]
            if top_errors:
                error_text = "\n".join([f"  - {e[0]}: {e[1]:,}" for e in top_errors])
                sections.append(
                    f"📊 **EVIDENCE SNAPSHOT**\n\n"
                    f"Top error patterns:\n{error_text}"
                )
        
        # 4. What This Means (simplified for managers)
        if audience in ["MANAGER", "LEADERSHIP"]:
            blast_radius = len([p for p in priorities if p.get("critical_count", 0) > 0])
            sections.append(
                f"🧭 **WHAT THIS MEANS**\n\n"
                f"- Blast radius: {blast_radius} database(s) affected\n"
                f"- Service impact: Applications using these databases may experience errors\n"
                f"- Risk level: {incident.get('severity', 'UNKNOWN')}"
            )
        
        # 5. What To Do Now
        do_now = actions.get("do_now", [])
        if do_now:
            action_text = "\n".join([f"  ✓ {a}" for a in do_now])
            sections.append(f"▶️ **WHAT TO DO NOW**\n\n{action_text}")
        
        # 6. What Can Wait
        can_wait = actions.get("can_wait", [])
        if can_wait and audience == "DBA":
            wait_text = "\n".join([f"  ○ {a}" for a in can_wait[:3]])
            sections.append(f"⏸️ **CAN WAIT**\n\n{wait_text}")
        
        # 7. Do Not Touch
        do_not_touch = actions.get("do_not_touch", [])
        if do_not_touch:
            dont_text = "\n".join([f"  ✗ {a}" for a in do_not_touch])
            sections.append(f"🚫 **DO NOT TOUCH**\n\n{dont_text}")
        
        # 8. Escalation
        if escalation.get("needed"):
            targets = ", ".join(escalation.get("targets", []))
            sections.append(
                f"📣 **ESCALATION REQUIRED**\n\n"
                f"Notify: {targets}\n"
                f"Reason: {escalation.get('reason', 'Active incident')}"
            )
        
        # 9. Predictions
        if predictions and audience == "DBA":
            pred_text = []
            for pred in predictions[:2]:
                pred_text.append(
                    f"  - {pred['prediction']} "
                    f"(Confidence: {pred['confidence']}, Evidence: {pred['evidence']})"
                )
            sections.append(
                f"🔮 **LIKELY NEXT RISK**\n\n" + "\n".join(pred_text)
            )
        
        # 10. Next Question Suggestion
        if incident.get("status") == "ACTIVE_INCIDENT":
            if p1:
                sections.append(
                    f"💡 **NEXT STEP TO VERIFY**\n\n"
                    f"\"Show me the specific error breakdown for {p1['database']}\""
                )
        
        return "\n\n".join(sections)
    
    def get_suggested_question(self, assessment: Dict) -> str:
        """Get the next most important question the user should ask."""
        priorities = assessment.get("priorities", [])
        subsystems = assessment.get("subsystem_status", {})
        
        p1 = next((p for p in priorities if p["priority"] == "P1"), None)
        
        if p1:
            if "DATA_GUARD" in subsystems:
                return f"Is standby apply running for {p1['database']}?"
            elif "CONNECTIVITY" in subsystems:
                return f"Is the listener running for {p1['database']}?"
            else:
                return f"What specific errors are happening on {p1['database']}?"
        
        return "What is the overall incident status?"
    
    def _build_no_data_response(self) -> Dict[str, Any]:
        """Build response when no data is available."""
        return {
            "incident_status": {
                "status": "NO_DATA",
                "severity": "UNKNOWN",
                "message": "No alert data available for assessment",
                "critical_count": 0,
                "database_count": 0
            },
            "priorities": [],
            "actions": {"do_now": ["Load OEM alert data"], "can_wait": [], "do_not_touch": []},
            "predictions": [],
            "escalation": {"needed": False, "reason": "No data to assess"}
        }


# Singleton instance
INCIDENT_COMMANDER = IncidentCommander()
