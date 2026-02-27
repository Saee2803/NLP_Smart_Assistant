# storage/__init__.py
"""
Storage Module

Provides persistent data layer with database abstraction, schema management, and CSV migration.
Supports SQLite (default) and PostgreSQL (optional).
"""

from storage.database import Database, get_db
from storage.schema import init_database
from storage.migration import CSVMigration

__all__ = [
    'Database',
    'get_db',
    'init_database',
    'CSVMigration'
]
