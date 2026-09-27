import logging
from typing import Optional

logger = logging.getLogger(__name__)

class RuntimeInterceptor:
    def __init__(self, patcher, config: dict):
        self.patcher = patcher
        self.config = config
        self._pending_patches: dict = {}

    def handle_error(self, tool_name: str, error_type: str, error_message: str) -> None:
        # MADDE 4: Artık post_tool_call tarafından gerçekten çağrılıyor
        patch = self.patcher.query_patch(error_type, error_message)
        
        if patch:
            logger.info("[RuntimeInterceptor] Found existing patch in FTS5 memory.")
            self._pending_patches["default"] = patch
        else:
            logger.warning("[RuntimeInterceptor] No historical patch found. Generating generic fallback.")
            self._pending_patches["default"] = f"System Note: Previous tool '{tool_name}' failed with {error_type}. Please adjust parameters or try an alternative approach."
            
            # MADDE 4: Öğrenme yolunu da wire ettik
            self.patcher.learn_from_outcome(
                error_type=error_type,
                error_message=error_message,
                fix_pattern="generic_fallback",
                context_patch=self._pending_patches["default"]
            )

    def get_context_patch(self, session_id: str) -> Optional[str]:
        return self._pending_patches.pop("default", None)
