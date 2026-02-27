"""
CONFIDENCE SCORER - Scores confidence in analysis results
"""
from typing import Dict, List
from collections import Counter


class ConfidenceScorer:
    """Scores confidence like cautious DBA."""
    
    def __init__(self):
        self.score_history = []
    
    def score(self, hypothesis: Dict, evidence: Dict, context: Dict = None) -> Dict:
        """Calculate confidence score."""
        factors = {}
        
        # Hypothesis probability
        prob = hypothesis.get("probability", 0.5)
        factors["hypothesis_strength"] = prob
        
        # Evidence strength
        ev_str = evidence.get("evidence_strength", "WEAK")
        ev_map = {"STRONG": 0.9, "MODERATE": 0.7, "WEAK": 0.4, "INSUFFICIENT": 0.2}
        factors["evidence_quality"] = ev_map.get(ev_str, 0.4)
        
        # Evidence quantity
        ev_count = evidence.get("evidence_count", 0)
        factors["evidence_quantity"] = min(ev_count / 10, 1.0)
        
        # Contradictions penalty
        contradictions = len(evidence.get("contradictions", []))
        factors["contradiction_penalty"] = max(0, 1 - (contradictions * 0.15))
        
        # Calculate final score
        weights = {
            "hypothesis_strength": 0.3,
            "evidence_quality": 0.35,
            "evidence_quantity": 0.2,
            "contradiction_penalty": 0.15
        }
        
        final = sum(factors[k] * weights[k] for k in weights)
        
        # Determine level
        if final >= 0.8:
            level = "HIGH"
        elif final >= 0.6:
            level = "MEDIUM"
        elif final >= 0.4:
            level = "LOW"
        else:
            level = "VERY_LOW"
        
        result = {
            "score": round(final, 2),
            "level": level,
            "factors": {k: round(v, 2) for k, v in factors.items()},
            "recommendation": self._get_recommendation(level)
        }
        
        self.score_history.append(result)
        return result
    
    def _get_recommendation(self, level: str) -> str:
        recs = {
            "HIGH": "Proceed with recommended actions",
            "MEDIUM": "Verify key evidence before acting",
            "LOW": "Gather more evidence",
            "VERY_LOW": "Investigation inconclusive - escalate"
        }
        return recs.get(level, "Review analysis")
    
    def aggregate_scores(self, scores: List[Dict]) -> Dict:
        """Aggregate multiple scores."""
        if not scores:
            return {"aggregate": 0, "level": "UNKNOWN"}
        
        values = [s.get("score", 0) for s in scores]
        avg = sum(values) / len(values)
        
        return {
            "aggregate": round(avg, 2),
            "min": round(min(values), 2),
            "max": round(max(values), 2),
            "count": len(scores)
        }
