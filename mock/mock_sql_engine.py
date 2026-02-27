# mock_sql_engine.py
# Dynamic mock SQL engine + alerts generator
import random
from datetime import datetime, timedelta

SEVERITIES = ["CRITICAL", "WARNING", "INFO"]
DBS = [
    ("FINDB", "DB-SERVER-01"),
    ("HRDB", "DB-SERVER-02"),
    ("PAYROLL", "DB-SERVER-03"),
    ("CRMDB", "DB-SERVER-04"),
    ("INVDB", "DB-SERVER-05")
]

def _now_str(delta_minutes=0):
    dt = datetime.now() - timedelta(minutes=delta_minutes)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def mock_sql_result(sql):
    """Return mock rows (list of dicts) based on SQL text heuristics"""
    s = (sql or "").lower()

    # Top cpu (v$sql & cpu)
    if "v$sql" in s and "cpu" in s:
        return [
            {"sql_id": f"{random.randint(1000,9999)}abcd", "cpu_time": random.randint(2000,20000)}
            for _ in range(5)
        ]

    # FRA usage
    if "v$recovery_file_dest" in s or "fra" in s:
        used = random.randint(20000, 42000)
        limit = max(used + random.randint(1000, 10000), used)
        used_pct = round(used/limit*100, 1)
        return [{"name": "FRA_DEST_01", "used_mb": used, "limit_mb": limit, "used_percent": used_pct}]

    # Tablespace usage
    if "dba_tablespace_usage_metrics" in s or "tablespace" in s:
        sample = [
            {"tablespace_name": "SYSTEM", "used_space": 9200, "tablespace_size": 10000, "used_percent": 92.0},
            {"tablespace_name": "SYSAUX", "used_space": 7800, "tablespace_size": 10000, "used_percent": 78.0},
            {"tablespace_name": "USERS", "used_space": 5200, "tablespace_size": 10000, "used_percent": 52.0},
        ]
        return sample

    # Blocking sessions / dba_blockers
    if "dba_blockers" in s or "blocking" in s or "lock" in s:
        return [
            {"sid": random.randint(100,999), "username": "APPS", "machine": "APP01"},
            {"sid": random.randint(100,999), "username": "HR", "machine": "WEB02"},
        ]

    # Active sessions
    if "from v$session" in s and "active" in s:
        return [
            {"username": "FIN_USER", "status": "ACTIVE", "machine": "APP01"},
            {"username": "HR_APP", "status": "ACTIVE", "machine": "WEB02"},
        ]

    # Sessions (all)
    if "from v$session" in s:
        return [
            {"username": "FIN_USER", "status": "ACTIVE"},
            {"username": "SYS", "status": "INACTIVE"},
            {"username": "CRM_APP", "status": "ACTIVE"},
        ]

    # Redo log switches
    if "v$log_history" in s or "redo log" in s:
        return [
            {"time": _now_str(60), "switches": random.randint(50,200)},
            {"time": _now_str(120), "switches": random.randint(10,100)},
        ]

    # DB size / dba_data_files
    if "dba_data_files" in s or "db size" in s:
        return [{"database": db, "size_gb": random.randint(50,500)} for db, _ in DBS[:3]]

    # Temp usage
    if "v$tempspace_usage" in s or "temp" in s:
        return [{"tablespace": "TEMP", "used_mb": random.randint(1000,8000), "free_mb": random.randint(500,4000)}]

    # Long running queries (elapsed_time)
    if "elapsed_time" in s or "long running" in s:
        return [
            {"sql_id": f"{random.randint(10000,99999)}", "elapsed_sec": random.randint(1800,7200)}
            for _ in range(3)
        ]

    # PGA / SGA / wait events / archive / backup
    if "v$pgastat" in s:
        return [{"total_pga_mb": 8200, "used_mb": random.randint(2000,7000)}]
    if "v$sga" in s:
        return [{"component": "Shared Pool", "size_mb": 6200}, {"component": "Buffer Cache", "size_mb": 8200}]
    if "v$system_event" in s or "wait event" in s:
        return [{"event": "db file sequential read", "waits": random.randint(10000,200000)}]
    if "archive" in s:
        return [{"log_seq": random.randint(4000,6000), "applied": random.choice(["YES","NO"])}]
    if "rman" in s or "backup" in s:
        return [{"status": random.choice(["COMPLETED","FAILED","RUNNING"]), "time": _now_str(30)}]

    # count(*)
    if "count(*)" in s or "count(" in s:
        return [{"active_sessions": random.randint(1,200)}]

    # growth trend
    if "dba_hist_tbspc_space_usage" in s or "growth trend" in s:
        base = random.randint(200,300)
        return [{"day": (datetime.now()-timedelta(days=i)).strftime("%Y-%m-%d"), "used_gb": base + i} for i in range(3)][::-1]

    # fallback
    return [{"error": "No mock data available for this SQL"}]


def generate_dynamic_alerts():
    """Return a JSON-like dict for /alerts endpoint with dynamic timestamps."""
    now = datetime.now()
    ongoing = []
    history = []

    # create 3 ongoing alerts (random)
    for i in range(3):
        db, server = random.choice(DBS)
        sev = random.choices(SEVERITIES, weights=[0.2, 0.3, 0.5])[0]
        msg = ""
        if sev == "CRITICAL":
            msg = random.choice([
                "CPU usage reached 98%",
                "FRA usage above 92%",
                "Redo log switch delay detected"
            ])
        elif sev == "WARNING":
            msg = random.choice([
                "Tablespace usage above 85%",
                "High temp usage observed",
                "Temp space growing"
            ])
        else:
            msg = random.choice(["Backup started successfully", "Archive log backup completed", "Checkpoint okay"])

        ongoing.append({
            "time": (now - timedelta(minutes=random.randint(0,20))).strftime("%Y-%m-%d %H:%M:%S"),
            "server": server,
            "database": db,
            "severity": sev,
            "message": msg
        })

    # history 4 entries
    for i in range(4):
        db, server = random.choice(DBS)
        history.append({
            "time": (now - timedelta(days=random.randint(1,7), hours=random.randint(0,23))).strftime("%Y-%m-%d %H:%M:%S"),
            "server": server,
            "database": db,
            "severity": random.choice(SEVERITIES),
            "message": random.choice([
                "Archive log backup completed",
                "Redo log switch observed",
                "Tablespace freed",
                "Backup failed with errors"
            ])
        })

    # top problematic dbs
    top = []
    for db, server in DBS[:3]:
        top.append({"database": db, "server": server, "issue_count": random.randint(3,25)})

    return {"ongoing": ongoing, "history": history, "top_problematic_databases": top}

