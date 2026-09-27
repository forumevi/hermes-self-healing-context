import logging

logger = logging.getLogger(__name__)

class MetricsTracker:
    def __init__(self):
        self._session_metrics: dict = {}
    
    def start_session(self, session_id: str) -> None:
        self._session_metrics[session_id] = {"errors": 0, "patches": 0}
    
    def end_session(self, session_id: str) -> None:
        metrics = self._session_metrics.pop(session_id, {})
        logger.info(f"[Metrics] Session {session_id} ended - Errors: {metrics.get('errors', 0)}, Patches: {metrics.get('patches', 0)}")
    
    def record_error(self, session_id: str) -> None:
        if session_id in self._session_metrics:
            self._session_metrics[session_id]["errors"] += 1
    
    def record_patch(self, session_id: str) -> None:
        if session_id in self._session_metrics:
            self._session_metrics[session_id]["patches"] += 1