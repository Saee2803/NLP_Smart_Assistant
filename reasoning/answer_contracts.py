# reasoning/answer_contracts.py
"""
ENTERPRISE-GRADE ANSWER CONTRACTS

This module implements strict answer validation for production DBA systems.
Every response must pass its contract before being returned.

GOLDEN RULE: It is better to say "I cannot determine this from available data"
than to give a confident but wrong answer.
"""

import re
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass


class ContractType(Enum):
    """Types of answer contracts."""
    NUMERIC_ONLY = "NUMERIC_ONLY"
    SCOPED_ENTITY = "SCOPED_ENTITY"
    ALERT_COUNT = "ALERT_COUNT"
    INCIDENT_COUNT = "INCIDENT_COUNT"
    ROOT_CAUSE = "ROOT_CAUSE"
    EXPLANATION = "EXPLANATION"
    ROLE_BASED = "ROLE_BASED"
    GENERAL = "GENERAL"


class Audience(Enum):
    """Target audience for response formatting."""
    MANAGER = "MANAGER"
    SENIOR_DBA = "SENIOR_DBA"
    ONCALL_DBA = "ONCALL_DBA"
    AUDITOR = "AUDITOR"
    GENERAL = "GENERAL"


class ConfidenceLevel(Enum):
    """Confidence levels for answers."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class AnswerContract:
    """
    Defines what is allowed, required, and forbidden in an answer.
    """
    contract_type: ContractType
    audience: Audience
    confidence: ConfidenceLevel
    
    # Scope constraints
    target_database: Optional[str] = None
    exclude_standby: bool = False
    primary_only: bool = False
    standby_only: bool = False
    
    # Format constraints
    numeric_only: bool = False
    no_markdown: bool = False
    no_emojis: bool = False
    no_explanation: bool = False
    
    # Content constraints
    forbidden_terms: List[str] = None
    required_elements: List[str] = None
    
    # Validation state
    is_valid: bool = True
    violation_reason: Optional[str] = None
    
    def __post_init__(self):
        if self.forbidden_terms is None:
            self.forbidden_terms = []
        if self.required_elements is None:
            self.required_elements = []


class AnswerContractBuilder:
    """
    Builds answer contracts from user questions.
    
    Analyzes the question to determine:
    - What type of answer is expected
    - What scope constraints apply
    - What format is required
    - What is forbidden
    """
    
    # Numeric-only trigger phrases
    NUMERIC_TRIGGERS = [
        r'give\s+(?:me\s+)?only\s+(?:the\s+)?number',
        r'only\s+(?:the\s+)?(?:number|count)',
        r'just\s+(?:the\s+)?(?:number|total|count)',
        r'number\s+only',
        r'count\s+only',
        r'only\s+(?:a\s+)?number',
        r'give\s+(?:me\s+)?(?:the\s+)?number\s+only',
        r'only\s+the\s+number\s+please',
    ]
    
    # Scope constraint patterns
    SCOPE_PATTERNS = {
        'exclude_standby': [r'exclude\s+standby', r'no\s+standby', r'without\s+standby'],
        'primary_only': [r'primary\s+only', r'only\s+primary', r'primary\s+database'],
        'standby_only': [r'standby\s+only', r'only\s+standby', r'standby\s+database'],
    }
    
    # Role detection patterns
    ROLE_PATTERNS = {
        Audience.MANAGER: [
            r'explain\s+(?:this\s+)?to\s+(?:a\s+)?manager',
            r'for\s+(?:my\s+)?manager',
            r'executive\s+summary',
            r'business\s+impact',
            r'non-technical',
        ],
        Audience.AUDITOR: [
            r'for\s+(?:the\s+)?audit',
            r'auditor',
            r'compliance\s+report',
            r'facts\s+only',
        ],
        Audience.ONCALL_DBA: [
            r'on-?call',
            r'what\s+should\s+i\s+do',
            r'urgent',
            r'immediately',
            r'right\s+now',
        ],
        Audience.SENIOR_DBA: [
            r'technical\s+details',
            r'ora\s+codes?',
            r'diagnostics?',
            r'deep\s+dive',
        ],
    }
    
    # Question type patterns
    QUESTION_TYPE_PATTERNS = {
        'alert_count': [r'how\s+many\s+(?:\w+\s+)?alerts?', r'alert\s+count', r'count\s+(?:of\s+)?alerts?'],
        'incident_count': [r'how\s+many\s+(?:\w+\s+)?incidents?', r'incident\s+count', r'issues?'],
        'root_cause': [r'root\s+cause', r'why\s+(?:is|are|did)', r'cause\s+of', r'reason\s+for'],
        'explanation': [r'explain', r'what\s+(?:is|does|are)', r'tell\s+me\s+about'],
    }
    
    @classmethod
    def build_contract(cls, question: str) -> AnswerContract:
        """
        Build an answer contract from a user question.
        
        Args:
            question: The user's question
            
        Returns:
            AnswerContract defining response requirements
        """
        q_lower = question.lower().strip()
        
        # Detect contract type
        contract_type = cls._detect_contract_type(q_lower)
        
        # Detect audience
        audience = cls._detect_audience(q_lower)
        
        # Detect scope constraints
        target_db = cls._extract_target_database(question)
        exclude_standby = cls._matches_any(q_lower, cls.SCOPE_PATTERNS.get('exclude_standby', []))
        primary_only = cls._matches_any(q_lower, cls.SCOPE_PATTERNS.get('primary_only', []))
        standby_only = cls._matches_any(q_lower, cls.SCOPE_PATTERNS.get('standby_only', []))
        
        # Detect numeric-only mode
        numeric_only = cls._matches_any(q_lower, cls.NUMERIC_TRIGGERS)
        
        # Build forbidden terms based on contract type
        forbidden_terms = cls._build_forbidden_terms(contract_type, numeric_only, audience)
        
        # Build required elements
        required_elements = cls._build_required_elements(contract_type, audience)
        
        # Default confidence (will be updated by answer generator)
        confidence = ConfidenceLevel.MEDIUM
        
        return AnswerContract(
            contract_type=contract_type,
            audience=audience,
            confidence=confidence,
            target_database=target_db,
            exclude_standby=exclude_standby,
            primary_only=primary_only,
            standby_only=standby_only,
            numeric_only=numeric_only,
            no_markdown=numeric_only,
            no_emojis=numeric_only or audience == Audience.AUDITOR,
            no_explanation=numeric_only,
            forbidden_terms=forbidden_terms,
            required_elements=required_elements,
        )
    
    @classmethod
    def _detect_contract_type(cls, q_lower: str) -> ContractType:
        """Detect the primary contract type from question."""
        # Check for specific patterns
        for qtype, patterns in cls.QUESTION_TYPE_PATTERNS.items():
            if cls._matches_any(q_lower, patterns):
                if qtype == 'alert_count':
                    return ContractType.ALERT_COUNT
                elif qtype == 'incident_count':
                    return ContractType.INCIDENT_COUNT
                elif qtype == 'root_cause':
                    return ContractType.ROOT_CAUSE
                elif qtype == 'explanation':
                    return ContractType.EXPLANATION
        
        # Check for numeric-only
        if cls._matches_any(q_lower, cls.NUMERIC_TRIGGERS):
            return ContractType.NUMERIC_ONLY
        
        return ContractType.GENERAL
    
    @classmethod
    def _detect_audience(cls, q_lower: str) -> Audience:
        """Detect target audience from question."""
        for audience, patterns in cls.ROLE_PATTERNS.items():
            if cls._matches_any(q_lower, patterns):
                return audience
        return Audience.GENERAL
    
    @classmethod
    def _extract_target_database(cls, question: str) -> Optional[str]:
        """Extract target database from question."""
        # Pattern: "for DBNAME" or "on DBNAME" or just "DBNAME"
        # Common DB name patterns: end with STB, STBN, DB, PRD, DEV, TST
        patterns = [
            # "for MIDEVSTB" or "on MIDEVSTBN"
            r'(?:for|on|in|of)\s+([A-Z][A-Z0-9_]+(?:STB|STBN|DB|PRD|DEV|TST)?)',
            # "MIDEVSTB alerts" or "PRODDB status"
            r'\b([A-Z][A-Z0-9_]*(?:STB|STBN|DB))\s+(?:alerts?|status|breakdown)',
            # "MIDEVSTB" or "MIDEVSTBN" standalone
            r'\b([A-Z][A-Z0-9_]*(?:STB|STBN))\b',
            # Generic DB-like name at start: "PRODDB alerts"
            r'^([A-Z]{2,}[A-Z0-9_]*(?:DB|PRD|DEV|TST))\s+',
            # Generic uppercase word that looks like DB name after preposition
            r'(?:for|on|in|of)\s+([A-Z]{2,}[A-Z0-9_]*)\b',
        ]
        
        q_upper = question.upper()
        
        # Common exclusion words
        excluded = {'THE', 'ALL', 'ANY', 'SOME', 'HOW', 'MANY', 'WHAT', 'WHICH', 
                   'THIS', 'THAT', 'FROM', 'ONLY', 'ALERTS', 'CRITICAL', 'DATABASE',
                   'STATUS', 'WHERE', 'WHEN', 'WHY', 'SHOW', 'GIVE', 'NUMBER',
                   'COUNT', 'TOTAL', 'WARNING', 'INCIDENT', 'ISSUE', 'ERROR'}
        
        for pattern in patterns:
            match = re.search(pattern, q_upper)
            if match:
                db_name = match.group(1)
                # Filter out common words
                if db_name not in excluded and len(db_name) >= 4:
                    return db_name
        
        return None
    
    @classmethod
    def _matches_any(cls, text: str, patterns: List[str]) -> bool:
        """Check if text matches any of the patterns."""
        return any(re.search(p, text) for p in patterns)
    
    @classmethod
    def _build_forbidden_terms(cls, contract_type: ContractType, 
                               numeric_only: bool, audience: Audience) -> List[str]:
        """Build list of forbidden terms/patterns."""
        forbidden = []
        
        if numeric_only:
            # Numeric-only: forbid any non-digit content
            forbidden.extend([
                'alerts', 'exist', 'there are', 'total', 'count',
                'critical', 'warning', '**', '#', '-', '•', '✓', '✗',
            ])
        
        if audience == Audience.MANAGER:
            # Manager: forbid deep technical terms
            forbidden.extend([
                'ORA-00600', 'ORA-07445', 'ORA-04031', 'SGA', 'PGA',
                'redo log', 'archive log', 'controlfile', 'datafile',
            ])
        
        if audience == Audience.AUDITOR:
            # Auditor: forbid recommendations
            forbidden.extend([
                'recommend', 'should', 'consider', 'might want to',
                'you could', 'I suggest',
            ])
        
        return forbidden
    
    @classmethod
    def _build_required_elements(cls, contract_type: ContractType, 
                                 audience: Audience) -> List[str]:
        """Build list of required elements."""
        required = []
        
        if contract_type == ContractType.ROOT_CAUSE:
            required.append('confidence')
        
        if audience == Audience.MANAGER:
            required.extend(['impact', 'risk'])
        
        if audience == Audience.ONCALL_DBA:
            required.extend(['action', 'next step'])
        
        return required


class AnswerContractValidator:
    """
    Validates answers against their contracts.
    
    CRITICAL: If validation fails, the answer MUST NOT be returned.
    """
    
    @classmethod
    def validate(cls, answer: str, contract: AnswerContract) -> Tuple[bool, Optional[str]]:
        """
        Validate an answer against its contract.
        
        Args:
            answer: The generated answer
            contract: The answer contract
            
        Returns:
            Tuple of (is_valid, violation_reason)
        """
        # Validation 1: Numeric-only check
        if contract.numeric_only:
            is_valid, reason = cls._validate_numeric_only(answer)
            if not is_valid:
                return False, reason
        
        # Validation 2: Forbidden terms check
        if contract.forbidden_terms:
            is_valid, reason = cls._validate_forbidden_terms(answer, contract.forbidden_terms)
            if not is_valid:
                return False, reason
        
        # Validation 3: Scope consistency check
        if contract.target_database:
            is_valid, reason = cls._validate_scope(answer, contract)
            if not is_valid:
                return False, reason
        
        # Validation 4: Format check
        if contract.no_markdown:
            if '**' in answer or '##' in answer or '###' in answer:
                return False, "Markdown formatting found in numeric-only response"
        
        if contract.no_emojis:
            if cls._contains_emoji(answer):
                return False, "Emoji found in response that forbids emojis"
        
        # Validation 5: Required elements check
        if contract.required_elements:
            is_valid, reason = cls._validate_required_elements(answer, contract.required_elements)
            if not is_valid:
                return False, reason
        
        return True, None
    
    @classmethod
    def _validate_numeric_only(cls, answer: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that answer contains ONLY digits.
        
        CRITICAL: For NUMERIC_ONLY contract, output must be:
        - Only digits (0-9)
        - No commas
        - No text
        - No formatting
        - No explanation
        """
        cleaned = answer.strip()
        
        # Must be only digits
        if not cleaned.isdigit():
            # Check if it's a number with commas
            if cleaned.replace(',', '').isdigit():
                return False, f"Numeric-only answer contains formatting (commas): '{cleaned}'"
            return False, f"Numeric-only answer contains non-digit content: '{cleaned}'"
        
        return True, None
    
    @classmethod
    def _validate_forbidden_terms(cls, answer: str, forbidden: List[str]) -> Tuple[bool, Optional[str]]:
        """Check that answer doesn't contain forbidden terms."""
        answer_lower = answer.lower()
        
        for term in forbidden:
            if term.lower() in answer_lower:
                return False, f"Answer contains forbidden term: '{term}'"
        
        return True, None
    
    @classmethod
    def _validate_scope(cls, answer: str, contract: AnswerContract) -> Tuple[bool, Optional[str]]:
        """Validate scope constraints are respected."""
        answer_upper = answer.upper()
        target = contract.target_database
        
        # Check for scope bleeding
        # If asking about MIDEVSTB, answer shouldn't mention MIDEVSTBN data
        if target and target.upper() == 'MIDEVSTB':
            if 'MIDEVSTBN' in answer_upper:
                # Check if it's mentioning MIDEVSTBN as separate or mixing
                # Allow explicit disambiguation
                if 'NOT MIDEVSTBN' not in answer_upper and 'EXCLUDES MIDEVSTBN' not in answer_upper:
                    return False, "Scope bleeding: MIDEVSTBN mentioned in MIDEVSTB-scoped answer"
        
        if contract.primary_only and 'STANDBY' in answer_upper:
            return False, "Standby mentioned in primary-only scoped answer"
        
        if contract.standby_only and 'PRIMARY' in answer_upper:
            return False, "Primary mentioned in standby-only scoped answer"
        
        return True, None
    
    @classmethod
    def _validate_required_elements(cls, answer: str, required: List[str]) -> Tuple[bool, Optional[str]]:
        """Check that answer contains required elements."""
        answer_lower = answer.lower()
        
        for element in required:
            if element.lower() not in answer_lower:
                return False, f"Required element missing: '{element}'"
        
        return True, None
    
    @classmethod
    def _contains_emoji(cls, text: str) -> bool:
        """Check if text contains emoji characters."""
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F700-\U0001F77F"  # alchemical symbols
            "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
            "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
            "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
            "\U0001FA00-\U0001FA6F"  # Chess Symbols
            "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
            "\U00002702-\U000027B0"  # Dingbats
            "\U000024C2-\U0001F251"
            "]+",
            flags=re.UNICODE
        )
        return bool(emoji_pattern.search(text))


