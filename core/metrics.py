"""
Performance Metrics Collector for Self-Healing Plugin.

Tracks plugin performance, hit rates, and latency.
"""

import time
from typing import Dict, Any
from collections import deque


class MetricsCollector:
    """
    Collects and reports plugin performance metrics.
    
    Tracks:
    - Total errors intercepted
    - Successful patches generated
    - Context injections
    - Average latency
    - Hit rate (successful patches / total errors)
    """
    
    def __init__(self, max_history: int = 10000):
        self.max_history = max_history
        
        # Counters
        self.total_errors = 0
        self.successful_patches = 0
        self.context_injections = 0
        self.session_starts = 0
        
        # Latency tracking
        self.latencies: deque = deque(maxlen=max_history)
        
        # Session tracking
        self.session_start_time: float = time.time()
    
    def record_session_start(self):
        """Record session start."""
        self.session_starts += 1
        self.session_start_time = time.time()
    
    def record_error_intercepted(self, latency_ms: float):
        """Record an intercepted error."""
        self.total_errors += 1
        self.latencies.append(latency_ms)
    
    def record_patch_generated(self):
        """Record a successful patch generation."""
        self.successful_patches += 1
    
    def record_context_injection(self):
        """Record a context injection."""
        self.context_injections += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        avg_latency = sum(self.latencies) / len(self.latencies) if self.latencies else 0
        hit_rate = (self.successful_patches / self.total_errors * 100) if self.total_errors > 0 else 0
        
        return {
            "total_errors": self.total_errors,
            "successful_patches": self.successful_patches,
            "context_injections": self.context_injections,
            "session_starts": self.session_starts,
            "avg_latency_ms": avg_latency,
            "hit_rate": hit_rate,
            "uptime_seconds": time.time() - self.session_start_time
        }
    
    def reset(self):
        """Reset all metrics."""
        self.total_errors = 0
        self.successful_patches = 0
        self.context_injections = 0
        self.session_starts = 0
        self.latencies.clear()
        self.session_start_time = time.time()
