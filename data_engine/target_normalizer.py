# data_engine/target_normalizer.py
"""
CANONICAL TARGET NORMALIZATION

This module provides a single, deterministic normalization function
used across all data pipelines to ensure consistent target naming.

Python 3.6.8 compatible - no f-strings, explicit type handling.
"""


class TargetNormalizer(object):
    """
    Canonicalizes target/database names across the system.
    
    Handles:
    - Case normalization (mixed case -> UPPER)
    - Listener filtering (19CLISTENER_* -> None)
    - Alias mapping (MIDDEVSTBN -> MIDDEVSTB)
    - Deterministic mapping (same input -> same output)
    """
    
    # Explicit alias mappings: variants -> canonical name
    # This is production-safe and auditable
    ALIASES = {
        # Example: these all refer to the same database
        # "MIDDEVSTBN": "MIDDEVSTB",   # Uncomment if you have actual aliases
        # "MIDEVSTB": "MIDDEVSTB",     # Uncomment if you have actual aliases
    }
    
    @staticmethod
    def normalize(target):
        """
        Normalize a target name to canonical form.
        
        Args:
            target: raw target name (str or None)
            
        Returns:
            Canonical target name (str) or None if invalid
            
        Rules:
        1. None / empty string -> None
        2. Whitespace stripped
        3. Converted to UPPERCASE
        4. 19CLISTENER_* entries -> None (Oracle listener noise)
        5. Apply explicit alias mappings
        
        Deterministic: f(x) always returns same result for same x
        """
        
        # Rule 1: None or empty -> None
        if not target:
            return None
        
        # Convert to string and strip whitespace
        target_str = str(target).strip()
        
        if not target_str:
            return None
        
        # Rule 3: Uppercase
        canonical = target_str.upper()
        
        # Rule 4: Filter listener noise (Oracle 19c specific)
        if canonical.startswith("19CLISTENER"):
            return None
        
        # Rule 5: Apply alias mappings (explicit, auditable)
        if canonical in TargetNormalizer.ALIASES:
            canonical = TargetNormalizer.ALIASES[canonical]
        
        return canonical
    
    @staticmethod
    def equals(target1, target2):
        """
        Safe target equality check.
        
        Normalizes both inputs and compares canonical forms.
        
        Args:
            target1, target2: raw target names
            
        Returns:
            True if normalized forms are equal (and not None)
        """
        norm1 = TargetNormalizer.normalize(target1)
        norm2 = TargetNormalizer.normalize(target2)
        
        # Both must be non-None and equal
        if norm1 is None or norm2 is None:
            return False
        
        return norm1 == norm2
    
    @staticmethod
    def matches_alert(alert, target):
        """
        Check if an alert's target matches the given target name.
        
        STRICT MATCHING: MIDEVSTB does NOT match MIDEVSTBN
        
        Args:
            alert: dict with 'target' or 'target_name' key
            target: target name to match
            
        Returns:
            True if alert belongs to this exact target
        """
        if not alert or not target:
            return False
        
        # Get alert's target from either key
        alert_target = alert.get("target_name") or alert.get("target") or ""
        
        # Use strict equality check
        return TargetNormalizer.equals(alert_target, target)
    
    @staticmethod
    def filter_alerts_by_target(alerts, target):
        """
        Filter a list of alerts to only those matching the target.
        
        STRICT MATCHING: MIDEVSTB does NOT match MIDEVSTBN
        
        Args:
            alerts: list of alert dicts
            target: target name to filter by
            
        Returns:
            List of alerts matching the target exactly
        """
        if not alerts or not target:
            return []
        
        return [a for a in alerts if TargetNormalizer.matches_alert(a, target)]


# Module-level convenience function (for backward compatibility)
def normalize_target(target):
    """Shorthand for TargetNormalizer.normalize()"""
    return TargetNormalizer.normalize(target)
