# storage/schema.py
"""
Database schema definitions for OEM Incident Intelligence System.

Tables:
  - alerts: Normalized OEM alerts
  - metrics: Normalized OEM metrics
  - incidents: Aggregated incidents
  - rca_results: Root cause analysis results
  - recommendations: Recommended actions with outcomes
  - learning_feedback: Tracking of recommendation success
  - patterns: Learned incident patterns
  - anomalies: Detected metric anomalies
  - audit_logs: System audit trail

Python 3.6 compatible.
"""

import sqlite3
from datetime import datetime


class Schema(object):
    """
    Database schema definitions.
    Supports both SQLite and PostgreSQL via abstract SQL.
    """
    
    # =====================================================
    # ALERTS TABLE
    # =====================================================
    
    ALERTS_TABLE = """
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        alert_time TIMESTAMP NOT NULL,
        target VARCHAR(255) NOT NULL,
        severity VARCHAR(50) NOT NULL,
        message TEXT,
        issue_type VARCHAR(100),
        source VARCHAR(50),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(alert_time, target, message)
    )
    """
    
    # =====================================================
    # METRICS TABLE
    # =====================================================
    
    METRICS_TABLE = """
    CREATE TABLE IF NOT EXISTS metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        metric_time TIMESTAMP NOT NULL,
        target VARCHAR(255) NOT NULL,
        metric_name VARCHAR(255) NOT NULL,
        metric_column VARCHAR(255),
        value FLOAT NOT NULL,
        category VARCHAR(100),
        severity VARCHAR(50),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    
    # =====================================================
    # INCIDENTS TABLE
    # =====================================================
    
    INCIDENTS_TABLE = """
    CREATE TABLE IF NOT EXISTS incidents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        target VARCHAR(255) NOT NULL,
        issue_type VARCHAR(100),
        severity VARCHAR(50),
        alert_count INTEGER DEFAULT 1,
        first_seen TIMESTAMP NOT NULL,
        last_seen TIMESTAMP NOT NULL,
        status VARCHAR(50) DEFAULT 'OPEN',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(target, issue_type, severity, first_seen)
    )
    """
    
    # =====================================================
    # RCA RESULTS TABLE
    # =====================================================
    
    RCA_RESULTS_TABLE = """
    CREATE TABLE IF NOT EXISTS rca_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        incident_id INTEGER,
        target VARCHAR(255) NOT NULL,
        root_cause VARCHAR(255),
        confidence FLOAT,
        supporting_metrics TEXT,
        recommendation TEXT,
        analyzed_at TIMESTAMP NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    
    # =====================================================
    # RECOMMENDATIONS TABLE
    # =====================================================
    
    RECOMMENDATIONS_TABLE = """
    CREATE TABLE IF NOT EXISTS recommendations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        issue_type VARCHAR(100) NOT NULL,
        action VARCHAR(255) NOT NULL,
        success_count INTEGER DEFAULT 0,
        failure_count INTEGER DEFAULT 0,
        partial_count INTEGER DEFAULT 0,
        confidence FLOAT DEFAULT 0,
        last_updated TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(issue_type, action)
    )
    """
    
    # =====================================================
    # LEARNING FEEDBACK TABLE
    # =====================================================
    
    LEARNING_FEEDBACK_TABLE = """
    CREATE TABLE IF NOT EXISTS learning_feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        issue_type VARCHAR(100) NOT NULL,
        action VARCHAR(255) NOT NULL,
        outcome VARCHAR(50) NOT NULL,
        notes TEXT,
        recorded_at TIMESTAMP NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    
    # =====================================================
    # PATTERNS TABLE (NEW - for pattern learning)
    # =====================================================
    
    PATTERNS_TABLE = """
    CREATE TABLE IF NOT EXISTS patterns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        target VARCHAR(255) NOT NULL,
        pattern_type VARCHAR(50) NOT NULL,
        pattern_value VARCHAR(255),
        incident_count INTEGER,
        confidence FLOAT,
        evidence TEXT,
        discovered_at TIMESTAMP NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(target, pattern_type, pattern_value)
    )
    """
    
    # =====================================================
    # ANOMALIES TABLE (NEW - for anomaly detection)
    # =====================================================
    
    ANOMALIES_TABLE = """
    CREATE TABLE IF NOT EXISTS anomalies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        target VARCHAR(255) NOT NULL,
        metric_name VARCHAR(255) NOT NULL,
        anomaly_time TIMESTAMP NOT NULL,
        anomaly_score FLOAT NOT NULL,
        baseline_value FLOAT,
        observed_value FLOAT,
        severity VARCHAR(50),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    
    # =====================================================
    # AUDIT LOGS TABLE
    # =====================================================
    
    AUDIT_LOGS_TABLE = """
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action VARCHAR(100) NOT NULL,
        entity_type VARCHAR(50),
        entity_id INTEGER,
        details TEXT,
        created_by VARCHAR(100),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    
    # =====================================================
    # INDEXES FOR PERFORMANCE
    # =====================================================
    
    INDEXES = [
        "CREATE INDEX IF NOT EXISTS idx_alerts_target ON alerts(target)",
        "CREATE INDEX IF NOT EXISTS idx_alerts_time ON alerts(alert_time)",
        "CREATE INDEX IF NOT EXISTS idx_metrics_target ON metrics(target)",
        "CREATE INDEX IF NOT EXISTS idx_metrics_time ON metrics(metric_time)",
        "CREATE INDEX IF NOT EXISTS idx_incidents_target ON incidents(target)",
        "CREATE INDEX IF NOT EXISTS idx_incidents_time ON incidents(first_seen)",
        "CREATE INDEX IF NOT EXISTS idx_patterns_target ON patterns(target)",
        "CREATE INDEX IF NOT EXISTS idx_anomalies_target ON anomalies(target)",
        "CREATE INDEX IF NOT EXISTS idx_anomalies_time ON anomalies(anomaly_time)"
    ]
    
    # =====================================================
    # ALL TABLES (for initialization)
    # =====================================================
    
    ALL_TABLES = [
        ALERTS_TABLE,
        METRICS_TABLE,
        INCIDENTS_TABLE,
        RCA_RESULTS_TABLE,
        RECOMMENDATIONS_TABLE,
        LEARNING_FEEDBACK_TABLE,
        PATTERNS_TABLE,
        ANOMALIES_TABLE,
        AUDIT_LOGS_TABLE
    ]


def init_database(db_path):
    """
    Initialize SQLite database with all required tables.
    
    Args:
        db_path: Path to SQLite database file
    
    Returns:
        Connection object
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Create all tables
    for table_sql in Schema.ALL_TABLES:
        cursor.execute(table_sql)
    
    # Create indexes
    for index_sql in Schema.INDEXES:
        cursor.execute(index_sql)
    
    conn.commit()
    return conn


def init_database_postgresql(connection_string):
    """
    Initialize PostgreSQL database with all required tables.
    
    Args:
        connection_string: PostgreSQL connection string
    
    Note:
        Requires psycopg2 to be installed.
        Falls back to SQLite if import fails.
    """
    try:
        import psycopg2
        
        # Parse connection string
        # Format: postgresql://user:pass@host:port/dbname
        conn = psycopg2.connect(connection_string)
        cursor = conn.cursor()
        
        for table_sql in Schema.ALL_TABLES:
            cursor.execute(table_sql)
        
        for index_sql in Schema.INDEXES:
            cursor.execute(index_sql)
        
        conn.commit()
        conn.close()
        
        print("[OK] PostgreSQL database initialized")
        return True
        
    except ImportError:
        print("[!] psycopg2 not installed. Falling back to SQLite.")
        return False
    except Exception as e:
        print("[!] PostgreSQL initialization failed: {0}".format(str(e)))
        print("[!] Falling back to SQLite")
        return False
