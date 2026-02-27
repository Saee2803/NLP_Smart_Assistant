# reasoning/enterprise_trust_engine.py
"""
PHASE 7: ENTERPRISE TRUST ENGINE (Master Orchestrator)

This is the central coordinator for all Phase 7 trust components.

Combines:
1. Answer Confidence Engine - confidence scoring
2. Evidence Layer - evidence-backed explanations
3. DB Scope Guard - strict database scoping
4. Safe Prediction Language - safe prediction formatting
5. Audit & Explainability - audit trails
6. Language Guardrails - quality checks
7. Uncertainty Handler - honest uncertainty handling

TRUST PRINCIPLES:
- Data is the source of truth
- Never over-promise
- Explain before advising
- Human + Professional tone

Every answer goes through this engine before reaching the user.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime

# Import all Phase 7 components
from reasoning.answer_confidence_engine import (
    ANSWER_CONFIDENCE,
    ConfidenceLevel,
    ConfidenceAssessment
)
from reasoning.evidence_layer import (
    EVIDENCE_LAYER,
    EvidencePackage
)
from reasoning.db_scope_guard import (
    DB_SCOPE_GUARD,
    ScopeValidation
)
from reasoning.safe_prediction_language import (
    SAFE_PREDICTION,
    SafePrediction
)
from reasoning.audit_explainability import (
    AUDIT_ENGINE,
    AuditRecord
)
from reasoning.language_guardrails import (
    LANGUAGE_GUARDRAILS,
    QualityCheck
)
from reasoning.uncertainty_handler import (
    UNCERTAINTY_HANDLER,
    UncertaintyResponse,
    UncertaintyType
)


@dataclass
class TrustedAnswer:
    """
    A fully validated, enterprise-ready answer.
    
    Contains:
    - The answer itself
    - Confidence assessment
    - Evidence package
    - Scope validation
    - Quality check
    - Audit record
    """
    answer: str
    confidence: ConfidenceAssessment
    evidence: EvidencePackage
    scope_valid: ScopeValidation
    quality_check: QualityCheck
    audit: Optional[AuditRecord] = None
    metadata: Dict = field(default_factory=dict)
    
    @property
    def is_trustworthy(self) -> bool:
        """Is this answer trustworthy enough to show?"""
        return (
            self.scope_valid.is_valid and
            self.quality_check.passed and
            self.confidence.score >= 0.3  # Minimum threshold to show answer
        )
    
    @property
    def trust_score(self) -> float:
        """Overall trust score (0.0 to 1.0)."""
        score = self.confidence.score
        
        # Penalty for scope issues
        if not self.scope_valid.is_valid:
            score *= 0.5
        
        # Penalty for quality issues
        if not self.quality_check.passed:
            score *= 0.8
        
        return score
    
    def to_dict(self) -> Dict:
        return {
            "answer": self.answer,
            "confidence": {
                "level": self.confidence.level.value,
                "score": self.confidence.score,
                "source": self.confidence.source
            },
            "evidence": self.evidence.to_audit(),
            "scope_valid": {
                "is_valid": self.scope_valid.is_valid,
                "requested_database": self.scope_valid.requested_database
            },
            "quality_passed": self.quality_check.passed,
            "is_trustworthy": self.is_trustworthy,
            "trust_score": self.trust_score,
            "metadata": self.metadata
        }
    
    def format_full_response(self) -> str:
        """Format the complete trusted response with all sections."""
        lines = []
        
        # Main answer
        lines.append(self.answer)
        lines.append("")
        
        # Evidence section
        if self.evidence.evidence_items:
            lines.append(self.evidence.to_display())
            lines.append("")
        
        # Confidence indicator
        if self.confidence.level == ConfidenceLevel.HIGH:
            conf_icon = "🟢"
        elif self.confidence.level == ConfidenceLevel.MEDIUM:
            conf_icon = "🟡"
        else:
            conf_icon = "🔴"
        
        lines.append("---")
        lines.append("{} **Confidence:** {} ({:.0f}%)".format(
            conf_icon,
            self.confidence.level.value,
            self.confidence.score * 100
        ))
        
        # Limitations if any
        if self.confidence.limitations:
            for limitation in self.confidence.limitations[:2]:
                lines.append("- {}".format(limitation))
        
        return "\n".join(lines)
    
    def format_concise(self) -> str:
        """Format a concise version (for executives)."""
        lines = []
        lines.append(self.answer[:500])
        lines.append("")
        lines.append("*Confidence: {}*".format(self.confidence.level.value))
        return "\n".join(lines)


class EnterpriseTrustEngine:
    """
    Master orchestrator for enterprise-grade trustworthy answers.
    
    Every answer flows through this engine:
    1. Validate scope (DB Scope Guard)
    2. Build evidence (Evidence Layer)
    3. Assess confidence (Answer Confidence)
    4. Apply language guardrails (Language Guardrails)
    5. Handle uncertainty if needed (Uncertainty Handler)
    6. Create audit trail (Audit & Explainability)
    7. Format final response
    """
    
    def __init__(self):
        self._answers_processed = 0
        self._answers_blocked = 0
        self._trust_scores = []
    
    def process_answer(
        self,
        question: str,
        raw_answer: str,
        answer_type: str,  # "count", "incident", "prediction", "root_cause", "unknown"
        target_database: str = None,
        data_sources: List[str] = None,
        alerts_used: List[Dict] = None,
        incidents_used: List[Dict] = None,
        context: Dict = None
    ) -> TrustedAnswer:
        """
        Process an answer through all trust components.
        
        Args:
            question: The user's question
            raw_answer: The initial answer (may be modified)
            answer_type: Type of answer for confidence scoring
            target_database: Database being queried (if specific)
            data_sources: List of data sources used
            alerts_used: Alert data used
            incidents_used: Incident data used
            context: Additional context
            
        Returns:
            TrustedAnswer with full validation
        """
        self._answers_processed += 1
        
        # Start audit trail
        AUDIT_ENGINE.start_audit(question, context or {})
        
        # Step 1: Validate scope
        AUDIT_ENGINE.add_step("Scope Validation", target_database or "all", "checking")
        scope_validation = self._validate_scope(
            raw_answer, target_database, alerts_used, incidents_used
        )
        
        if not scope_validation.is_valid:
            scope_reason = "; ".join(scope_validation.violations) if scope_validation.violations else "scope issue"
            AUDIT_ENGINE.add_step("Scope Issue", scope_reason, "filtered")
            raw_answer = self._filter_out_of_scope(raw_answer, scope_validation)
        
        # Step 2: Build evidence
        AUDIT_ENGINE.add_step("Building Evidence", "data analysis", "started")
        evidence = self._build_evidence(
            answer_type, alerts_used, incidents_used, target_database
        )
        AUDIT_ENGINE.add_data_source("OEM Alert Data")
        if incidents_used:
            AUDIT_ENGINE.add_data_source("Incident History")
        
        # Step 3: Assess confidence
        AUDIT_ENGINE.add_step("Confidence Assessment", answer_type, "calculating")
        confidence = self._assess_confidence(
            answer_type, raw_answer, alerts_used, incidents_used, evidence
        )
        AUDIT_ENGINE.set_confidence(confidence.level.value, confidence.score)
        
        # Step 4: Apply language guardrails
        AUDIT_ENGINE.add_step("Language Check", raw_answer[:50], "sanitizing")
        sanitized_answer = LANGUAGE_GUARDRAILS.sanitize_response(raw_answer)
        quality = LANGUAGE_GUARDRAILS.full_quality_check(sanitized_answer)
        
        # Step 5: Handle prediction language if needed
        if answer_type == "prediction":
            AUDIT_ENGINE.add_step("Prediction Formatting", "safety check", "applying")
            sanitized_text, replaced_phrases = SAFE_PREDICTION.sanitize_text(sanitized_answer)
            if replaced_phrases:
                sanitized_answer = sanitized_text
                AUDIT_ENGINE.add_step(
                    "Replaced Unsafe Phrases",
                    str(len(replaced_phrases)),
                    "complete"
                )
        
        # Step 6: Handle uncertainty if low confidence
        if confidence.score < 0.5:
            AUDIT_ENGINE.add_step("Uncertainty Handling", "low confidence", "applying")
            uncertainty_note = self._build_uncertainty_note(confidence)
            if uncertainty_note:
                sanitized_answer = uncertainty_note + "\n\n" + sanitized_answer
        
        AUDIT_ENGINE.set_answer_summary(sanitized_answer[:200])
        
        # Build the trusted answer
        trusted = TrustedAnswer(
            answer=sanitized_answer,
            confidence=confidence,
            evidence=evidence,
            scope_valid=scope_validation,
            quality_check=quality,
            metadata={
                "answer_type": answer_type,
                "target": target_database,
                "processed_at": datetime.now().isoformat()
            }
        )
        
        # Complete audit
        trusted.audit = AUDIT_ENGINE.complete_audit()
        
        # Track stats
        self._trust_scores.append(trusted.trust_score)
        if not trusted.is_trustworthy:
            self._answers_blocked += 1
        
        return trusted
    
    def _validate_scope(
        self,
        answer: str,
        target: str,
        alerts: List[Dict],
        incidents: List[Dict]
    ) -> ScopeValidation:
        """Validate database scope."""
        if not target:
            return ScopeValidation(is_valid=True, requested_database="ALL", actual_databases=[])
        
        # Get databases from alerts
        actual_dbs = []
        if alerts:
            for a in alerts:
                db = a.get("target") or a.get("target_name") or ""
                if db:
                    actual_dbs.append(db)
        
        return DB_SCOPE_GUARD.validate_scope(
            requested_db=target,
            actual_dbs=list(set(actual_dbs))
        )
    
    def _filter_out_of_scope(
        self,
        answer: str,
        scope: ScopeValidation
    ) -> str:
        """Filter out of scope content from answer."""
        if scope.is_valid:
            return answer
        
        # Add scope warning - use violations or relationship note
        reason = ""
        if scope.violations:
            reason = "; ".join(scope.violations)
        elif scope.relationship_note:
            reason = scope.relationship_note
        else:
            reason = "Scope validation issue detected"
        
        warning = "⚠️ **Scope Note:** {}\n\n".format(reason)
        return warning + answer
    
    def _build_evidence(
        self,
        answer_type: str,
        alerts: List[Dict],
        incidents: List[Dict],
        target: str
    ) -> EvidencePackage:
        """Build evidence package based on answer type."""
        if answer_type == "count":
            count = len(alerts) if alerts else 0
            return EVIDENCE_LAYER.build_count_evidence(
                count=count, 
                entity_type="alerts", 
                database=target or "all"
            )
        
        elif answer_type == "incident":
            total_alerts = len(alerts) if alerts else 0
            unique_incidents = len(incidents) if incidents else 0
            return EVIDENCE_LAYER.build_incident_evidence(
                total_alerts=total_alerts,
                unique_incidents=unique_incidents
            )
        
        elif answer_type == "prediction":
            return EVIDENCE_LAYER.build_prediction_evidence(
                prediction="Risk assessment based on historical data",
                risk_level="MEDIUM",
                data_points=len(alerts) if alerts else 0,
                limitations=["CSV data lacks real-time metrics"]
            )
        
        elif answer_type == "root_cause":
            return EVIDENCE_LAYER.build_root_cause_evidence(
                root_cause="Pattern-based analysis",
                confidence=0.7,
                supporting_evidence=["Alert pattern analysis"]
            )
        
        else:
            return EVIDENCE_LAYER.build_unknown_evidence(
                what_was_asked=target or "unknown",
                what_we_have=["CSV alert data"],
                what_we_lack=["Specific information requested"]
            )
    
    def _assess_confidence(
        self,
        answer_type: str,
        answer: str,
        alerts: List[Dict],
        incidents: List[Dict],
        evidence: EvidencePackage
    ) -> ConfidenceAssessment:
        """Assess confidence based on answer type and data."""
        if answer_type == "count":
            count = len(alerts) if alerts else 0
            return ANSWER_CONFIDENCE.assess_count_answer(count, entity_type="alerts")
        
        elif answer_type == "prediction":
            return ANSWER_CONFIDENCE.assess_prediction_answer(
                prediction_type="risk",
                data_points=len(alerts) if alerts else 0
            )
        
        elif answer_type in ("unknown", "no_data"):
            return ANSWER_CONFIDENCE.assess_unknown_answer("unknown topic")
        
        else:
            # General assessment
            return ANSWER_CONFIDENCE.assess_confidence(
                answer_type=answer_type,
                data_source="csv_raw" if alerts else "none",
                record_count=len(alerts) if alerts else 0
            )
    
    def _build_uncertainty_note(self, confidence: ConfidenceAssessment) -> str:
        """Build uncertainty note for low confidence answers."""
        if confidence.score >= 0.5:
            return ""
        
        if confidence.score < 0.3:
            return "⚠️ **Limited Data:** This answer has low confidence due to limited available data."
        else:
            return "📊 **Note:** Confidence is moderate. Additional data would improve accuracy."
    
    def quick_validate(self, answer: str, target: str = None) -> bool:
        """Quick validation check - returns True if answer seems valid."""
        # Check scope if target specified
        if target:
            scope = DB_SCOPE_GUARD.check_response_scope(answer, target)
            if not scope.is_valid:
                return False
        
        # Check language quality
        quality = LANGUAGE_GUARDRAILS.full_quality_check(answer)
        return quality.passed
    
    def format_for_audience(
        self,
        trusted_answer: TrustedAnswer,
        audience: str = "dba"  # "dba", "executive", "auditor"
    ) -> str:
        """Format trusted answer for specific audience."""
        if audience == "executive":
            return LANGUAGE_GUARDRAILS.format_for_executive(trusted_answer.answer)
        elif audience == "auditor":
            full_response = trusted_answer.format_full_response()
            return LANGUAGE_GUARDRAILS.format_for_auditor(full_response)
        else:
            return LANGUAGE_GUARDRAILS.format_for_senior_dba(
                trusted_answer.format_full_response()
            )
    
    def get_audit_trail(self, question: str = None) -> Optional[AuditRecord]:
        """Get audit trail for a question."""
        if question:
            return AUDIT_ENGINE.get_audit_for_question(question)
        return AUDIT_ENGINE.get_current_audit()
    
    def get_stats(self) -> Dict:
        """Get engine statistics."""
        avg_trust = (
            sum(self._trust_scores) / len(self._trust_scores)
            if self._trust_scores else 0
        )
        
        return {
            "answers_processed": self._answers_processed,
            "answers_blocked": self._answers_blocked,
            "average_trust_score": avg_trust,
            "language_stats": LANGUAGE_GUARDRAILS.get_stats(),
            "uncertainty_stats": UNCERTAINTY_HANDLER.get_stats()
        }


# Singleton instance
ENTERPRISE_TRUST = EnterpriseTrustEngine()


# Convenience functions
def process_answer(
    question: str,
    answer: str,
    answer_type: str,
    target: str = None,
    alerts: List[Dict] = None
) -> TrustedAnswer:
    """Process an answer through the trust engine."""
    return ENTERPRISE_TRUST.process_answer(
        question=question,
        raw_answer=answer,
        answer_type=answer_type,
        target_database=target,
        alerts_used=alerts
    )


def quick_validate(answer: str, target: str = None) -> bool:
    """Quick validation check."""
    return ENTERPRISE_TRUST.quick_validate(answer, target)


def format_trusted_response(
    trusted: TrustedAnswer,
    audience: str = "dba"
) -> str:
    """Format trusted answer for audience."""
    return ENTERPRISE_TRUST.format_for_audience(trusted, audience)


def get_trust_stats() -> Dict:
    """Get trust engine statistics."""
    return ENTERPRISE_TRUST.get_stats()
