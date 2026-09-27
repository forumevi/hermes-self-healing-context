import os
import logging
from typing import Any, Dict, Optional

try:
    from .core.runtime_interceptor import RuntimeInterceptor
    from .core.fts5_memory_patcher import MemoryPatcher
    from .core.metrics import MetricsTracker
except ImportError:
    from core.runtime_interceptor import RuntimeInterceptor
    from core.fts5_memory_patcher import MemoryPatcher
    from core.metrics import MetricsTracker

logger = logging.getLogger(__name__)

class HermesSelfHealingPlugin:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        hermes_home = os.getenv("HERMES_HOME", os.path.expanduser("~/.hermes"))
        db_path = self.config.get("db_path", os.path.join(hermes_home, "memory.db"))
        
        self.patcher = MemoryPatcher(db_path=db_path)
        self.interceptor = RuntimeInterceptor(patcher=self.patcher, config=self.config)
        self.metrics = MetricsTracker()

    def on_session_start(self, **kwargs) -> None:
        session_id = kwargs.get("session_id", "unknown")
        logger.info(f"[SelfHealing] Session started: {session_id}")
        self.metrics.start_session(session_id)

    def on_session_end(self, **kwargs) -> None:
        session_id = kwargs.get("session_id", "unknown")
        logger.info(f"[SelfHealing] Session ended: {session_id}")
        self.interceptor.clear_session(session_id)
        self.metrics.end_session(session_id)
        self.patcher.close()

    def post_tool_call(self, **kwargs) -> None:
        session_id = kwargs.get("session_id", "unknown")
        tool_name = kwargs.get("tool_name", "unknown")
        status = kwargs.get("status", "success")
        error_type = kwargs.get("error_type", "")
        error_message = kwargs.get("error_message", "")
        
        if status == "error" or error_type:
            logger.warning(f"[SelfHealing] Tool error intercepted: {tool_name} - {error_type}")
            self.metrics.record_error(session_id)
            self.interceptor.handle_error(
                session_id=session_id,
                tool_name=tool_name,
                error_type=error_type,
                error_message=error_message
            )

    def pre_llm_call(self, **kwargs) -> Optional[str]:
        session_id = kwargs.get("session_id", "unknown")
        patch = self.interceptor.get_context_patch(session_id)
        if patch:
            logger.info(f"[SelfHealing] Injecting context patch for session {session_id}")
            self.metrics.record_patch(session_id)
            return patch
        return None