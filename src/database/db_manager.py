"""SQLite connection lifecycle and schema initialization."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from src.config import DATABASE_PATH


class DatabaseManager:
    """Open one connection per operation; schema.sql is the schema source."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = str(db_path if db_path is not None else DATABASE_PATH)

    def get_connection(self) -> sqlite3.Connection:
        """Return a connection owned by the caller (which must close it)."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Commit on success, roll back on failure, and always close."""
        conn = self.get_connection()
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def initialize_database(self, schema_file: Optional[str] = None) -> None:
        """Create tables idempotently from schema.sql; never rewrite old data."""
        schema_path = (
            Path(schema_file) if schema_file else Path(__file__).with_name("schema.sql")
        )
        schema = schema_path.read_text(encoding="utf-8")
        with self.connection() as conn:
            conn.executescript(schema)
