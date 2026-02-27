"""
ACTION RECOMMENDER - Recommends DBA remediation actions
"""
from datetime import datetime
from typing import Dict, List


class ActionRecommender:
    """Recommends DBA actions with commands."""
    
    ACTIONS = {
        "TABLESPACE_EXHAUSTION": {
            "immediate": [
                {"action": "Check tablespace usage", "command": "SELECT tablespace_name, ROUND(used_percent,2) pct FROM DBA_TABLESPACE_USAGE_METRICS WHERE used_percent > 85;"},
                {"action": "Find largest segments", "command": "SELECT owner, segment_name, ROUND(bytes/1024/1024/1024,2) gb FROM DBA_SEGMENTS ORDER BY bytes DESC FETCH FIRST 10 ROWS ONLY;"},
                {"action": "Check autoextend", "command": "SELECT file_name, autoextensible, ROUND(maxbytes/1024/1024/1024,2) max_gb FROM DBA_DATA_FILES;"}
            ],
            "remediation": [
                {"action": "Add datafile", "command": "ALTER TABLESPACE <TS> ADD DATAFILE SIZE 10G AUTOEXTEND ON;", "risk": "LOW"},
                {"action": "Enable autoextend", "command": "ALTER DATABASE DATAFILE '<FILE>' AUTOEXTEND ON MAXSIZE 32G;", "risk": "LOW"}
            ],
            "escalation": "Storage Team if no space available"
        },
        "INTERNAL_DATABASE_ERROR": {
            "immediate": [
                {"action": "Check alert log", "command": "tail -100 $ORACLE_BASE/diag/rdbms/*/*/trace/alert*.log | grep -A5 'ORA-600'"},
                {"action": "Get error details", "command": "SELECT * FROM V$DIAG_ALERT_EXT WHERE message_text LIKE '%ORA-600%' ORDER BY originating_timestamp DESC FETCH FIRST 5 ROWS ONLY;"},
                {"action": "Flush shared pool", "command": "ALTER SYSTEM FLUSH SHARED_POOL;"}
            ],
            "remediation": [
                {"action": "Search MOS for bug", "command": "MOS Search: ORA-600 [<args>]", "risk": "N/A"},
                {"action": "Apply patch", "command": "opatch apply <PATCH>", "risk": "HIGH"}
            ],
            "escalation": "Oracle SR for production impact"
        },
        "MEMORY_EXHAUSTION": {
            "immediate": [
                {"action": "Check SGA/PGA", "command": "SELECT name, ROUND(value/1024/1024/1024,2) gb FROM V$SGA UNION SELECT name, ROUND(value/1024/1024/1024,2) FROM V$PGASTAT WHERE name LIKE '%allocated%';"},
                {"action": "Find memory hogs", "command": "SELECT s.sid, s.username, ROUND(p.pga_alloc_mem/1024/1024,2) pga_mb FROM V$SESSION s JOIN V$PROCESS p ON s.paddr=p.addr ORDER BY p.pga_alloc_mem DESC FETCH FIRST 10 ROWS ONLY;"}
            ],
            "remediation": [
                {"action": "Flush shared pool", "command": "ALTER SYSTEM FLUSH SHARED_POOL;", "risk": "LOW"},
                {"action": "Kill session", "command": "ALTER SYSTEM KILL SESSION '<SID>,<SERIAL#>' IMMEDIATE;", "risk": "MEDIUM"}
            ],
            "escalation": "DBA Lead if persists"
        },
        "NETWORK_CONNECTIVITY": {
            "immediate": [
                {"action": "Check listener", "command": "lsnrctl status"},
                {"action": "Test TNS", "command": "tnsping <SERVICE>"},
                {"action": "Check listener log", "command": "tail -50 $ORACLE_BASE/diag/tnslsnr/*/listener/trace/listener.log"}
            ],
            "remediation": [
                {"action": "Restart listener", "command": "lsnrctl stop; lsnrctl start", "risk": "LOW"},
                {"action": "Register services", "command": "ALTER SYSTEM REGISTER;", "risk": "LOW"}
            ],
            "escalation": "Network Team"
        },
        "DATAGUARD_REPLICATION": {
            "immediate": [
                {"action": "Check DG status", "command": "DGMGRL> SHOW CONFIGURATION;"},
                {"action": "Check lag", "command": "SELECT name, value FROM V$DATAGUARD_STATS WHERE name LIKE '%lag%';"},
                {"action": "Check gap", "command": "SELECT * FROM V$ARCHIVE_GAP;"}
            ],
            "remediation": [
                {"action": "Switch logfile", "command": "ALTER SYSTEM ARCHIVE LOG CURRENT;", "risk": "LOW"},
                {"action": "Restart apply", "command": "ALTER DATABASE RECOVER MANAGED STANDBY DATABASE CANCEL; ALTER DATABASE RECOVER MANAGED STANDBY DATABASE USING CURRENT LOGFILE DISCONNECT;", "risk": "LOW"}
            ],
            "escalation": "DBA Lead for failover consideration"
        },
        "DATABASE_UNAVAILABLE": {
            "immediate": [
                {"action": "Check processes", "command": "ps -ef | grep pmon"},
                {"action": "Check alert log", "command": "tail -200 <ALERT_LOG> | grep -i 'shutdown\\|error'"},
                {"action": "Check OS resources", "command": "df -h; free -g; uptime"}
            ],
            "remediation": [
                {"action": "Startup database", "command": "sqlplus / as sysdba <<< 'STARTUP;'", "risk": "LOW"},
                {"action": "Startup mount", "command": "STARTUP MOUNT; ALTER DATABASE OPEN;", "risk": "MEDIUM"}
            ],
            "escalation": "IMMEDIATE to DBA Lead and Management"
        },
        "CPU_SATURATION": {
            "immediate": [
                {"action": "Find CPU sessions", "command": "SELECT sid, username, sql_id FROM V$SESSION WHERE status='ACTIVE' ORDER BY last_call_et DESC FETCH FIRST 10 ROWS ONLY;"},
                {"action": "Check parallel", "command": "SELECT username, sql_id, COUNT(*) px FROM V$PX_SESSION GROUP BY username, sql_id;"}
            ],
            "remediation": [
                {"action": "Kill runaway", "command": "ALTER SYSTEM KILL SESSION '<SID>,<SERIAL#>' IMMEDIATE;", "risk": "MEDIUM"},
                {"action": "Limit parallel", "command": "ALTER SYSTEM SET parallel_max_servers=<N>;", "risk": "MEDIUM"}
            ],
            "escalation": "DBA Lead"
        }
    }
    
    def recommend(self, decision: Dict, context: Dict = None) -> Dict:
        cause = decision.get("decision", "")
        actions = self.ACTIONS.get(cause, self.ACTIONS.get("INTERNAL_DATABASE_ERROR"))
        
        return {
            "cause": cause,
            "urgency": decision.get("action_urgency", "MEDIUM"),
            "immediate_actions": actions.get("immediate", []),
            "remediation": actions.get("remediation", []),
            "escalation": actions.get("escalation", "DBA Lead"),
            "context": context
        }
    
    def generate_runbook(self, decision: Dict, target: str) -> str:
        plan = self.recommend(decision, {"target": target})
        lines = [
            "=" * 60,
            "RUNBOOK: {} - {}".format(plan["cause"], target),
            "Urgency: {}".format(plan["urgency"]),
            "=" * 60,
            "\n## DIAGNOSTIC STEPS\n"
        ]
        for i, a in enumerate(plan["immediate_actions"], 1):
            lines.append("{}. {}".format(i, a["action"]))
            lines.append("   ```\n   {}\n   ```".format(a["command"]))
        
        lines.append("\n## REMEDIATION\n")
        for i, a in enumerate(plan["remediation"], 1):
            lines.append("{}. {} [Risk: {}]".format(i, a["action"], a.get("risk", "UNKNOWN")))
            lines.append("   ```\n   {}\n   ```".format(a["command"]))
        
        lines.append("\n## ESCALATION: {}".format(plan["escalation"]))
        return "\n".join(lines)
