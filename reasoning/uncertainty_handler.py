# reasoning/uncertainty_handler.py
"""
PHASE 7: UNCERTAINTY HANDLER

Enterprise requirement: The system must NEVER hallucinate or make up data.

When data is missing, uncertain, or unavailable:
1. Acknowledge the limitation honestly
2. Explain what data would be needed
3. Provide what CAN be said with confidence
4. Never guess or fabricate

TRUST PRINCIPLE: "I don't know" is a valid, honest answer.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum


class UncertaintyType(Enum):
    """Types of uncertainty in answers."""
    NO_DATA = "no_data"             # Data doesn't exist
    STALE_DATA = "stale_data"       # Data exists but is old
    INCOMPLETE = "incomplete"        # Partial data available
    CONFLICTING = "conflicting"      # Multiple data sources disagree
    LOW_CONFIDENCE = "low_confidence"  # Data exists but uncertain
    UNKNOWN_METRIC = "unknown_metric"  # Metric not recognized
    OUT_OF_SCOPE = "out_of_scope"      # Question outside system capability


@dataclass
class UncertaintyResponse:
    """A structured response for uncertain situations."""
    uncertainty_type: UncertaintyType
    what_we_know: str
    what_we_dont_know: str
    what_would_help: str
    honest_answer: str
    confidence: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "uncertainty_type": self.uncertainty_type.value,
            "what_we_know": self.what_we_know,
            "what_we_dont_know": self.what_we_dont_know,
            "what_would_help": self.what_would_help,
            "honest_answer": self.honest_answer,
            "confidence": self.confidence
        }
    
    def format_response(self) -> str:
        """Format as a human-readable response."""
        lines = []
        
        lines.append(self.honest_answer)
        lines.append("")
        
        if self.what_we_know:
            lines.append("**What we know:** {}".format(self.what_we_know))
        
        if self.what_we_dont_know:
            lines.append("**Limitation:** {}".format(self.what_we_dont_know))
        
        if self.what_would_help:
            lines.append("**What would help:** {}".format(self.what_would_help))
        
        return "\n".join(lines)


class UncertaintyHandler:
    """
    Handles situations where the system cannot give a confident answer.
    
    Core philosophy: Honesty > False confidence
    """
    
    # Honest acknowledgment phrases
    HONEST_PHRASES = {
        UncertaintyType.NO_DATA: [
            "I don't have data for this",
            "This information isn't available in our current data",
            "No data found for this query"
        ],
        UncertaintyType.STALE_DATA: [
            "The most recent data is from {} ago",
            "Our data may be outdated (last update: {})",
            "I have older data, but recent information is unavailable"
        ],
        UncertaintyType.INCOMPLETE: [
            "I have partial information",
            "Some data is available, but the picture is incomplete",
            "I found some data, but it doesn't cover everything"
        ],
        UncertaintyType.CONFLICTING: [
            "Different data sources show different values",
            "There are conflicting indicators",
            "The data is not consistent across sources"
        ],
        UncertaintyType.LOW_CONFIDENCE: [
            "I can provide an estimate, but confidence is low",
            "Based on limited data, my best assessment is",
            "With significant uncertainty"
        ],
        UncertaintyType.UNKNOWN_METRIC: [
            "I don't recognize this metric",
            "This metric isn't tracked in our system",
            "Unable to find data for this specific metric"
        ],
        UncertaintyType.OUT_OF_SCOPE: [
            "This is outside what I can analyze",
            "I'm not able to answer questions about this topic",
            "This type of query isn't supported"
        ]
    }
    
    def __init__(self):
        self._uncertainty_count = 0
        self._by_type = {}
    
    def handle_no_data(
        self,
        what_was_asked: str,
        target: str = None,
        metric: str = None
    ) -> UncertaintyResponse:
        """Handle case when no data is available."""
        self._track_uncertainty(UncertaintyType.NO_DATA)
        
        if target and metric:
            what_we_know = "You asked about {} for database {}".format(metric, target)
            what_we_dont_know = "No {} data is currently available for {}".format(metric, target)
            what_would_help = "Check if {} is being monitored in OEM".format(target)
        elif target:
            what_we_know = "You asked about database {}".format(target)
            what_we_dont_know = "No data is currently available for {}".format(target)
            what_would_help = "Verify that {} exists and is monitored".format(target)
        else:
            what_we_know = "You asked: {}".format(what_was_asked)
            what_we_dont_know = "I couldn't find relevant data to answer this"
            what_would_help = "Try specifying a database name or metric"
        
        return UncertaintyResponse(
            uncertainty_type=UncertaintyType.NO_DATA,
            what_we_know=what_we_know,
            what_we_dont_know=what_we_dont_know,
            what_would_help=what_would_help,
            honest_answer="I don't have the data needed to answer this question.",
            confidence=0.0
        )
    
    def handle_stale_data(
        self,
        what_was_asked: str,
        data_age: str,
        last_value: Any = None
    ) -> UncertaintyResponse:
        """Handle case when data is outdated."""
        self._track_uncertainty(UncertaintyType.STALE_DATA)
        
        what_we_know = "The last recorded data is from {}".format(data_age)
        
        if last_value is not None:
            what_we_know += ". At that time, the value was {}".format(last_value)
        
        return UncertaintyResponse(
            uncertainty_type=UncertaintyType.STALE_DATA,
            what_we_know=what_we_know,
            what_we_dont_know="Current real-time data is not available",
            what_would_help="Fresh data collection from the database",
            honest_answer="The most recent data I have is from {}. This may not reflect current conditions.".format(data_age),
            confidence=0.3
        )
    
    def handle_incomplete_data(
        self,
        what_was_asked: str,
        what_we_have: str,
        what_is_missing: str
    ) -> UncertaintyResponse:
        """Handle case when data is partial."""
        self._track_uncertainty(UncertaintyType.INCOMPLETE)
        
        return UncertaintyResponse(
            uncertainty_type=UncertaintyType.INCOMPLETE,
            what_we_know=what_we_have,
            what_we_dont_know=what_is_missing,
            what_would_help="Additional data collection for the missing components",
            honest_answer="I have partial information. {}. However, I'm missing {}.".format(
                what_we_have, what_is_missing.lower()
            ),
            confidence=0.4
        )
    
    def handle_conflicting_data(
        self,
        what_was_asked: str,
        source1: str,
        value1: Any,
        source2: str,
        value2: Any
    ) -> UncertaintyResponse:
        """Handle case when data sources conflict."""
        self._track_uncertainty(UncertaintyType.CONFLICTING)
        
        return UncertaintyResponse(
            uncertainty_type=UncertaintyType.CONFLICTING,
            what_we_know="{} shows {}, while {} shows {}".format(
                source1, value1, source2, value2
            ),
            what_we_dont_know="Which source is more accurate for this situation",
            what_would_help="Manual verification or additional data points",
            honest_answer="I'm seeing conflicting information. {} reports {}, but {} reports {}. Manual verification is recommended.".format(
                source1, value1, source2, value2
            ),
            confidence=0.3
        )
    
    def handle_low_confidence(
        self,
        what_was_asked: str,
        best_guess: str,
        why_uncertain: str,
        confidence: float
    ) -> UncertaintyResponse:
        """Handle case when confidence is low."""
        self._track_uncertainty(UncertaintyType.LOW_CONFIDENCE)
        
        conf_pct = int(confidence * 100)
        
        return UncertaintyResponse(
            uncertainty_type=UncertaintyType.LOW_CONFIDENCE,
            what_we_know=best_guess,
            what_we_dont_know=why_uncertain,
            what_would_help="More data points to increase confidence",
            honest_answer="Based on limited data ({}% confidence): {}. Note: {}".format(
                conf_pct, best_guess, why_uncertain
            ),
            confidence=confidence
        )
    
    def handle_unknown_metric(
        self,
        metric_name: str,
        similar_metrics: List[str] = None
    ) -> UncertaintyResponse:
        """Handle case when metric is not recognized."""
        self._track_uncertainty(UncertaintyType.UNKNOWN_METRIC)
        
        what_would_help = "Verify the metric name"
        if similar_metrics:
            what_would_help = "Did you mean: {}?".format(", ".join(similar_metrics))
        
        return UncertaintyResponse(
            uncertainty_type=UncertaintyType.UNKNOWN_METRIC,
            what_we_know="You asked about metric '{}'".format(metric_name),
            what_we_dont_know="This metric isn't tracked in our monitoring data",
            what_would_help=what_would_help,
            honest_answer="I don't have data for the metric '{}'. This metric may not be monitored or may use a different name.".format(
                metric_name
            ),
            confidence=0.0
        )
    
    def handle_out_of_scope(
        self,
        what_was_asked: str,
        what_i_can_do: str
    ) -> UncertaintyResponse:
        """Handle case when question is outside system scope."""
        self._track_uncertainty(UncertaintyType.OUT_OF_SCOPE)
        
        return UncertaintyResponse(
            uncertainty_type=UncertaintyType.OUT_OF_SCOPE,
            what_we_know="Your question: {}".format(what_was_asked),
            what_we_dont_know="This type of analysis is outside my capabilities",
            what_would_help=what_i_can_do,
            honest_answer="I'm not able to answer this type of question. {}".format(
                what_i_can_do
            ),
            confidence=0.0
        )
    
    def create_honest_response(
        self,
        question: str,
        partial_answer: str = None,
        uncertainty_reason: str = None,
        confidence: float = 0.0
    ) -> str:
        """
        Create an honest response that acknowledges uncertainty.
        
        This is the main entry point for building uncertain responses.
        """
        lines = []
        
        if confidence < 0.3:
            lines.append("⚠️ **Limited Data Available**")
            lines.append("")
        elif confidence < 0.5:
            lines.append("📊 **Partial Information**")
            lines.append("")
        
        if partial_answer:
            lines.append("Based on available data: {}".format(partial_answer))
            lines.append("")
        
        if uncertainty_reason:
            lines.append("**Note:** {}".format(uncertainty_reason))
        
        if confidence > 0:
            lines.append("")
            lines.append("*Confidence: {}%*".format(int(confidence * 100)))
        
        return "\n".join(lines) if lines else "I don't have enough information to answer this question."
    
    def _track_uncertainty(self, uncertainty_type: UncertaintyType):
        """Track uncertainty for analytics."""
        self._uncertainty_count += 1
        type_name = uncertainty_type.value
        self._by_type[type_name] = self._by_type.get(type_name, 0) + 1
    
    def get_stats(self) -> Dict:
        """Get uncertainty handling statistics."""
        return {
            "total_uncertainties": self._uncertainty_count,
            "by_type": self._by_type
        }


# Singleton instance
UNCERTAINTY_HANDLER = UncertaintyHandler()


# Convenience functions
def handle_no_data(what_was_asked: str, target: str = None) -> UncertaintyResponse:
    """Handle no data scenario."""
    return UNCERTAINTY_HANDLER.handle_no_data(what_was_asked, target)


def handle_unknown_metric(metric_name: str) -> UncertaintyResponse:
    """Handle unknown metric."""
    return UNCERTAINTY_HANDLER.handle_unknown_metric(metric_name)


def handle_low_confidence(
    what_was_asked: str,
    best_guess: str,
    why_uncertain: str,
    confidence: float
) -> UncertaintyResponse:
    """Handle low confidence scenario."""
    return UNCERTAINTY_HANDLER.handle_low_confidence(
        what_was_asked, best_guess, why_uncertain, confidence
    )


def create_honest_response(
    question: str,
    partial_answer: str = None,
    confidence: float = 0.0
) -> str:
    """Create an honest response with uncertainty acknowledgment."""
    return UNCERTAINTY_HANDLER.create_honest_response(
        question, partial_answer, confidence=confidence
    )
