# reasoning/safe_prediction_language.py
"""
PHASE 7: SAFE PREDICTION & RISK LANGUAGE

Ensures all predictions use appropriate uncertainty language.

FORBIDDEN PHRASES:
- "Will fail"
- "Definitely crash"
- "Guaranteed issue"
- "Certain to happen"

REQUIRED PHRASES:
- "Risk indicator"
- "Based on patterns"
- "Confidence: LOW/MEDIUM"
- "Verify with live metrics"

TRUST PRINCIPLE: Never over-promise. Use probability + confidence.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import re


@dataclass
class SafePrediction:
    """A prediction formatted with safe, appropriate language."""
    prediction_text: str
    confidence_level: str  # LOW, MEDIUM (never HIGH for predictions)
    risk_level: str  # LOW, MEDIUM, HIGH
    reasoning: str
    limitations: List[str]
    verification_steps: List[str]
    
    def to_display(self) -> str:
        """Format prediction for user display."""
        lines = []
        
        # Prediction with clear qualifier
        lines.append("### 🔮 Prediction")
        lines.append(self.prediction_text)
        lines.append("")
        
        # Confidence - always show prominently
        if self.confidence_level == "LOW":
            lines.append("**Confidence:** 🔴 LOW")
        else:
            lines.append("**Confidence:** 🟡 MEDIUM")
        
        lines.append("**Risk Level:** {}".format(self.risk_level))
        lines.append("")
        
        # Reasoning
        lines.append("**Reasoning:** {}".format(self.reasoning))
        lines.append("")
        
        # Limitations - ALWAYS show
        lines.append("**⚠️ Limitations:**")
        for limit in self.limitations:
            lines.append("- {}".format(limit))
        lines.append("")
        
        # Verification
        lines.append("**Recommended Verification:**")
        for step in self.verification_steps:
            lines.append("- {}".format(step))
        
        # Disclaimer
        lines.append("")
        lines.append("*This is a risk indicator, not a failure prediction.*")
        
        return "\n".join(lines)


class SafePredictionLanguage:
    """
    Transforms predictions into safe, appropriately uncertain language.
    
    CORE RULE: Predictions are NEVER HIGH confidence.
    """
    
    # Forbidden phrases that imply certainty
    FORBIDDEN_PHRASES = [
        r'\bwill fail\b',
        r'\bwill crash\b',
        r'\bwill definitely\b',
        r'\bdefinitely\b',
        r'\bguaranteed\b',
        r'\bcertain to\b',
        r'\bcertainly\b',
        r'\bwill certainly\b',
        r'\binevitable\b',
        r'\bwithout doubt\b',
        r'\bfor sure\b',
        r'\babsolutely\b',
        r'\b100%\b',
        r'\bwill always\b',
    ]
    
    # Safe replacements
    SAFE_REPLACEMENTS = {
        r'\bwill fail\b': "shows elevated failure risk",
        r'\bwill crash\b': "may experience instability",
        r'\bwill definitely\b': "is likely to",
        r'\bdefinitely\b': "likely",
        r'\bguaranteed\b': "probable",
        r'\bcertain to\b': "likely to",
        r'\bcertainly\b': "likely",
        r'\binevitable\b': "probable",
        r'\bwithout doubt\b': "with high probability",
        r'\bfor sure\b': "most likely",
        r'\babsolutely\b': "very likely",
        r'\b100%\b': "high probability",
    }
    
    # Standard limitations for all predictions
    STANDARD_LIMITATIONS = [
        "CSV data lacks real-time health metrics",
        "No live database connection for verification",
        "Based on historical patterns, not current state"
    ]
    
    # Standard verification steps
    STANDARD_VERIFICATION = [
        "Check current database status in OEM",
        "Verify alert log for recent entries",
        "Confirm with live monitoring tools"
    ]
    
    def __init__(self):
        self._unsafe_detections = []
    
    def sanitize_text(self, text: str) -> Tuple[str, List[str]]:
        """
        Sanitize prediction text, replacing forbidden phrases.
        
        Returns:
            Tuple of (sanitized_text, list of phrases that were replaced)
        """
        sanitized = text
        replaced = []
        
        for pattern, replacement in self.SAFE_REPLACEMENTS.items():
            if re.search(pattern, text, re.IGNORECASE):
                replaced.append(pattern)
                sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        
        if replaced:
            self._unsafe_detections.append({
                "original": text,
                "sanitized": sanitized,
                "replaced": replaced
            })
        
        return sanitized, replaced
    
    def check_for_forbidden_phrases(self, text: str) -> List[str]:
        """Check if text contains any forbidden phrases."""
        found = []
        for pattern in self.FORBIDDEN_PHRASES:
            if re.search(pattern, text, re.IGNORECASE):
                found.append(pattern)
        return found
    
    def build_safe_prediction(
        self,
        database: str,
        risk_indicator: str,
        data_points: int,
        critical_ratio: float = 0.0,
        custom_limitations: List[str] = None
    ) -> SafePrediction:
        """
        Build a safely-worded prediction.
        
        Args:
            database: Database being predicted about
            risk_indicator: What the risk indicator shows
            data_points: Number of data points informing prediction
            critical_ratio: Ratio of critical alerts (0.0 to 1.0)
            custom_limitations: Additional limitations to mention
        """
        custom_limitations = custom_limitations or []
        
        # Determine confidence (NEVER HIGH for predictions)
        if data_points > 10000 and critical_ratio > 0.3:
            confidence = "MEDIUM"
            confidence_reason = "High data volume with significant critical ratio"
        elif data_points > 1000:
            confidence = "MEDIUM"
            confidence_reason = "Moderate data volume"
        else:
            confidence = "LOW"
            confidence_reason = "Limited data available"
        
        # Determine risk level
        if critical_ratio > 0.5:
            risk = "HIGH"
        elif critical_ratio > 0.2:
            risk = "MEDIUM"
        else:
            risk = "LOW"
        
        # Build prediction text with safe language
        prediction_text = (
            "Based on historical alert patterns, **{}** shows {} instability risk. "
            "This assessment is derived from {:,} data points with {:.1f}% critical alerts."
        ).format(
            database,
            risk.lower(),
            data_points,
            critical_ratio * 100
        )
        
        # Combine limitations
        all_limitations = self.STANDARD_LIMITATIONS.copy()
        all_limitations.extend(custom_limitations)
        
        return SafePrediction(
            prediction_text=prediction_text,
            confidence_level=confidence,
            risk_level=risk,
            reasoning=confidence_reason,
            limitations=all_limitations[:5],  # Limit for readability
            verification_steps=self.STANDARD_VERIFICATION
        )
    
    def build_failure_prediction(
        self,
        database: str,
        failure_probability: str,  # "low", "medium", "high"
        based_on: List[str]
    ) -> SafePrediction:
        """
        Build a failure prediction with mandatory safety language.
        """
        # Map probability to safe text
        prob_text = {
            "low": "lower than average",
            "medium": "moderate",
            "high": "elevated"
        }.get(failure_probability.lower(), "uncertain")
        
        prediction_text = (
            "**{}** shows {} risk indicators based on alert patterns. "
            "This is a risk assessment, not a failure prediction."
        ).format(database, prob_text)
        
        # Confidence is at most MEDIUM for failure predictions
        confidence = "LOW" if failure_probability.lower() == "high" else "MEDIUM"
        
        return SafePrediction(
            prediction_text=prediction_text,
            confidence_level=confidence,
            risk_level=failure_probability.upper(),
            reasoning="Based on: {}".format(", ".join(based_on[:3])),
            limitations=self.STANDARD_LIMITATIONS,
            verification_steps=self.STANDARD_VERIFICATION
        )
    
    def format_risk_statement(
        self,
        database: str,
        risk_level: str,
        reason: str
    ) -> str:
        """
        Format a single risk statement with safe language.
        """
        templates = {
            "HIGH": (
                "**{}** shows elevated risk indicators. {}. "
                "This warrants attention but is not a guaranteed failure."
            ),
            "MEDIUM": (
                "**{}** shows moderate risk indicators. {}. "
                "Recommend monitoring for changes."
            ),
            "LOW": (
                "**{}** shows lower risk indicators. {}. "
                "Continue normal monitoring."
            )
        }
        
        template = templates.get(risk_level.upper(), templates["MEDIUM"])
        return template.format(database, reason)
    
    def add_prediction_disclaimer(self, text: str) -> str:
        """Add standard prediction disclaimer to text."""
        disclaimer = (
            "\n\n---\n"
            "*⚠️ This is a risk indicator based on historical patterns. "
            "Verify with live monitoring tools before taking action.*"
        )
        return text + disclaimer
    
    def get_unsafe_detections(self) -> List[Dict]:
        """Get list of unsafe phrases that were detected and replaced."""
        return self._unsafe_detections.copy()
    
    def clear_detections(self):
        """Clear detection history."""
        self._unsafe_detections = []


# Singleton instance
SAFE_PREDICTION = SafePredictionLanguage()


# Convenience functions
def make_prediction_safe(text: str) -> str:
    """Sanitize prediction text."""
    safe_text, _ = SAFE_PREDICTION.sanitize_text(text)
    return safe_text


def check_prediction_safety(text: str) -> bool:
    """Check if prediction text is safe (no forbidden phrases)."""
    return len(SAFE_PREDICTION.check_for_forbidden_phrases(text)) == 0


def build_safe_risk_prediction(database: str, data_points: int, critical_ratio: float) -> SafePrediction:
    """Build a safe prediction for a database."""
    return SAFE_PREDICTION.build_safe_prediction(
        database=database,
        risk_indicator="alert patterns",
        data_points=data_points,
        critical_ratio=critical_ratio
    )
