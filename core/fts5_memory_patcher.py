import sqlite3
import os
from typing import Optional

class MemoryPatcher:
    """
    Queries Hermes SQLite FTS5 long-term memory to fetch historical context 
    and construct dynamic mitigation patches during execution crashes.
    """
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.path.expanduser("~/.hermes/memory.db")

    def fetch_and_patch_context(self, error_type: str, error_message: str, traceback_str: str) -> str:
        search_query = f"{error_type} mock fixture loop"
        matched_knowledge = self._query_fts5(search_query)

        patch_payload = (
            f"\n--- [HERMES DYNAMIC SELF-HEALING CONTEXT INJECTED] ---\n"
            f"Detected Failure: {error_message}\n"
            f"Automated Recovery Context:\n"
            f"1. Verify mock fixture initialization (_skill_nudge_interval, _iters_since_skill).\n"
            f"2. Ensure sync execution loops do not await synchronous return values.\n"
            f"Historical Context Match: {matched_knowledge or 'Standard execution fallback applied.'}\n"
            f"-------------------------------------------------------\n"
        )
        return patch_payload

    def _query_fts5(self, query: str) -> Optional[str]:
        if not os.path.exists(self.db_path):
            return None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT content FROM memory_fts WHERE memory_fts MATCH ? LIMIT 1", (query,))
            row = cursor.fetchone()
            conn.close()
            return row[0] if row else None
        except Exception:
            return None
