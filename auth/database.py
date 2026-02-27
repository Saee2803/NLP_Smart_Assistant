import sqlite3
from pathlib import Path

# Absolute project root
BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "users.db"

def get_db():
    conn = sqlite3.connect(
        str(DB_PATH),
        check_same_thread=False
    )
    conn.row_factory = sqlite3.Row
    return conn

