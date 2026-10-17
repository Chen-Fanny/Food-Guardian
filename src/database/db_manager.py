"""
SQLite Database Connection and Initialization Manager.
[Status: Under Development]
"""

import sqlite3
from typing import Optional
from src.config import DATABASE_PATH


class DatabaseManager:
    """Manages SQLite database connections and executes initialization scripts."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(DATABASE_PATH)

    def get_connection(self) -> sqlite3.Connection:
        """Create and return a new SQLite connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize_database(self, schema_file: Optional[str] = None) -> None:
        """
        Execute schema.sql to initialize database tables.
        [Planned - To be implemented during development phase]
        """
        raise NotImplementedError("Database initialization is planned for the development phase.")
