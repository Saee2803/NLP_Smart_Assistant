"""
REASONING ORCHESTRATOR - Orchestrates all reasoning modules
"""
from typing import Dict, List, Optional
from datetime import datetime

from .hypothesis_engine import HypothesisEngine
from .evidence_collector import EvidenceCollector
from .decision_engine import DecisionEngine
from .action_recommender import ActionRecommender
from .pattern_recognizer import PatternRecognizer
from .confidence_scorer import ConfidenceScorer
from .context_tracker import CONTEXT


class ReasoningOrchestrator:
    """
    Main orchestrator - coordinates all reasoning like senior DBA.
    
    Flow:
    1. Generate hypotheses from symptoms
    2. Collect evidence for each hypothesis
    3. Recognize any known patterns
    4. Make decision with confidence scoring
    5. Recommend actions
    6. Update context for follow-ups
    """
    
    def __init__(self, alerts: List[Dict] = None, metrics: List[Dict] = None):
        self.alerts = alerts or []
        self.metrics = metrics or []
        
        # Initialize modules
        self.hypothesis_engine = HypothesisEngine()
        self.evidence_collector = EvidenceCollector()
        self.decision_engine = DecisionEngine()
        self.action_recommender = ActionRecommender()
        self.pattern_recognizer = PatternRecognizer()
        self.confidence_scorer = ConfidenceScorer()
        self.context = CONTEXT
    
    def analyze(self, target: str = None, question: str = None) -> Dict:
        """
        Full analysis pipeline.
        
        Args:
            target: Database target name
            question: User question for context
            
        Returns:
            Complete analysis result
        """
        start = datetime.now()
        
        # Filter alerts by target
        alerts = self.alerts
        if target:
            target_upper = target.upper()
            alerts = [a for a in self.alerts 
                     if target_upper in (a.get("target") or a.get("target_name") or "").upper()]
        
        if not alerts:
            return self._no_data_response(target)
        
        # Step 1: Generate hypotheses
        hypotheses = self.hypothesis_engine.generate_hypotheses(alerts, self.metrics, target)
        
        # Step 2: Collect evidence for each hypothesis
        evidence_packages = {}
        for h in hypotheses[:5]:  # Top 5 only
            h_id = h.get("id") or h.get("pattern")
            evidence = self.evidence_collector.collect_evidence(h, alerts, self.metrics, target)
            evidence_packages[h_id] = evidence
        
        # Step 3: Recognize patterns
        pattern = self.pattern_recognizer.recognize(alerts, target)
        
        # Step 4: Make decision
        decision = self.decision_engine.make_decision(hypotheses, evidence_packages)
        
        # Step 5: Score confidence
        if hypotheses:
            primary_evidence = evidence_packages.get(hypotheses[0].get("id") or hypotheses[0].get("pattern"), {})
            confidence = self.confidence_scorer.score(hypotheses[0], primary_evidence)
        else:
            confidence = {"score": 0, "level": "VERY_LOW"}
        
        # Step 6: Recommend actions
        actions = self.action_recommender.recommend(decision, {"target": target})
        
        # Update context
        self.context.update(
            target=target,
            cause=decision.get("decision"),
            findings={
                "alert_count": len(alerts),
                "hypotheses": len(hypotheses),
                "decision": decision.get("decision")
            }
        )
        
        elapsed = (datetime.now() - start).total_seconds()
        
        return {
            "target": target,
            "alert_count": len(alerts),
            "hypotheses": hypotheses[:5],
            "evidence": evidence_packages,
            "pattern": pattern,
            "decision": decision,
            "confidence": confidence,
            "actions": actions,
            "analysis_time_seconds": round(elapsed, 2),
            "answer": self._build_answer(target, alerts, decision, confidence, actions, pattern)
        }
    
    def quick_analyze(self, target: str) -> Dict:
        """Quick analysis - just root cause and actions."""
        alerts = [a for a in self.alerts 
                 if target.upper() in (a.get("target") or a.get("target_name") or "").upper()]
        
        if not alerts:
            return {"error": "No alerts for {}".format(target)}
        
        hypotheses = self.hypothesis_engine.generate_hypotheses(alerts)
        if not hypotheses:
            return {"error": "Could not generate hypotheses"}
        
        top = hypotheses[0]
        return {
            "target": target,
            "alerts": len(alerts),
            "root_cause": top.get("pattern"),
            "probability": top.get("probability"),
            "actions": self.action_recommender.ACTIONS.get(
                top.get("pattern"), {}).get("immediate", [])[:3]
        }
    
    def get_actions_for_cause(self, cause: str, target: str = None) -> str:
        """Get runbook for a specific cause."""
        decision = {"decision": cause, "action_urgency": "HIGH"}
        return self.action_recommender.generate_runbook(decision, target or "TARGET")
    
    def _no_data_response(self, target: str) -> Dict:
        all_targets = set()
        for a in self.alerts:
            t = (a.get("target") or a.get("target_name") or "").upper()
            if t:
                all_targets.add(t)
        
        return {
            "target": target,
            "alert_count": 0,
            "error": "No alerts found for {}".format(target),
            "available_targets": list(all_targets)[:10],
            "answer": "I don't see any alerts for **{}** in the current dataset. This may indicate the database is healthy, or it's not included in the monitoring scope.{}".format(
                target, 
                " Available databases: {}".format(", ".join(list(all_targets)[:5])) if all_targets else "")
        }
    
    def _build_answer(self, target: str, alerts: List, decision: Dict, 
                     confidence: Dict, actions: Dict, pattern: Dict) -> str:
        """
        Build formatted answer with DBA intelligence.
        
        Uses human-friendly language appropriate for a senior DBA.
        """
        lines = []
        alert_count = len(alerts)
        root_cause = decision.get("decision", "UNKNOWN").replace("_", " ").title()
        conf_level = confidence.get("level", "UNKNOWN")
        
        # Opening with direct assessment (DBA-friendly)
        if target:
            lines.append("**Analysis for {}** ({:,} alerts analyzed)\n".format(target, alert_count))
        else:
            lines.append("**System-Wide Analysis** ({:,} alerts analyzed)\n".format(alert_count))
        
        # Root cause with confidence context
        if conf_level in ["HIGH", "VERY_HIGH"]:
            lines.append("**Likely Root Cause:** {}".format(root_cause))
            lines.append("This determination has high confidence based on the available evidence.")
        elif conf_level == "MEDIUM":
            lines.append("**Probable Cause:** {}".format(root_cause))
            lines.append("This is the most likely explanation based on available data, though further investigation may be needed.")
        else:
            lines.append("**Suspected Cause:** {}".format(root_cause))
            lines.append("Confidence is limited — additional investigation is recommended.")
        
        # Pattern match (if detected)
        if pattern.get("pattern_id"):
            lines.append("\n**Known Pattern Match:** {} ({:.0%} match)".format(
                pattern.get("pattern_name"), pattern.get("confidence", 0)))
            lines.append("This pattern has been seen before and is well-understood.")
        
        # Assessment rationale in DBA language
        rationale = decision.get("rationale", "")
        if rationale:
            lines.append("\n**Assessment:** {}".format(rationale))
        
        # Recommended actions (marked as suggestions)
        immediate = actions.get("immediate_actions", [])[:3]
        if immediate:
            lines.append("\n**Suggested Next Steps:**")
            for i, a in enumerate(immediate, 1):
                action_text = a.get("action", "") if isinstance(a, dict) else str(a)
                lines.append("{}. {}".format(i, action_text))
        
        # Urgency assessment
        urgency = decision.get("action_urgency", "MEDIUM")
        if urgency == "HIGH" or urgency == "CRITICAL":
            lines.append("\n⚠️ **Urgency:** {} — Immediate attention recommended.".format(urgency))
        elif urgency == "MEDIUM":
            lines.append("\n**Urgency:** {} — Review at your earliest convenience.".format(urgency))
        else:
            lines.append("\n**Urgency:** {} — Can be addressed during normal operations.".format(urgency))
        
        # Escalation (if needed)
        if actions.get("escalation"):
            lines.append("\n**Escalation Note:** {}".format(actions["escalation"]))
        
        return "\n".join(lines)

