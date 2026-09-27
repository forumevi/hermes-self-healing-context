import os
import logging
from typing import Any, Dict, Optional

# Çift uyumlu import: Hem Hermes loader (package) hem pytest (direct) için çalışır
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
    """
    Main plugin class implementing Hermes Agent's standard plugin interface.
    
    This plugin intercepts runtime exceptions during Hermes Agent execution,
    queries a local FTS5 memory database for historical fix patterns, and
    dynamically patches the context window to enable zero-downtime recovery.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the self-healing plugin with all components.
        """
        self.config = config or {}
        
        # HERMES_HOME'a saygı duy, yoksa ~/.hermes kullan
        hermes_home = os.getenv("HERMES_HOME", os.path.expanduser("~/.hermes"))
        db_path = self.config.get("db_path", os.path.join(hermes_home, "memory.db"))
        
        self.patcher = MemoryPatcher(db_path=db_path)
        self.interceptor = RuntimeInterceptor(patcher=self.patcher, config=self.config)
        self.metrics = MetricsTracker()

    def on_session_start(self, **kwargs) -> None:
        """
        Called when a new Hermes Agent session starts.
        """
        session_id = kwargs.get("session_id", "unknown")
        logger.info(f"[SelfHealing] Session started: {session_id}")
        self.metrics.start_session(session_id)

    def on_session_end(self, **kwargs) -> None:
        """
        Called when Hermes Agent session ends.
        """
        session_id = kwargs.get("session_id", "unknown")
        logger.info(f"[SelfHealing] Session ended: {session_id}")
        self.metrics.end_session(session_id)
        self.patcher.close()

    def post_tool_call(self, **kwargs) -> None:
        """
        Called after each tool execution by Hermes Agent.
        Intercepts exceptions and generates context patches for later injection.
        """
        tool_name = kwargs.get("tool_name", "unknown")
        status = kwargs.get("status", "success")
        error_type = kwargs.get("error_type", "")
        error_message = kwargs.get("error_message", "")
        
        # Core 'result'ı string olarak gönderir, dict değil. 
        # 'status' veya 'error_type' ile hata kontrolü yaparız.
        if status == "error" or error_type:
            logger.warning(f"[SelfHealing] Tool error intercepted: {tool_name} - {error_type}")
            # Dead code'u wire ettik
            self.interceptor.handle_error(
                tool_name=tool_name,
                error_type=error_type,
                error_message=error_message
            )

    def pre_llm_call(self, **kwargs) -> Optional[str]:
        """
        Called before each LLM call by Hermes Agent.
        Injects accumulated context patches into the prompt.
        """
        session_id = kwargs.get("session_id", "unknown")
        
        # Bir hata yakalandıysa, interceptor'dan yama al ve LLM prompt'una ekle
        patch = self.interceptor.get_context_patch(session_id)
        if patch:
            logger.info(f"[SelfHealing] Injecting context patch for session {session_id}")
            return patch
            
        return None