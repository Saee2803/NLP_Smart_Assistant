"""
PATTERN RECOGNIZER - Recognizes recurring incident patterns
"""
from datetime import datetime, timedelta
from collections import Counter
from typing import Dict, List
import re
import hashlib


class PatternRecognizer:
    """Recognizes patterns like experienced DBA."""
    
    PATTERNS = {
        "NIGHTLY_BATCH_SPACE": {
            "name": "Nightly Batch Tablespace Exhaustion",
            "codes": ["ORA-1653", "ORA-1654"],
            "time_window": (20, 4),
            "keywords": ["batch", "etl", "tablespace"],
            "resolution": "Add datafile before batch window"
        },
        "WEEKEND_MEMORY": {
            "name": "Weekend Maintenance Memory Pressure",
            "codes": ["ORA-4031"],
            "days": ["Saturday", "Sunday"],
            "keywords": ["memory", "maintenance"],
            "resolution": "Flush shared pool, increase memory for maintenance"
        },
        "NETWORK_INTERMITTENT": {
            "name": "Intermittent Network Issues",
            "codes": ["ORA-12170", "ORA-12154"],
            "keywords": ["listener", "tns", "timeout"],
            "resolution": "Check network stability, restart listener"
        },
        "DATAGUARD_LAG": {
            "name": "Data Guard Lag Pattern",
            "codes": [],
            "keywords": ["lag", "standby", "apply", "sync"],
            "resolution": "Check network, verify redo transport"
        },
        "ORA600_RECURRING": {
            "name": "Recurring Internal Error",
            "codes": ["ORA-600", "ORA-7445"],
            "keywords": ["internal"],
            "resolution": "Apply Oracle patch, search MOS"
        }
    }
    
    def __init__(self):
        self.learned_patterns = {}
    
    def recognize(self, alerts: List[Dict], target: str = None) -> Dict:
        if not alerts:
            return {"pattern_id": None, "confidence": 0}
        
        if target:
            alerts = [a for a in alerts if target.upper() in (a.get("target") or "").upper()]
        
        sig = self._extract_signature(alerts)
        best_match, best_score = None, 0
        
        for pid, pattern in self.PATTERNS.items():
            score = self._match_pattern(sig, pattern)
            if score > best_score:
                best_score, best_match = score, pid
        
        if best_match and best_score > 0.5:
            p = self.PATTERNS[best_match]
            return {
                "pattern_id": best_match,
                "pattern_name": p["name"],
                "confidence": round(best_score, 2),
                "resolution": p["resolution"],
                "signature": sig
            }
        
        return {"pattern_id": None, "confidence": best_score, "signature": sig}
    
    def _extract_signature(self, alerts: List[Dict]) -> Dict:
        codes, keywords, hours = Counter(), Counter(), Counter()
        kw_list = ["tablespace", "memory", "cpu", "network", "listener", "lag", "standby", "batch", "internal"]
        
        for a in alerts:
            msg = (a.get("message") or a.get("alert_message") or "").upper()
            time_str = a.get("alert_time") or a.get("time") or ""
            
            for m in re.findall(r'ORA-\d+', msg):
                codes[m] += 1
            for kw in kw_list:
                if kw.upper() in msg:
                    keywords[kw] += 1
            
            try:
                dt = datetime.strptime(str(time_str)[:19], "%Y-%m-%dT%H:%M:%S")
                hours[dt.hour] += 1
            except:
                pass
        
        return {
            "codes": [c for c, _ in codes.most_common(5)],
            "keywords": [k for k, _ in keywords.most_common(5)],
            "peak_hours": [h for h, _ in hours.most_common(3)],
            "count": len(alerts)
        }
    
    def _match_pattern(self, sig: Dict, pattern: Dict) -> float:
        score = 0
        
        # Code match
        if pattern.get("codes"):
            overlap = len(set(sig["codes"]) & set(pattern["codes"]))
            score += 0.4 * (overlap / len(pattern["codes"])) if overlap else 0
        
        # Keyword match
        if pattern.get("keywords"):
            overlap = len(set(sig["keywords"]) & set(pattern["keywords"]))
            score += 0.4 * (overlap / len(pattern["keywords"])) if overlap else 0
        
        # Time match
        if pattern.get("time_window") and sig.get("peak_hours"):
            start, end = pattern["time_window"]
            night = sum(1 for h in sig["peak_hours"] if h >= start or h <= end)
            score += 0.2 * (night / len(sig["peak_hours"]))
        
        return score
    
    def learn_pattern(self, sig: Dict, resolution: str, name: str = None) -> str:
        pid = "LEARNED_" + hashlib.md5(str(sig).encode()).hexdigest()[:8]
        self.learned_patterns[pid] = {
            "name": name or "Learned Pattern",
            "codes": sig.get("codes", []),
            "keywords": sig.get("keywords", []),
            "resolution": resolution,
            "learned_at": datetime.now().isoformat()
        }
        return pid
