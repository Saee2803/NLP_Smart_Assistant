"""
ANSWER FORMATTER - Formats answers consistently
"""
from typing import Dict, List, Optional


class AnswerFormatter:
    """Formats answers in consistent DBA style."""
    
    @staticmethod
    def format_analysis(summary: str, checked: List[str], findings: List[str],
                       assessment: str, actions: List[str], stats: Dict = None) -> str:
        """Build structured answer."""
        lines = []
        
        lines.append("**{}**\n".format(summary))
        
        if stats:
            lines.append("**Data Analyzed:**")
            for k, v in stats.items():
                lines.append("- {}: {:,}".format(k.replace("_", " ").title(), v) 
                           if isinstance(v, int) else "- {}: {}".format(k.replace("_", " ").title(), v))
            lines.append("")
        
        if findings:
            lines.append("**Key Findings:**")
            for f in findings[:7]:
                lines.append("- {}".format(f))
            lines.append("")
        
        if assessment:
            lines.append("**Assessment:** {}\n".format(assessment))
        
        if actions:
            lines.append("**Recommended Actions:**")
            for i, a in enumerate(actions[:5], 1):
                lines.append("{}. {}".format(i, a))
        
        return "\n".join(lines)
    
    @staticmethod
    def format_no_data(query_type: str, searched: str, 
                       alternatives: List[str] = None) -> str:
        """Format no-data response with alternatives."""
        lines = [
            "**No {} Found**\n".format(query_type),
            "**Searched:** {}".format(searched)
        ]
        
        if alternatives:
            lines.append("\n**Available:**")
            for alt in alternatives[:5]:
                lines.append("- {}".format(alt))
        
        return "\n".join(lines)
    
    @staticmethod
    def format_comparison(title: str, items: List[Dict], 
                         value_field: str = "count") -> str:
        """Format comparison table."""
        lines = ["**{}**\n".format(title)]
        
        for i, item in enumerate(items[:10], 1):
            name = item.get("name", item.get("database", item.get("target", "Unknown")))
            value = item.get(value_field, item.get("count", 0))
            pct = item.get("percentage", "")
            
            if pct:
                lines.append("{}. **{}**: {:,} ({}%)".format(i, name, value, pct))
            else:
                lines.append("{}. **{}**: {:,}".format(i, name, value))
        
        return "\n".join(lines)
    
    @staticmethod
    def format_decision(decision: Dict) -> str:
        """Format decision summary."""
        lines = [
            "**Decision: {}**".format(decision.get("decision", "UNKNOWN").replace("_", " ").title()),
            "- Confidence: {:.0%}".format(decision.get("confidence", 0)),
            "- Certainty: {}".format(decision.get("certainty", "UNKNOWN")),
            "- Urgency: {}".format(decision.get("action_urgency", "MEDIUM")),
            "",
            "**Rationale:** {}".format(decision.get("rationale", ""))
        ]
        
        alts = decision.get("alternatives", [])
        if alts:
            lines.append("\n**Alternatives Considered:**")
            for a in alts[:3]:
                lines.append("- {}: {:.0%}".format(a.get("cause", ""), a.get("score", 0)))
        
        return "\n".join(lines)
    
    @staticmethod
    def format_runbook(title: str, steps: List[Dict], 
                       escalation: str = None) -> str:
        """Format runbook."""
        lines = [
            "=" * 50,
            "RUNBOOK: {}".format(title),
            "=" * 50,
            ""
        ]
        
        for i, step in enumerate(steps, 1):
            lines.append("## Step {}: {}".format(i, step.get("action", "")))
            if step.get("command"):
                lines.append("```")
                lines.append(step["command"])
                lines.append("```")
            if step.get("expected"):
                lines.append("Expected: {}".format(step["expected"]))
            lines.append("")
        
        if escalation:
            lines.append("## ESCALATION")
            lines.append(escalation)
        
        return "\n".join(lines)
    
    @staticmethod
    def format_prediction(prediction: Dict) -> str:
        """Format failure prediction."""
        lines = ["**Failure Prediction Analysis**\n"]
        
        if prediction.get("highest_risk"):
            hr = prediction["highest_risk"]
            lines.append("**Highest Risk:** {} (Score: {:.3f})".format(
                hr.get("database"), hr.get("risk_score", 0)))
            lines.append("- Risk Level: {}".format(hr.get("risk_level")))
            lines.append("- Primary Issue: {}".format(hr.get("primary_issue")))
            lines.append("- Recommendation: {}".format(hr.get("recommendation")))
        
        preds = prediction.get("predictions", [])
        if len(preds) > 1:
            lines.append("\n**Other At-Risk Databases:**")
            for p in preds[1:5]:
                lines.append("- {}: {} ({})".format(
                    p.get("database"), p.get("risk_level"), p.get("primary_issue")))
        
        return "\n".join(lines)
