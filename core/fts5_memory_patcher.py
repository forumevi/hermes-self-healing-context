import os
import sqlite3
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class MemoryPatcher:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def _get_connection(self) -> sqlite3.Connection:
        # MADDE 5: Lazy creation (register anında değil, ilk kullanımda oluştur)
        if self._conn is None:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(self.db_path)
            self._setup_fts5()
        return self._conn

    def _setup_fts5(self):
        self._conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS error_patterns 
            USING fts5(error_type, error_message, fix_pattern, context_patch)
        """)
        self._conn.commit()

    def query_patch(self, error_type: str, error_message: str) -> Optional[str]:
        conn = self._get_connection()
        query = "SELECT context_patch FROM error_patterns WHERE error_patterns MATCH ? LIMIT 1"
        cursor = conn.execute(query, (f'"{error_type}" OR "{error_message}"',))
        result = cursor.fetchone()
        return result[0] if result else None

    # MADDE 4: Bu fonksiyon artık runtime_interceptor tarafından çağrılacak
    def learn_from_outcome(self, error_type: str, error_message: str, fix_pattern: str, context_patch: str):
        conn = self._get_connection()
        conn.execute("""
            INSERT INTO error_patterns (error_type, error_message, fix_pattern, context_patch)
            VALUES (?, ?, ?, ?)
        """, (error_type, error_message, fix_pattern, context_patch))
        conn.commit()

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
