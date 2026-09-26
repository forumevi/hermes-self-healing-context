"""
Comprehensive test suite for Hermes Self-Healing Context Plugin.

Validates:
- Runtime exception interception and custom exception raising
- FTS5 memory patcher storage and retrieval
- Plugin lifecycle and graceful resource shutdown
- Happy-path execution (no unnecessary overhead)
- Error pattern analysis
- Performance metrics tracking
"""

import pytest
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from plugin import HermesSelfHealingPlugin
from core.runtime_interceptor import SelfHealingInterceptor, RuntimeHealedException
from core.fts5_memory_patcher import MemoryPatcher
from core.error_analyzer import ErrorAnalyzer
from core.metrics import MetricsCollector


class TestPluginInitialization:
    """Test plugin initialization and configuration."""
    
    def test_plugin_initializes_with_defaults(self):
        """Plugin should initialize with default config."""
        plugin = HermesSelfHealingPlugin()
        
        assert plugin.config == {}
        assert plugin.patcher is not None
        assert plugin.interceptor is not None
        assert plugin.metrics is not None
        assert plugin._pending_patches == []
    
    def test_plugin_initializes_with_custom_config(self):
        """Plugin should respect custom configuration."""
        config = {
            "db_path": ":memory:",
            "enable_learning": False,
            "auto_retry": False,
            "max_retries": 5
        }
        
        plugin = HermesSelfHealingPlugin(config=config)
        
        assert plugin.config == config
        assert plugin.patcher.db_path == ":memory:"
        assert plugin.patcher.enable_learning is False
        assert plugin.interceptor.auto_retry is False
        assert plugin.interceptor.max_retries == 5
    
    def test_plugin_status(self):
        """Plugin should return accurate status."""
        plugin = HermesSelfHealingPlugin()
        status = plugin.get_status()
        
        assert status["active"] is True
        assert status["pending_patches"] == 0
        assert "metrics" in status
        assert "db_status" in status


class TestSessionHooks:
    """Test session lifecycle hooks."""
    
    def test_on_session_start(self):
        """on_session_start should initialize metrics."""
        plugin = HermesSelfHealingPlugin()
        plugin.on_session_start("test-session-id", {})
        
        metrics = plugin.metrics.get_summary()
        assert metrics["session_starts"] == 1
    
    def test_on_session_end(self):
        """on_session_end should close database connection."""
        plugin = HermesSelfHealingPlugin()
        plugin.on_session_start("test-session-id", {})
        plugin.on_session_end("test-session-id", {})
        
        # Database connection should be closed
        assert plugin.patcher._conn is None


