"""
Error Pattern Analyzer for Advanced Self-Healing.

Analyzes error patterns to provide proactive recommendations
and identify systemic issues.
"""

import time
from typing import Dict, List, Any, Optional
from collections import defaultdict


class ErrorAnalyzer:
    """
    Analyzes error patterns to provide insights and recommendations.
    
    Features:
    - Error frequency analysis
    - Root cause clustering
    - Proactive recommendations
    - Systemic issue detection
    """
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.error_history: List[Dict[str, Any]] = []
        self.pattern_clusters: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
    def record_error(self, error_type: str, error_message: str, 
                    context: Optional[Dict[str, Any]] = None) -> None:
        """Record an error for pattern analysis."""
        entry = {
            "type": error_type,
            "message": error_message,
            "context": context or {},
            "timestamp": time.time()
        }
        
        self.error_history.append(entry)
        self.pattern_clusters[error_type].append(entry)
        
        # Trim history if needed
        if len(self.error_history) > self.max_history:
            self.error_history = self.error_history[-self.max_history:]
    
    def get_frequent_errors(self, threshold: int = 3) -> List[Dict[str, Any]]:
        """Get errors that occur more than threshold times."""
        frequent = []
        
        for error_type, occurrences in self.pattern_clusters.items():
            if len(occurrences) >= threshold:
                frequent.append({
                    "type": error_type,
                    "count": len(occurrences),
                    "latest_message": occurrences[-1]["message"],
                    "first_seen": occurrences[0]["timestamp"],
                    "last_seen": occurrences[-1]["timestamp"]
                })
        
        return sorted(frequent, key=lambda x: x["count"], reverse=True)
    
    def get_recommendations(self) -> List[str]:
        """Generate proactive recommendations based on error patterns."""
        recommendations = []
        
        frequent_errors = self.get_frequent_errors(threshold=3)
        
        if frequent_errors:
            top_error = frequent_errors[0]
            recommendations.append(
                f"⚠️ **Recurring Error:** {top_error['type']} has occurred "
                f"{top_error['count']} times. Consider investigating the root cause."
            )
        
        # Check for error bursts (many errors in short time)
        recent_errors = [
            e for e in self.error_history
            if time.time() - e["timestamp"] < 300  # Last 5 minutes
        ]
        
        if len(recent_errors) > 10:
            recommendations.append(
                f"🚨 **Error Burst:** {len(recent_errors)} errors in the last 5 minutes. "
                f"System may be unstable."
            )
        
        return recommendations
    
    def get_summary(self) -> Dict[str, Any]:
        """Get error analysis summary."""
        return {
            "total_errors": len(self.error_history),
            "unique_error_types": len(self.pattern_clusters),
            "frequent_errors": len(self.get_frequent_errors()),
            "recent_errors_5min": len([
                e for e in self.error_history
                if time.time() - e["timestamp"] < 300
            ]),
            "top_error_types": [
                {"type": t, "count": len(o)}
                for t, o in sorted(
                    self.pattern_clusters.items(),
                    key=lambda x: len(x[1]),
                    reverse=True
                )[:5]
            ]
        }
    
    def clear_history(self):
        """Clear error history."""
        self.error_history.clear()
        self.pattern_clusters.clear()
