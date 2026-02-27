# reasoning/answer_confidence_engine.py
"""
PHASE 7: ANSWER CONFIDENCE ENGINE

Attaches confidence levels to EVERY answer based on data source quality.

Confidence Levels:
- HIGH (0.85-1.0): Directly supported by CSV data (counts, exact matches)
- MEDIUM (0.5-0.84): Inferred from strong patterns (rankings, correlations)
- LOW (0.0-0.49): Weak signal, needs human validation (predictions, guesses)

Rules:
- Counts from CSV = HIGH
- Rankings/comparisons = MEDIUM  
- Predictions = LOW or MEDIUM only (never HIGH)
- Missing data = LOW with explicit disclaimer

This engine ensures DBA TRUST by never over-promising.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum


class ConfidenceLevel(Enum):
    """Confidence level enum with display properties."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    
    @property
    def emoji(self) -> str:
        return {
            "HIGH": "🟢",
            "MEDIUM": "🟡",
            "LOW": "🔴"
        }.get(self.value, "⚪")
    
    @property
    def description(self) -> str:
        return {
            "HIGH": "Directly supported by CSV data",
            "MEDIUM": "Inferred from patterns",
            "LOW": "Weak signal - needs verification"
        }.get(self.value, "Unknown")


@dataclass
class ConfidenceAssessment:
    """Complete confidence assessment for an answer."""
    level: ConfidenceLevel
    score: float  # 0.0 to 1.0
    source: str  # e.g., "CSV alert data (649,769 records)"
    reasoning: str  # Why this confidence level
    data_backing: List[str] = field(default_factory=list)  # Evidence items
    limitations: List[str] = field(default_factory=list)  # Known gaps
    
    def to_display(self) -> str:
        """Format for user display."""
        lines = []
        lines.append("**Confidence:** {} {} ({:.0f}%)".format(
            self.level.emoji, self.level.value, self.score * 100
        ))
        lines.append("**Source:** {}".format(self.source))
        
        if self.limitations:
            lines.append("**Limitations:** {}".format(", ".join(self.limitations)))
        
        return "\n".join(lines)
    
    def to_audit(self) -> Dict:
        """Format for audit trail."""
        return {
            "confidence_level": self.level.value,
            "confidence_score": self.score,
            "data_source": self.source,
            "reasoning": self.reasoning,
            "data_backing": self.data_backing,
            "limitations": self.limitations
        }


