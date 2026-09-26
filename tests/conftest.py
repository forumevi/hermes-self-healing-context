"""
Test fixtures for Hermes Self-Healing Context Plugin tests.
"""

import pytest
import sqlite3
import tempfile
from pathlib import Path


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary FTS5 database for testing."""
    db_path = str(tmp_path / "test_memory.db")
    conn = sqlite3.connect(db_path)
    
    # Create FTS5 table
    conn.execute("""
        CREATE VIRTUAL TABLE error_patterns USING fts5(
            error_type, error_message, fix_pattern,
            success_count, failure_count
        )
    """)
    
    # Insert sample test data
    test_data = [
        ("TimeoutError", "Connection timeout", "Retry with exponential backoff", 10, 2),
        ("ValueError", "Invalid input format", "Validate input before processing", 15, 1),
        ("ConnectionError", "Network unreachable", "Check network configuration", 8, 3),
    ]
    
    for error_type, message, fix, success, failure in test_data:
        conn.execute(
            """INSERT INTO error_patterns 
               (error_type, error_message, fix_pattern, success_count, failure_count)
               VALUES (?, ?, ?, ?, ?)""",
            (error_type, message, fix, success, failure)
        )
    
    conn.commit()
    conn.close()
    
    return db_path


@pytest.fixture
def sample_plugin():
    """Create a sample plugin instance for testing."""
    from plugin import HermesSelfHealingPlugin
    
    plugin = HermesSelfHealingPlugin(config={
        "enable_learning": False,
        "auto_retry": False
    })
    
    yield plugin
    
    # Cleanup
    plugin.patcher.close()
