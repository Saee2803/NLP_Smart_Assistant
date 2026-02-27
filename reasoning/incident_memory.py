"""
Incident Memory Store - Phase 6 Component
==========================================
Historical learning from past incidents.

For each resolved or recurring incident, stores:
- Incident signature (error + DB + category)
- Alert volume
- Resolution outcome (manual tag or inferred)
- Time to stabilize
- DBA actions taken (descriptive, no SQL)

RULES:
- Uses probability language only
- Never guarantees outcomes
- Compares similar patterns, doesn't predict exact resolution
"""

import json
import os
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict


class IncidentSignature:
    """
    Creates unique signature for an incident.
    Used to match similar incidents across time.
    """
    
    @staticmethod
    def create(database: str, error_type: str, category: str) -> str:
        """
        Create a unique incident signature.
        Signature = hash of (database + error_type + category)
        """
        # Ensure all values are strings
        db = str(database or 'UNKNOWN').upper()
        err = str(error_type or 'UNKNOWN').upper()[:50]
        cat = str(category or 'GENERAL').upper()
        normalized = f"{db}|{err}|{cat}"
        return hashlib.md5(normalized.encode()).hexdigest()[:16]
    
    @staticmethod
    def create_fuzzy(error_type: str, category: str) -> str:
        """
        Create a fuzzy signature (database-independent).
        Used to find similar incidents across different databases.
        """
        err = str(error_type or 'UNKNOWN').upper()[:50]
        cat = str(category or 'GENERAL').upper()
        normalized = f"{err}|{cat}"
        return hashlib.md5(normalized.encode()).hexdigest()[:12]


class IncidentMemoryEntry:
    """
    Single incident memory entry.
    """
    
    def __init__(self, data: Dict = None):
        if data:
            self.signature = data.get('signature', '')
            self.fuzzy_signature = data.get('fuzzy_signature', '')
            self.database = data.get('database', '')
            self.error_type = data.get('error_type', '')
            self.category = data.get('category', '')
            self.first_seen = data.get('first_seen', '')
            self.last_seen = data.get('last_seen', '')
            self.alert_count = data.get('alert_count', 0)
            self.peak_alert_rate = data.get('peak_alert_rate', 0)  # alerts per hour
            self.resolution_outcome = data.get('resolution_outcome', 'unknown')
            self.time_to_stabilize_hours = data.get('time_to_stabilize_hours', 0)
            self.dba_actions = data.get('dba_actions', [])
            self.recurrence_count = data.get('recurrence_count', 1)
            self.notes = data.get('notes', '')
        else:
            self.signature = ''
            self.fuzzy_signature = ''
            self.database = ''
            self.error_type = ''
            self.category = ''
            self.first_seen = ''
            self.last_seen = ''
            self.alert_count = 0
            self.peak_alert_rate = 0
            self.resolution_outcome = 'unknown'
            self.time_to_stabilize_hours = 0
            self.dba_actions = []
            self.recurrence_count = 1
            self.notes = ''
    
    def to_dict(self) -> Dict:
        return {
            'signature': self.signature,
            'fuzzy_signature': self.fuzzy_signature,
            'database': self.database,
            'error_type': self.error_type,
            'category': self.category,
            'first_seen': self.first_seen,
            'last_seen': self.last_seen,
            'alert_count': self.alert_count,
            'peak_alert_rate': self.peak_alert_rate,
            'resolution_outcome': self.resolution_outcome,
            'time_to_stabilize_hours': self.time_to_stabilize_hours,
            'dba_actions': self.dba_actions,
            'recurrence_count': self.recurrence_count,
            'notes': self.notes
        }


class IncidentOutcome:
    """Resolution outcome types."""
    SELF_RESOLVED = 'self_resolved'      # Resolved without intervention
    MANUAL_RESOLVED = 'manual_resolved'  # DBA intervention needed
    ESCALATED = 'escalated'              # Needed escalation (Oracle Support, etc.)
    RECURRING = 'recurring'              # Keeps coming back
    UNKNOWN = 'unknown'                  # Outcome not determined


