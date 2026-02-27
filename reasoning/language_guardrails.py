# reasoning/language_guardrails.py
"""
PHASE 7: LANGUAGE GUARDRAILS

Enterprise requirement: All responses must meet quality standards:
1. No panic language
2. Short paragraphs (max 3-4 sentences)
3. Senior DBA professional tone
4. No jargon overload
5. Clear action items when relevant

TRUST PRINCIPLE: Speak like a calm, experienced senior DBA.
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional
import re


@dataclass
class QualityCheck:
    """Result of a language quality check."""
    passed: bool
    issues: List[str]
    suggestions: List[str]
    
    def to_dict(self):
        return {
            "passed": self.passed,
            "issues": self.issues,
            "suggestions": self.suggestions
        }


class LanguageGuardrails:
    """
    Ensures all responses meet enterprise language standards.
    
    Checks for:
    - Panic/alarmist language
    - Overly long paragraphs
    - Unprofessional tone
    - Jargon overload
    """
    
    # Panic phrases to avoid
    PANIC_PHRASES = [
        "critical failure",
        "catastrophic",
        "disaster",
        "emergency",
        "panic",
        "urgent action required",
        "immediately stop",
        "system down",
        "complete failure",
        "total loss",
        "cannot recover",
        "no hope",
        "worst case",
        "dead",
        "crashed beyond repair"
    ]
    
    # Calm replacements for panic phrases
    CALM_REPLACEMENTS = {
        "critical failure": "significant issue requiring attention",
        "catastrophic": "serious",
        "disaster": "significant incident",
        "emergency": "priority situation",
        "panic": "concern",
        "urgent action required": "prompt attention recommended",
        "immediately stop": "consider pausing",
        "system down": "system unavailable",
        "complete failure": "service interruption",
        "total loss": "data unavailability",
        "cannot recover": "recovery options are limited",
        "no hope": "challenging situation",
        "worst case": "more serious scenario",
        "dead": "unresponsive",
        "crashed beyond repair": "requires recovery procedures"
    }
    
    # Professional tone markers (good to have)
    PROFESSIONAL_MARKERS = [
        "recommend",
        "suggest",
        "consider",
        "based on",
        "indicates",
        "appears",
        "observed",
        "analysis shows",
        "data suggests"
    ]
    
    # Max paragraph length (sentences)
    MAX_SENTENCES_PER_PARAGRAPH = 4
    
    # Max response length (characters)
    MAX_RESPONSE_LENGTH = 3000
    
    def __init__(self):
        self._checks_performed = 0
        self._issues_found = 0
    
    def check_for_panic_language(self, text: str) -> Tuple[bool, List[str]]:
        """
        Check for panic/alarmist language.
        
        Returns:
            (has_panic, list of panic phrases found)
        """
        text_lower = text.lower()
        found = []
        
        for phrase in self.PANIC_PHRASES:
            if phrase in text_lower:
                found.append(phrase)
        
        return (len(found) > 0, found)
    
    def calm_down_text(self, text: str) -> str:
        """Replace panic phrases with calmer alternatives."""
        result = text
        
        for panic, calm in self.CALM_REPLACEMENTS.items():
            # Case-insensitive replacement
            pattern = re.compile(re.escape(panic), re.IGNORECASE)
            result = pattern.sub(calm, result)
        
        return result
    
    def check_paragraph_length(self, text: str) -> Tuple[bool, List[str]]:
        """
        Check for overly long paragraphs.
        
        Returns:
            (has_long_paragraphs, list of issues)
        """
        paragraphs = text.split('\n\n')
        issues = []
        
        for i, para in enumerate(paragraphs):
            if not para.strip():
                continue
            
            # Count sentences (rough approximation)
            sentences = len(re.findall(r'[.!?]+', para))
            
            if sentences > self.MAX_SENTENCES_PER_PARAGRAPH:
                issues.append(
                    "Paragraph {} has {} sentences (max {})".format(
                        i + 1, sentences, self.MAX_SENTENCES_PER_PARAGRAPH
                    )
                )
        
        return (len(issues) > 0, issues)
    
    def check_response_length(self, text: str) -> Tuple[bool, str]:
        """
        Check if response is too long.
        
        Returns:
            (is_too_long, message)
        """
        if len(text) > self.MAX_RESPONSE_LENGTH:
            return (
                True,
                "Response is {} chars (max {})".format(
                    len(text), self.MAX_RESPONSE_LENGTH
                )
            )
        return (False, "")
    
    def check_professional_tone(self, text: str) -> Tuple[bool, str]:
        """
        Check if response has professional tone markers.
        
        Returns:
            (is_professional, message)
        """
        text_lower = text.lower()
        
        markers_found = sum(
            1 for marker in self.PROFESSIONAL_MARKERS
            if marker in text_lower
        )
        
        # Want at least 1-2 professional markers in a response
        if len(text) > 100 and markers_found == 0:
            return (
                False,
                "Response lacks professional tone markers"
            )
        
        return (True, "")
    
    def check_jargon_density(self, text: str) -> Tuple[bool, str]:
        """
        Check for excessive technical jargon.
        
        Returns:
            (has_excessive_jargon, message)
        """
        # Count technical terms
        jargon_patterns = [
            r'\bOEM\b',
            r'\bASM\b',
            r'\bRMAn\b',
            r'\bPGA\b',
            r'\bSGA\b',
            r'\bORA-\d+',
            r'\bv\$\w+',
            r'\bDBA_\w+',
            r'\bALL_\w+'
        ]
        
        jargon_count = sum(
            len(re.findall(pattern, text, re.IGNORECASE))
            for pattern in jargon_patterns
        )
        
        # Calculate jargon density
        word_count = len(text.split())
        if word_count > 0:
            density = jargon_count / word_count
            if density > 0.15:  # More than 15% jargon
                return (
                    True,
                    "High jargon density ({:.1%})".format(density)
                )
        
        return (False, "")
    
    def full_quality_check(self, text: str) -> QualityCheck:
        """
        Perform full quality check on a response.
        
        Returns QualityCheck with all issues and suggestions.
        """
        self._checks_performed += 1
        issues = []
        suggestions = []
        
        # Check panic language
        has_panic, panic_phrases = self.check_for_panic_language(text)
        if has_panic:
            issues.append("Contains panic language: {}".format(", ".join(panic_phrases)))
            suggestions.append("Replace panic phrases with calmer alternatives")
        
        # Check paragraph length
        has_long, long_issues = self.check_paragraph_length(text)
        if has_long:
            issues.extend(long_issues)
            suggestions.append("Break long paragraphs into 3-4 sentences each")
        
        # Check response length
        is_long, length_msg = self.check_response_length(text)
        if is_long:
            issues.append(length_msg)
            suggestions.append("Summarize key points more concisely")
        
        # Check professional tone
        is_professional, tone_msg = self.check_professional_tone(text)
        if not is_professional:
            issues.append(tone_msg)
            suggestions.append("Add professional qualifiers like 'based on data' or 'analysis suggests'")
        
        # Check jargon
        has_jargon, jargon_msg = self.check_jargon_density(text)
        if has_jargon:
            issues.append(jargon_msg)
            suggestions.append("Reduce technical jargon or add explanations")
        
        if issues:
            self._issues_found += 1
        
        return QualityCheck(
            passed=len(issues) == 0,
            issues=issues,
            suggestions=suggestions
        )
    
    def sanitize_response(self, text: str) -> str:
        """
        Apply all guardrails to sanitize a response.
        
        This is the main entry point for cleaning up responses.
        """
        result = text
        
        # Replace panic language
        result = self.calm_down_text(result)
        
        # Truncate if too long (preserve ending)
        if len(result) > self.MAX_RESPONSE_LENGTH:
            result = result[:self.MAX_RESPONSE_LENGTH - 50] + "...\n\n[Response truncated for brevity]"
        
        return result
    
    def format_for_senior_dba(self, text: str) -> str:
        """
        Format response for senior DBA audience.
        
        - Clear and direct
        - Technical but not overwhelming
        - Actionable when relevant
        """
        result = self.sanitize_response(text)
        
        # Add professional framing if missing
        is_professional, _ = self.check_professional_tone(result)
        if not is_professional and len(result) > 100:
            result = "Based on the available data:\n\n" + result
        
        return result
    
    def format_for_executive(self, text: str) -> str:
        """
        Format response for executive audience.
        
        - Very concise (under 500 chars)
        - Focus on impact and risk
        - No technical details
        """
        result = text
        
        # Remove technical jargon explanations
        result = re.sub(r'\([^)]*ORA-[^)]*\)', '', result)
        result = re.sub(r'\([^)]*v\$[^)]*\)', '', result)
        
        # Truncate for executive brevity
        if len(result) > 500:
            # Try to find a good break point
            sentences = re.split(r'[.!?]+', result)
            result = ""
            for sentence in sentences:
                if len(result) + len(sentence) < 450:
                    result += sentence.strip() + ". "
                else:
                    break
            result = result.strip()
            if not result.endswith('.'):
                result += "."
        
        return result
    
    def format_for_auditor(self, text: str, include_sources: bool = True) -> str:
        """
        Format response for auditor audience.
        
        - Include data sources
        - Show confidence levels
        - Traceable claims
        """
        result = self.sanitize_response(text)
        
        if include_sources:
            result += "\n\n---\n*This response is based on OEM data and is available for audit review.*"
        
        return result
    
    def get_stats(self) -> dict:
        """Get guardrail statistics."""
        return {
            "checks_performed": self._checks_performed,
            "issues_found": self._issues_found,
            "issue_rate": self._issues_found / max(1, self._checks_performed)
        }


# Singleton instance
LANGUAGE_GUARDRAILS = LanguageGuardrails()


# Convenience functions
def check_response_quality(text: str) -> QualityCheck:
    """Check response quality against guardrails."""
    return LANGUAGE_GUARDRAILS.full_quality_check(text)


def sanitize_response(text: str) -> str:
    """Sanitize response to meet guardrails."""
    return LANGUAGE_GUARDRAILS.sanitize_response(text)


def format_for_dba(text: str) -> str:
    """Format for senior DBA audience."""
    return LANGUAGE_GUARDRAILS.format_for_senior_dba(text)


def format_for_executive(text: str) -> str:
    """Format for executive audience."""
    return LANGUAGE_GUARDRAILS.format_for_executive(text)


def format_for_auditor(text: str) -> str:
    """Format for auditor audience."""
    return LANGUAGE_GUARDRAILS.format_for_auditor(text)
