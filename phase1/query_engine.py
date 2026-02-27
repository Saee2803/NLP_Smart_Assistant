"""
PHASE 1: Query Engine
=====================
Executes queries against CSV-loaded alert data.

RULES:
- Data source is ONLY from CSV (static dataset)
- No live DB, no API calls, no assumptions
- If data missing → explicitly return empty with reason
- No guessing or inference

SUPPORTED OPERATIONS:
- count: Count alerts matching filters
- list: Get list of alerts matching filters
- status: Get status summary for a database
- fact: Get factual information from data
"""

from typing import Dict, Any, List, Optional
from data_engine.global_cache import GLOBAL_DATA, SYSTEM_READY


class Phase1QueryEngine:
    """
    Query engine for Phase 1 - operates ONLY on CSV-loaded data.
    
    All queries are deterministic and based solely on loaded data.
    No inference, no predictions, no hallucination.
    """
    
    def __init__(self):
        """Initialize the query engine."""
        self._alerts_cache = None
        self._db_list_cache = None
    
    @property
    def alerts(self) -> List[Dict]:
        """Get alerts from global data cache."""
        if self._alerts_cache is None:
            self._alerts_cache = GLOBAL_DATA.get("alerts", [])
        return self._alerts_cache
    
    @property
    def known_databases(self) -> List[str]:
        """Get list of known database names from data."""
        if self._db_list_cache is None:
            dbs = set()
            for alert in self.alerts:
                db = (alert.get("target_name") or alert.get("target") or "").upper()
                if db:
                    dbs.add(db)
            self._db_list_cache = sorted(dbs)
        return self._db_list_cache
    
    def is_ready(self) -> bool:
        """Check if the data is loaded and ready."""
        return SYSTEM_READY.get("ready", False) and len(self.alerts) > 0
    
    def refresh_cache(self):
        """Refresh the internal cache (call after data reload)."""
        self._alerts_cache = None
        self._db_list_cache = None
    
    def execute(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a query based on parsed intent.
        
        Args:
            intent: Structured intent from Phase1IntentParser
            
        Returns:
            Query result with data and metadata
        """
        if not self.is_ready():
            return {
                "success": False,
                "error": "DATA_NOT_LOADED",
                "message": "Alert data is not available. Please wait for system initialization.",
                "data": None
            }
        
        intent_type = intent.get("intent_type", "UNKNOWN")
        
        if intent_type == "UNKNOWN":
            return {
                "success": False,
                "error": "UNKNOWN_INTENT",
                "message": "I don't have enough information to understand this question.",
                "data": None,
                "confidence": intent.get("confidence", 0)
            }
        
        # Apply filters first
        filtered_alerts = self._apply_filters(
            database=intent.get("database"),
            severity=intent.get("severity"),
            category=intent.get("category")
        )
        
        # Execute based on intent type
        if intent_type == "COUNT":
            return self._execute_count(filtered_alerts, intent)
        elif intent_type == "LIST":
            return self._execute_list(filtered_alerts, intent)
        elif intent_type == "STATUS":
            return self._execute_status(filtered_alerts, intent)
        elif intent_type == "FACT":
            return self._execute_fact(filtered_alerts, intent)
        else:
            return {
                "success": False,
                "error": "UNSUPPORTED_INTENT",
                "message": f"Intent type '{intent_type}' is not supported in Phase 1.",
                "data": None
            }
    
    def _apply_filters(
        self,
        database: Optional[str] = None,
        severity: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[Dict]:
        """
        Apply filters to the alert data.
        
        Args:
            database: Database name filter (None = all, "ALL" = all)
            severity: Severity filter (CRITICAL, WARNING, ALL, None)
            category: Category filter (ALERT, STANDBY, DATAGUARD, ALL, None)
            
        Returns:
            Filtered list of alerts
        """
        filtered = self.alerts
        
        # Filter by database
        if database and database != "ALL":
            db_upper = database.upper()
            filtered = [
                a for a in filtered
                if db_upper in (a.get("target_name") or a.get("target") or "").upper()
                or (a.get("target_name") or a.get("target") or "").upper() in db_upper
            ]
        
        # Filter by severity
        if severity and severity != "ALL":
            severity_upper = severity.upper()
            filtered = [
                a for a in filtered
                if (a.get("severity") or a.get("alert_state") or "").upper() == severity_upper
            ]
        
        # Filter by category
        if category and category != "ALL":
            if category == "STANDBY" or category == "DATAGUARD":
                # Standby/DataGuard keywords
                dg_keywords = [
                    "standby", "data guard", "dataguard", "apply lag",
                    "transport lag", "mrp", "redo apply", "ora-16",
                    "physical standby", "replica"
                ]
                filtered = [
                    a for a in filtered
                    if any(kw in (a.get("message") or a.get("msg_text") or "").lower() 
                           for kw in dg_keywords)
                    or any(kw in (a.get("issue_type") or "").lower() 
                           for kw in ["standby", "dataguard"])
                ]
            elif category == "ALERT":
                # General alerts (non-standby)
                pass  # No additional filter needed
        
        return filtered
    
    def _execute_count(self, alerts: List[Dict], intent: Dict) -> Dict[str, Any]:
        """Execute a COUNT query."""
        count = len(alerts)
        
        # Build filter description
        filters = []
        if intent.get("severity"):
            filters.append(intent["severity"])
        if intent.get("category"):
            filters.append(intent["category"].lower())
        if intent.get("database") and intent["database"] != "ALL":
            filters.append(f"for {intent['database']}")
        
        filter_desc = " ".join(filters) if filters else "total"
        
        return {
            "success": True,
            "intent_type": "COUNT",
            "data": {
                "count": count,
                "filter_description": filter_desc,
                "database": intent.get("database"),
                "severity": intent.get("severity"),
                "category": intent.get("category")
            }
        }
    
    def _execute_list(self, alerts: List[Dict], intent: Dict) -> Dict[str, Any]:
        """Execute a LIST query."""
        limit = intent.get("limit") or 20  # Default limit
        
        # Sort by severity (CRITICAL first) then by timestamp if available
        sorted_alerts = sorted(
            alerts,
            key=lambda a: (
                0 if (a.get("severity") or "").upper() == "CRITICAL" else 1,
                a.get("occurred") or a.get("timestamp") or ""
            ),
            reverse=False
        )
        
        limited_alerts = sorted_alerts[:limit]
        
        # Extract relevant fields for display
        result_alerts = []
        for a in limited_alerts:
            result_alerts.append({
                "database": (a.get("target_name") or a.get("target") or "UNKNOWN").upper(),
                "severity": (a.get("severity") or a.get("alert_state") or "UNKNOWN").upper(),
                "message": a.get("message") or a.get("msg_text") or "No message",
                "timestamp": a.get("occurred") or a.get("timestamp") or None,
                "error_code": self._extract_error_code(a.get("message") or a.get("msg_text") or "")
            })
        
        return {
            "success": True,
            "intent_type": "LIST",
            "data": {
                "alerts": result_alerts,
                "total_count": len(alerts),
                "shown_count": len(limited_alerts),
                "limit": limit,
                "database": intent.get("database"),
                "severity": intent.get("severity"),
                "category": intent.get("category")
            }
        }
    
    def _execute_status(self, alerts: List[Dict], intent: Dict) -> Dict[str, Any]:
        """Execute a STATUS query."""
        database = intent.get("database")
        
        if not database or database == "ALL":
            # Status for all databases
            db_stats = {}
            for a in alerts:
                db = (a.get("target_name") or a.get("target") or "UNKNOWN").upper()
                if db not in db_stats:
                    db_stats[db] = {"critical": 0, "warning": 0, "total": 0}
                db_stats[db]["total"] += 1
                sev = (a.get("severity") or a.get("alert_state") or "").upper()
                if sev == "CRITICAL":
                    db_stats[db]["critical"] += 1
                elif sev == "WARNING":
                    db_stats[db]["warning"] += 1
            
            return {
                "success": True,
                "intent_type": "STATUS",
                "data": {
                    "databases": db_stats,
                    "total_alerts": len(alerts),
                    "database_count": len(db_stats)
                }
            }
        else:
            # Status for specific database
            critical = sum(1 for a in alerts 
                          if (a.get("severity") or a.get("alert_state") or "").upper() == "CRITICAL")
            warning = sum(1 for a in alerts 
                         if (a.get("severity") or a.get("alert_state") or "").upper() == "WARNING")
            
            # Determine status
            if critical > 0:
                status = "CRITICAL"
            elif warning > 0:
                status = "WARNING"
            elif len(alerts) > 0:
                status = "INFO"
            else:
                status = "HEALTHY"
            
            return {
                "success": True,
                "intent_type": "STATUS",
                "data": {
                    "database": database,
                    "status": status,
                    "critical_count": critical,
                    "warning_count": warning,
                    "total_alerts": len(alerts)
                }
            }
    
    def _execute_fact(self, alerts: List[Dict], intent: Dict) -> Dict[str, Any]:
        """Execute a FACT query - general factual information."""
        # Count by severity
        severity_counts = {}
        for a in alerts:
            sev = (a.get("severity") or a.get("alert_state") or "UNKNOWN").upper()
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        
        # Count by database
        db_counts = {}
        for a in alerts:
            db = (a.get("target_name") or a.get("target") or "UNKNOWN").upper()
            db_counts[db] = db_counts.get(db, 0) + 1
        
        return {
            "success": True,
            "intent_type": "FACT",
            "data": {
                "total_alerts": len(alerts),
                "severity_breakdown": severity_counts,
                "database_breakdown": db_counts,
                "database": intent.get("database"),
                "severity": intent.get("severity"),
                "category": intent.get("category")
            }
        }
    
    def _extract_error_code(self, message: str) -> Optional[str]:
        """Extract ORA error code from message."""
        import re
        match = re.search(r'ORA-\d+', message.upper())
        return match.group(0) if match else None


# Singleton instance
_engine_instance = None

def get_engine() -> Phase1QueryEngine:
    """Get or create the query engine instance."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = Phase1QueryEngine()
    return _engine_instance


def execute_query(intent: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function to execute a query."""
    engine = get_engine()
    return engine.execute(intent)
