"""
RISK PREDICTOR - Predicts which database will fail next
"""
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from typing import Dict, List


class RiskPredictor:
    """Predicts failures like experienced DBA."""
    
    # Risk factors and weights
    WEIGHTS = {
        "alert_volume": 0.25,
        "critical_ratio": 0.30,
        "trend": 0.20,
        "pattern_severity": 0.25
    }
    
    CRITICAL_PATTERNS = {
        "INTERNAL_DATABASE_ERROR": 1.0,
        "DATABASE_UNAVAILABLE": 1.0,
        "DATAGUARD_REPLICATION": 0.9,
        "TABLESPACE_EXHAUSTION": 0.8,
        "MEMORY_EXHAUSTION": 0.8,
        "NETWORK_CONNECTIVITY": 0.7,
        "CPU_SATURATION": 0.6
    }
    
    def predict_failures(self, alerts: List[Dict], top_n: int = 5) -> Dict:
        """Predict which databases are at highest risk."""
        
        # Group by database
        db_alerts = defaultdict(list)
        for a in alerts:
            db = (a.get("target") or a.get("target_name") or "UNKNOWN").upper()
            db_alerts[db].append(a)
        
        if not db_alerts:
            return {"predictions": [], "message": "No data"}
        
        # Score each database
        scores = {}
        for db, db_alert_list in db_alerts.items():
            scores[db] = self._calculate_risk(db, db_alert_list, len(alerts))
        
        # Sort by risk
        ranked = sorted(scores.items(), key=lambda x: x[1]["score"], reverse=True)
        
        predictions = []
        for db, data in ranked[:top_n]:
            predictions.append({
                "database": db,
                "risk_score": round(data["score"], 3),
                "risk_level": data["level"],
                "alert_count": data["alert_count"],
                "critical_ratio": data["critical_ratio"],
                "primary_issue": data["primary_issue"],
                "recommendation": self._get_recommendation(data)
            })
        
        return {
            "predictions": predictions,
            "highest_risk": predictions[0] if predictions else None,
            "total_databases": len(db_alerts),
            "generated_at": datetime.now().isoformat()
        }
    
    def _calculate_risk(self, db: str, alerts: List[Dict], total: int) -> Dict:
        """Calculate risk score for a database."""
        count = len(alerts)
        
        # Volume factor (relative to total)
        volume_score = min(count / (total * 0.1), 1.0)  # Normalize
        
        # Critical ratio
        critical = sum(1 for a in alerts 
                      if "CRITICAL" in (a.get("severity") or a.get("alert_state") or "").upper())
        critical_ratio = critical / count if count else 0
        
        # Pattern severity
        issue_types = Counter()
        for a in alerts:
            it = (a.get("issue_type") or "UNKNOWN").upper()
            msg = (a.get("message") or "").upper()
            
            if "ORA-600" in msg or "ORA-7445" in msg:
                issue_types["INTERNAL_DATABASE_ERROR"] += 1
            elif "TABLESPACE" in msg or "ORA-1653" in msg:
                issue_types["TABLESPACE_EXHAUSTION"] += 1
            elif "MEMORY" in msg or "ORA-4031" in msg:
                issue_types["MEMORY_EXHAUSTION"] += 1
            elif "ORA-12" in msg or "LISTENER" in msg:
                issue_types["NETWORK_CONNECTIVITY"] += 1
            elif "STANDBY" in msg or "LAG" in msg:
                issue_types["DATAGUARD_REPLICATION"] += 1
            else:
                issue_types[it] += 1
        
        primary_issue = issue_types.most_common(1)[0][0] if issue_types else "UNKNOWN"
        pattern_score = self.CRITICAL_PATTERNS.get(primary_issue, 0.5)
        
        # Trend (recent vs older) - simplified
        trend_score = 0.5  # Neutral without timestamps
        
        # Weighted score
        final = (
            self.WEIGHTS["alert_volume"] * volume_score +
            self.WEIGHTS["critical_ratio"] * critical_ratio +
            self.WEIGHTS["trend"] * trend_score +
            self.WEIGHTS["pattern_severity"] * pattern_score
        )
        
        # Risk level
        if final >= 0.7:
            level = "CRITICAL"
        elif final >= 0.5:
            level = "HIGH"
        elif final >= 0.3:
            level = "MEDIUM"
        else:
            level = "LOW"
        
        return {
            "score": final,
            "level": level,
            "alert_count": count,
            "critical_ratio": round(critical_ratio * 100, 1),
            "primary_issue": primary_issue,
            "issue_distribution": dict(issue_types.most_common(3))
        }
    
    def _get_recommendation(self, data: Dict) -> str:
        """Get recommendation based on risk."""
        level = data["level"]
        issue = data["primary_issue"]
        
        if level == "CRITICAL":
            return "IMMEDIATE attention required. Review {} alerts.".format(issue)
        elif level == "HIGH":
            return "Schedule urgent review for {} issues.".format(issue)
        elif level == "MEDIUM":
            return "Monitor closely. {} trending up.".format(issue)
        else:
            return "Normal monitoring. No immediate action."
    
    def compare_risk_over_time(self, current: List[Dict], previous: List[Dict]) -> Dict:
        """Compare risk between two time periods."""
        current_pred = self.predict_failures(current)
        previous_pred = self.predict_failures(previous)
        
        current_scores = {p["database"]: p["risk_score"] for p in current_pred["predictions"]}
        previous_scores = {p["database"]: p["risk_score"] for p in previous_pred["predictions"]}
        
        changes = []
        for db in set(current_scores.keys()) | set(previous_scores.keys()):
            curr = current_scores.get(db, 0)
            prev = previous_scores.get(db, 0)
            change = curr - prev
            
            if abs(change) > 0.1:
                changes.append({
                    "database": db,
                    "current_risk": round(curr, 3),
                    "previous_risk": round(prev, 3),
                    "change": round(change, 3),
                    "direction": "INCREASED" if change > 0 else "DECREASED"
                })
        
        return {
            "significant_changes": sorted(changes, key=lambda x: abs(x["change"]), reverse=True),
            "current_highest": current_pred.get("highest_risk"),
            "previous_highest": previous_pred.get("highest_risk")
        }