class IncidentMemoryStore:
    """
    Stores and retrieves incident memory.
    Enables learning from past incidents.
    
    SAFETY RULES:
    - Only stores factual observations
    - Never predicts exact outcomes
    - Uses probability language
    - Admits when insufficient history
    """
    
    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path or os.path.join(
            os.path.dirname(__file__), '..', 'data', 'incident_memory.json'
        )
        self.memory: Dict[str, IncidentMemoryEntry] = {}
        self.fuzzy_index: Dict[str, List[str]] = defaultdict(list)  # fuzzy_sig -> [signatures]
        self._load()
    
    def _load(self):
        """Load incident memory from storage."""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                
                for sig, entry_data in data.get('incidents', {}).items():
                    entry = IncidentMemoryEntry(entry_data)
                    self.memory[sig] = entry
                    if entry.fuzzy_signature:
                        self.fuzzy_index[entry.fuzzy_signature].append(sig)
        except Exception as e:
            print(f"[!] Could not load incident memory: {e}")
            self.memory = {}
            self.fuzzy_index = defaultdict(list)
    
    def _save(self):
        """Save incident memory to storage."""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            data = {
                'last_updated': datetime.now().isoformat(),
                'incident_count': len(self.memory),
                'incidents': {sig: entry.to_dict() for sig, entry in self.memory.items()}
            }
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[!] Could not save incident memory: {e}")
    
    def record_incident(self, database: str, error_type: str, category: str,
                       alert_count: int, first_seen: str, last_seen: str,
                       outcome: str = None, dba_actions: List[str] = None):
        """
        Record or update an incident in memory.
        """
        signature = IncidentSignature.create(database, error_type, category)
        fuzzy_sig = IncidentSignature.create_fuzzy(error_type, category)
        
        if signature in self.memory:
            # Update existing
            entry = self.memory[signature]
            entry.last_seen = last_seen
            entry.alert_count += alert_count
            entry.recurrence_count += 1
            if outcome:
                entry.resolution_outcome = outcome
            if dba_actions:
                entry.dba_actions = list(set(entry.dba_actions + dba_actions))
        else:
            # Create new
            entry = IncidentMemoryEntry()
            entry.signature = signature
            entry.fuzzy_signature = fuzzy_sig
            entry.database = database
            entry.error_type = error_type[:100]
            entry.category = category
            entry.first_seen = first_seen
            entry.last_seen = last_seen
            entry.alert_count = alert_count
            entry.resolution_outcome = outcome or IncidentOutcome.UNKNOWN
            entry.dba_actions = dba_actions or []
            entry.recurrence_count = 1
            
            self.memory[signature] = entry
            self.fuzzy_index[fuzzy_sig].append(signature)
        
        self._save()
    
    def find_similar(self, database: str, error_type: str, category: str) -> List[IncidentMemoryEntry]:
        """
        Find similar incidents in memory.
        First tries exact match, then fuzzy match.
        """
        similar = []
        
        # Exact match
        signature = IncidentSignature.create(database, error_type, category)
        if signature in self.memory:
            similar.append(self.memory[signature])
        
        # Fuzzy match (same error type/category, different database)
        fuzzy_sig = IncidentSignature.create_fuzzy(error_type, category)
        for sig in self.fuzzy_index.get(fuzzy_sig, []):
            if sig != signature and sig in self.memory:
                similar.append(self.memory[sig])
        
        return similar
    
    def get_historical_context(self, database: str, error_type: str, 
                               category: str) -> Dict:
        """
        Get historical context for an incident.
        Returns structured information with probability language.
        """
        similar = self.find_similar(database, error_type, category)
        
        context = {
            'has_history': len(similar) > 0,
            'similar_incidents': len(similar),
            'exact_matches': 0,
            'fuzzy_matches': 0,
            'typical_outcome': None,
            'typical_duration': None,
            'recurrence_pattern': None,
            'historical_insights': [],
            'confidence': 'LOW'
        }
        
        if not similar:
            context['historical_insights'].append(
                "No similar incidents found in memory. This appears to be a new pattern."
            )
            return context
        
        # Analyze similar incidents
        signature = IncidentSignature.create(database, error_type, category)
        outcomes = defaultdict(int)
        durations = []
        recurrences = []
        
        for entry in similar:
            if entry.signature == signature:
                context['exact_matches'] += 1
            else:
                context['fuzzy_matches'] += 1
            
            outcomes[entry.resolution_outcome] += 1
            if entry.time_to_stabilize_hours > 0:
                durations.append(entry.time_to_stabilize_hours)
            recurrences.append(entry.recurrence_count)
        
        # Determine typical outcome
        if outcomes:
            most_common = max(outcomes.items(), key=lambda x: x[1])
            context['typical_outcome'] = most_common[0]
            
            if most_common[0] == IncidentOutcome.SELF_RESOLVED:
                context['historical_insights'].append(
                    "Similar incidents have often resolved without intervention."
                )
            elif most_common[0] == IncidentOutcome.RECURRING:
                context['historical_insights'].append(
                    "This type of incident has a history of recurring."
                )
        
        # Typical duration
        if durations:
            avg_duration = sum(durations) / len(durations)
            context['typical_duration'] = avg_duration
            context['historical_insights'].append(
                f"Similar incidents typically stabilized within {avg_duration:.1f} hours."
            )
        
        # Recurrence pattern
        avg_recurrence = sum(recurrences) / len(recurrences) if recurrences else 1
        if avg_recurrence > 2:
            context['recurrence_pattern'] = 'frequent'
            context['historical_insights'].append(
                f"This pattern has recurred an average of {avg_recurrence:.1f} times."
            )
        
        # Set confidence
        if context['exact_matches'] >= 2:
            context['confidence'] = 'HIGH'
        elif context['exact_matches'] >= 1 or context['fuzzy_matches'] >= 3:
            context['confidence'] = 'MEDIUM'
        else:
            context['confidence'] = 'LOW'
        
        return context
    
    def format_historical_insight(self, database: str, error_type: str,
                                  category: str) -> str:
        """
        Format historical context as human-readable insight.
        Uses appropriate uncertainty language.
        """
        context = self.get_historical_context(database, error_type, category)
        
        if not context['has_history']:
            return ""
        
        lines = []
        lines.append("### 📚 Historical Context")
        lines.append("")
        
        if context['exact_matches'] > 0:
            lines.append(f"**Similar incidents observed:** {context['similar_incidents']} times")
            lines.append(f"- Same database: {context['exact_matches']}")
            lines.append(f"- Similar pattern elsewhere: {context['fuzzy_matches']}")
            lines.append("")
        
        for insight in context['historical_insights']:
            lines.append(f"- {insight}")
        
        lines.append("")
        lines.append(f"*Historical confidence: {context['confidence']}*")
        lines.append("")
        lines.append("*Note: Past patterns are indicative, not predictive. "
                    "Actual behavior may differ.*")
        
        return "\n".join(lines)
    
    def learn_from_current_data(self, incidents: List[Dict]):
        """
        Learn from current incident data.
        Updates memory with new observations.
        
        This is called to build up historical knowledge over time.
        """
        for incident in incidents:
            database = incident.get('database', 'UNKNOWN')
            error_type = incident.get('error_type', incident.get('message', ''))[:100]
            category = incident.get('category', 'GENERAL')
            alert_count = incident.get('alert_count', 1)
            
            # Handle first_seen/last_seen - convert datetime to string if needed
            first_seen = incident.get('first_seen', datetime.now())
            last_seen = incident.get('last_seen', datetime.now())
            
            # Convert to string if datetime
            if hasattr(first_seen, 'isoformat'):
                first_seen = first_seen.isoformat()
            elif not isinstance(first_seen, str):
                first_seen = str(first_seen)
                
            if hasattr(last_seen, 'isoformat'):
                last_seen = last_seen.isoformat()
            elif not isinstance(last_seen, str):
                last_seen = str(last_seen)
            
            # Infer outcome based on pattern
            pattern = incident.get('pattern', '')
            if isinstance(pattern, str):
                if 'stable' in pattern.lower() or 'decreasing' in pattern.lower():
                    outcome = IncidentOutcome.SELF_RESOLVED
                elif 'escalating' in pattern.lower():
                    outcome = IncidentOutcome.RECURRING
                else:
                    outcome = IncidentOutcome.UNKNOWN
            else:
                outcome = IncidentOutcome.UNKNOWN
            
            self.record_incident(
                database=database,
                error_type=error_type,
                category=category,
                alert_count=alert_count,
                first_seen=first_seen,
                last_seen=last_seen,
                outcome=outcome
            )
    
    def get_memory_stats(self) -> Dict:
        """Get statistics about incident memory."""
        return {
            'total_incidents': len(self.memory),
            'unique_patterns': len(self.fuzzy_index),
            'databases_tracked': len(set(e.database for e in self.memory.values())),
            'has_history': len(self.memory) > 0
        }


# Singleton instance
INCIDENT_MEMORY = IncidentMemoryStore()
