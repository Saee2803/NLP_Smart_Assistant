# reasoning/db_scope_guard.py
"""
PHASE 7: STRICT DATABASE SCOPE ENFORCEMENT

Prevents cross-database data leakage in responses.

CRITICAL RULES:
1. If user asks about "MIDEVSTB" → NEVER show MIDEVSTBN data silently
2. If related databases are involved → explicitly state the relationship
3. All database filtering MUST be exact match (not substring)

This fixes the bug where "show alerts for MIDEVSTB" returned MIDEVSTBN data.

TRUST PRINCIPLE: Data is scoped correctly. No silent mixing.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
import re


@dataclass
class ScopeValidation:
    """Result of database scope validation."""
    is_valid: bool
    requested_database: str
    actual_databases: List[str]
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    relationship_note: str = None  # If related DBs found
    
    def to_display(self) -> str:
        if self.is_valid and not self.warnings:
            return ""
        
        lines = []
        if self.violations:
            lines.append("⚠️ **Scope Violations Detected:**")
            for v in self.violations:
                lines.append("- {}".format(v))
        
        if self.relationship_note:
            lines.append("\n📝 **Note:** {}".format(self.relationship_note))
        
        return "\n".join(lines)


class DBScopeGuard:
    """
    Enforces strict database scope in all queries and responses.
    
    ZERO TOLERANCE for cross-database leakage.
    """
    
    # Known database relationships (primary -> standby, etc.)
    KNOWN_RELATIONSHIPS = {
        "MIDEVSTB": ["MIDEVSTBN"],  # MIDEVSTBN is standby for MIDEVSTB
        "PRODDB": ["PRODDB_STANDBY"],
        "FINDB": ["FINDB_DR"],
    }
    
    # Reverse mapping for lookups
    REVERSE_RELATIONSHIPS = {}
    for primary, standbys in KNOWN_RELATIONSHIPS.items():
        for standby in standbys:
            REVERSE_RELATIONSHIPS[standby] = primary
    
    def __init__(self):
        self._scope_violations = []
    
    def validate_scope(
        self,
        requested_db: str,
        actual_dbs: List[str],
        allow_related: bool = False
    ) -> ScopeValidation:
        """
        Validate that response data matches the requested database scope.
        
        Args:
            requested_db: Database user asked about
            actual_dbs: Databases actually in the response data
            allow_related: Whether to allow related databases (with disclosure)
            
        Returns:
            ScopeValidation with any violations or warnings
        """
        if not requested_db:
            # No specific database requested - scope is global
            return ScopeValidation(
                is_valid=True,
                requested_database="ALL",
                actual_databases=actual_dbs
            )
        
        requested_upper = requested_db.upper()
        actual_upper = [db.upper() for db in actual_dbs]
        
        violations = []
        warnings = []
        relationship_note = None
        
        # Check for exact match
        exact_match_found = requested_upper in actual_upper
        
        # Check for related databases
        related_dbs = self.KNOWN_RELATIONSHIPS.get(requested_upper, [])
        related_dbs = [db.upper() for db in related_dbs]
        
        # Also check reverse - if they asked about standby, mention primary
        primary_db = self.REVERSE_RELATIONSHIPS.get(requested_upper)
        if primary_db:
            related_dbs.append(primary_db.upper())
        
        # Check each database in response
        for db in actual_upper:
            if db == requested_upper:
                # Exact match - OK
                continue
            elif db in related_dbs:
                # Related database - warn but allow with disclosure
                if allow_related:
                    warnings.append(
                        "Related database {} included in results".format(db)
                    )
                    relationship_note = self._build_relationship_note(requested_upper, db)
                else:
                    violations.append(
                        "Data from {} included when {} was requested".format(db, requested_upper)
                    )
            else:
                # Unrelated database - VIOLATION
                violations.append(
                    "SCOPE VIOLATION: {} data found when {} was requested".format(
                        db, requested_upper
                    )
                )
        
        is_valid = len(violations) == 0
        
        if violations:
            self._scope_violations.append({
                "requested": requested_upper,
                "actual": actual_upper,
                "violations": violations
            })
        
        return ScopeValidation(
            is_valid=is_valid,
            requested_database=requested_upper,
            actual_databases=actual_upper,
            violations=violations,
            warnings=warnings,
            relationship_note=relationship_note
        )
    
    def _build_relationship_note(self, primary: str, related: str) -> str:
        """Build a clear explanation of database relationship."""
        # Check if primary->standby or standby->primary
        if related in self.KNOWN_RELATIONSHIPS.get(primary, []):
            return "{} is affected. Related standby database {} also shows correlated errors.".format(
                primary, related
            )
        elif primary in self.KNOWN_RELATIONSHIPS.get(related, []):
            return "{} (standby) is affected. Primary database {} may also be impacted.".format(
                primary, related
            )
        else:
            return "{} and {} are related databases.".format(primary, related)
    
    def filter_alerts_strict(
        self,
        alerts: List[Dict],
        target_database: str
    ) -> Tuple[List[Dict], ScopeValidation]:
        """
        Filter alerts with STRICT database matching.
        
        MIDEVSTB should NOT match MIDEVSTBN.
        
        Returns:
            Tuple of (filtered_alerts, scope_validation)
        """
        if not target_database:
            return alerts, ScopeValidation(
                is_valid=True,
                requested_database="ALL",
                actual_databases=list(set(
                    (a.get("target") or a.get("target_name") or "").upper()
                    for a in alerts if a.get("target") or a.get("target_name")
                ))
            )
        
        target_upper = target_database.upper()
        filtered = []
        seen_dbs = set()
        
        for alert in alerts:
            alert_db = (alert.get("target") or alert.get("target_name") or "").upper()
            seen_dbs.add(alert_db)
            
            # STRICT MATCH - exact equality only
            if alert_db == target_upper:
                filtered.append(alert)
        
        # Validate scope
        filtered_dbs = list(set(
            (a.get("target") or a.get("target_name") or "").upper()
            for a in filtered if a.get("target") or a.get("target_name")
        ))
        
        validation = self.validate_scope(
            requested_db=target_database,
            actual_dbs=filtered_dbs
        )
        
        # Add note if we filtered out related databases
        related = self.KNOWN_RELATIONSHIPS.get(target_upper, [])
        related_in_data = [db for db in seen_dbs if db in [r.upper() for r in related]]
        
        if related_in_data and not filtered_dbs:
            validation.relationship_note = (
                "No alerts found for {}. Related database {} has alerts.".format(
                    target_upper, ", ".join(related_in_data)
                )
            )
        elif related_in_data:
            validation.relationship_note = (
                "Showing {} only. Related database {} also has alerts "
                "(not included in this response).".format(
                    target_upper, ", ".join(related_in_data)
                )
            )
        
        return filtered, validation
    
    def filter_incidents_strict(
        self,
        incidents: List[Dict],
        target_database: str
    ) -> Tuple[List[Dict], ScopeValidation]:
        """
        Filter incidents with STRICT database matching.
        """
        if not target_database:
            return incidents, ScopeValidation(
                is_valid=True,
                requested_database="ALL",
                actual_databases=list(set(
                    str(i.get("target") or i.get("database") or "").upper()
                    for i in incidents if i.get("target") or i.get("database")
                ))
            )
        
        target_upper = target_database.upper()
        filtered = []
        
        for incident in incidents:
            incident_db = str(incident.get("target") or incident.get("database") or "").upper()
            
            # STRICT MATCH
            if incident_db == target_upper:
                filtered.append(incident)
        
        filtered_dbs = list(set(
            str(i.get("target") or i.get("database") or "").upper()
            for i in filtered if i.get("target") or i.get("database")
        ))
        
        return filtered, self.validate_scope(target_database, filtered_dbs)
    
    def check_response_scope(
        self,
        response_text: str,
        requested_db: str
    ) -> ScopeValidation:
        """
        Check if a response text mentions databases outside the requested scope.
        
        Use this as a final safety check before returning a response.
        """
        if not requested_db:
            return ScopeValidation(
                is_valid=True,
                requested_database="ALL",
                actual_databases=[]
            )
        
        requested_upper = requested_db.upper()
        related = self.KNOWN_RELATIONSHIPS.get(requested_upper, [])
        related_upper = [r.upper() for r in related]
        
        # Find all database mentions in response
        # Look for patterns like **DBNAME** or DBNAME: or "DBNAME"
        db_pattern = r'\b([A-Z][A-Z0-9_]{3,}[A-Z0-9])\b'
        mentions = set(re.findall(db_pattern, response_text.upper()))
        
        # Filter to likely database names (heuristic)
        likely_dbs = [m for m in mentions if len(m) >= 5 and not m.startswith("HTTP")]
        
        violations = []
        for db in likely_dbs:
            if db == requested_upper:
                continue  # OK
            elif db in related_upper:
                continue  # Related, might be OK with disclosure
            elif "MIDEVSTB" in db or "PRODDB" in db or "FINDB" in db:
                # Looks like a database name - check if it's a violation
                if db != requested_upper and db not in related_upper:
                    violations.append(
                        "Response mentions {} but {} was requested".format(db, requested_upper)
                    )
        
        return ScopeValidation(
            is_valid=len(violations) == 0,
            requested_database=requested_upper,
            actual_databases=list(likely_dbs),
            violations=violations
        )
    
    def get_scope_violations(self) -> List[Dict]:
        """Get all recorded scope violations."""
        return self._scope_violations.copy()
    
    def clear_violations(self):
        """Clear recorded violations."""
        self._scope_violations = []


# Singleton instance
DB_SCOPE_GUARD = DBScopeGuard()


# Convenience functions
def validate_db_scope(requested_db: str, actual_dbs: List[str]) -> ScopeValidation:
    """Shorthand for DB_SCOPE_GUARD.validate_scope()"""
    return DB_SCOPE_GUARD.validate_scope(requested_db, actual_dbs)


def filter_by_database_strict(alerts: List[Dict], database: str) -> List[Dict]:
    """Filter alerts with strict database matching."""
    filtered, _ = DB_SCOPE_GUARD.filter_alerts_strict(alerts, database)
    return filtered
