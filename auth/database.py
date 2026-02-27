import sqlite3
import os

def get_db():
    # Render cloud writeable temp directory
    DB_PATH = os.path.join("/tmp", "users.db")
    
    conn = sqlite3.connect(
        DB_PATH,
        check_same_thread=False
    )
    
    conn.row_factory = sqlite3.Row
    
    # Create users table if not exists
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT
        )
    """)
    conn.commit()
    
    return conn