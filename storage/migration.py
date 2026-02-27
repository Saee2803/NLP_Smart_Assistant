# storage/migration.py
"""
Migration script: Load CSV data into persistent database.

One-time bootstrap to migrate existing CSV data into the database.
Idempotent - can run multiple times safely (uses INSERT OR IGNORE).

Python 3.6 compatible.
"""

from datetime import datetime
from config.settings import settings
from storage.database import get_db
import os
import csv


class CSVMigration(object):
    """
    Migrates data from CSV files to database.
    """
    
    def __init__(self, db=None):
        """
        Initialize migration.
        
        Args:
            db: Database instance (optional, will get default if not provided)
        """
        self.db = db or get_db()
    
    # =====================================================
    # ALERT MIGRATION
    # =====================================================
    
    def migrate_alerts_csv(self, csv_path=None):
        """
        Load alerts from CSV file into database.
        
        Args:
            csv_path: Path to oem_alerts_raw.csv
        
        Returns:
            Number of alerts loaded
        """
        csv_path = csv_path or settings.get_alerts_csv_path()
        
        if not os.path.exists(csv_path):
            print("[!] Alerts CSV not found: {0}".format(csv_path))
            return 0
        
        count = 0
        try:
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        alert_time = row.get('alert_time', '')
                        target = row.get('target_name', '')
                        severity = row.get('alert_critical', 'LOW')
                        message = row.get('message', '')
                        issue_type = row.get('issue_type', 'UNKNOWN')
                        
                        if alert_time and target:
                            self.db.insert_alert(
                                alert_time=alert_time,
                                target=target,
                                severity=severity,
                                message=message,
                                issue_type=issue_type,
                                source='OEM_CSV'
                            )
                            count += 1
                            
                            if count % 10000 == 0:
                                print("[MIGRATE] Loaded {0} alerts...".format(count))
                    except Exception as e:
                        pass
        except Exception as e:
            print("[!] Error loading alerts CSV: {0}".format(str(e)))
        
        print("[OK] Migrated {0} alerts".format(count))
        return count
    
    # =====================================================
    # METRICS MIGRATION
    # =====================================================
    
    def migrate_metrics_csv(self, csv_path=None):
        """
        Load metrics from CSV file into database.
        
        Args:
            csv_path: Path to oem_metrics.csv or variant
        
        Returns:
            Number of metrics loaded
        """
        csv_path = csv_path or settings.get_metrics_csv_path()
        
        if not os.path.exists(csv_path):
            print("[!] Metrics CSV not found: {0}".format(csv_path))
            return 0
        
        count = 0
        try:
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        metric_time = row.get('metric_time', '') or row.get('timestamp', '')
                        target = row.get('target_name', '') or row.get('target', '')
                        metric_name = row.get('metric_name', '')
                        value = row.get('value', '')
                        metric_column = row.get('metric_column', '')
                        category = row.get('category', '')
                        
                        if metric_time and target and metric_name and value:
                            try:
                                val = float(value)
                                self.db.insert_metric(
                                    metric_time=metric_time,
                                    target=target,
                                    metric_name=metric_name,
                                    value=val,
                                    metric_column=metric_column,
                                    category=category
                                )
                                count += 1
                                
                                if count % 10000 == 0:
                                    print("[MIGRATE] Loaded {0} metrics...".format(count))
                            except (ValueError, TypeError):
                                pass
                    except Exception as e:
                        pass
        except Exception as e:
            print("[!] Error loading metrics CSV: {0}".format(str(e)))
        
        print("[OK] Migrated {0} metrics".format(count))
        return count
    
    # =====================================================
    # FULL MIGRATION
    # =====================================================
    
    def migrate_all(self, alerts_csv=None, metrics_csvs=None):
        """
        Perform complete CSV -> Database migration.
        
        Args:
            alerts_csv: Path to alerts CSV
            metrics_csvs: List of paths to metrics CSVs (or None for auto-detect)
        
        Returns:
            Dictionary with migration results
        """
        print("[MIGRATE] Starting CSV to Database migration")
        print("[MIGRATE] Storage backend: {0}".format(self.db.backend))
        
        results = {}
        
        # Migrate alerts
        alert_count = self.migrate_alerts_csv(alerts_csv)
        results['alerts'] = alert_count
        
        # Migrate metrics
        if metrics_csvs is None:
            # Auto-detect metrics CSVs
            metrics_dir = os.path.dirname(settings.get_metrics_csv_path())
            metrics_csvs = []
            
            for filename in os.listdir(metrics_dir):
                if filename.startswith('oem_metrics') and filename.endswith('.csv'):
                    metrics_csvs.append(os.path.join(metrics_dir, filename))
        
        metrics_count = 0
        for csv_path in metrics_csvs:
            metrics_count += self.migrate_metrics_csv(csv_path)
        
        results['metrics'] = metrics_count
        
        print("[OK] Migration complete!")
        print("[OK] Alerts: {0}, Metrics: {1}".format(results['alerts'], results['metrics']))
        
        return results
    
    # =====================================================
    # BOOTSTRAP CHECK
    # =====================================================
    
    def should_migrate(self):
        """
        Check if migration should run.
        
        Returns:
            True if database is empty and migration is needed
        """
        # Simple heuristic: if alerts table is empty, we need to migrate
        incidents = self.db.get_incidents(days=1)
        return len(incidents) == 0
    
    def run_if_needed(self):
        """
        Run migration only if database is empty.
        
        Returns:
            True if migration was run, False if skipped
        """
        if not self.should_migrate():
            print("[SKIP] Database already populated, skipping migration")
            return False
        
        if not settings.AUTO_MIGRATE_CSV:
            print("[SKIP] AUTO_MIGRATE_CSV is disabled")
            return False
        
        self.migrate_all()
        return True


# Standalone migration runner
if __name__ == '__main__':
    migration = CSVMigration()
    migration.migrate_all()