class AnswerConfidenceEngine:
    """
    Scores confidence for any answer based on how it was derived.
    
    TRUST PRINCIPLE: Data is the source of truth.
    """
    
    # Answer types and their base confidence
    ANSWER_TYPE_CONFIDENCE = {
        # HIGH confidence - direct data
        "count": 0.95,
        "exact_match": 0.95,
        "list": 0.90,
        "aggregation": 0.90,
        
        # MEDIUM confidence - derived/inferred
        "ranking": 0.70,
        "comparison": 0.70,
        "correlation": 0.65,
        "pattern": 0.60,
        "trend": 0.55,
        
        # LOW confidence - predictions/guesses
        "prediction": 0.40,
        "risk_assessment": 0.45,
        "recommendation": 0.50,
        "inference": 0.45,
        "guess": 0.25,
        
        # Unknown
        "unknown": 0.30
    }
    
    # Data source quality multipliers
    DATA_SOURCE_QUALITY = {
        "csv_raw": 1.0,  # Direct CSV data
        "csv_aggregated": 0.95,  # Aggregated from CSV
        "cached": 0.90,  # From cache
        "inferred": 0.70,  # Inferred from patterns
        "historical": 0.60,  # From historical memory
        "knowledge_base": 0.75,  # From static knowledge
        "combined": 0.65,  # Multiple sources merged
        "none": 0.20  # No data backing
    }
    
    def __init__(self):
        self._audit_trail = []
    
    def assess_confidence(
        self,
        answer_type: str,
        data_source: str,
        record_count: int = 0,
        has_exact_match: bool = False,
        is_prediction: bool = False,
        missing_data: List[str] = None,
        evidence_items: List[str] = None
    ) -> ConfidenceAssessment:
        """
        Assess confidence for an answer.
        
        Args:
            answer_type: Type of answer (count, ranking, prediction, etc.)
            data_source: Where data came from (csv_raw, inferred, etc.)
            record_count: Number of records backing the answer
            has_exact_match: Whether answer is exact match from data
            is_prediction: Whether this is a prediction (caps confidence)
            missing_data: List of missing data points
            evidence_items: List of evidence supporting the answer
            
        Returns:
            ConfidenceAssessment with level, score, and explanation
        """
        missing_data = missing_data or []
        evidence_items = evidence_items or []
        
        # Get base confidence from answer type
        base_confidence = self.ANSWER_TYPE_CONFIDENCE.get(
            answer_type.lower(), 0.50
        )
        
        # Apply data source quality multiplier
        source_quality = self.DATA_SOURCE_QUALITY.get(
            data_source.lower(), 0.50
        )
        
        score = base_confidence * source_quality
        
        # Boost for high record counts
        if record_count > 1000:
            score = min(1.0, score * 1.1)
        elif record_count > 100:
            score = min(1.0, score * 1.05)
        elif record_count == 0:
            score = score * 0.5
        
        # Boost for exact matches
        if has_exact_match:
            score = min(1.0, score * 1.15)
        
        # Cap predictions at MEDIUM
        if is_prediction:
            score = min(0.60, score)
        
        # Penalty for missing data
        if missing_data:
            penalty = 0.05 * len(missing_data)
            score = max(0.1, score - penalty)
        
        # Determine level
        if score >= 0.85:
            level = ConfidenceLevel.HIGH
        elif score >= 0.50:
            level = ConfidenceLevel.MEDIUM
        else:
            level = ConfidenceLevel.LOW
        
        # Build source description
        if data_source == "csv_raw":
            source_desc = "CSV alert data"
            if record_count > 0:
                source_desc += " ({:,} records)".format(record_count)
        elif data_source == "csv_aggregated":
            source_desc = "Aggregated CSV data"
        elif data_source == "knowledge_base":
            source_desc = "DBA Knowledge Base"
        elif data_source == "historical":
            source_desc = "Historical incident memory"
        else:
            source_desc = data_source.replace("_", " ").title()
        
        # Build reasoning
        reasoning_parts = []
        reasoning_parts.append("{} answer type".format(answer_type.replace("_", " ").title()))
        if record_count > 0:
            reasoning_parts.append("{:,} data points".format(record_count))
        if has_exact_match:
            reasoning_parts.append("exact match found")
        if is_prediction:
            reasoning_parts.append("prediction capped at MEDIUM")
        if missing_data:
            reasoning_parts.append("{} missing data points".format(len(missing_data)))
        
        reasoning = "; ".join(reasoning_parts)
        
        # Build limitations
        limitations = []
        if missing_data:
            limitations.extend(missing_data)
        if is_prediction:
            limitations.append("Prediction based on patterns, not certainty")
        if data_source in ["inferred", "historical", "combined"]:
            limitations.append("Not directly from raw data")
        
        assessment = ConfidenceAssessment(
            level=level,
            score=score,
            source=source_desc,
            reasoning=reasoning,
            data_backing=evidence_items,
            limitations=limitations
        )
        
        # Add to audit trail
        self._audit_trail.append({
            "answer_type": answer_type,
            "assessment": assessment.to_audit()
        })
        
        return assessment
    
    def assess_count_answer(
        self,
        count: int,
        entity_type: str,
        from_csv: bool = True,
        filter_applied: str = None
    ) -> ConfidenceAssessment:
        """
        Assess confidence for a count-type answer.
        
        Counts from CSV are always HIGH confidence.
        """
        evidence = ["{:,} {} counted".format(count, entity_type)]
        if filter_applied:
            evidence.append("Filter: {}".format(filter_applied))
        
        return self.assess_confidence(
            answer_type="count",
            data_source="csv_raw" if from_csv else "cached",
            record_count=count,
            has_exact_match=True,
            evidence_items=evidence
        )
    
    def assess_prediction_answer(
        self,
        prediction_type: str,
        data_points: int,
        missing_metrics: List[str] = None
    ) -> ConfidenceAssessment:
        """
        Assess confidence for a prediction-type answer.
        
        Predictions are ALWAYS capped at MEDIUM (never HIGH).
        """
        missing_metrics = missing_metrics or []
        
        # Add standard prediction limitations
        standard_limitations = [
            "CSV data lacks live health metrics",
            "No real-time monitoring data"
        ]
        all_missing = missing_metrics + standard_limitations
        
        return self.assess_confidence(
            answer_type="prediction",
            data_source="csv_aggregated",
            record_count=data_points,
            is_prediction=True,
            missing_data=all_missing[:3]  # Limit to 3 for readability
        )
    
    def assess_ranking_answer(
        self,
        ranked_items: int,
        ranking_criteria: str
    ) -> ConfidenceAssessment:
        """
        Assess confidence for a ranking-type answer.
        """
        evidence = [
            "{} items ranked".format(ranked_items),
            "Criteria: {}".format(ranking_criteria)
        ]
        
        return self.assess_confidence(
            answer_type="ranking",
            data_source="csv_aggregated",
            record_count=ranked_items,
            evidence_items=evidence
        )
    
    def assess_unknown_answer(
        self,
        what_was_asked: str,
        what_we_have: List[str] = None
    ) -> ConfidenceAssessment:
        """
        Assess confidence when we don't have data to answer.
        
        This ensures HONEST UNCERTAINTY - never hallucinate.
        """
        what_we_have = what_we_have or []
        
        limitations = [
            "Requested data not available in CSV",
            "Cannot provide answer without source data"
        ]
        
        evidence = []
        if what_we_have:
            evidence = ["Available: {}".format(", ".join(what_we_have))]
        
        return ConfidenceAssessment(
            level=ConfidenceLevel.LOW,
            score=0.20,
            source="No matching data found",
            reasoning="Unable to answer '{}' - data not available".format(what_was_asked),
            data_backing=evidence,
            limitations=limitations
        )
    
    def get_audit_trail(self) -> List[Dict]:
        """Get the audit trail of all confidence assessments."""
        return self._audit_trail.copy()
    
    def clear_audit_trail(self):
        """Clear the audit trail."""
        self._audit_trail = []


# Singleton instance
ANSWER_CONFIDENCE = AnswerConfidenceEngine()


# Convenience functions
def assess_confidence(answer_type: str, data_source: str, **kwargs) -> ConfidenceAssessment:
    """Shorthand for ANSWER_CONFIDENCE.assess_confidence()"""
    return ANSWER_CONFIDENCE.assess_confidence(answer_type, data_source, **kwargs)


def format_confidence_badge(assessment: ConfidenceAssessment) -> str:
    """Format a compact confidence badge for display."""
    return "{} {} ({:.0f}%)".format(
        assessment.level.emoji,
        assessment.level.value,
        assessment.score * 100
    )