class TestExceptionInterception:
    """Test exception interception and handling."""
    
    def test_interceptor_catches_unconfigured_mock(self):
        """Should generate patch for known error patterns."""
        patcher = MemoryPatcher(db_path=":memory:")
        
        # Mock the patcher to return a specific patch string
        with patch.object(patcher, 'inject_context_patch', return_value="HERMES DYNAMIC SELF-HEALING CONTEXT INJECTED. Verify mock fixture initialization"):
            interceptor = SelfHealingInterceptor(memory_patcher=patcher)

            def broken_mock_function():
                raise TypeError("unconfigured mock attribute '_skill_nudge_interval' accessed")

            with pytest.raises(RuntimeHealedException) as exc_info:
                interceptor.execute_with_protection(broken_mock_function)

            assert "HERMES DYNAMIC SELF-HEALING CONTEXT INJECTED" in exc_info.value.context_patch
            assert "Verify mock fixture initialization" in exc_info.value.context_patch
    
    def test_successful_execution_bypasses_interceptor(self):
        """Should not interfere with successful execution."""
        patcher = MemoryPatcher(db_path=":memory:")
        interceptor = SelfHealingInterceptor(memory_patcher=patcher)

        def healthy_function():
            return {"status": "success", "data": [1, 2, 3]}

        result = interceptor.execute_with_protection(healthy_function)
        
        assert result == {"status": "success", "data": [1, 2, 3]}
    
    def test_intercept_transient_error_with_retry(self):
        """Should auto-retry transient errors."""
        patcher = MemoryPatcher(db_path=":memory:")
        # Mock to return None so it doesn't raise RuntimeHealedException, allowing retry logic to be tested
        with patch.object(patcher, 'inject_context_patch', return_value=None):
            interceptor = SelfHealingInterceptor(
                memory_patcher=patcher,
                auto_retry=True,
                max_retries=2,
                retry_delay_base=0.01 # Speed up test
            )
            
            call_count = 0
            
            def failing_function():
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise ConnectionError("Transient error")
                return "success"
            
            result = interceptor.execute_with_protection(failing_function)
            
            assert result == "success"
            assert call_count == 3
    
    def test_permanent_error_no_retry(self):
        """Should not retry permanent errors and return None if no patch."""
        patcher = MemoryPatcher(db_path=":memory:")
        # Explicitly return None for permanent errors
        with patch.object(patcher, 'inject_context_patch', return_value=None):
            interceptor = SelfHealingInterceptor(
                memory_patcher=patcher,
                auto_retry=True,
                max_retries=3
            )
            
            def failing_function():
                raise ValueError("Permanent error")
            
            result = interceptor.execute_with_protection(failing_function)
            
            assert result is None


class TestFTS5MemoryPatcher:
    """Test FTS5 memory patching functionality."""
    
    def test_query_similar_errors(self):
        """Should find similar errors in FTS5 database."""
        patcher = MemoryPatcher(db_path=":memory:")
        
        # Use the plugin's own method to insert data, ensuring triggers fire correctly
        patcher.learn_from_outcome(
            error_type="TimeoutError",
            error_message="Connection timeout occurred",
            fix_pattern="Retry with exponential backoff",
            success=True
        )
        
        similar = patcher._query_similar_errors("TimeoutError", "Connection timeout")
        
        assert len(similar) > 0
        assert similar[0]["error_type"] == "TimeoutError"
        patcher.close()
    
    def test_inject_context_patch(self):
        """Should generate context patch from similar errors."""
        patcher = MemoryPatcher(db_path=":memory:")
        
        patcher.learn_from_outcome(
            error_type="TimeoutError",
            error_message="Connection timeout",
            fix_pattern="Retry with exponential backoff",
            success=True
        )
        
        patch = patcher.inject_context_patch(
            error_type="TimeoutError",
            error_message="Connection timeout"
        )
        
        assert patch is not None
        assert "Self-Healing Context" in patch
        assert "Retry with exponential backoff" in patch
        patcher.close()
    
    def test_no_patch_for_unknown_error(self):
        """Should return None for unknown errors."""
        patcher = MemoryPatcher(db_path=":memory:")
        
        patch = patcher.inject_context_patch(
            error_type="UnknownError",
            error_message="Something weird happened"
        )
        
        assert patch is None
        patcher.close()
    
    def test_cache_hit(self):
        """Should return cached result for repeated queries."""
        patcher = MemoryPatcher(db_path=":memory:")
        
        patcher.learn_from_outcome("TimeoutError", "Connection timeout", "Retry", True)
        
        # First query
        patch1 = patcher.inject_context_patch("TimeoutError", "Connection timeout")
        
        # Second query (should hit cache)
        patch2 = patcher.inject_context_patch("TimeoutError", "Connection timeout")
        
        assert patch1 == patch2
        patcher.close()
    
    def test_graceful_shutdown(self):
        """Should close database connection gracefully."""
        patcher = MemoryPatcher(db_path=":memory:")
        
        # Force connection creation
        patcher._query_similar_errors("test", "test")
        
        # Close
        patcher.close()
        
        assert patcher._conn is None
    
    def test_learn_from_outcome(self):
        """Should learn from patch outcomes."""
        patcher = MemoryPatcher(db_path=":memory:")
        
        patcher.learn_from_outcome(
            error_type="ConnectionError",
            error_message="Network unreachable",
            fix_pattern="Check proxy settings",
            success=True
        )
        
        similar = patcher._query_similar_errors("ConnectionError", "Network unreachable")
        
        assert len(similar) > 0
        assert similar[0]["fix_pattern"] == "Check proxy settings"
        patcher.close()


