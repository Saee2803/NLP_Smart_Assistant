# reasoning/evidence_layer.py
"""
PHASE 7: EVIDENCE-BACKED EXPLANATION LAYER

Every non-trivial answer MUST include:
1. What we see (the facts)
2. Why it matters (the interpretation)
3. Evidence from data (the proof)

This ensures:
- DBA trusts the answer (can verify)
- Manager understands impact
- Auditor can trace the logic

TRUST PRINCIPLE: Explain before advising.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import Counter


@dataclass
class EvidenceItem:
    """A single piece of evidence supporting an answer."""
    fact: str  # What the data shows
    source: str  # Where it came from
    value: str  # The actual value/number
    relevance: str  # Why this matters
    
    def to_display(self) -> str:
        return "- **{}**: {} (Source: {})".format(self.fact, self.value, self.source)
    
    def to_audit(self) -> Dict:
        return {
            "fact": self.fact,
            "source": self.source,
            "value": self.value,
            "relevance": self.relevance
        }


@dataclass
class EvidencePackage:
    """Complete evidence package for an answer."""
    what_we_see: str  # Summary of observations
    why_it_matters: str  # Interpretation and impact
    evidence_items: List[EvidenceItem] = field(default_factory=list)
    data_sources: List[str] = field(default_factory=list)
    analysis_steps: List[str] = field(default_factory=list)
    
    def to_display(self) -> str:
        """Format for user display."""
        lines = []
        
        # What we see
        lines.append("### 🔍 What We See")
        lines.append(self.what_we_see)
        lines.append("")
        
        # Why it matters
        lines.append("### ⚠️ Why It Matters")
        lines.append(self.why_it_matters)
        lines.append("")
        
        # Evidence
        if self.evidence_items:
            lines.append("### 📊 Evidence")
            for item in self.evidence_items[:5]:  # Limit to 5 for readability
                lines.append(item.to_display())
        
        return "\n".join(lines)
    
    def to_audit(self) -> Dict:
        """Format for audit trail."""
        return {
            "what_we_see": self.what_we_see,
            "why_it_matters": self.why_it_matters,
            "evidence_items": [e.to_audit() for e in self.evidence_items],
            "data_sources": self.data_sources,
            "analysis_steps": self.analysis_steps
        }


class EvidenceLayer:
    """
    Builds evidence-backed explanations for any answer.
    
    TRUST PRINCIPLE: The DBA must understand WHY before WHAT to do.
    """
    
    def __init__(self):
        self._evidence_cache = {}
    
    def build_count_evidence(
        self,
        count: int,
        entity_type: str,
        database: str = None,
        severity: str = None,
        breakdown: Dict[str, int] = None
    ) -> EvidencePackage:
        """
        Build evidence for a count-type answer.
        
        Example: "How many critical alerts for MIDEVSTB?"
        """
        # What we see
        what_we_see_parts = []
        if database:
            what_we_see_parts.append("**{:,}** {} for **{}**".format(count, entity_type, database))
        else:
            what_we_see_parts.append("**{:,}** {} across all databases".format(count, entity_type))
        
        if severity:
            what_we_see_parts.append("Filtered by severity: {}".format(severity))
        
        what_we_see = ". ".join(what_we_see_parts)
        
        # Why it matters
        if count > 100000:
            why_matters = "This is an extremely high volume. However, high count does not necessarily mean high risk - many alerts may be repeated instances of the same issue."
        elif count > 10000:
            why_matters = "This is a significant volume. Investigation is warranted to determine if these represent unique incidents or alert flooding."
        elif count > 1000:
            why_matters = "This is a moderate volume. Worth monitoring for patterns."
        elif count > 0:
            why_matters = "This is a manageable volume. Normal operations can proceed with routine monitoring."
        else:
            why_matters = "No {} found matching the criteria.".format(entity_type)
        
        # Evidence items
        evidence_items = []
        evidence_items.append(EvidenceItem(
            fact="Total Count",
            source="CSV alert data",
            value="{:,}".format(count),
            relevance="Direct count from source data"
        ))
        
        if breakdown:
            for key, val in list(breakdown.items())[:3]:
                evidence_items.append(EvidenceItem(
                    fact=key,
                    source="CSV aggregation",
                    value="{:,}".format(val),
                    relevance="Breakdown by {}".format(key)
                ))
        
        return EvidencePackage(
            what_we_see=what_we_see,
            why_it_matters=why_matters,
            evidence_items=evidence_items,
            data_sources=["CSV alert data"],
            analysis_steps=["Count aggregation", "Severity filter" if severity else "No filter"]
        )
    
    def build_incident_evidence(
        self,
        total_alerts: int,
        unique_incidents: int,
        top_incident: str = None,
        incident_pattern: str = None
    ) -> EvidencePackage:
        """
        Build evidence for incident analysis.
        
        Key insight: 100,000 alerts ≠ 100,000 incidents
        """
        # What we see
        if unique_incidents == 1:
            what_we_see = "**{:,} alerts** clustered into **1 unique incident**".format(total_alerts)
        else:
            what_we_see = "**{:,} alerts** clustered into **{:,} unique incidents**".format(
                total_alerts, unique_incidents
            )
        
        # Why it matters - THIS IS THE KEY INSIGHT
        ratio = total_alerts / max(unique_incidents, 1)
        if ratio > 1000:
            why_matters = (
                "This indicates **alert flooding** rather than multiple independent failures. "
                "The same underlying issue is generating repeated alerts. "
                "Focus on resolving the root cause, not each individual alert."
            )
        elif ratio > 100:
            why_matters = (
                "Significant alert repetition detected. "
                "A few core issues are generating many alerts. "
                "Prioritize the highest-frequency incidents."
            )
        elif ratio > 10:
            why_matters = (
                "Moderate alert clustering. "
                "Some incidents are generating multiple alerts. "
                "Standard incident triage applies."
            )
        else:
            why_matters = (
                "Each alert roughly corresponds to a unique incident. "
                "This suggests diverse, independent issues."
            )
        
        # Evidence items
        evidence_items = [
            EvidenceItem(
                fact="Total Alerts",
                source="CSV data",
                value="{:,}".format(total_alerts),
                relevance="Raw alert count"
            ),
            EvidenceItem(
                fact="Unique Incidents",
                source="Incident clustering",
                value="{:,}".format(unique_incidents),
                relevance="Deduplicated incident count"
            ),
            EvidenceItem(
                fact="Alert-to-Incident Ratio",
                source="Computed",
                value="{:.0f}:1".format(ratio),
                relevance="Indicates alert flooding level"
            )
        ]
        
        if top_incident:
            evidence_items.append(EvidenceItem(
                fact="Top Incident",
                source="Frequency analysis",
                value=top_incident,
                relevance="Highest-frequency incident"
            ))
        
        if incident_pattern:
            evidence_items.append(EvidenceItem(
                fact="Pattern",
                source="Temporal analysis",
                value=incident_pattern,
                relevance="Incident trajectory"
            ))
        
        return EvidencePackage(
            what_we_see=what_we_see,
            why_it_matters=why_matters,
            evidence_items=evidence_items,
            data_sources=["CSV alert data", "Incident clustering engine"],
            analysis_steps=[
                "Alert ingestion",
                "Signature-based clustering",
                "Deduplication",
                "Pattern analysis"
            ]
        )
    
    def build_root_cause_evidence(
        self,
        root_cause: str,
        confidence: float,
        supporting_evidence: List[str],
        ora_codes: List[Dict] = None
    ) -> EvidencePackage:
        """
        Build evidence for root cause analysis.
        """
        # What we see
        what_we_see = "Primary root cause identified: **{}**".format(root_cause)
        
        # Why it matters
        if confidence >= 0.8:
            why_matters = "This root cause has strong evidence support. Recommended for immediate investigation."
        elif confidence >= 0.5:
            why_matters = "This root cause has moderate evidence support. Consider as primary hypothesis but verify."
        else:
            why_matters = "This is a possible root cause but evidence is weak. Multiple hypotheses should be considered."
        
        # Evidence items
        evidence_items = []
        for i, ev in enumerate(supporting_evidence[:5]):
            evidence_items.append(EvidenceItem(
                fact="Evidence {}".format(i + 1),
                source="Alert analysis",
                value=ev,
                relevance="Supports root cause hypothesis"
            ))
        
        if ora_codes:
            for ora in ora_codes[:3]:
                evidence_items.append(EvidenceItem(
                    fact="ORA Code",
                    source="Error extraction",
                    value="{} ({:,} occurrences)".format(
                        ora.get("code", "Unknown"),
                        ora.get("count", 0)
                    ),
                    relevance="Error frequency indicator"
                ))
        
        return EvidencePackage(
            what_we_see=what_we_see,
            why_it_matters=why_matters,
            evidence_items=evidence_items,
            data_sources=["CSV alert data", "ORA code extraction", "Pattern matching"],
            analysis_steps=[
                "Error code extraction",
                "Frequency analysis",
                "Pattern matching",
                "Root cause scoring"
            ]
        )
    
    def build_prediction_evidence(
        self,
        prediction: str,
        risk_level: str,
        data_points: int,
        limitations: List[str]
    ) -> EvidencePackage:
        """
        Build evidence for prediction-type answers.
        
        CRITICAL: Predictions must be clearly marked as uncertain.
        """
        # What we see
        what_we_see = "**Prediction:** {}".format(prediction)
        
        # Why it matters - with STRONG caveats
        why_matters = (
            "This is a **risk indicator**, not a failure prediction. "
            "Risk level: **{}**. ".format(risk_level) +
            "CSV data lacks real-time health metrics, so this assessment is based on historical patterns only."
        )
        
        # Evidence items
        evidence_items = [
            EvidenceItem(
                fact="Data Points Analyzed",
                source="CSV alert data",
                value="{:,}".format(data_points),
                relevance="Volume of data informing prediction"
            ),
            EvidenceItem(
                fact="Risk Level",
                source="Risk scoring algorithm",
                value=risk_level,
                relevance="Computed risk classification"
            )
        ]
        
        # Add limitations as evidence
        for i, limit in enumerate(limitations[:3]):
            evidence_items.append(EvidenceItem(
                fact="Limitation {}".format(i + 1),
                source="Data gap analysis",
                value=limit,
                relevance="Factors limiting prediction confidence"
            ))
        
        return EvidencePackage(
            what_we_see=what_we_see,
            why_it_matters=why_matters,
            evidence_items=evidence_items,
            data_sources=["CSV alert data", "Historical patterns"],
            analysis_steps=[
                "Alert trend analysis",
                "Pattern recognition",
                "Risk scoring",
                "Confidence assessment"
            ]
        )
    
    def build_unknown_evidence(
        self,
        what_was_asked: str,
        what_we_have: List[str],
        what_we_lack: List[str]
    ) -> EvidencePackage:
        """
        Build evidence when we cannot answer a question.
        
        TRUST PRINCIPLE: Never hallucinate. Be honest about gaps.
        """
        # What we see
        what_we_see = "**Cannot provide definitive answer** for: {}".format(what_was_asked)
        
        # Why it matters
        why_matters = (
            "The requested information is not available in the CSV data. "
            "Providing an answer without data would be speculation."
        )
        
        # Evidence items
        evidence_items = []
        
        for item in what_we_have[:3]:
            evidence_items.append(EvidenceItem(
                fact="Available Data",
                source="CSV",
                value=item,
                relevance="Data we have access to"
            ))
        
        for item in what_we_lack[:3]:
            evidence_items.append(EvidenceItem(
                fact="Missing Data",
                source="Gap analysis",
                value=item,
                relevance="Required but not available"
            ))
        
        return EvidencePackage(
            what_we_see=what_we_see,
            why_it_matters=why_matters,
            evidence_items=evidence_items,
            data_sources=["Data availability check"],
            analysis_steps=[
                "Query analysis",
                "Data source check",
                "Gap identification"
            ]
        )


# Singleton instance
EVIDENCE_LAYER = EvidenceLayer()


# Convenience functions
def build_evidence(evidence_type: str, **kwargs) -> EvidencePackage:
    """Build evidence package by type."""
    if evidence_type == "count":
        return EVIDENCE_LAYER.build_count_evidence(**kwargs)
    elif evidence_type == "incident":
        return EVIDENCE_LAYER.build_incident_evidence(**kwargs)
    elif evidence_type == "root_cause":
        return EVIDENCE_LAYER.build_root_cause_evidence(**kwargs)
    elif evidence_type == "prediction":
        return EVIDENCE_LAYER.build_prediction_evidence(**kwargs)
    elif evidence_type == "unknown":
        return EVIDENCE_LAYER.build_unknown_evidence(**kwargs)
    else:
        raise ValueError("Unknown evidence type: {}".format(evidence_type))
