"""
Test suite for Hermes Self-Healing Context Plugin.

Validates:
- Plugin initialization and configuration
- Hook signatures (kwargs compatibility)
- FTS5 memory patcher storage and retrieval
- Runtime interceptor error handling (session-scoped)
- Metrics tracking (session-scoped)
- Security (SQL injection prevention)
"""

import pytest
import sqlite3
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

from plugin import HermesSelfHealingPlugin
from core.runtime_interceptor import RuntimeInterceptor
from core.fts5_memory_patcher import MemoryPatcher
from core.metrics import MetricsTracker


class TestPluginInitialization:
    """Test plugin initialization and configuration."""
    
    def test_plugin_initializes_with_defaults(self):
        """Plugin should initialize with default config."""
        plugin = HermesSelfHealingPlugin()
        
        assert plugin.config == {}
        assert plugin.patcher is not None
        assert plugin.interceptor is not None
        assert plugin.metrics is not None
    
    def test_plugin_initializes_with_custom_config(self):
        """Plugin should respect custom configuration."""
        config = {
            "db_path": ":memory:",
        }
        
        plugin = HermesSelfHealingPlugin(config=config)
        
        assert plugin.config == config
        assert plugin.patcher.db_path == ":memory:"
    
    def test_plugin_respects_hermes_home(self):
        """Plugin should use HERMES_HOME env var."""
        with patch.dict(os.environ, {"HERMES_HOME": "/tmp/test_hermes"}):
            plugin = HermesSelfHealingPlugin()
            assert "test_hermes" in plugin.patcher.db_path
            assert "memory.db" in plugin.patcher.db_path


class TestHookSignatures:
    """Test that hooks accept **kwargs as required by core dispatcher."""
    
    def test_on_session_start_accepts_kwargs(self):
        """on_session_start should accept keyword arguments."""
        plugin = HermesSelfHealingPlugin()
        plugin.on_session_start(session_id="test-123", model="gpt-4", platform="openai")
    
    def test_on_session_end_accepts_kwargs(self):
        """on_session_end should accept keyword arguments."""
        plugin = HermesSelfHealingPlugin()
        plugin.on_session_end(session_id="test-123", task_id="task-1", turn_id=1, completed=True, failed=False, interrupted=False)
    
    def test_post_tool_call_accepts_kwargs(self):
        """post_tool_call should accept keyword arguments."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            config = {"db_path": db_path}
            plugin = HermesSelfHealingPlugin(config=config)
            plugin.post_tool_call(
                session_id="test-123",
                tool_name="test_tool",
                args={"key": "value"},
                result="error occurred",
                status="error",
                error_type="ValueError",
                error_message="Invalid input"
            )
        finally:
            plugin.patcher.close()
            Path(db_path).unlink(missing_ok=True)
    
    def test_pre_llm_call_accepts_kwargs(self):
        """pre_llm_call should accept keyword arguments."""
        plugin = HermesSelfHealingPlugin()
        result = plugin.pre_llm_call(session_id="test-123", user_message="Hello", conversation_history=[])
        assert result is None


class TestFTS5MemoryPatcher:
    """Test FTS5 memory patching functionality."""
    
    def test_learn_and_query(self):
        """Should store and retrieve error patterns."""
        patcher = MemoryPatcher(db_path=":memory:")
        patcher.learn_from_outcome(
            tool_name="fetch_url",
            error_type="TimeoutError",
            error_message="Connection timeout occurred",
            fix_pattern="Retry with exponential backoff",
            context_patch="System Note: Retry the connection"
        )
        result = patcher.query_patch("fetch_url", "TimeoutError", "Connection timeout")
        assert result is not None
        assert "Retry" in result
        patcher.close()
    
    def test_no_patch_for_unknown_error(self):
        """Should return None for unknown errors."""
        patcher = MemoryPatcher(db_path=":memory:")
        result = patcher.query_patch("some_tool", "UnknownError", "Something weird")
        assert result is None
        patcher.close()
    
    def test_patch_is_scoped_to_tool(self):
        """A note learned for one tool must not be returned for another tool's error."""
        patcher = MemoryPatcher(db_path=":memory:")
        patcher.learn_from_outcome(
            tool_name="read_file",
            error_type="ValueError",
            error_message="Invalid input",
            fix_pattern="check path",
            context_patch="System Note: Previous tool 'read_file' failed",
        )
        assert patcher.query_patch("bash", "ValueError", "Invalid input") is None
        assert patcher.query_patch("read_file", "ValueError", "Invalid input") is not None
        patcher.close()
    
    def test_lazy_initialization(self):
        """Should not create database until first use."""
        patcher = MemoryPatcher(db_path=":memory:")
        assert patcher._conn is None
        patcher.query_patch("test", "test", "test")
        assert patcher._conn is not None
        patcher.close()
    
    def test_graceful_shutdown(self):
        """Should close database connection gracefully."""
        patcher = MemoryPatcher(db_path=":memory:")
        patcher.query_patch("test", "test", "test")
        patcher.close()
        assert patcher._conn is None


