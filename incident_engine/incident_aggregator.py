from collections import defaultdict
from datetime import timedelta
from incident_engine.alert_type_classifier import classify_alert_type, get_alert_group_key


class IncidentAggregator:
    """
    Groups alerts into incidents using TIME-WINDOW based aggregation.
    
    Industry-standard approach:
    - Group alerts by (target, issue_type, severity)
    - Alerts within 10 minutes are SAME incident
    - Time gap > 10 minutes = NEW incident
    - Preserves display_alert_type for DBA-grade display
    
    Python 3.6 compatible:
    - No f-strings
    - Explicit None checks
    - Safe datetime comparisons
    - Deterministic sorting
    """

    # TIME WINDOW: 10 minutes (in seconds)
    TIME_WINDOW_SECONDS = 600

    def __init__(self, alerts):
        """
        Initialize with alerts.
        Python 3.6 safe: explicit None checks, no walrus operators.
        """
        self.alerts = []
        
        if not alerts:
            return
        
        # Filter: only alerts with valid time AND target
        for a in alerts:
            if a is None:
                continue
            
            alert_time = a.get("time")
            target = a.get("target")
            
            # Must have both time and target to participate in aggregation
            if alert_time is not None and target:
                self.alerts.append(a)
        
        # Sort by time (CRITICAL: enables time-window logic)
        # Python 3.6 safe: explicit key function
        try:
            self.alerts.sort(key=lambda a: a["time"])
        except Exception:
            # If sorting fails, keep unsorted (but will affect incident count)
            pass

    # -------------------------------------------------
    # BUILD INCIDENTS WITH TIME-WINDOW LOGIC
    # -------------------------------------------------
    def build_incidents(self):
        """
        Algorithm:
        1. Sort alerts by time
        2. For each alert, check if it can extend previous incident
        3. If time gap > 10 min, create new incident
        4. Otherwise, add to current incident
        
        Python 3.6 safe: no f-strings, explicit None checks
        """
        incidents = []
        
        if not self.alerts:
            return incidents
        
        # Current incident being built
        current_incident = None
        
        for a in self.alerts:
            if a is None:
                continue
            
            # Extract alert properties
            target = a.get("target")
            issue = a.get("issue_type")
            severity = a.get("severity")
            alert_time = a.get("time")
            message = a.get("message")
            
            # Get display_alert_type (derive if not present)
            display_alert_type = a.get("display_alert_type")
            if not display_alert_type:
                display_alert_type = classify_alert_type(issue, message)
            
            # Safety checks (defensive programming)
            if target is None or alert_time is None:
                continue
            
            if issue is None:
                issue = "OTHER"
            
            if severity is None:
                severity = "INFO"
            
            # ===== Check if we can extend current incident =====
            can_extend = False
            
            if current_incident is not None:
                # Must match: target, issue_type, severity (exact match)
                same_group = (
                    current_incident["target"] == target and
                    current_incident["issue_type"] == issue and
                    current_incident["severity"] == severity
                )
                
                if same_group:
                    # Check time window: gap must be <= 10 minutes
                    last_seen = current_incident["last_seen"]
                    
                    if last_seen is not None:
                        time_gap = alert_time - last_seen
                        
                        # Safe timedelta comparison (Python 3.6 compatible)
                        max_gap = timedelta(seconds=self.TIME_WINDOW_SECONDS)
                        
                        if time_gap <= max_gap:
                            can_extend = True
            
            # ===== Extend current incident or create new =====
            if can_extend:
                # Add to current incident
                current_incident["count"] += 1
                current_incident["last_seen"] = alert_time
                # Keep the most specific display_alert_type seen
                if display_alert_type and display_alert_type != current_incident.get("display_alert_type"):
                    # Prefer more specific types (with brackets)
                    if "[" in str(display_alert_type):
                        current_incident["display_alert_type"] = display_alert_type
            else:
                # Save previous incident (if exists)
                if current_incident is not None:
                    incidents.append(current_incident)
                
                # Create new incident with display_alert_type
                current_incident = {
                    "target": target,
                    "issue_type": issue,
                    "display_alert_type": display_alert_type,
                    "severity": severity,
                    "count": 1,
                    "first_seen": alert_time,
                    "last_seen": alert_time,
                }
        
        # Don't forget the last incident
        if current_incident is not None:
            incidents.append(current_incident)
        
        return incidents

