"""
Hermes Self-Healing Context Plugin
Main Gateway Plugin entrypoint for Nous Research Hermes Agent.

Intercepts runtime errors, queries FTS5 memory for historical fixes,
and dynamically patches the context window for zero-downtime recovery.

Features:
- Runtime exception interception with classification
- FTS5 dynamic context injection from local memory
- Auto-retry for transient errors with exponential backoff
- Error pattern learning and confidence scoring
- Performance metrics tracking (latency, hit rate)
- SQL injection prevention and input sanitization
- Connection pooling and graceful shutdown

Plugin Hooks (Hermes Agent Standard):
- on_session_start(session_id, context)
- on_session_end(session_id, context)
- post_tool_call(tool_name, tool_args, tool_result, context)
- pre_llm_call(messages, context) -> Optional[str]
"""

import time
from typing import Dict, Any, Optional, List


from core.runtime_interceptor import SelfHealingInterceptor
from core.fts5_memory_patcher import MemoryPatcher
from core.error_analyzer import ErrorAnalyzer
from core.metrics import MetricsCollector


class HermesSelfHealingPlugin:
    """
    Main plugin class implementing Hermes Agent's standard plugin interface.
    
    This plugin intercepts runtime exceptions during Hermes Agent execution,
    queries a local FTS5 memory database for historical fix patterns, and
    dynamically patches the context window to enable zero-downtime recovery.
    
    Usage:
        The plugin is automatically loaded by Hermes Agent's plugin discovery
        system when placed in ~/.hermes/plugins/hermes-self-healing-context/
    
    Configuration (optional, via plugin.json or config dict):
        - db_path: Path to SQLite FTS5 database (default: ~/.hermes/memory.db)
        - enable_learning: Learn from patch outcomes (default: True)
        - auto_retry: Retry transient errors (default: True)
        - max_retries: Maximum retry attempts (default: 2)
        - max_cache_size: Maximum cached query results (default: 1000)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the self-healing plugin with all components.
        
        Args:
            config: Optional configuration dictionary. If None, defaults are used.
        """
        self.config = config or {}
        
        # Initialize FTS5 memory patcher
        self.patcher = MemoryPatcher(
            db_path=self.config.get("db_path"),
            enable_learning=self.config.get("enable_learning", True),
            max_cache_size=self.config.get("max_cache_size", 1000)
        )
        
        # Initialize runtime interceptor with auto-retry
        self.interceptor = SelfHealingInterceptor(
            memory_patcher=self.patcher,
            auto_retry=self.config.get("auto_retry", True),
            max_retries=self.config.get("max_retries", 2)
        )
        
        # Initialize error pattern analyzer
        self.analyzer = ErrorAnalyzer()
        
        # Initialize performance metrics collector
        self.metrics = MetricsCollector()
        
        # Pending patches to inject into context
        self._pending_patches: List[str] = []
        
        # Feature flags for logging
        learning_enabled = self.config.get("enable_learning", True)
        retry_enabled = self.config.get("auto_retry", True)
        
        print("[Hermes-Self-Healing] Plugin initialized with advanced features:")
        print(f"  - Error pattern learning: {'ENABLED' if learning_enabled else 'DISABLED'}")
        print(f"  - Auto-retry for transient errors: {'ENABLED' if retry_enabled else 'DISABLED'}")
        print("  - Performance metrics tracking: ENABLED")
        print("  - Confidence scoring: ENABLED")

    def on_session_start(self, session_id: str, context: Dict[str, Any]) -> None:
        """
        Called when a new Hermes Agent session starts.
        
        Initializes metrics tracking and clears error history
        to ensure clean session isolation.
        
        Args:
            session_id: Unique session identifier
            context: Session context dictionary
        """
        print(f"[Hermes-Self-Healing] Engine active for session {session_id}. Monitoring execution loop...")
        self.metrics.record_session_start()
        self.analyzer.clear_history()

    def on_session_end(self, session_id: str, context: Dict[str, Any]) -> None:
        """
        Called when Hermes Agent session ends.
        
        Performs graceful shutdown:
        - Closes database connection
        - Prints session metrics summary
        - Provides recommendations based on error patterns
        
        Args:
            session_id: Unique session identifier
            context: Session context dictionary
        """
        print(f"[Hermes-Self-Healing] Shutting down gracefully for session {session_id}...")
        
        # Close database connection (critical for preventing locks)
        self.patcher.close()
        
        # Print session metrics summary
        metrics_summary = self.metrics.get_summary()
        print("[Hermes-Self-Healing] Session metrics:")
        print(f"  - Total errors intercepted: {metrics_summary.get('total_errors', 0)}")
        print(f"  - Successful patches: {metrics_summary.get('successful_patches', 0)}")
        print(f"  - Average latency: {metrics_summary.get('avg_latency_ms', 0):.2f}ms")
        print(f"  - Hit rate: {metrics_summary.get('hit_rate', 0):.1f}%")
        
        # Print recommendations if any recurring issues detected
        recommendations = self.analyzer.get_recommendations()
        if recommendations:
            print("[Hermes-Self-Healing] Recommendations:")
            for rec in recommendations:
                print(f"  {rec}")

    def post_tool_call(
        self, 
        tool_name: str, 
        tool_args: Dict[str, Any], 
        tool_result: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> None:
        """
        Called after each tool execution by Hermes Agent.
        
        Intercepts exceptions and generates context patches for later injection.
        
        Args:
            tool_name: Name of the tool that was executed
            tool_args: Arguments passed to the tool
            tool_result: Tool execution result dictionary
                Format: {"success": bool, "output": str, "error": str, "error_type": str}
            context: Tool execution context
        """
        # Check if tool execution failed
        if not tool_result.get("success", True):
            # Extract error information
            error_message = tool_result.get("error", "Unknown error")
            error_type = tool_result.get("error_type", type(error_message).__name__)
            
            # Record error for pattern analysis
            self.analyzer.record_error(error_type, error_message, {
                "tool_name": tool_name,
                "tool_args": tool_args
            })
            
            # Intercept and generate context patch
            start_time = time.time()
            patch = self.interceptor.intercept_error(error_type, error_message)
            latency_ms = (time.time() - start_time) * 1000
            
            # Record metrics
            self.metrics.record_error_intercepted(latency_ms)
            
            if patch:
                self._pending_patches.append(patch)
                self.metrics.record_patch_generated()
                print(f"[Hermes-Self-Healing] Generated context patch for: {error_type} (from tool: {tool_name})")

    def pre_llm_call(
        self, 
        messages: List[Dict[str, Any]], 
        context: Dict[str, Any]
    ) -> Optional[str]:
        """
        Called before each LLM call by Hermes Agent.
        
        Injects accumulated context patches into the prompt.
        Returns a string that Hermes will automatically append to the system prompt.
        
        Args:
            messages: List of message dictionaries to be sent to LLM
            context: LLM call context dictionary
            
        Returns:
            Optional[str]: Patches to inject into system prompt, or None if no patches
        """
        if not self._pending_patches:
            return None
        
        # Combine all pending patches
        patches_text = "\n\n".join(self._pending_patches)
        self._pending_patches.clear()
        
        # Record context injection metric
        self.metrics.record_context_injection()
        print(f"[Hermes-Self-Healing] Injected patches into context")
        
        # Return patches as string - Hermes will automatically append to system prompt
        return patches_text

    def get_status(self) -> Dict[str, Any]:
        """
        Returns comprehensive plugin status and metrics.
        
        Useful for debugging and monitoring plugin health.
        
        Returns:
            Dict containing:
            - active: bool indicating plugin is running
            - pending_patches: number of patches waiting injection
            - metrics: performance metrics summary
            - db_status: database connection status
            - error_analysis: error pattern analysis summary
        """
        return {
            "active": True,
            "pending_patches": len(self._pending_patches),
            "metrics": self.metrics.get_summary(),
            "db_status": self.patcher.get_status(),
            "error_analysis": self.analyzer.get_summary()
        }
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"HermesSelfHealingPlugin("
            f"pending_patches={len(self._pending_patches)}, "
            f"db_path={self.patcher.db_path!r})"
        )
