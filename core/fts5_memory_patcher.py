"""
FTS5 Memory Patcher with Connection Pooling and Learning.

Queries SQLite FTS5 memory for historical error fix patterns
and generates context patches for dynamic injection.

Uses content table pattern for proper FTS5 INSERT support.
"""

import sqlite3
import hashlib
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import contextmanager


class MemoryPatcher:
    """
    Queries Hermes Agent's FTS5 memory database for error fix patterns.
    
    Features:
    - Connection pooling for performance
    - Query result caching
    - Confidence scoring based on pattern similarity
    - Learning from successful/unsuccessful patches
    - SQL injection prevention
    - Content table pattern for proper FTS5 support
    """
    
    def __init__(
        self,
        db_path: Optional[str] = None,
        enable_learning: bool = True,
        max_cache_size: int = 1000,
        cache_ttl: int = 300
    ):
        self.db_path = db_path or str(Path.home() / ".hermes" / "memory.db")
        self.enable_learning = enable_learning
        self.max_cache_size = max_cache_size
        self.cache_ttl = cache_ttl
        
        # Connection pool (single connection for now, can be extended)
        self._conn: Optional[sqlite3.Connection] = None
        self._ensure_fts5_tables()
        
        # Query cache
        self._cache: Dict[str, Dict[str, Any]] = {}
        
        print(f"[MemoryPatcher] Initialized with db_path={self.db_path}")

    @contextmanager
    def _get_connection(self):
        """Context manager for safe connection handling."""
        if self._conn is None:
            try:
                self._conn = sqlite3.connect(self.db_path, timeout=5.0)
                self._conn.row_factory = sqlite3.Row
            except sqlite3.Error as e:
                print(f"[MemoryPatcher] Failed to connect: {e}")
                raise
        
        try:
            yield self._conn
        except sqlite3.Error as e:
            print(f"[MemoryPatcher] Database error: {e}")
            self._conn = None  # Reset connection on error
            raise

    def _ensure_fts5_tables(self):
        """Ensure FTS5 tables exist with content table pattern."""
        try:
            with self._get_connection() as conn:
                # Create content table (normal table for INSERT)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS error_patterns_content (
                        rowid INTEGER PRIMARY KEY AUTOINCREMENT,
                        error_type TEXT NOT NULL,
                        error_message TEXT NOT NULL,
                        fix_pattern TEXT NOT NULL,
                        success_count INTEGER DEFAULT 0,
                        failure_count INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create FTS5 virtual table (index for MATCH queries)
                conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS error_patterns_fts USING fts5(
                        error_type, error_message, fix_pattern,
                        content=error_patterns_content,
                        content_rowid=rowid,
                        tokenize="porter unicode61"
                    )
                """)
                
                # Create triggers for automatic sync
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS error_patterns_ai AFTER INSERT ON error_patterns_content BEGIN
                        INSERT INTO error_patterns_fts(rowid, error_type, error_message, fix_pattern)
                        VALUES (new.rowid, new.error_type, new.error_message, new.fix_pattern);
                    END;
                """)
                
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS error_patterns_ad AFTER DELETE ON error_patterns_content BEGIN
                        INSERT INTO error_patterns_fts(error_patterns_fts, rowid, error_type, error_message, fix_pattern)
                        VALUES ('delete', old.rowid, old.error_type, old.error_message, old.fix_pattern);
                    END;
                """)
                
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS error_patterns_au AFTER UPDATE ON error_patterns_content BEGIN
                        INSERT INTO error_patterns_fts(error_patterns_fts, rowid, error_type, error_message, fix_pattern)
                        VALUES ('delete', old.rowid, old.error_type, old.error_message, old.fix_pattern);
                        INSERT INTO error_patterns_fts(rowid, error_type, error_message, fix_pattern)
                        VALUES (new.rowid, new.error_type, new.error_message, new.fix_pattern);
                    END;
                """)
                
                conn.commit()
                print("[MemoryPatcher] FTS5 tables initialized successfully")
                
        except sqlite3.Error as e:
            print(f"[MemoryPatcher] FTS5 initialization failed: {e}")
            if self._conn:
                self._conn.close()
                self._conn = None
            raise

    def inject_context_patch(
        self,
        error_type: str,
        error_message: str,
        is_transient: bool = False,
        pattern_analysis: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Query FTS5 memory for similar errors and generate context patch.
        
        Args:
            error_type: Exception class name
            error_message: Exception message
            is_transient: Whether this is a transient error
            pattern_analysis: Pre-computed pattern analysis
            
        Returns:
            Context patch string if fix found, None otherwise
        """
        # Check cache first
        cache_key = self._generate_cache_key(error_type, error_message)
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if time.time() - cached["timestamp"] < self.cache_ttl:
                return cached["patch"]
        
        # Query FTS5 for similar errors
        similar_errors = self._query_similar_errors(error_type, error_message)
        
        if not similar_errors:
            return None
        
        # Generate context patch with confidence scoring
        patch = self._generate_patch(
            error_type=error_type,
            error_message=error_message,
            similar_errors=similar_errors,
            is_transient=is_transient,
            pattern_analysis=pattern_analysis
        )
        
        # Update cache
        self._cache[cache_key] = {
            "patch": patch,
            "timestamp": time.time()
        }
        
        # Evict old cache entries if needed
        if len(self._cache) > self.max_cache_size:
            oldest_keys = sorted(self._cache.keys(), 
                               key=lambda k: self._cache[k]["timestamp"])[:100]
            for key in oldest_keys:
                del self._cache[key]
        
        return patch

    def _query_similar_errors(self, error_type: str, error_message: str) -> List[Dict[str, Any]]:
        """
        Query FTS5 for similar error patterns.
        
        Uses parameterized queries to prevent SQL injection.
        """
        try:
            with self._get_connection() as conn:
                # Use FTS5 MATCH query with parameterized inputs
                query = """
                    SELECT c.error_type, c.error_message, c.fix_pattern, 
                           c.success_count, c.failure_count,
                           fts.rank
                    FROM error_patterns_fts fts
                    JOIN error_patterns_content c ON fts.rowid = c.rowid
                    WHERE error_patterns_fts MATCH ?
                    ORDER BY fts.rank
                    LIMIT 5
                """
                
                # Sanitize input for FTS5 MATCH
                sanitized_type = self._sanitize_fts5_input(error_type)
                sanitized_message = self._sanitize_fts5_input(error_message)
                
                cursor = conn.execute(query, (f'"{sanitized_type}" OR "{sanitized_message}"',))
                results = []
                
                for row in cursor.fetchall():
                    results.append({
                        "error_type": row["error_type"],
                        "error_message": row["error_message"],
                        "fix_pattern": row["fix_pattern"],
                        "success_count": row["success_count"],
                        "failure_count": row["failure_count"],
                        "rank": row["rank"]
                    })
                
                return results
                
        except sqlite3.Error as e:
            print(f"[MemoryPatcher] Query failed: {e}")
            return []

    def _generate_patch(
        self,
        error_type: str,
        error_message: str,
        similar_errors: List[Dict[str, Any]],
        is_transient: bool,
        pattern_analysis: Optional[Dict[str, Any]]
    ) -> str:
        """
        Generate a context patch from similar errors.
        
        Includes confidence scoring and fix recommendations.
        """
        # Calculate overall confidence
        total_success = sum(e["success_count"] for e in similar_errors)
        total_failure = sum(e["failure_count"] for e in similar_errors)
        
        if total_success + total_failure > 0:
            confidence = (total_success / (total_success + total_failure)) * 100
        else:
            confidence = 50.0
        
        # Get top fix pattern
        top_fix = similar_errors[0]["fix_pattern"] if similar_errors else "No fix available"
        
        # Build patch
        patch_parts = [
            f"\n\n## [Self-Healing Context] Error Recovery Guidance",
            f"",
            f"**Detected Error:** {error_type}",
            f"**Error Message:** {error_message[:200]}",
            f"**Confidence Score:** {confidence:.1f}%",
            f"**Similar Cases Found:** {len(similar_errors)}",
            f"",
            f"### Recommended Fix Pattern:",
            f"",
            f"```",
            f"{top_fix}",
            f"```",
            f"",
            f"### Historical Success Rate:",
            f"",
            f"- Successful applications: {total_success}",
            f"- Failed applications: {total_failure}",
            f"",
        ]
        
        if is_transient:
            patch_parts.extend([
                f"### Note: Transient Error",
                f"",
                f"This appears to be a transient error. Consider retrying the operation",
                f"after a brief delay.",
                f"",
            ])
        
        if pattern_analysis and pattern_analysis.get("is_recurring"):
            patch_parts.extend([
                f"### Warning: Recurring Error",
                f"",
                f"This error has occurred {pattern_analysis['occurrence_count']} times",
                f"in this session. Consider investigating the root cause.",
                f"",
            ])
        
        return "\n".join(patch_parts)

    def learn_from_outcome(self, error_type: str, error_message: str, 
                          fix_pattern: str, success: bool):
        """
        Learn from patch outcome to improve future recommendations.
        
        Inserts or updates error pattern in FTS5 content table.
        """
        if not self.enable_learning:
            return
        
        try:
            with self._get_connection() as conn:
                # Check if pattern exists
                cursor = conn.execute(
                    "SELECT rowid, success_count, failure_count FROM error_patterns_content WHERE fix_pattern = ?",
                    (fix_pattern,)
                )
                row = cursor.fetchone()
                
                if row:
                    # Update existing pattern
                    if success:
                        conn.execute(
                            "UPDATE error_patterns_content SET success_count = success_count + 1 WHERE rowid = ?",
                            (row["rowid"],)
                        )
                    else:
                        conn.execute(
                            "UPDATE error_patterns_content SET failure_count = failure_count + 1 WHERE rowid = ?",
                            (row["rowid"],)
                        )
                else:
                    # Insert new pattern
                    conn.execute(
                        """INSERT INTO error_patterns_content 
                           (error_type, error_message, fix_pattern, success_count, failure_count)
                           VALUES (?, ?, ?, ?, ?)""",
                        (error_type, error_message, fix_pattern, 
                         1 if success else 0, 0 if success else 1)
                    )
                
                conn.commit()
                
        except sqlite3.Error as e:
            print(f"[MemoryPatcher] Learning failed: {e}")

    def _generate_cache_key(self, error_type: str, error_message: str) -> str:
        """Generate a stable cache key from error details."""
        content = f"{error_type}:{error_message[:500]}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _sanitize_fts5_input(self, text: str) -> str:
        """Sanitize input for FTS5 MATCH queries to prevent injection."""
        # Remove FTS5 special characters
        special_chars = ['"', '*', '-', '+', '~', '^', '(', ')', 'AND', 'OR', 'NOT']
        sanitized = text
        for char in special_chars:
            sanitized = sanitized.replace(char, " ")
        return sanitized.strip()[:200]  # Limit length

    def get_status(self) -> Dict[str, Any]:
        """Returns plugin status."""
        return {
            "db_path": self.db_path,
            "cache_size": len(self._cache),
            "learning_enabled": self.enable_learning,
            "connection_active": self._conn is not None
        }

    def close(self):
        """Gracefully close database connection."""
        if self._conn:
            try:
                self._conn.close()
                print("[MemoryPatcher] Database connection closed")
            except sqlite3.Error as e:
                print(f"[MemoryPatcher] Error closing connection: {e}")
            finally:
                self._conn = None
