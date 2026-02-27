import sqlite3
from pathlib import Path

BASE_DIR = Path(_file_).resolve().parents[1]
DB_PATH = BASE_DIR / "users.db"

conn = sqlite3.connect(str(DB_PATH))
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL
)
""")

conn.commit()
conn.close()

print("✅ users table created successfully at", DB_PATH)
