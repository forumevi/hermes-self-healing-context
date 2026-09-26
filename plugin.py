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
"""

import time
from typing import Dict, Any, Optional

from core.runtime_interceptor import SelfHealingInterceptor
from core.fts5_memory_patcher import MemoryPatcher
from core.error_analyzer import ErrorAnalyzer
from core.metrics import MetricsCollector


class HermesSelfHealingPlugin:
    """
    Main plugin class implementing Hermes Agent's standard plugin interface.
    
    Hooks:
    - on_session_start: Initialize engine
    - on_session_end: Graceful shutdown
    - post_tool_call: Intercept exceptions after tool execution
    - pre_llm_call: Inject context patches before LLM calls
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Initialize components
        self.patcher = MemoryPatcher(
            db_path=self.config.get("db_path"),
            enable_learning=self.config.get("enable_learning", True),
            max_cache_size=self.config.get("max_cache_size", 1000)
        )
        
        self.interceptor = SelfHealingInterceptor(
            memory_patcher=self.patcher,
            auto_retry=self.config.get("auto_retry", True),
            max_retries=self.config.get("max_retries", 2)
        )
        
        self.analyzer = ErrorAnalyzer()
        self.metrics = MetricsCollector()
        
        # Pending patches to inject into context
        self._pending_patches = []
        
        print("[Hermes-Self-Healing] Plugin initialized with advanced features:")
        print("  - Error pattern learning: ENABLED" if self.config.get("enable_learning", True) else "  - Error pattern learning: DISABLED")
        print("  - Auto-retry for transient errors: ENABLED" if self.config.get("auto_retry", True) else "  - Auto-retry for transient errors: DISABLED")
        print("  - Performance metrics tracking: ENABLED")
        print("  - Confidence scoring: ENABLED")

    def on_session_start(self, context: Dict[str, Any]) -> None:
        """Called when a new session starts."""
        print("[Hermes-Self-Healing] Engine active. Monitoring execution loop...")
        self.metrics.record_session_start()
        self.analyzer.clear_history()

    def on_session_end(self, context: Dict[str, Any]) -> None:
        """Called when session ends - graceful shutdown."""
        print("[Hermes-Self-Healing] Shutting down gracefully...")
        
        # Close database connection
        self.patcher.close()
        
        # Print session summary
        metrics_summary = self.metrics.get_summary()
        print(f"[Hermes-Self-Healing] Session metrics:")
        print(f"  - Total errors intercepted: {metrics_summary.get('total_errors', 0)}")
        print(f"  - Successful patches: {metrics_summary.get('successful_patches', 0)}")
        print(f"  - Average latency: {metrics_summary.get('avg_latency_ms', 0):.2f}ms")
        print(f"  - Hit rate: {metrics_summary.get('hit_rate', 0):.1f}%")
        
        # Print recommendations if any
        recommendations = self.analyzer.get_recommendations()
        if recommendations:
            print(f"[Hermes-Self-Healing] Recommendations:")
            for rec in recommendations:
                print(f"  {rec}")

    def post_tool_call(self, context: Dict[str, Any], result: Dict[str, Any]) -> None:
        """
        Called after each tool execution.
        Intercepts exceptions and generates context patches.
        """
        if result.get("error"):
            error_type = result.get("error_type", "UnknownError")
            error_message = result.get("error", "Unknown error")
            
            # Record error for analysis
            self.analyzer.record_error(error_type, error_message)
            
            # Intercept and analyze
            start_time = time.time()
            patch = self.interceptor.intercept_error(error_type, error_message)
            latency_ms = (time.time() - start_time) * 1000
            
            # Record metrics
            self.metrics.record_error_intercepted(latency_ms)
            
            if patch:
                self._pending_patches.append(patch)
                self.metrics.record_patch_generated()
                print(f"[Hermes-Self-Healing] Generated context patch for: {error_type}")

    def pre_llm_call(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Called before LLM call.
        Injects accumulated context patches into the prompt.
        """
        if self._pending_patches:
            patches_text = "\n\n".join(self._pending_patches)
            self._pending_patches.clear()
            
            # Inject into context
            if "system_prompt" in context:
                context["system_prompt"] += f"\n\n{patches_text}"
            elif "messages" in context:
                context["messages"].append({
                    "role": "system",
                    "content": patches_text
                })
            
            self.metrics.record_context_injection()
            print(f"[Hermes-Self-Healing] Injected patches into context")
        
        return context

    def get_status(self) -> Dict[str, Any]:
        """Returns plugin status and metrics."""
        return {
            "active": True,
            "pending_patches": len(self._pending_patches),
            "metrics": self.metrics.get_summary(),
            "db_status": self.patcher.get_status(),
            "error_analysis": self.analyzer.get_summary()
        }