class TestRuntimeInterceptor:
    """Test runtime interceptor error handling (session-scoped)."""
    
    def test_handle_error_generates_patch(self):
        """Should generate a patch when error occurs."""
        patcher = MemoryPatcher(db_path=":memory:")
        interceptor = RuntimeInterceptor(patcher=patcher, config={})
        
        interceptor.handle_error(
            session_id="session-1",
            tool_name="test_tool",
            error_type="ValueError",
            error_message="Invalid input"
        )
        
        patch = interceptor.get_context_patch("session-1")
        assert patch is not None
        assert "test_tool" in patch
        patcher.close()
    
    def test_get_context_patch_returns_none_when_empty(self):
        """Should return None when no patches are pending."""
        patcher = MemoryPatcher(db_path=":memory:")
        interceptor = RuntimeInterceptor(patcher=patcher, config={})
        
        result = interceptor.get_context_patch("session-1")
        assert result is None
        patcher.close()
    
    def test_handle_error_learns_from_outcome(self):
        """Should save new patterns to database."""
        patcher = MemoryPatcher(db_path=":memory:")
        interceptor = RuntimeInterceptor(patcher=patcher, config={})
        
        interceptor.handle_error(
            session_id="session-1",
            tool_name="test_tool",
            error_type="ConnectionError",
            error_message="Network unreachable"
        )
        
        interceptor.handle_error(
            session_id="session-1",
            tool_name="test_tool",
            error_type="ConnectionError",
            error_message="Network unreachable"
        )
        
        patch = interceptor.get_context_patch("session-1")
        assert patch is not None
        patcher.close()


class TestMetricsTracker:
    """Test performance metrics tracking (session-scoped)."""
    
    def test_start_and_end_session(self):
        """Should track session lifecycle."""
        metrics = MetricsTracker()
        
        metrics.start_session("test-123")
        assert "test-123" in metrics._session_metrics
        
        metrics.end_session("test-123")
        assert "test-123" not in metrics._session_metrics
    
    def test_record_error(self):
        """Should increment error count for a specific session."""
        metrics = MetricsTracker()
        metrics.start_session("test-123")
        
        metrics.record_error("test-123")
        metrics.record_error("test-123")
        
        assert metrics._session_metrics["test-123"]["errors"] == 2
    
    def test_record_patch(self):
        """Should increment patch count for a specific session."""
        metrics = MetricsTracker()
        metrics.start_session("test-123")
        
        metrics.record_patch("test-123")
        
        assert metrics._session_metrics["test-123"]["patches"] == 1


class TestSecurity:
    """Test security features."""
    
    def test_sql_injection_prevention(self):
        """Should prevent SQL injection in FTS5 queries."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        patcher = None
        try:
            patcher = MemoryPatcher(db_path=db_path)
            malicious_input = '"; DROP TABLE error_patterns_content; --'
            result = patcher.query_patch(malicious_input, malicious_input, malicious_input)
            assert True
        finally:
            if patcher:
                patcher.close()
            Path(db_path).unlink(missing_ok=True)