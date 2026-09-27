import logging
from typing import Optional

logger = logging.getLogger(__name__)

class RuntimeInterceptor:
    def __init__(self, patcher, config: dict):
        self.patcher = patcher
        self.config = config
        self._pending_patches: dict = {}

    def handle_error(self, session_id: str, tool_name: str, error_type: str, error_message: str) -> None:
        patch = self.patcher.query_patch(tool_name, error_type, error_message)
        
        if patch:
            logger.info("[RuntimeInterceptor] Found existing patch in FTS5 memory.")
            self._pending_patches[session_id] = patch
        else:
            logger.warning("[RuntimeInterceptor] No historical patch found. Generating generic fallback.")
            fallback_patch = f"System Note: Previous tool '{tool_name}' failed with {error_type}. Please adjust parameters or try an alternative approach."
            self._pending_patches[session_id] = fallback_patch
            # FALLBACK'İ KAYDETMEYİ BIRAKTIK - sadece bellekte tutuyoruz

    def get_context_patch(self, session_id: str) -> Optional[str]:
        return self._pending_patches.pop(session_id, None)

    def clear_session(self, session_id: str) -> None:
        self._pending_patches.pop(session_id, None)