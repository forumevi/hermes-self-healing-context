import logging
from typing import Optional

logger = logging.getLogger(__name__)

class MetricsTracker:
    """
    Simple metrics tracker for the self-healing plugin.
    Tracks session starts/ends and basic error counts.
    """
    
    def __init__(self):
        self.current_session: Optional[str] = None
        self.error_count: int = 0
        self.patch_count: int = 0
    
    def start_session(self, session_id: str) -> None:
        """Called when a new session starts."""
        self.current_session = session_id
        self.error_count = 0
        self.patch_count = 0
        logger.debug(f"[Metrics] Session {session_id} started")
    
    def end_session(self, session_id: str) -> None:
        """Called when a session ends."""
        logger.info(
            f"[Metrics] Session {session_id} ended - "
            f"Errors: {self.error_count}, Patches: {self.patch_count}"
        )
        self.current_session = None
    
    def record_error(self) -> None:
        """Record an error occurrence."""
        self.error_count += 1
    
    def record_patch(self) -> None:
        """Record a successful patch injection."""
        self.patch_count += 1