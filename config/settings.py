# config/settings.py
"""
Configuration Management for OEM Incident Intelligence System

Handles database connection, storage backend, and system settings.
Python 3.6 compatible - no dataclasses, no f-strings.
"""

import os


class Settings(object):
    """
    Application settings with safe defaults.
    Can be overridden via environment variables or config file.
    """
    
    # =====================================================
    # DATABASE CONFIGURATION
    # =====================================================
    
    # Storage backend: 'sqlite' or 'postgresql'
    STORAGE_BACKEND = os.getenv('STORAGE_BACKEND', 'sqlite')
    
    # SQLite
    SQLITE_DB_PATH = os.getenv('SQLITE_DB_PATH', 'oem_incident_system.db')
    
    # PostgreSQL
    POSTGRESQL_HOST = os.getenv('POSTGRESQL_HOST', 'localhost')
    POSTGRESQL_PORT = int(os.getenv('POSTGRESQL_PORT', '5432'))
    POSTGRESQL_USER = os.getenv('POSTGRESQL_USER', 'oem_user')
    POSTGRESQL_PASSWORD = os.getenv('POSTGRESQL_PASSWORD', 'oem_password')
    POSTGRESQL_DB = os.getenv('POSTGRESQL_DB', 'oem_incident_intelligence')
    
    # =====================================================
    # DATA PATHS
    # =====================================================
    
    ALERTS_CSV_PATH = os.getenv('ALERTS_CSV_PATH', 'data/alerts/oem_alerts_raw.csv')
    METRICS_DIR_PATH = os.getenv('METRICS_DIR_PATH', 'data/metrics')
    
    # =====================================================
    # LEARNING & ANOMALY CONFIGURATION
    # =====================================================
    
    # Pattern learning lookback (days)
    PATTERN_LEARNING_DAYS = int(os.getenv('PATTERN_LEARNING_DAYS', '60'))
    
    # Anomaly detection z-score threshold
    ANOMALY_Z_THRESHOLD = float(os.getenv('ANOMALY_Z_THRESHOLD', '2.5'))
    
    # Rolling window for anomaly detection (minutes)
    ANOMALY_ROLLING_WINDOW_MINUTES = int(os.getenv('ANOMALY_ROLLING_WINDOW_MINUTES', '30'))
    
    # =====================================================
    # LOGGING
    # =====================================================
    
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'oem_system.log')
    
    # =====================================================
    # BOOTSTRAP FLAGS
    # =====================================================
    
    # If True, migrate CSV data to DB on startup
    AUTO_MIGRATE_CSV = os.getenv('AUTO_MIGRATE_CSV', 'true').lower() == 'true'
    
    # If True, clear existing DB before migration (CAREFUL!)
    CLEAR_DB_BEFORE_MIGRATE = os.getenv('CLEAR_DB_BEFORE_MIGRATE', 'false').lower() == 'true'
    
    # =====================================================
    # CLASS METHODS
    # =====================================================
    
    @classmethod
    def get_db_connection_string(cls):
        """
        Return appropriate connection string for configured backend.
        Python 3.6 safe - uses .format()
        """
        if cls.STORAGE_BACKEND == 'postgresql':
            return 'postgresql://{0}:{1}@{2}:{3}/{4}'.format(
                cls.POSTGRESQL_USER,
                cls.POSTGRESQL_PASSWORD,
                cls.POSTGRESQL_HOST,
                cls.POSTGRESQL_PORT,
                cls.POSTGRESQL_DB
            )
        else:  # sqlite
            return 'sqlite:///{0}'.format(cls.SQLITE_DB_PATH)
    
    @classmethod
    def get_sqlite_path(cls):
        """Return absolute path to SQLite database"""
        return cls.SQLITE_DB_PATH
    
    @classmethod
    def is_postgresql(cls):
        """Check if using PostgreSQL backend"""
        return cls.STORAGE_BACKEND == 'postgresql'
    
    @classmethod
    def is_sqlite(cls):
        """Check if using SQLite backend"""
        return cls.STORAGE_BACKEND == 'sqlite'
    
    @classmethod
    def get_alerts_csv_path(cls):
        """Return absolute path to alerts CSV"""
        return cls.ALERTS_CSV_PATH
    
    @classmethod
    def get_metrics_csv_path(cls):
        """Return absolute path to metrics CSV (first one)"""
        return os.path.join(cls.METRICS_DIR_PATH, 'oem_metrics.csv')
    
    @classmethod
    def get_metrics_dir_path(cls):
        """Return path to metrics directory"""
        return cls.METRICS_DIR_PATH
    
    # =====================================================
    # PHASE 3: SLA, REPORTING, REMEDIATION
    # =====================================================
    
    # SLA Tracking
    SLA_TRACKING_ENABLED = os.getenv('SLA_TRACKING_ENABLED', 'true').lower() == 'true'
    SLA_LOOKBACK_DAYS = int(os.getenv('SLA_LOOKBACK_DAYS', '7'))
    
    # Reporting
    REPORTING_ENABLED = os.getenv('REPORTING_ENABLED', 'true').lower() == 'true'
    REPORT_OUTPUT_DIR = os.getenv('REPORT_OUTPUT_DIR', 'reports')
    REPORT_SMTP_ENABLED = os.getenv('REPORT_SMTP_ENABLED', 'false').lower() == 'true'
    REPORT_SMTP_HOST = os.getenv('REPORT_SMTP_HOST', 'smtp.company.com')
    REPORT_SMTP_PORT = int(os.getenv('REPORT_SMTP_PORT', '25'))
    REPORT_EMAIL_FROM = os.getenv('REPORT_EMAIL_FROM', 'alerts@company.com')
    
    # Auto-Remediation
    REMEDIATION_ENABLED = os.getenv('REMEDIATION_ENABLED', 'true').lower() == 'true'
    AUTO_EXECUTE_REMEDIATION = os.getenv('AUTO_EXECUTE_REMEDIATION', 'false').lower() == 'true'
    REMEDIATION_MIN_CONFIDENCE = float(os.getenv('REMEDIATION_MIN_CONFIDENCE', '0.85'))
    REMEDIATION_DRY_RUN_DEFAULT = os.getenv('REMEDIATION_DRY_RUN_DEFAULT', 'true').lower() == 'true'


# Global settings instance
settings = Settings()
