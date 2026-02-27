"""
DECISION ENGINE

Purpose:
    Makes final decisions by weighing hypotheses against evidence.
    A senior DBA doesn't just report findings - they make decisions.

Algorithm:
    1. Collect all hypotheses with their evidence
    2. Apply decision rules (confidence thresholds, risk weights)
    3. Select best hypothesis or declare inconclusive
    4. Generate decision rationale

Function Signatures:
    make_decision(hypotheses: List[Dict], evidence: Dict) -> Decision
    apply_decision_rules(candidates: List[Dict]) -> RankedDecisions
    generate_rationale(decision: Dict) -> str

Example Output:
    {
        "decision": "TABLESPACE_EXHAUSTION",
        "confidence": 0.89,
        "rationale": "Strong evidence: ORA-1653 (47 occurrences), storage at 98.7%",
        "action_urgency": "HIGH",
        "alternatives_considered": ["MEMORY_ISSUE", "INTERNAL_ERROR"],
        "decision_factors": {
            "evidence_strength": 0.92,
            "hypothesis_probability": 0.85,
            "risk_severity": 0.90
        }
    }
"""

from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import re


class DecisionEngine:
    """
    Makes decisions like a senior DBA with years of experience.
    """
    
    # Decision thresholds
    HIGH_CONFIDENCE_THRESHOLD = 0.75
    MEDIUM_CONFIDENCE_THRESHOLD = 0.50
    MINIMUM_EVIDENCE_ITEMS = 2
    
    # Risk multipliers by issue type
    RISK_MULTIPLIERS = {
        "INTERNAL_DATABASE_ERROR": 1.5,      # ORA-600 is always serious
        "DATABASE_UNAVAILABLE": 2.0,          # DB down is critical
        "DATAGUARD_REPLICATION": 1.3,         # DR issues need attention
        "TABLESPACE_EXHAUSTION": 1.2,         # Space issues escalate
        "MEMORY_EXHAUSTION": 1.2,             # Memory can cause crashes
        "NETWORK_CONNECTIVITY": 1.1,          # Network affects availability
        "CPU_SATURATION": 1.0,                # CPU is often recoverable
        "LOCK_CONTENTION": 1.0,               # Locks usually resolve
        "OTHER": 0.8                          # Generic issues lower priority
    }
    
    # Decision rules
    DECISION_RULES = {
        "DEFINITIVE": {
            "min_confidence": 0.80,
            "min_evidence_items": 3,
            "max_alternatives_close": 0  # No close alternatives
        },
        "PROBABLE": {
            "min_confidence": 0.60,
            "min_evidence_items": 2,
            "max_alternatives_close": 2
        },
        "POSSIBLE": {
            "min_confidence": 0.40,
            "min_evidence_items": 1,
            "max_alternatives_close": 3
        },
        "INCONCLUSIVE": {
            "min_confidence": 0.0,
            "min_evidence_items": 0,
            "max_alternatives_close": 999
        }
    }
    
    def __init__(self):
        """Initialize decision engine."""
        self.decision_history = []
        self.rule_applications = []
    
    def make_decision(self,
                     hypotheses: List[Dict],
                     evidence_packages: Dict[str, Dict] = None,
                     context: Dict = None) -> Dict:
        """
        Make a decision from hypotheses and evidence.
        
        Args:
            hypotheses: Ranked list of hypotheses
            evidence_packages: Evidence for each hypothesis
            context: Additional context (target, time, etc.)
            
        Returns:
            Decision dictionary with rationale
        """
        if not hypotheses:
            return self._create_inconclusive_decision("No hypotheses generated")
        
        # Score each hypothesis with evidence
        scored_candidates = []
        for h in hypotheses:
            h_id = h.get("id") or h.get("pattern")
            evidence = evidence_packages.get(h_id, {}) if evidence_packages else {}
            
            score = self._calculate_decision_score(h, evidence)
            scored_candidates.append({
                "hypothesis": h,
                "evidence": evidence,
                "decision_score": score
            })
        
        # Sort by decision score
        scored_candidates.sort(key=lambda x: x["decision_score"], reverse=True)
        
        # Apply decision rules
        decision = self._apply_decision_rules(scored_candidates)
        
        # Add context
        if context:
            decision["context"] = {
                "target": context.get("target"),
                "time_range": context.get("time_range"),
                "analyzed_at": datetime.now().isoformat()
            }
        
        # Store in history
        self.decision_history.append(decision)
        
        return decision
    
    def _calculate_decision_score(self, 
                                  hypothesis: Dict, 
                                  evidence: Dict) -> float:
        """Calculate composite decision score."""
        # Base probability
        prob = hypothesis.get("probability", 0.5)
        
        # Evidence strength factor
        evidence_strength = evidence.get("evidence_strength", "WEAK")
        strength_multipliers = {
            "STRONG": 1.3,
            "MODERATE": 1.0,
            "WEAK": 0.7,
            "INSUFFICIENT": 0.4
        }
        evidence_factor = strength_multipliers.get(evidence_strength, 0.7)
        
        # Evidence count factor
        evidence_count = evidence.get("evidence_count", 0)
        count_factor = min(1.0 + (evidence_count * 0.05), 1.5)
        
        # Risk multiplier based on issue type
        pattern = hypothesis.get("pattern", "OTHER")
        risk_mult = self.RISK_MULTIPLIERS.get(pattern, 1.0)
        
        # Contradiction penalty
        contradictions = len(evidence.get("contradictions", []))
        contradiction_penalty = contradictions * 0.1
        
        # Final score
        score = (prob * evidence_factor * count_factor * risk_mult) - contradiction_penalty
        
        return min(max(score, 0.0), 1.0)  # Clamp to [0, 1]
    
    def _apply_decision_rules(self, candidates: List[Dict]) -> Dict:
        """Apply decision rules to select best candidate."""
        if not candidates:
            return self._create_inconclusive_decision("No candidates")
        
        best = candidates[0]
        best_score = best["decision_score"]
        best_hyp = best["hypothesis"]
        
        # Check how close alternatives are
        close_alternatives = []
        for c in candidates[1:5]:  # Check top 5
            if c["decision_score"] > best_score * 0.8:  # Within 80%
                close_alternatives.append(c)
        
        # Determine decision certainty
        evidence_count = best.get("evidence", {}).get("evidence_count", 0)
        
        if best_score >= self.DECISION_RULES["DEFINITIVE"]["min_confidence"] and \
           evidence_count >= self.DECISION_RULES["DEFINITIVE"]["min_evidence_items"] and \
           len(close_alternatives) <= self.DECISION_RULES["DEFINITIVE"]["max_alternatives_close"]:
            certainty = "DEFINITIVE"
        elif best_score >= self.DECISION_RULES["PROBABLE"]["min_confidence"] and \
             evidence_count >= self.DECISION_RULES["PROBABLE"]["min_evidence_items"]:
            certainty = "PROBABLE"
        elif best_score >= self.DECISION_RULES["POSSIBLE"]["min_confidence"]:
            certainty = "POSSIBLE"
        else:
            certainty = "INCONCLUSIVE"
        
        # Build decision
        decision = {
            "decision": best_hyp.get("pattern") or best_hyp.get("title"),
            "confidence": round(best_score, 2),
            "certainty": certainty,
            "rationale": self._generate_rationale(best, close_alternatives),
            "action_urgency": self._determine_urgency(best_hyp, best_score),
            "alternatives_considered": [
                {
                    "cause": c["hypothesis"].get("pattern"),
                    "score": round(c["decision_score"], 2)
                } for c in close_alternatives[:3]
            ],
            "decision_factors": {
                "hypothesis_probability": best_hyp.get("probability", 0),
                "evidence_strength": best.get("evidence", {}).get("evidence_strength", "UNKNOWN"),
                "evidence_count": evidence_count,
                "risk_multiplier": self.RISK_MULTIPLIERS.get(
                    best_hyp.get("pattern", "OTHER"), 1.0)
            },
            "primary_evidence": best.get("evidence", {}).get("evidence_items", [])[:5],
            "contradictions": best.get("evidence", {}).get("contradictions", [])
        }
        
        return decision
    
    def _generate_rationale(self, 
                           best: Dict, 
                           alternatives: List[Dict]) -> str:
        """Generate human-readable decision rationale."""
        hyp = best["hypothesis"]
        evidence = best.get("evidence", {})
        
        pattern = hyp.get("pattern", "UNKNOWN")
        prob = hyp.get("probability", 0)
        
        # Build rationale parts
        parts = []
        
        # Main decision reason
        parts.append("Selected {} (confidence: {:.0%})".format(
            pattern.replace("_", " ").title(), best["decision_score"]))
        
        # Evidence summary
        evidence_items = evidence.get("evidence_items", [])
        if evidence_items:
            top_evidence = [e.get("item", "") for e in evidence_items[:3]]
            parts.append("Key evidence: {}".format("; ".join(top_evidence)))
        
        # Why not alternatives
        if alternatives:
            alt_names = [a["hypothesis"].get("pattern", "") for a in alternatives[:2]]
            parts.append("Ruled out: {} (lower evidence support)".format(
                ", ".join(alt_names)))
        
        # Hypothesis support
        evidence_for = hyp.get("evidence_for", [])
        if evidence_for:
            parts.append("Supporting factors: {}".format(
                ", ".join(evidence_for[:2])))
        
        return ". ".join(parts)
    
    def _determine_urgency(self, hypothesis: Dict, score: float) -> str:
        """Determine action urgency based on decision."""
        pattern = hypothesis.get("pattern", "")
        
        # Critical patterns are always urgent
        critical_patterns = [
            "DATABASE_UNAVAILABLE", "INTERNAL_DATABASE_ERROR",
            "DATAGUARD_REPLICATION"
        ]
        
        if pattern in critical_patterns:
            return "CRITICAL"
        
        # High score + certain patterns = HIGH
        high_patterns = [
            "TABLESPACE_EXHAUSTION", "MEMORY_EXHAUSTION",
            "NETWORK_CONNECTIVITY"
        ]
        
        if pattern in high_patterns and score > 0.7:
            return "HIGH"
        
        if score > 0.6:
            return "MEDIUM"
        
        return "LOW"
    
    def _create_inconclusive_decision(self, reason: str) -> Dict:
        """Create an inconclusive decision response."""
        return {
            "decision": "INCONCLUSIVE",
            "confidence": 0.0,
            "certainty": "INCONCLUSIVE",
            "rationale": "Unable to make decision: {}".format(reason),
            "action_urgency": "LOW",
            "alternatives_considered": [],
            "decision_factors": {},
            "recommendation": "Gather more evidence or provide additional context"
        }
    
    def compare_decisions(self, 
                         decisions: List[Dict]) -> Dict:
        """
        Compare multiple decisions (e.g., across time periods or databases).
        
        Args:
            decisions: List of decision dictionaries
            
        Returns:
            Comparison summary
        """
        if not decisions:
            return {"comparison": "No decisions to compare"}
        
        # Group by decision type
        by_type = defaultdict(list)
        for d in decisions:
            by_type[d.get("decision", "UNKNOWN")].append(d)
        
        # Find most common
        most_common = max(by_type.items(), key=lambda x: len(x[1]))
        
        # Calculate average confidence
        confidences = [d.get("confidence", 0) for d in decisions]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        # Find agreement level
        total = len(decisions)
        max_agreement = len(most_common[1])
        agreement_pct = max_agreement / total if total > 0 else 0
        
        return {
            "total_decisions": total,
            "dominant_cause": most_common[0],
            "dominance_ratio": round(agreement_pct, 2),
            "average_confidence": round(avg_confidence, 2),
            "cause_distribution": {k: len(v) for k, v in by_type.items()},
            "consensus": "STRONG" if agreement_pct > 0.7 else "MODERATE" if agreement_pct > 0.5 else "WEAK"
        }
    
    def explain_decision(self, decision: Dict) -> str:
        """
        Generate detailed explanation of a decision.
        
        Args:
            decision: Decision dictionary
            
        Returns:
            Formatted explanation string
        """
        lines = []
        
        lines.append("=" * 60)
        lines.append("DECISION EXPLANATION")
        lines.append("=" * 60)
        
        # Main decision
        lines.append("\n**Primary Diagnosis:** {}".format(
            decision.get("decision", "UNKNOWN").replace("_", " ").title()))
        lines.append("**Confidence:** {:.0%}".format(decision.get("confidence", 0)))
        lines.append("**Certainty Level:** {}".format(decision.get("certainty", "UNKNOWN")))
        lines.append("**Action Urgency:** {}".format(decision.get("action_urgency", "UNKNOWN")))
        
        # Rationale
        lines.append("\n**Rationale:**")
        lines.append(decision.get("rationale", "No rationale provided"))
        
        # Evidence
        primary_evidence = decision.get("primary_evidence", [])
        if primary_evidence:
            lines.append("\n**Supporting Evidence:**")
            for i, e in enumerate(primary_evidence[:5], 1):
                item = e.get("item", str(e))
                weight = e.get("weight", 0)
                lines.append("  {}. {} (weight: {:.2f})".format(i, item, weight))
        
        # Contradictions
        contradictions = decision.get("contradictions", [])
        if contradictions:
            lines.append("\n**Contradicting Evidence:**")
            for c in contradictions[:3]:
                lines.append("  - {}".format(c.get("item", str(c))))
        
        # Alternatives
        alternatives = decision.get("alternatives_considered", [])
        if alternatives:
            lines.append("\n**Alternatives Considered:**")
            for alt in alternatives:
                lines.append("  - {}: {:.0%} confidence".format(
                    alt.get("cause", "Unknown"), alt.get("score", 0)))
        
        # Decision factors
        factors = decision.get("decision_factors", {})
        if factors:
            lines.append("\n**Decision Factors:**")
            for factor, value in factors.items():
                lines.append("  - {}: {}".format(
                    factor.replace("_", " ").title(), value))
        
        lines.append("\n" + "=" * 60)
        
        return "\n".join(lines)


