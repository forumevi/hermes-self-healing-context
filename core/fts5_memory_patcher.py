import os
import sqlite3
import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class MemoryPatcher:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._fts5_initialized = False

    def _get_connection(self) -> sqlite3.Connection:
        if self._conn is None:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(self.db_path)
        return self._conn

    def _setup_fts5(self):
        if self._fts5_initialized:
            return
        try:
            self._conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS error_patterns 
                USING fts5(tool_name, error_type, error_message, fix_pattern, context_patch)
            """)
            self._conn.commit()
            self._fts5_initialized = True
        except sqlite3.OperationalError as e:
            if "already exists" in str(e):
                self._fts5_initialized = True
            else:
                raise

    @staticmethod
    def _sanitize_fts5_input(text: str) -> str:
        """FTS5 MATCH syntax'ı için özel karakterleri temizle."""
        text = text.replace('"', '').replace("'", '')
        text = text.replace(';', '').replace('--', '')
        text = re.sub(r'[^\w\s]', ' ', text)
        return text.strip()

    def query_patch(self, tool_name: str, error_type: str, error_message: str) -> Optional[str]:
        conn = self._get_connection()
        self._setup_fts5()
        
        safe_tool = self._sanitize_fts5_input(tool_name)
        safe_type = self._sanitize_fts5_input(error_type)
        safe_msg = self._sanitize_fts5_input(error_message)
        
        if not safe_tool or (not safe_type and not safe_msg):
            return None
        
        query = "SELECT context_patch FROM error_patterns WHERE error_patterns MATCH ? LIMIT 1"
        search_term = f'"{safe_type}" OR "{safe_msg}"' if safe_type and safe_msg else f'"{safe_type or safe_msg}"'
        search_term = f'tool_name:"{safe_tool}" AND ({search_term})'
        
        try:
            cursor = conn.execute(query, (search_term,))
            result = cursor.fetchone()
            return result[0] if result else None
        except sqlite3.OperationalError:
            return None

    def learn_from_outcome(self, tool_name: str, error_type: str, error_message: str, fix_pattern: str, context_patch: str):
        conn = self._get_connection()
        self._setup_fts5()
        conn.execute("""
            INSERT INTO error_patterns (tool_name, error_type, error_message, fix_pattern, context_patch)
            VALUES (?, ?, ?, ?, ?)
        """, (tool_name, error_type, error_message, fix_pattern, context_patch))
        conn.commit()

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
            self._fts5_initialized = False