"""
Hermes Self-Healing Context Plugin
Main Gateway Plugin entrypoint for Nous Research Hermes Agent.

Intercepts runtime errors, queries FTS5 memory for historical fixes,
and dynamically patches the context window for zero-downtime recovery.
"""

from core.runtime_interceptor import SelfHealingInterceptor
from core.fts5_memory_patcher import MemoryPatcher
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
    
    def __init__(self, config: dict = None):
        self.config = config or {}
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
        self.metrics = MetricsCollector()
        self._pending_patches = []
        
        print("[Hermes-Self-Healing] Plugin initialized with advanced features:")
        print("  - Error pattern learning: ENABLED")
        print("  - Auto-retry for transient errors: ENABLED")
        print("  - Performance metrics tracking: ENABLED")
        print("  - Confidence scoring: ENABLED")

    def on_session_start(self, context: dict):
        """Called when a new session starts."""
        print("[Hermes-Self-Healing] Engine active. Monitoring execution loop...")
        self.metrics.record_session_start()

    def on_session_end(self, context: dict):
        """Called when session ends - graceful shutdown."""
        print("[Hermes-Self-Healing] Shutting down gracefully...")
        self.patcher.close()
        metrics_summary = self.metrics.get_summary()
        print(f"[Hermes-Self-Healing] Session metrics:")
        print(f"  - Total errors intercepted: {metrics_summary.get('total_errors', 0)}")
        print(f"  - Successful patches: {metrics_summary.get('successful_patches', 0)}")
        print(f"  - Average latency: {metrics_summary.get('avg_latency_ms', 0):.2f}ms")
        print(f"  - Hit rate: {metrics_summary.get('hit_rate', 0):.1f}%")

    def post_tool_call(self, context: dict, result: dict):
        """
        Called after each tool execution.
        Intercepts exceptions and generates context patches.
        """
        if result.get("error"):
            error_type = result.get("error_type", "UnknownError")
            error_message = result.get("error", "Unknown error")
            
            # Intercept and analyze
            patch = self.interceptor.intercept_error(error_type, error_message)
            
            if patch:
                self._pending_patches.append(patch)
                self.metrics.record_patch_generated()
                print(f"[Hermes-Self-Healing] Generated context patch for: {error_type}")

    def pre_llm_call(self, context: dict) -> dict:
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
            print(f"[Hermes-Self-Healing] Injected {len(patches_text.split('##'))} patches into context")
        
        return context

    def get_status(self) -> dict:
        """Returns plugin status and metrics."""
        return {
            "active": True,
            "pending_patches": len(self._pending_patches),
            "metrics": self.metrics.get_summary(),
            "db_status": self.patcher.get_status()
        }
