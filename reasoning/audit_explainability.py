# reasoning/audit_explainability.py
"""
PHASE 7: AUDIT & EXPLAINABILITY MODE

Enterprise requirement: Auditors must be able to trace how any answer was derived.

When enabled, shows:
1. Data sources used
2. Logic steps taken
3. Confidence scoring breakdown
4. Any assumptions made

This is MANDATORY for production enterprise deployments.

TRUST PRINCIPLE: Every answer must be traceable and verifiable.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import json


@dataclass
class AuditStep:
    """A single step in the answer derivation process."""
    step_number: int
    action: str  # What was done
    input_data: str  # What data was used
    output: str  # What was produced
    duration_ms: int = 0  # How long it took
    
    def to_dict(self) -> Dict:
        return {
            "step": self.step_number,
            "action": self.action,
            "input": self.input_data,
            "output": self.output,
            "duration_ms": self.duration_ms
        }


@dataclass
class AuditRecord:
    """Complete audit record for an answer."""
    question: str
    timestamp: str
    answer_summary: str
    confidence_level: str
    confidence_score: float
    data_sources: List[str]
    logic_steps: List[AuditStep]
    assumptions: List[str]
    limitations: List[str]
    query_context: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "question": self.question,
            "timestamp": self.timestamp,
            "answer_summary": self.answer_summary,
            "confidence": {
                "level": self.confidence_level,
                "score": self.confidence_score
            },
            "data_sources": self.data_sources,
            "logic_steps": [s.to_dict() for s in self.logic_steps],
            "assumptions": self.assumptions,
            "limitations": self.limitations,
            "context": self.query_context
        }
    
    def to_display(self) -> str:
        """Format for human-readable display."""
        lines = []
        
        lines.append("## 📋 Audit Trail")
        lines.append("")
        lines.append("**Question:** {}".format(self.question))
        lines.append("**Timestamp:** {}".format(self.timestamp))
        lines.append("**Confidence:** {} ({:.0f}%)".format(
            self.confidence_level, self.confidence_score * 100
        ))
        lines.append("")
        
        # Data sources
        lines.append("### 📁 Data Sources")
        for source in self.data_sources:
            lines.append("- {}".format(source))
        lines.append("")
        
        # Logic steps
        lines.append("### 🔄 Processing Steps")
        for step in self.logic_steps:
            lines.append("{}. **{}**: {} → {}".format(
                step.step_number, step.action, step.input_data, step.output
            ))
        lines.append("")
        
        # Assumptions
        if self.assumptions:
            lines.append("### ⚠️ Assumptions Made")
            for assumption in self.assumptions:
                lines.append("- {}".format(assumption))
            lines.append("")
        
        # Limitations
        if self.limitations:
            lines.append("### 🚫 Limitations")
            for limitation in self.limitations:
                lines.append("- {}".format(limitation))
        
        return "\n".join(lines)
    
    def to_json(self) -> str:
        """Format for JSON export."""
        return json.dumps(self.to_dict(), indent=2, default=str)


class AuditExplainabilityEngine:
    """
    Tracks and explains how every answer is derived.
    
    Can be toggled on/off for performance.
    """
    
    def __init__(self, enabled: bool = True):
        self._enabled = enabled
        self._current_record = None
        self._history = []
        self._step_counter = 0
    
    @property
    def is_enabled(self) -> bool:
        return self._enabled
    
    def enable(self):
        """Enable audit mode."""
        self._enabled = True
    
    def disable(self):
        """Disable audit mode."""
        self._enabled = False
    
    def start_audit(self, question: str, context: Dict = None) -> None:
        """Start a new audit record for a question."""
        if not self._enabled:
            return
        
        self._step_counter = 0
        self._current_record = AuditRecord(
            question=question,
            timestamp=datetime.now().isoformat(),
            answer_summary="",
            confidence_level="UNKNOWN",
            confidence_score=0.0,
            data_sources=[],
            logic_steps=[],
            assumptions=[],
            limitations=[],
            query_context=context or {}
        )
    
    def add_step(
        self,
        action: str,
        input_data: str,
        output: str,
        duration_ms: int = 0
    ) -> None:
        """Add a processing step to the current audit."""
        if not self._enabled or not self._current_record:
            return
        
        self._step_counter += 1
        step = AuditStep(
            step_number=self._step_counter,
            action=action,
            input_data=input_data,
            output=output,
            duration_ms=duration_ms
        )
        self._current_record.logic_steps.append(step)
    
    def add_data_source(self, source: str) -> None:
        """Add a data source to the current audit."""
        if not self._enabled or not self._current_record:
            return
        
        if source not in self._current_record.data_sources:
            self._current_record.data_sources.append(source)
    
    def add_assumption(self, assumption: str) -> None:
        """Add an assumption to the current audit."""
        if not self._enabled or not self._current_record:
            return
        
        if assumption not in self._current_record.assumptions:
            self._current_record.assumptions.append(assumption)
    
    def add_limitation(self, limitation: str) -> None:
        """Add a limitation to the current audit."""
        if not self._enabled or not self._current_record:
            return
        
        if limitation not in self._current_record.limitations:
            self._current_record.limitations.append(limitation)
    
    def set_confidence(self, level: str, score: float) -> None:
        """Set the confidence assessment for the current audit."""
        if not self._enabled or not self._current_record:
            return
        
        self._current_record.confidence_level = level
        self._current_record.confidence_score = score
    
    def set_answer_summary(self, summary: str) -> None:
        """Set the answer summary for the current audit."""
        if not self._enabled or not self._current_record:
            return
        
        self._current_record.answer_summary = summary[:500]  # Limit length
    
    def complete_audit(self) -> Optional[AuditRecord]:
        """Complete the current audit and add to history."""
        if not self._enabled or not self._current_record:
            return None
        
        record = self._current_record
        self._history.append(record)
        
        # Keep history bounded
        if len(self._history) > 1000:
            self._history = self._history[-500:]
        
        self._current_record = None
        return record
    
    def get_current_audit(self) -> Optional[AuditRecord]:
        """Get the current in-progress audit record."""
        return self._current_record
    
    def get_history(self, limit: int = 100) -> List[AuditRecord]:
        """Get audit history."""
        return self._history[-limit:]
    
    def get_audit_for_question(self, question: str) -> Optional[AuditRecord]:
        """Find the audit record for a specific question."""
        for record in reversed(self._history):
            if record.question.lower() == question.lower():
                return record
        return None
    
    def export_history(self, filepath: str = None) -> str:
        """Export audit history as JSON."""
        data = {
            "export_time": datetime.now().isoformat(),
            "total_records": len(self._history),
            "records": [r.to_dict() for r in self._history]
        }
        json_str = json.dumps(data, indent=2, default=str)
        
        if filepath:
            with open(filepath, 'w') as f:
                f.write(json_str)
        
        return json_str
    
    def clear_history(self):
        """Clear audit history."""
        self._history = []
    
    def build_explainability_response(
        self,
        question: str,
        answer: str,
        data_sources: List[str],
        steps: List[str],
        confidence: float
    ) -> str:
        """
        Build a complete explainability response.
        
        Use this to append explanation to any answer.
        """
        lines = []
        lines.append("")
        lines.append("---")
        lines.append("### 📋 How This Answer Was Derived")
        lines.append("")
        
        # Sources
        lines.append("**Data Sources:**")
        for source in data_sources[:5]:
            lines.append("- {}".format(source))
        lines.append("")
        
        # Steps
        lines.append("**Analysis Steps:**")
        for i, step in enumerate(steps[:5], 1):
            lines.append("{}. {}".format(i, step))
        lines.append("")
        
        # Confidence
        if confidence >= 0.85:
            conf_label = "🟢 HIGH"
        elif confidence >= 0.50:
            conf_label = "🟡 MEDIUM"
        else:
            conf_label = "🔴 LOW"
        
        lines.append("**Confidence:** {} ({:.0f}%)".format(conf_label, confidence * 100))
        
        return "\n".join(lines)


# Singleton instance
AUDIT_ENGINE = AuditExplainabilityEngine(enabled=True)


# Convenience functions
def start_audit(question: str, context: Dict = None) -> None:
    """Start auditing a new question."""
    AUDIT_ENGINE.start_audit(question, context)


def audit_step(action: str, input_data: str, output: str) -> None:
    """Add an audit step."""
    AUDIT_ENGINE.add_step(action, input_data, output)


def complete_audit() -> Optional[AuditRecord]:
    """Complete the current audit."""
    return AUDIT_ENGINE.complete_audit()


def get_explainability_section(
    data_sources: List[str],
    steps: List[str],
    confidence: float
) -> str:
    """Get formatted explainability section to append to answer."""
    return AUDIT_ENGINE.build_explainability_response(
        question="",
        answer="",
        data_sources=data_sources,
        steps=steps,
        confidence=confidence
    )
