# sla/sla_config.py
"""
SLA Configuration Management

Stores and retrieves SLA definitions per database/service.
Persisted to database for easy management.

Python 3.6 compatible.
"""


class SLAConfig(object):
    """
    SLA configuration definition.
    """
    
    def __init__(self, target, availability_pct=99.0, max_incidents=5, 
                 max_mttr_minutes=30, window='daily'):
        """
        Initialize SLA config.
        
        Args:
            target: Database/service name (e.g., 'FINDB', 'HRDB')
            availability_pct: Target availability % (0-100)
            max_incidents: Max incidents allowed in window
            max_mttr_minutes: Max MTTR in minutes
            window: Window type ('daily', 'weekly', 'monthly')
        """
        self.target = target
        self.availability_pct = availability_pct
        self.max_incidents = max_incidents
        self.max_mttr_minutes = max_mttr_minutes
        self.window = window
        self.enabled = True
    
    def to_dict(self):
        """Convert to dict for storage."""
        return {
            'target': self.target,
            'availability_pct': self.availability_pct,
            'max_incidents': self.max_incidents,
            'max_mttr_minutes': self.max_mttr_minutes,
            'window': self.window,
            'enabled': self.enabled
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create from dict."""
        obj = cls(
            target=data['target'],
            availability_pct=data.get('availability_pct', 99.0),
            max_incidents=data.get('max_incidents', 5),
            max_mttr_minutes=data.get('max_mttr_minutes', 30),
            window=data.get('window', 'daily')
        )
        obj.enabled = data.get('enabled', True)
        return obj


class SLAConfigManager(object):
    """
    Manages SLA configurations.
    Stores in database for persistence.
    """
    
    def __init__(self, db):
        """
        Initialize manager.
        
        Args:
            db: Database instance with query capability
        """
        self.db = db
        self._ensure_sla_table()
    
    def _ensure_sla_table(self):
        """Ensure SLA config table exists."""
        try:
            # Try to query - will fail if table doesn't exist
            self.db.query(
                'SELECT * FROM sla_configs LIMIT 1'
            )
        except Exception:
            # Create table if it doesn't exist
            self.db.execute('''
                CREATE TABLE IF NOT EXISTS sla_configs (
                    target TEXT PRIMARY KEY,
                    availability_pct REAL DEFAULT 99.0,
                    max_incidents INTEGER DEFAULT 5,
                    max_mttr_minutes INTEGER DEFAULT 30,
                    window TEXT DEFAULT 'daily',
                    enabled BOOLEAN DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
    
    def set_sla(self, config):
        """
        Store SLA config.
        
        Args:
            config: SLAConfig instance
        """
        self.db.execute(
            '''INSERT OR REPLACE INTO sla_configs 
               (target, availability_pct, max_incidents, max_mttr_minutes, window, enabled)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (config.target, config.availability_pct, config.max_incidents,
             config.max_mttr_minutes, config.window, config.enabled)
        )
    
    def get_sla(self, target):
        """
        Get SLA config for target.
        
        Args:
            target: Database/service name
        
        Returns:
            SLAConfig or None
        """
        try:
            result = self.db.query(
                'SELECT * FROM sla_configs WHERE target = ?',
                (target,)
            )
            
            if result:
                return SLAConfig.from_dict(result[0])
        except Exception:
            pass
        
        return None
    
    def get_all_slas(self):
        """
        Get all SLA configs.
        
        Returns:
            List of SLAConfig objects
        """
        try:
            results = self.db.query(
                'SELECT * FROM sla_configs WHERE enabled = 1'
            )
            
            return [SLAConfig.from_dict(r) for r in results]
        except Exception:
            return []
    
    def disable_sla(self, target):
        """Disable SLA tracking for target."""
        self.db.execute(
            'UPDATE sla_configs SET enabled = 0 WHERE target = ?',
            (target,)
        )
    
    def enable_sla(self, target):
        """Enable SLA tracking for target."""
        self.db.execute(
            'UPDATE sla_configs SET enabled = 1 WHERE target = ?',
            (target,)
        )


class SLAPresets(object):
    """Standard SLA presets."""
    
    @staticmethod
    def standard(target):
        """Standard SLA: 99% availability, 5 incidents, 30 min MTTR."""
        return SLAConfig(
            target=target,
            availability_pct=99.0,
            max_incidents=5,
            max_mttr_minutes=30,
            window='daily'
        )
    
    @staticmethod
    def critical(target):
        """Critical SLA: 99.9% availability, 2 incidents, 15 min MTTR."""
        return SLAConfig(
            target=target,
            availability_pct=99.9,
            max_incidents=2,
            max_mttr_minutes=15,
            window='daily'
        )
    
    @staticmethod
    def best_effort(target):
        """Best-effort SLA: 95% availability, 10 incidents, 60 min MTTR."""
        return SLAConfig(
            target=target,
            availability_pct=95.0,
            max_incidents=10,
            max_mttr_minutes=60,
            window='daily'
        )
