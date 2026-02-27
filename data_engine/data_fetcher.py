import csv
import os
import re
from datetime import datetime, timedelta
from glob import glob

from incident_engine.alert_normalizer import AlertNormalizer
from incident_engine.incident_aggregator import IncidentAggregator
from data_engine.metrics_store import MetricStore

try:
    from oem_ingestion.xml_parser import OEMXMLParser
    XML_AVAILABLE = True
except ImportError:
    XML_AVAILABLE = False
    print("[!] XML parser not available, using CSV only")


# ===========================================
# PRODUCTION MODE DETECTION
# ===========================================
PRODUCTION_MODE = os.environ.get("RENDER", "false").lower() == "true" or \
                  os.environ.get("PRODUCTION", "false").lower() == "true" or \
                  os.environ.get("CLOUD_DEPLOY", "false").lower() == "true"


class DataFetcher:
    """
    Loads OEM data from XML (primary) or CSV (fallback):
    - XML: Parses OEM XML files from oem_ingestion/xml_samples/
    - CSV: Falls back to CSV if no XML found
    - DEMO: Uses demo data in production/cloud mode when no data files available
    - Prepares: normalized alerts, aggregated incidents, merged metrics
    
    Python 3.6 compatible:
    - No datetime.fromisoformat() (Python 3.7+)
    - No f-strings
    - Explicit exception handling
    """

    ALERTS_CSV = "data/alerts/oem_alerts_raw.csv"
    XML_DIR = "oem_ingestion/xml_samples"
    XML_PATTERN = "*.xml"
    
    # Configuration: CSV-first mode (enterprise standard)
    # Set to False to prefer CSV, True to prefer XML
    PREFER_XML = False

    # =================================================
    # DEMO DATA FOR CLOUD DEPLOYMENT
    # =================================================
    @staticmethod
    def _generate_demo_data():
        """
        Generate demo/sample data for cloud deployment.
        This allows the application to run without local CSV files.
        """
        now = datetime.now()
        demo_alerts = []
        
        # Sample database targets
        targets = ["PRODDB01", "PRODDB02", "DEVDB01", "TESTDB01", "HRDB01"]
        alert_types = [
            ("CPU_UTILIZATION", "High CPU usage detected", "Critical"),
            ("MEMORY_PRESSURE", "Memory pressure warning", "Warning"),
            ("TABLESPACE_FULL", "Tablespace usage critical", "Critical"),
            ("LISTENER_DOWN", "Database listener not responding", "Critical"),
            ("BACKUP_FAILED", "Backup job failed", "Warning"),
            ("LONG_RUNNING_QUERY", "Query running for extended period", "Info"),
            ("CONNECTION_SPIKE", "Unusual connection spike detected", "Warning"),
            ("REDO_LOG_SWITCH", "Frequent redo log switches", "Info"),
        ]
        
        for i in range(50):
            alert_time = now - timedelta(hours=i * 2, minutes=(i * 7) % 60)
            target = targets[i % len(targets)]
            alert_type, message, severity = alert_types[i % len(alert_types)]
            
            demo_alerts.append({
                "alert_time": alert_time.strftime("%d-%m-%Y %H:%M"),
                "target": target,
                "target_name": target,
                "alert_state": severity,
                "message": "{0}: {1} on {2}".format(alert_type, message, target),
                "source": "DEMO_DATA"
            })
        
        # Sample metrics
        demo_metrics = []
        metric_types = ["cpu_percent", "memory_percent", "disk_io", "active_sessions"]
        for i in range(100):
            metric_time = now - timedelta(hours=i)
            target = targets[i % len(targets)]
            metric = metric_types[i % len(metric_types)]
            value = 50 + (i % 40)  # Random-ish value between 50-90
            
            demo_metrics.append({
                "time": metric_time.strftime("%Y-%m-%d %H:%M:%S"),
                "target": target,
                "metric": metric,
                "value": value
            })
        
        print("[*] DEMO MODE: Generated {0} sample alerts and {1} metrics".format(
            len(demo_alerts), len(demo_metrics)
        ))
        
        return demo_alerts, demo_metrics

    # =================================================
    # MAIN FETCH
    # =================================================
    def fetch(self, filters=None):
        """
        Main data fetch pipeline.
        Tries XML first (primary source), falls back to CSV.
        Python 3.6 safe.
        """

        # -----------------------------
        # CONFIGURABLE: CSV-FIRST OR XML-FIRST
        # -----------------------------
        raw_alerts = []
        xml_metrics = []
        
        # ENTERPRISE MODE: CSV as primary source (OEM XML already converted upstream)
        if not self.PREFER_XML and os.path.exists(self.ALERTS_CSV):
            print("[*] CSV mode (primary): Loading OEM data from structured CSV files")
            try:
                with open(self.ALERTS_CSV, encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row:
                            raw_alerts.append(row)
            except IOError as e:
                msg = "Error reading CSV file {0}: {1}".format(self.ALERTS_CSV, str(e))
                raise IOError(msg)

            print("[*] Raw alerts read from CSV: {0}".format(len(raw_alerts)))
        
        # OPTIONAL: XML INGESTION (if enabled and CSV didn't provide data)
        elif XML_AVAILABLE and os.path.isdir(self.XML_DIR):
            xml_files = glob(os.path.join(self.XML_DIR, self.XML_PATTERN))
            if xml_files:
                print("[*] XML ingestion mode: Found {0} XML files".format(len(xml_files)))
                for xml_file in xml_files:
                    try:
                        parser = OEMXMLParser(xml_file)
                        events = parser.flatten_events()
                        
                        # Convert XML events to alert format
                        for event in events:
                            raw_alerts.append({
                                "alert_time": str(event.get("start_time", "")),
                                "target": event.get("database", "UNKNOWN"),
                                "alert_state": event.get("severity", "INFO"),
                                "message": event.get("message", ""),
                                "source": "OEM_XML"
                            })
                            
                            # Extract metrics from XML
                            metrics_data = event.get("metrics", {})
                            if metrics_data:
                                for metric_name, metric_value in metrics_data.items():
                                    if metric_value is not None:
                                        xml_metrics.append({
                                            "time": event.get("start_time"),
                                            "target": event.get("database"),
                                            "metric": metric_name,
                                            "value": metric_value
                                        })
                        
                        print("[OK] Parsed XML: {0} -> {1} events".format(
                            os.path.basename(xml_file), len(events)
                        ))
                    except Exception as e:
                        print("[!] XML parse error ({0}): {1}".format(
                            os.path.basename(xml_file), str(e)
                        ))
                
                if raw_alerts:
                    print("[*] Total raw alerts from XML: {0}".format(len(raw_alerts)))
        
        # FALLBACK: Use demo data in cloud/production mode
        demo_metrics = []
        if not raw_alerts:
            if PRODUCTION_MODE:
                print("[*] CLOUD DEPLOYMENT MODE: Using demo data (no local CSV/XML)")
                raw_alerts, demo_metrics = self._generate_demo_data()
            else:
                msg = "No data available: CSV not found and XML ingestion disabled/unavailable"
                raise FileNotFoundError(msg)

        # -----------------------------
        # NORMALIZE ALERTS
        # (AlertNormalizer is Python 3.6 compatible)
        # -----------------------------
        alerts = AlertNormalizer.normalize(raw_alerts)

        # Don't double-resolve time; AlertNormalizer already does it
        # The following code was redundant and caused issues:
        # for a in alerts:
        #     a["time"] = self._resolve_time(a)

        # Filter alerts with valid times (important for aggregation)
        valid_alerts = []
        for a in alerts:
            if a and a.get("time") is not None:
                valid_alerts.append(a)
        
        alerts = valid_alerts

        # -----------------------------
        # BUILD INCIDENTS
        # (Time-window aggregation: 10 min windows)
        # IncidentAggregator is Python 3.6 compatible
        # -----------------------------
        aggregator = IncidentAggregator(alerts)
        incidents = aggregator.build_incidents()

        # -----------------------------
        # LOAD + MERGE METRICS
        # -----------------------------
        metric_store = MetricStore()
        metrics = metric_store.all()
        
        # Merge XML metrics if available
        if xml_metrics:
            print("[*] Merging {0} metrics from XML".format(len(xml_metrics)))
            metrics.extend(xml_metrics)
        
        # Merge demo metrics if in demo mode
        if demo_metrics:
            print("[*] Merging {0} demo metrics".format(len(demo_metrics)))
            metrics.extend(demo_metrics)

        # -----------------------------
        # FINAL LOGS
        # -----------------------------
        print("===================================")
        print("[OK] Alerts normalized : {0}".format(len(alerts)))
        print("[OK] Incidents built   : {0}".format(len(incidents)))
        print("[OK] Metrics merged    : {0}".format(len(metrics)))
        print("===================================")

        return {
            "alerts": alerts,
            "incidents": incidents,
            "metrics": metrics
        }

    # =================================================
    # DEPRECATED: Time resolution moved to AlertNormalizer
    # =================================================
    def _resolve_time(self, alert):
        """
        DEPRECATED: AlertNormalizer.parse_time() handles this.
        Kept for backward compatibility.
        
        Resolve alert time from:
        1. alert_time column
        2. time column
        3. embedded message timestamp
        
        Python 3.6 safe - NO datetime.fromisoformat()
        """

        if not alert:
            return None
        
        # Get raw time value
        raw = alert.get("alert_time")
        if not raw:
            raw = alert.get("time")
        
        if not raw:
            return None
        
        raw_str = str(raw).strip()
        
        if not raw_str:
            return None

        # Try parsing with common formats first
        formats = [
            "%d-%m-%Y %H:%M",
            "%d-%m-%Y %H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%a %b %d %H:%M:%S %Y",
        ]
        
        for fmt in formats:
            try:
                parsed = datetime.strptime(raw_str, fmt)
                if parsed is not None:
                    return parsed
            except (ValueError, TypeError):
                pass
            except Exception:
                pass

        # Extract from message
        return self._extract_time_from_message(alert.get("message"))

    # =================================================
    # MESSAGE TIME EXTRACTION
    # =================================================
    def _extract_time_from_message(self, message):
        """
        Extract timestamp from OEM message text.
        Example OEM message:
        Mon Jun 23 10:06:16 2025
        
        Python 3.6 safe.
        """

        if not message:
            return None

        message_str = str(message)

        pattern = (
            r"([A-Z][a-z]{2}\s+"
            r"[A-Z][a-z]{2}\s+"
            r"\d{2}\s+"
            r"\d{2}:\d{2}:\d{2}\s+"
            r"\d{4})"
        )

        match = re.search(pattern, message_str)
        if not match:
            return None

        try:
            parsed = datetime.strptime(
                match.group(1),
                "%a %b %d %H:%M:%S %Y"
            )
            if parsed is not None:
                return parsed
        except (ValueError, TypeError):
            return None
        except Exception:
            return None
        
        return None