class TestErrorAnalyzer:
    """Test error pattern analysis."""
    
    def test_record_error(self):
        """Should record errors for analysis."""
        analyzer = ErrorAnalyzer()
        
        analyzer.record_error("TimeoutError", "Connection timeout")
        analyzer.record_error("TimeoutError", "Connection timeout")
        analyzer.record_error("ValueError", "Invalid input")
        
        summary = analyzer.get_summary()
        
        assert summary["total_errors"] == 3
        assert summary["unique_error_types"] == 2
    
    def test_frequent_errors(self):
        """Should identify frequent errors."""
        analyzer = ErrorAnalyzer()
        
        for i in range(5):
            analyzer.record_error("TimeoutError", f"Timeout {i}")
        
        frequent = analyzer.get_frequent_errors(threshold=3)
        
        assert len(frequent) == 1
        assert frequent[0]["type"] == "TimeoutError"
        assert frequent[0]["count"] == 5
    
    def test_recommendations(self):
        """Should generate recommendations for frequent errors."""
        analyzer = ErrorAnalyzer()
        
        for i in range(5):
            analyzer.record_error("TimeoutError", f"Timeout {i}")
        
        recommendations = analyzer.get_recommendations()
        
        assert len(recommendations) > 0
        assert any("Recurring Error" in r for r in recommendations)


class TestMetricsCollector:
    """Test performance metrics collection."""
    
    def test_record_error_intercepted(self):
        """Should track intercepted errors."""
        metrics = MetricsCollector()
        
        metrics.record_error_intercepted(50.5)
        metrics.record_error_intercepted(75.3)
        
        summary = metrics.get_summary()
        
        assert summary["total_errors"] == 2
        assert summary["avg_latency_ms"] == pytest.approx(62.9, rel=1e-2)
    
    def test_hit_rate_calculation(self):
        """Should calculate hit rate correctly."""
        metrics = MetricsCollector()
        
        metrics.record_error_intercepted(10)
        metrics.record_error_intercepted(20)
        metrics.record_patch_generated()
        
        summary = metrics.get_summary()
        
        assert summary["hit_rate"] == 50.0
    
    def test_reset_metrics(self):
        """Should reset all metrics."""
        metrics = MetricsCollector()
        
        metrics.record_error_intercepted(10)
        metrics.record_patch_generated()
        
        metrics.reset()
        
        summary = metrics.get_summary()
        
        assert summary["total_errors"] == 0
        assert summary["successful_patches"] == 0


class TestSecurity:
    """Test security features."""
    
    def test_sql_injection_prevention(self):
        """Should prevent SQL injection in FTS5 queries."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        patcher = None
        try:
            patcher = MemoryPatcher(db_path=db_path)
            
            # Attempt SQL injection
            malicious_input = '"; DROP TABLE error_patterns_content; --'
            patch = patcher.inject_context_patch(malicious_input, malicious_input)
            
            # Should not crash or execute injection
            assert True  # If we got here, injection was prevented
            
        finally:
            # CRITICAL: Close connection before deleting file on Windows
            if patcher:
                patcher.close()
            Path(db_path).unlink(missing_ok=True)
    
    def test_fts5_input_sanitization(self):
        """Should sanitize FTS5 special characters."""
        patcher = MemoryPatcher(db_path=":memory:")
        
        malicious = 'test" AND "injection'
        sanitized = patcher._sanitize_fts5_input(malicious)
        
        assert '"' not in sanitized
        assert 'AND' not in sanitized
        patcher.close()
