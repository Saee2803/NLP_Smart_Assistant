from datetime import datetime
import re
from data_engine.target_normalizer import TargetNormalizer
from incident_engine.alert_type_classifier import classify_alert_type


class AlertNormalizer:
    """
    Normalizes raw OEM alert CSV rows into clean internal format
    Python 3.6 compatible - no f-strings, safe datetime parsing
    """

    # -------------------------------------------------
    # TIME PARSER
    # -------------------------------------------------
    @staticmethod
    def parse_time(val):
        """
        Parse alert time from various OEM formats.
        Python 3.6 safe - no f-strings, explicit exception handling.
        """
        if not val:
            return None

        val = str(val).strip()
        
        if not val:
            return None

        # Try common OEM datetime formats
        formats = [
            "%d-%m-%Y %H:%M",
            "%d-%m-%Y %H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%a %b %d %H:%M:%S %Y",  # OEM text format
        ]

        for fmt in formats:
            try:
                parsed = datetime.strptime(val, fmt)
                if parsed is not None:
                    return parsed
            except (ValueError, TypeError):
                # Try next format
                pass
            except Exception:
                # Catch any other exception
                pass

        # Fallback: extract timestamp from OEM message using regex
        match = re.search(
            r"([A-Z][a-z]{2} [A-Z][a-z]{2} \d{2} \d{2}:\d{2}:\d{2} \d{4})",
            val
        )
        if match:
            try:
                parsed = datetime.strptime(match.group(1), "%a %b %d %H:%M:%S %Y")
                if parsed is not None:
                    return parsed
            except (ValueError, TypeError):
                pass
            except Exception:
                pass

        # Failed to parse
        return None

    # -------------------------------------------------
    # MAIN NORMALIZER
    # -------------------------------------------------
    @staticmethod
    def normalize(rows):
        """
        Normalize raw CSV rows into standard alert format.
        Python 3.6 safe - explicit None checks, no modern syntax.
        """
        normalized = []

        if not rows:
            return normalized

        for row in rows:
            if not row or row is None:
                continue

            # =========================================
            # SEVERITY (with defensive checks)
            # =========================================
            severity_raw = row.get("alert_state")
            if severity_raw is None:
                severity_raw = ""
            
            severity = str(severity_raw).upper().strip()
            
            if severity not in ("CRITICAL", "WARNING", "INFO"):
                severity = "INFO"

            # =========================================
            # TARGET / HOST (CRITICAL: must not be empty)
            # =========================================
            target_name = row.get("target_name")
            host_name = row.get("host_name")
            
            # Priority: target_name > host_name > empty string
            if target_name:
                target_raw = str(target_name).strip()
            elif host_name:
                target_raw = str(host_name).strip()
            else:
                target_raw = ""

            # CRITICAL: Normalize target here
            target = TargetNormalizer.normalize(target_raw)
            
            # Skip alerts with no valid target (listener noise, empty, etc)
            if not target:
                continue

            # =========================================
            # MESSAGE (with defaults)
            # =========================================
            message_raw = row.get("message")
            if not message_raw:
                message_raw = row.get("alert_message")
            if not message_raw:
                message_raw = "Unknown OEM alert"
            
            message = str(message_raw)

            # =========================================
            # ISSUE TYPE (based on message keywords)
            # =========================================
            message_lower = message.lower()
            
            if "ORA-" in message or "Internal error" in message:
                issue_type = "INTERNAL_ERROR"
            elif "space" in message_lower:
                issue_type = "STORAGE"
            elif "cpu" in message_lower:
                issue_type = "CPU"
            elif "down" in message_lower or "unavailable" in message_lower:
                issue_type = "AVAILABILITY"
            else:
                issue_type = "OTHER"

            # =========================================
            # TARGET TYPE (with default)
            # =========================================
            target_type_raw = row.get("target_type")
            if target_type_raw:
                target_type = str(target_type_raw)
            else:
                target_type = "oracle_database"

            # =========================================
            # METRIC NAME (optional)
            # =========================================
            metric_raw = row.get("metric_name")
            metric = str(metric_raw) if metric_raw else None

            # =========================================
            # PARSE TIME (critical for incident aggregation)
            # =========================================
            alert_time_raw = row.get("alert_time")
            alert_time = AlertNormalizer.parse_time(alert_time_raw)

            # =========================================
            # DISPLAY ALERT TYPE (DBA-GRADE CLASSIFICATION)
            # Derives meaningful type from INTERNAL_ERROR + message
            # =========================================
            display_alert_type = classify_alert_type(issue_type, message)

            # Build normalized alert
            normalized_alert = {
                "time": alert_time,
                "target": target,
                "target_type": target_type,
                "host": str(host_name) if host_name else None,
                "severity": severity,
                "message": message,
                "metric": metric,
                "issue_type": issue_type,
                "display_alert_type": display_alert_type,
            }

            normalized.append(normalized_alert)

        return normalized

