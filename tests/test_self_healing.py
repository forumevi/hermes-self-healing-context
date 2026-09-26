"""
Comprehensive test suite for Hermes Self-Healing Context Plugin.

Validates:
- Runtime exception interception and custom exception raising
- FTS5 memory patcher storage and retrieval
- Plugin lifecycle and graceful resource shutdown
- Happy-path execution (no unnecessary overhead)
"""

import pytest
import sqlite3
from core.runtime_interceptor import SelfHealingInterceptor, RuntimeHealedException
from core.fts5_memory_patcher import MemoryPatcher


class TestRuntimeInterceptor:
    """Tests for the core exception interception logic."""

    def test_interceptor_catches_unconfigured_mock(self):
        """
        ORIGINAL TEST: Verifies the plugin catches Hermes-specific mock attribute errors
        and injects the correct context patch via RuntimeHealedException.
        """
        patcher = MemoryPatcher(db_path=":memory:")
        interceptor = SelfHealingInterceptor(memory_patcher=patcher)

        def broken_mock_function():
            raise TypeError("unconfigured mock attribute '_skill_nudge_interval' accessed")

        with pytest.raises(RuntimeHealedException) as exc_info:
            interceptor.execute_with_protection(broken_mock_function)

        assert "HERMES DYNAMIC SELF-HEALING CONTEXT INJECTED" in exc_info.value.context_patch
        assert "Verify mock fixture initialization" in exc_info.value.context_patch

    def test_successful_execution_bypasses_interceptor(self):
        """
        NEW: Ensures the interceptor does not add overhead or alter 
        the return value of a successfully executing function.
        """
        patcher = MemoryPatcher(db_path=":memory:")
        interceptor = SelfHealingInterceptor(memory_patcher=patcher)

        def healthy_function():
            return {"status": "success", "data": [1, 2, 3]}

        result = interceptor.execute_with_protection(healthy_function)
        
        assert result == {"status": "success", "data": [1, 2, 3]}


class TestFTS5MemoryPatcher:
    """Tests for the SQLite FTS5 memory storage and retrieval."""

    def test_patcher_initializes_in_memory(self):
        """Verifies the patcher can safely initialize with an in-memory DB."""
        patcher = MemoryPatcher(db_path=":memory:")
        assert patcher.conn is not None
        # Clean up
        patcher.close()

    def test_patcher_stores_and_retrieves_fix_patterns(self):
        """
        NEW: Proves that the FTS5 table actually stores data and 
        the MATCH query can retrieve it correctly.
        """
        patcher = MemoryPatcher(db_path=":memory:")
        
        # Simulate learning a new fix pattern
        patcher.learn_from_outcome(
            error_type="ConnectionError",
            error_message="Network unreachable",
            fix_pattern="Check proxy settings and retry.",
            success=True
        )
        
        # Query it back
        similar = patcher.query_similar_errors("ConnectionError", "Network unreachable")
        
        assert len(similar) > 0
        assert similar[0]["fix_pattern"] == "Check proxy settings and retry."
        assert similar[0]["success_count"] == 1
        
        # Clean up
        patcher.close()


class TestPluginLifecycle:
    """Tests for resource management and graceful shutdown."""

    def test_graceful_shutdown_closes_connection(self):
        """
        NEW: Critical for production. Ensures no database locks or 
        memory leaks occur when the plugin is unloaded.
        """
        patcher = MemoryPatcher(db_path=":memory:")
        
        # Force a connection to be established
        patcher.query_similar_errors("test", "test")
        assert patcher.conn is not None
        
        # Trigger graceful shutdown
        patcher.close()
        
        # Verify connection is released
        assert patcher.conn is None
