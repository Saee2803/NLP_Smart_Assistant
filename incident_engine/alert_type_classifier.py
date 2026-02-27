"""
Alert Type Classifier Module

Provides DBA-grade classification of Oracle OEM alerts.
Derives meaningful display types from generic INTERNAL_ERROR alerts
by parsing the message content for specific ORA error codes and patterns.

This module follows Oracle OEM conventions for error classification.
Python 3.6 compatible - no f-strings, explicit exception handling.
"""

import re


class AlertTypeClassifier:
    """
    Classifies Oracle alert messages into meaningful, DBA-readable categories.
    
    Designed to:
    - Parse ORA-600 internal errors with argument extraction
    - Identify ORA-7445 process crashes
    - Detect alert log access/write failures
    - Classify background process failures
    - Fallback gracefully for unknown patterns
    
    Usage:
        classifier = AlertTypeClassifier()
        display_type = classifier.classify(issue_type, message)
    """

    # =========================================================
    # ORA-600 ARGUMENT CATEGORIES (based on Oracle documentation)
    # Common ORA-600 argument ranges and their meanings
    # =========================================================
    ORA600_CATEGORIES = {
        # Memory / Buffer Cache issues
        (1000, 1999): "Memory Corruption",
        (2000, 2999): "Buffer Cache Issue",
        
        # Redo / Recovery
        (3000, 3999): "Redo Log Issue",
        (4000, 4999): "Recovery Issue",
        
        # Dictionary / Metadata
        (5000, 5999): "Dictionary Corruption",
        (6000, 6999): "Segment Issue",
        
        # Transaction / Undo
        (7000, 7999): "Transaction Issue",
        (8000, 8999): "Undo Issue",
        
        # SQL Execution
        (9000, 9999): "SQL Execution Issue",
        (10000, 10999): "Parse Issue",
        
        # Row Cache / Library Cache
        (11000, 11999): "Row Cache Issue",
        (12000, 12999): "Library Cache Issue",
        
        # Kernel / Internal
        (13000, 13999): "Kernel Issue",
        (14000, 14999): "Internal Allocation",
        (15000, 15999): "Index Issue",
        
        # Space Management
        (16000, 16999): "Space Management",
        (17000, 17999): "Block Corruption",
        
        # Enqueue / Lock
        (18000, 18999): "Enqueue Issue",
        (19000, 19999): "Lock Issue",
        
        # Generic high-number ranges
        (20000, 29999): "Internal Processing",
        (30000, 39999): "Server Process Issue",
    }

    # =========================================================
    # REGEX PATTERNS for message parsing
    # =========================================================
    PATTERNS = {
        # ORA-600 with brackets: ORA-600 [13011], ORA 600 [13011], etc.
        "ora600_bracketed": re.compile(
            r"ORA[-\s]?600\s*\[(\d+)\]",
            re.IGNORECASE
        ),
        
        # ORA-600 with parentheses: ORA-600 (13011)
        "ora600_parens": re.compile(
            r"ORA[-\s]?600\s*\((\d+)\)",
            re.IGNORECASE
        ),
        
        # Generic ORA-600 without argument
        "ora600_generic": re.compile(
            r"ORA[-\s]?600(?!\s*[\[\(])",
            re.IGNORECASE
        ),
        
        # ORA-7445 process crash with optional details
        "ora7445": re.compile(
            r"ORA[-\s]?7445\s*(?:\[([^\]]+)\])?",
            re.IGNORECASE
        ),
        
        # ORA-4031 shared pool exhaustion
        "ora4031": re.compile(
            r"ORA[-\s]?4031",
            re.IGNORECASE
        ),
        
        # ORA-4030 process memory
        "ora4030": re.compile(
            r"ORA[-\s]?4030",
            re.IGNORECASE
        ),
        
        # Alert log access failures
        "alert_log_access": re.compile(
            r"(?:alert\s*log|log\.xml).*(?:access|write|read|permission|denied|failed)",
            re.IGNORECASE
        ),
        
        # Alert log write specific
        "alert_log_write": re.compile(
            r"(?:write|append).*(?:alert|log)|(?:alert|log).*(?:write|append)",
            re.IGNORECASE
        ),
        
        # Background process crashes
        "bg_process_crash": re.compile(
            r"(?:background\s+process|SMON|PMON|DBW\d*|LGWR|CKPT|ARC\d*|RECO|MMON|MMNL).*(?:crash|fail|termin|abort|die)",
            re.IGNORECASE
        ),
        
        # Specific background process names
        "bg_process_name": re.compile(
            r"\b(SMON|PMON|DBW\d*|LGWR|CKPT|ARC\d*|RECO|MMON|MMNL|J\d{3}|CJQ\d*|SMCO)\b",
            re.IGNORECASE
        ),
        
        # Datafile / tablespace issues
        "datafile_issue": re.compile(
            r"(?:datafile|tablespace|dbf).*(?:error|corrupt|offline|missing)",
            re.IGNORECASE
        ),
        
        # ASM issues
        "asm_issue": re.compile(
            r"(?:ASM|diskgroup|ASM\s*disk).*(?:error|fail|offline|dismount)",
            re.IGNORECASE
        ),
        
        # Block corruption
        "block_corruption": re.compile(
            r"(?:block|corrupt|checksum).*(?:corrupt|error|invalid|bad)",
            re.IGNORECASE
        ),
        
        # Listener issues
        "listener_issue": re.compile(
            r"(?:listener|TNS|lsnr).*(?:fail|error|down|stop|refuse)",
            re.IGNORECASE
        ),
        
        # Archive log issues
        "archivelog_issue": re.compile(
            r"(?:archive|archivelog|ARC\d*).*(?:fail|error|stuck|destination)",
            re.IGNORECASE
        ),
        
        # Generic internal error (for messages that say "internal error")
        "internal_error_generic": re.compile(
            r"internal\s+error",
            re.IGNORECASE
        ),
    }

    # =========================================================
    # CLASSIFICATION METHODS
    # =========================================================
    
    @classmethod
    def classify(cls, issue_type, message):
        """
        Main classification method.
        
        Args:
            issue_type: Original issue type from OEM (e.g., "INTERNAL_ERROR")
            message: Full alert message text
        
        Returns:
            str: DBA-readable display alert type
        
        Python 3.6 compatible - no f-strings.
        """
        if not message:
            return issue_type or "Unknown Alert"
        
        message_str = str(message)
        
        # Only process INTERNAL_ERROR types (don't change other types)
        if issue_type and str(issue_type).upper() != "INTERNAL_ERROR":
            return issue_type
        
        # Try ORA-600 with argument first (most specific)
        result = cls._classify_ora600(message_str)
        if result:
            return result
        
        # Try ORA-7445
        result = cls._classify_ora7445(message_str)
        if result:
            return result
        
        # Try ORA-4031/4030 (memory issues)
        result = cls._classify_memory_errors(message_str)
        if result:
            return result
        
        # Try alert log issues
        result = cls._classify_alert_log(message_str)
        if result:
            return result
        
        # Try background process issues
        result = cls._classify_bg_process(message_str)
        if result:
            return result
        
        # Try other specific patterns
        result = cls._classify_other_patterns(message_str)
        if result:
            return result
        
        # Fallback for generic internal errors
        if cls.PATTERNS["internal_error_generic"].search(message_str):
            return "Oracle Internal Error"
        
        # Ultimate fallback
        return issue_type or "Oracle Internal Error"
    
    @classmethod
    def _classify_ora600(cls, message):
        """
        Classify ORA-600 errors with argument extraction.
        Returns detailed classification based on the error argument.
        """
        # Try bracketed format first: ORA-600 [13011]
        match = cls.PATTERNS["ora600_bracketed"].search(message)
        if match:
            arg = match.group(1)
            return cls._format_ora600(arg)
        
        # Try parentheses format: ORA-600 (13011)
        match = cls.PATTERNS["ora600_parens"].search(message)
        if match:
            arg = match.group(1)
            return cls._format_ora600(arg)
        
        # Generic ORA-600 without argument
        if cls.PATTERNS["ora600_generic"].search(message):
            return "ORA-600 – Internal Error"
        
        return None
    
    @classmethod
    def _format_ora600(cls, argument):
        """
        Format ORA-600 with argument and category.
        """
        try:
            arg_num = int(argument)
            category = cls._get_ora600_category(arg_num)
            return "ORA-600 [{0}] – {1}".format(argument, category)
        except (ValueError, TypeError):
            # Non-numeric argument (e.g., string codes)
            return "ORA-600 [{0}] – Internal Error".format(argument)
    
    @classmethod
    def _get_ora600_category(cls, arg_num):
        """
        Get the category description for an ORA-600 argument number.
        """
        for (low, high), category in cls.ORA600_CATEGORIES.items():
            if low <= arg_num <= high:
                return category
        return "Internal Error"
    
    @classmethod
    def _classify_ora7445(cls, message):
        """
        Classify ORA-7445 process crash errors.
        """
        match = cls.PATTERNS["ora7445"].search(message)
        if match:
            detail = match.group(1)
            if detail:
                # Truncate long details
                detail_short = detail[:30] if len(detail) > 30 else detail
                return "ORA-7445 [{0}] – Process Crash".format(detail_short)
            return "ORA-7445 – Process Crash"
        return None
    
    @classmethod
    def _classify_memory_errors(cls, message):
        """
        Classify memory-related ORA errors.
        """
        if cls.PATTERNS["ora4031"].search(message):
            return "ORA-4031 – Shared Pool Exhaustion"
        if cls.PATTERNS["ora4030"].search(message):
            return "ORA-4030 – Process Memory Error"
        return None
    
    @classmethod
    def _classify_alert_log(cls, message):
        """
        Classify alert log access/write issues.
        """
        if cls.PATTERNS["alert_log_write"].search(message):
            return "Alert Log Write Failure"
        if cls.PATTERNS["alert_log_access"].search(message):
            return "Alert Log Access Error"
        return None
    
    @classmethod
    def _classify_bg_process(cls, message):
        """
        Classify background process failures.
        """
        if cls.PATTERNS["bg_process_crash"].search(message):
            # Try to identify specific process
            proc_match = cls.PATTERNS["bg_process_name"].search(message)
            if proc_match:
                process = proc_match.group(1).upper()
                return "{0} Process Failure".format(process)
            return "Background Process Failure"
        return None
    
    @classmethod
    def _classify_other_patterns(cls, message):
        """
        Classify other specific patterns.
        """
        if cls.PATTERNS["block_corruption"].search(message):
            return "Block Corruption Detected"
        if cls.PATTERNS["datafile_issue"].search(message):
            return "Datafile Issue"
        if cls.PATTERNS["asm_issue"].search(message):
            return "ASM Disk Issue"
        if cls.PATTERNS["listener_issue"].search(message):
            return "Listener Issue"
        if cls.PATTERNS["archivelog_issue"].search(message):
            return "Archive Log Issue"
        return None
    
    # =========================================================
    # GROUPING AND AGGREGATION SUPPORT
    # =========================================================
    
    @classmethod
    def get_group_key(cls, display_alert_type):
        """
        Get a grouping key for similar alert types.
        Useful for history view aggregation.
        
        Examples:
            "ORA-600 [13011] – Kernel Issue" -> "ORA-600 Kernel Issue"
            "ORA-600 [13094] – Kernel Issue" -> "ORA-600 Kernel Issue"
            "ORA-7445 [kgepop] – Process Crash" -> "ORA-7445 Process Crash"
        """
        if not display_alert_type:
            return "Unknown"
        
        display_str = str(display_alert_type)
        
        # ORA-600 grouping: extract category
        ora600_match = re.match(r"ORA-600\s*\[[^\]]+\]\s*–\s*(.+)", display_str)
        if ora600_match:
            category = ora600_match.group(1)
            return "ORA-600 {0}".format(category)
        
        # ORA-7445 grouping
        if display_str.startswith("ORA-7445"):
            return "ORA-7445 Process Crash"
        
        # Process failures grouping
        if "Process Failure" in display_str:
            return "Background Process Failure"
        
        # Alert log grouping
        if "Alert Log" in display_str:
            return "Alert Log Issue"
        
        # Return as-is for other types
        return display_str
    
    @classmethod
    def extract_ora_code(cls, message):
        """
        Extract the primary ORA error code from a message.
        Returns tuple (code, argument) or (None, None).
        
        Examples:
            "ORA-600 [13011]" -> ("ORA-600", "13011")
            "ORA-7445 [kgepop]" -> ("ORA-7445", "kgepop")
            "ORA-4031" -> ("ORA-4031", None)
        """
        if not message:
            return (None, None)
        
        message_str = str(message)
        
        # ORA-600 with argument
        match = cls.PATTERNS["ora600_bracketed"].search(message_str)
        if match:
            return ("ORA-600", match.group(1))
        
        match = cls.PATTERNS["ora600_parens"].search(message_str)
        if match:
            return ("ORA-600", match.group(1))
        
        # ORA-7445
        match = cls.PATTERNS["ora7445"].search(message_str)
        if match:
            return ("ORA-7445", match.group(1))
        
        # ORA-4031/4030
        if cls.PATTERNS["ora4031"].search(message_str):
            return ("ORA-4031", None)
        if cls.PATTERNS["ora4030"].search(message_str):
            return ("ORA-4030", None)
        
        # Generic ORA-600
        if cls.PATTERNS["ora600_generic"].search(message_str):
            return ("ORA-600", None)
        
        return (None, None)


# =========================================================
# MODULE-LEVEL CONVENIENCE FUNCTION
# =========================================================

def classify_alert_type(issue_type, message):
    """
    Convenience function for classifying alert types.
    
    Args:
        issue_type: Original issue type (e.g., "INTERNAL_ERROR")
        message: Alert message text
    
    Returns:
        str: DBA-readable display alert type
    """
    return AlertTypeClassifier.classify(issue_type, message)


def get_alert_group_key(display_alert_type):
    """
    Convenience function for getting grouping key.
    
    Args:
        display_alert_type: The classified display type
    
    Returns:
        str: Grouping key for aggregation
    """
    return AlertTypeClassifier.get_group_key(display_alert_type)