class DecisionValidator:
    """
    Validates decisions against historical outcomes.
    """
    
    def __init__(self):
        self.validation_history = []
    
    def validate_decision(self,
                         decision: Dict,
                         actual_outcome: str = None) -> Dict:
        """
        Validate a decision against actual outcome.
        
        Args:
            decision: Decision dictionary
            actual_outcome: What actually happened (if known)
            
        Returns:
            Validation result
        """
        validation = {
            "decision": decision.get("decision"),
            "confidence": decision.get("confidence"),
            "timestamp": datetime.now().isoformat()
        }
        
        # Basic validation checks
        issues = []
        
        # Check confidence vs certainty alignment
        confidence = decision.get("confidence", 0)
        certainty = decision.get("certainty", "")
        
        if confidence > 0.8 and certainty not in ["DEFINITIVE", "PROBABLE"]:
            issues.append("High confidence with low certainty - review evidence")
        
        if confidence < 0.5 and decision.get("action_urgency") == "CRITICAL":
            issues.append("Low confidence with critical urgency - gather more evidence")
        
        # Check evidence support
        evidence_count = decision.get("decision_factors", {}).get("evidence_count", 0)
        if confidence > 0.7 and evidence_count < 2:
            issues.append("High confidence with minimal evidence")
        
        # Check for contradictions
        contradictions = decision.get("contradictions", [])
        if len(contradictions) > 2 and certainty == "DEFINITIVE":
            issues.append("Multiple contradictions with definitive certainty")
        
        validation["issues"] = issues
        validation["is_valid"] = len(issues) == 0
        
        # Compare to actual if provided
        if actual_outcome:
            validation["actual_outcome"] = actual_outcome
            validation["was_correct"] = decision.get("decision") == actual_outcome
        
        self.validation_history.append(validation)
        
        return validation
    
    def get_accuracy_metrics(self) -> Dict:
        """Get accuracy metrics from validation history."""
        if not self.validation_history:
            return {"message": "No validation history"}
        
        validated = [v for v in self.validation_history if "was_correct" in v]
        
        if not validated:
            return {"message": "No outcomes recorded for validation"}
        
        correct = sum(1 for v in validated if v["was_correct"])
        total = len(validated)
        
        return {
            "total_validated": total,
            "correct": correct,
            "accuracy": round(correct / total, 2) if total > 0 else 0,
            "by_confidence": self._accuracy_by_confidence(validated)
        }
    
    def _accuracy_by_confidence(self, validated: List[Dict]) -> Dict:
        """Calculate accuracy by confidence band."""
        bands = {
            "high": {"correct": 0, "total": 0},     # > 0.7
            "medium": {"correct": 0, "total": 0},   # 0.4-0.7
            "low": {"correct": 0, "total": 0}       # < 0.4
        }
        
        for v in validated:
            conf = v.get("confidence", 0)
            if conf > 0.7:
                band = "high"
            elif conf > 0.4:
                band = "medium"
            else:
                band = "low"
            
            bands[band]["total"] += 1
            if v.get("was_correct"):
                bands[band]["correct"] += 1
        
        return {
            band: {
                "accuracy": round(data["correct"] / data["total"], 2) if data["total"] > 0 else 0,
                "total": data["total"]
            }
            for band, data in bands.items()
        }
