"""
Runtime Exception Interceptor with Auto-Retry and Pattern Learning.

Intercepts unhandled exceptions during Hermes Agent execution,
analyzes error patterns, and coordinates with MemoryPatcher for context injection.
"""

import time
import traceback
from typing import Optional, Dict, Any, Callable


# Transient errors that benefit from auto-retry
TRANSIENT_ERRORS = {
    "ConnectionError",
    "TimeoutError", 
    "RateLimitError",
    "TemporaryNetworkError",
    "ServiceUnavailableError"
}


class RuntimeHealedException(Exception):
    """
    Custom exception raised when self-healing intervention occurs.
    Contains the original error and the generated context patch.
    """
    def __init__(self, message: str, context_patch: str):
        super().__init__(message)
        self.context_patch = context_patch


class SelfHealingInterceptor:
    """
    Intercepts runtime exceptions and coordinates self-healing responses.
    
    Features:
    - Exception classification (transient vs permanent)
    - Auto-retry for transient errors with exponential backoff
    - Pattern learning from error history
    - Confidence scoring for fix recommendations
    """
    
    def __init__(
        self,
        memory_patcher,
        auto_retry: bool = True,
        max_retries: int = 2,
        retry_delay_base: float = 1.0
    ):
        self.memory_patcher = memory_patcher
        self.auto_retry = auto_retry
        self.max_retries = max_retries
        self.retry_delay_base = retry_delay_base
        self._error_history = []
        
        print("[SelfHealingInterceptor] Initialized with auto-retry and pattern learning")

    def intercept_error(self, error_type: str, error_message: str, 
                       traceback_str: Optional[str] = None) -> Optional[str]:
        """
        Intercept an error and generate a context patch.
        
        Args:
            error_type: Exception class name
            error_message: Exception message
            traceback_str: Optional full traceback string
            
        Returns:
            Context patch string if fix found, None otherwise
        """
        # Classify error
        is_transient = error_type in TRANSIENT_ERRORS
        
        # Check error history for patterns
        pattern_analysis = self._analyze_pattern(error_type, error_message)
        
        # Query FTS5 memory for similar errors
        patch = self.memory_patcher.inject_context_patch(
            error_type=error_type,
            error_message=error_message,
            is_transient=is_transient,
            pattern_analysis=pattern_analysis
        )
        
        if patch:
            self._record_error(error_type, error_message, success=True)
            return patch
        else:
            self._record_error(error_type, error_message, success=False)
            return None

    def execute_with_protection(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with exception protection and auto-retry.
        
        Args:
            func: Function to execute
            *args, **kwargs: Function arguments
            
        Returns:
            Function result or None if failed after retries
            
        Raises:
            RuntimeHealedException: If self-healing intervention occurs
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                return result
                
            except Exception as e:
                last_exception = e
                error_type = type(e).__name__
                error_message = str(e)
                traceback_str = traceback.format_exc()
                
                # Intercept error
                patch = self.intercept_error(error_type, error_message, traceback_str)
                
                # Auto-retry if transient and attempts remain
                if self.auto_retry and error_type in TRANSIENT_ERRORS and attempt < self.max_retries:
                    delay = self.retry_delay_base * (2 ** attempt)
                    print(f"[SelfHealingInterceptor] Transient error, retrying in {delay:.1f}s (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(delay)
                    continue
                
                # Permanent error or max retries exceeded
                if patch:
                    raise RuntimeHealedException(str(e), patch)
                break
        
        # All attempts failed
        if last_exception:
            print(f"[SelfHealingInterceptor] Function failed after {self.max_retries + 1} attempts: {last_exception}")
        
        return None

    def _analyze_pattern(self, error_type: str, error_message: str) -> Dict[str, Any]:
        """
        Analyze error pattern for learning and confidence scoring.
        
        Returns:
            Dict with pattern analysis results
        """
        # Check if this error type has been seen before
        similar_errors = [
            e for e in self._error_history
            if e["type"] == error_type
        ]
        
        occurrence_count = len(similar_errors)
        success_count = sum(1 for e in similar_errors if e.get("success"))
        
        # Calculate confidence based on historical success rate
        if occurrence_count > 0:
            confidence = (success_count / occurrence_count) * 100
        else:
            confidence = 50.0  # Default for new error types
        
        return {
            "occurrence_count": occurrence_count,
            "success_count": success_count,
            "confidence": confidence,
            "is_recurring": occurrence_count > 2
        }

    def _record_error(self, error_type: str, error_message: str, success: bool):
        """Record error in history for pattern analysis."""
        self._error_history.append({
            "type": error_type,
            "message": error_message,
            "success": success,
            "timestamp": time.time()
        })
        
        # Keep only last 1000 errors to prevent memory bloat
        if len(self._error_history) > 1000:
            self._error_history = self._error_history[-1000:]

    def get_error_history(self) -> list:
        """Returns recent error history for debugging."""
        return self._error_history[-100:]