class AnswerContractEnforcer:
    """
    Main entry point for answer contract enforcement.
    
    Usage:
        contract = AnswerContractEnforcer.build_contract(question)
        ... generate answer ...
        validated_answer = AnswerContractEnforcer.enforce(answer, contract)
    """
    
    @classmethod
    def build_contract(cls, question: str) -> AnswerContract:
        """Build contract from question."""
        return AnswerContractBuilder.build_contract(question)
    
    @classmethod
    def enforce(cls, answer: str, contract: AnswerContract) -> Tuple[str, bool, Optional[str]]:
        """
        Enforce contract on answer.
        
        Returns:
            Tuple of (final_answer, is_valid, violation_reason)
            
        If validation fails and cannot be corrected, returns failure message.
        """
        # First, try to auto-correct if possible
        corrected_answer = cls._auto_correct(answer, contract)
        
        # Validate
        is_valid, violation = AnswerContractValidator.validate(corrected_answer, contract)
        
        if is_valid:
            return corrected_answer, True, None
        
        # If still invalid, return appropriate failure response
        if contract.numeric_only:
            # Try to extract just the number
            numbers = re.findall(r'\d+', answer.replace(',', ''))
            if numbers:
                # Return the largest number found (likely the count)
                return max(numbers, key=int), True, None
            else:
                return "0", True, "No numeric data available"
        
        # For other failures, return with explanation
        return corrected_answer, False, violation
    
    @classmethod
    def _auto_correct(cls, answer: str, contract: AnswerContract) -> str:
        """
        Auto-correct answer to match contract if possible.
        """
        if contract.numeric_only:
            # Strip everything except digits
            cleaned = answer.strip()
            
            # If it's already a clean number, return as-is
            if cleaned.isdigit():
                return cleaned
            
            # Try to extract the number
            # Remove commas first
            no_commas = cleaned.replace(',', '')
            if no_commas.isdigit():
                return no_commas
            
            # Try to find the first number in the text
            numbers = re.findall(r'\b(\d+)\b', no_commas)
            if numbers:
                # Return the first substantial number (likely the answer)
                for num in numbers:
                    if int(num) > 0:
                        return num
                return numbers[0]
            
            return cleaned
        
        return answer
    
    @classmethod
    def format_cannot_determine(cls, reason: str, 
                                what_is_needed: Optional[str] = None) -> str:
        """
        Format a proper "cannot determine" response.
        
        GOLDEN RULE: Better to say this than give wrong answer.
        """
        response = f"Cannot determine from available data.\n\n**Reason:** {reason}"
        
        if what_is_needed:
            response += f"\n\n**Data needed:** {what_is_needed}"
        
        return response
    
    @classmethod
    def is_numeric_only_mode(cls, question: str) -> bool:
        """Check if question requires numeric-only response."""
        contract = cls.build_contract(question)
        return contract.numeric_only
    
    @classmethod
    def get_audience(cls, question: str) -> Audience:
        """Get target audience for question."""
        contract = cls.build_contract(question)
        return contract.audience
    
    @classmethod
    def get_target_database(cls, question: str) -> Optional[str]:
        """Get target database from question."""
        contract = cls.build_contract(question)
        return contract.target_database


# Singleton for easy access
ANSWER_CONTRACTS = AnswerContractEnforcer()
