# storage/database.py
"""
Database abstraction layer for OEM Incident Intelligence System.

Provides unified interface for both SQLite and PostgreSQL.
Manages CRUD operations for all entities.

Python 3.6 compatible - no dataclasses, no f-strings.
"""

import sqlite3
from datetime import datetime, timedelta
from config.settings import settings
from storage.schema import init_database


class Database(object):
    """
    Database abstraction layer.
    Supports SQLite (default) and PostgreSQL (optional).
    """
    
    def __init__(self):
        """Initialize database connection."""
        self.backend = settings.STORAGE_BACKEND
        self.conn = None
        self._connect()
    
    def _connect(self):
        """Establish database connection."""
        if self.backend == 'sqlite':
            self.conn = init_database(settings.get_sqlite_path())
            print("[OK] SQLite database connected: {0}".format(settings.get_sqlite_path()))
        else:
            # PostgreSQL fallback
            print("[!] PostgreSQL not yet implemented, using SQLite")
            self.conn = init_database(settings.get_sqlite_path())
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
    
    # =====================================================
    # ALERTS OPERATIONS
    # =====================================================
    
    def insert_alert(self, alert_time, target, severity, message, issue_type, source='OEM'):
        """Insert an alert into database."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO alerts 
                (alert_time, target, severity, message, issue_type, source)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (alert_time, target, severity, message, issue_type, source))
            self.conn.commit()
        except Exception as e:
            print("[!] Error inserting alert: {0}".format(str(e)))
    
    def get_alerts(self, target=None, days=7):
        """
        Retrieve alerts from database.
        
        Args:
            target: Optional database/target filter
            days: Look back N days (default 7)
        
        Returns:
            List of alert dictionaries
        """
        cursor = self.conn.cursor()
        
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        
        if target:
            cursor.execute("""
                SELECT * FROM alerts
                WHERE target = ? AND alert_time >= ?
                ORDER BY alert_time DESC
            """, (target, cutoff_time))
        else:
            cursor.execute("""
                SELECT * FROM alerts
                WHERE alert_time >= ?
                ORDER BY alert_time DESC
            """, (cutoff_time,))
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    # =====================================================
    # METRICS OPERATIONS
    # =====================================================
    
    def insert_metric(self, metric_time, target, metric_name, value, metric_column=None, category=None, severity=None):
        """Insert a metric into database."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO metrics 
                (metric_time, target, metric_name, metric_column, value, category, severity)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (metric_time, target, metric_name, metric_column, value, category, severity))
            self.conn.commit()
        except Exception as e:
            print("[!] Error inserting metric: {0}".format(str(e)))
    
    def get_metrics(self, target=None, days=7):
        """
        Retrieve metrics from database.
        
        Args:
            target: Optional database/target filter
            days: Look back N days
        
        Returns:
            List of metric dictionaries
        """
        cursor = self.conn.cursor()
        
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        
        if target:
            cursor.execute("""
                SELECT * FROM metrics
                WHERE target = ? AND metric_time >= ?
                ORDER BY metric_time DESC
            """, (target, cutoff_time))
        else:
            cursor.execute("""
                SELECT * FROM metrics
                WHERE metric_time >= ?
                ORDER BY metric_time DESC
            """, (cutoff_time,))
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    # =====================================================
    # INCIDENTS OPERATIONS
    # =====================================================
    
    def insert_incident(self, target, issue_type, severity, alert_count, first_seen, last_seen):
        """Insert an incident into database."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO incidents 
                (target, issue_type, severity, alert_count, first_seen, last_seen)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (target, issue_type, severity, alert_count, first_seen, last_seen))
            self.conn.commit()
        except Exception as e:
            print("[!] Error inserting incident: {0}".format(str(e)))
    
    def get_incidents(self, target=None, days=7):
        """Retrieve incidents from database."""
        cursor = self.conn.cursor()
        
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        
        if target:
            cursor.execute("""
                SELECT * FROM incidents
                WHERE target = ? AND first_seen >= ?
                ORDER BY first_seen DESC
            """, (target, cutoff_time))
        else:
            cursor.execute("""
                SELECT * FROM incidents
                WHERE first_seen >= ?
                ORDER BY first_seen DESC
            """, (cutoff_time,))
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    # =====================================================
    # PATTERNS OPERATIONS (NEW)
    # =====================================================
    
    def insert_pattern(self, target, pattern_type, pattern_value, incident_count, confidence, evidence):
        """Insert a discovered pattern."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO patterns 
                (target, pattern_type, pattern_value, incident_count, confidence, evidence, discovered_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (target, pattern_type, pattern_value, incident_count, confidence, evidence, datetime.utcnow()))
            self.conn.commit()
        except Exception as e:
            print("[!] Error inserting pattern: {0}".format(str(e)))
    
    def get_patterns(self, target=None):
        """Retrieve discovered patterns."""
        cursor = self.conn.cursor()
        
        if target:
            cursor.execute("""
                SELECT * FROM patterns WHERE target = ? ORDER BY confidence DESC
            """, (target,))
        else:
            cursor.execute("SELECT * FROM patterns ORDER BY confidence DESC")
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    # =====================================================
    # ANOMALIES OPERATIONS (NEW)
    # =====================================================
    
    def insert_anomaly(self, target, metric_name, anomaly_time, anomaly_score, baseline_value, observed_value, severity=None):
        """Insert a detected anomaly."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO anomalies 
                (target, metric_name, anomaly_time, anomaly_score, baseline_value, observed_value, severity)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (target, metric_name, anomaly_time, anomaly_score, baseline_value, observed_value, severity))
            self.conn.commit()
        except Exception as e:
            print("[!] Error inserting anomaly: {0}".format(str(e)))
    
    def get_anomalies(self, target=None, days=7):
        """Retrieve detected anomalies."""
        cursor = self.conn.cursor()
        
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        
        if target:
            cursor.execute("""
                SELECT * FROM anomalies
                WHERE target = ? AND anomaly_time >= ?
                ORDER BY anomaly_time DESC
            """, (target, cutoff_time))
        else:
            cursor.execute("""
                SELECT * FROM anomalies
                WHERE anomaly_time >= ?
                ORDER BY anomaly_time DESC
            """, (cutoff_time,))
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    # =====================================================
    # RECOMMENDATIONS OPERATIONS
    # =====================================================
    
    def insert_recommendation(self, issue_type, action, outcome):
        """Record a recommendation outcome."""
        try:
            cursor = self.conn.cursor()
            
            # Get or create recommendation
            cursor.execute("""
                SELECT * FROM recommendations WHERE issue_type = ? AND action = ?
            """, (issue_type, action))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update counts
                success_count = existing['success_count']
                failure_count = existing['failure_count']
                partial_count = existing['partial_count']
                
                if outcome == 'SUCCESS':
                    success_count += 1
                elif outcome == 'FAILED':
                    failure_count += 1
                else:
                    partial_count += 1
                
                total = success_count + failure_count + partial_count
                confidence = (success_count * 100.0 / total) if total > 0 else 0
                
                cursor.execute("""
                    UPDATE recommendations 
                    SET success_count=?, failure_count=?, partial_count=?, confidence=?, last_updated=?
                    WHERE issue_type=? AND action=?
                """, (success_count, failure_count, partial_count, confidence, datetime.utcnow(), issue_type, action))
            else:
                # Create new
                confidence = 100 if outcome == 'SUCCESS' else 0
                counts = {
                    'SUCCESS': (1, 0, 0),
                    'FAILED': (0, 1, 0),
                    'PARTIAL': (0, 0, 1)
                }
                success, failure, partial = counts.get(outcome, (0, 0, 0))
                
                cursor.execute("""
                    INSERT INTO recommendations 
                    (issue_type, action, success_count, failure_count, partial_count, confidence)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (issue_type, action, success, failure, partial, confidence))
            
            self.conn.commit()
        except Exception as e:
            print("[!] Error recording recommendation: {0}".format(str(e)))
    
    def get_recommendations(self, issue_type):
        """Get recommendations for an issue type."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM recommendations 
            WHERE issue_type = ?
            ORDER BY confidence DESC
        """, (issue_type,))
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    # =====================================================
    # AUDIT LOGGING
    # =====================================================
    
    def log_action(self, action, entity_type, entity_id, details, created_by='SYSTEM'):
        """Log an audit action."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO audit_logs (action, entity_type, entity_id, details, created_by)
                VALUES (?, ?, ?, ?, ?)
            """, (action, entity_type, entity_id, details, created_by))
            self.conn.commit()
        except Exception as e:
            print("[!] Error logging action: {0}".format(str(e)))


# Global database instance
_db = None


def get_db():
    """Get or create global database instance."""
    global _db
    if _db is None:
        _db = Database()
    return _db
