import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import json
import threading
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Data class to store performance metrics."""
    operation_name: str
    execution_time: float
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = True
    error_message: Optional[str] = None
    input_size: Optional[int] = None
    output_size: Optional[int] = None


class PerformanceMonitor:
    """Monitor and track performance metrics for RAG operations."""
    
    def __init__(self, max_metrics_history: int = 1000):
        """
        Initialize the performance monitor.
        
        Args:
            max_metrics_history: Maximum number of metrics to keep in history
        """
        self.max_metrics_history = max_metrics_history
        self.metrics_history: List[PerformanceMetrics] = []
        self.operation_stats: Dict[str, List[float]] = defaultdict(list)
        self.lock = threading.Lock()
        
    def record_operation(self, operation_name: str, execution_time: float,
                        success: bool = True, error_message: Optional[str] = None,
                        input_size: Optional[int] = None, output_size: Optional[int] = None):
        """
        Record a performance metric for an operation.
        
        Args:
            operation_name: Name of the operation
            execution_time: Time taken to execute the operation (in seconds)
            success: Whether the operation was successful
            error_message: Error message if operation failed
            input_size: Size of input data (optional)
            output_size: Size of output data (optional)
        """
        with self.lock:
            # Create metrics object
            metrics = PerformanceMetrics(
                operation_name=operation_name,
                execution_time=execution_time,
                success=success,
                error_message=error_message,
                input_size=input_size,
                output_size=output_size
            )
            
            # Add to history
            self.metrics_history.append(metrics)
            
            # Keep only the most recent metrics
            if len(self.metrics_history) > self.max_metrics_history:
                self.metrics_history = self.metrics_history[-self.max_metrics_history:]
            
            # Update operation stats
            if success:
                self.operation_stats[operation_name].append(execution_time)
                
                # Keep only recent stats
                if len(self.operation_stats[operation_name]) > 100:
                    self.operation_stats[operation_name] = self.operation_stats[operation_name][-100:]
            
            logger.info(f"Recorded operation: {operation_name}, Time: {execution_time:.4f}s, Success: {success}")

    def track(self, operation_name: str, input_size: Optional[int] = None) -> 'PerformanceTimer':
        """
        Track a performance operation using a context manager.
        
        Args:
            operation_name: Name of the operation being tracked
            input_size: Size of input data (optional)
            
        Returns:
            PerformanceTimer context manager for timing the operation
        """
        return PerformanceTimer(self, operation_name, input_size)
    
    def get_average_time(self, operation_name: str) -> Optional[float]:
        """
        Get the average execution time for an operation.
        
        Args:
            operation_name: Name of the operation
            
        Returns:
            Average execution time or None if no data
        """
        with self.lock:
            times = self.operation_stats.get(operation_name, [])
            if not times:
                return None
            return sum(times) / len(times)
    
    def get_success_rate(self, operation_name: str) -> float:
        """
        Get the success rate for an operation.
        
        Args:
            operation_name: Name of the operation
            
        Returns:
            Success rate as a percentage (0-100)
        """
        with self.lock:
            total_operations = len([m for m in self.metrics_history if m.operation_name == operation_name])
            if total_operations == 0:
                return 100.0  # No operations recorded, assume 100% success
            
            successful_operations = len([
                m for m in self.metrics_history 
                if m.operation_name == operation_name and m.success
            ])
            
            return (successful_operations / total_operations) * 100
    
    def get_recent_metrics(self, limit: int = 10) -> List[PerformanceMetrics]:
        """
        Get recent performance metrics.
        
        Args:
            limit: Number of recent metrics to return
            
        Returns:
            List of recent performance metrics
        """
        with self.lock:
            return self.metrics_history[-limit:] if self.metrics_history else []
    
    def get_operation_summary(self) -> Dict[str, Dict[str, Any]]:
        """
        Get a summary of all operations.
        
        Returns:
            Dictionary with operation summaries
        """
        with self.lock:
            summary = {}
            for operation_name in self.operation_stats.keys():
                times = self.operation_stats[operation_name]
                if times:
                    summary[operation_name] = {
                        "average_time": sum(times) / len(times),
                        "min_time": min(times),
                        "max_time": max(times),
                        "total_executions": len(times),
                        "success_rate": self.get_success_rate(operation_name)
                    }
            return summary
    
    def clear_history(self):
        """Clear all performance metrics history."""
        with self.lock:
            self.metrics_history.clear()
            self.operation_stats.clear()
    
    def export_metrics(self, filepath: str):
        """
        Export metrics to a JSON file.
        
        Args:
            filepath: Path to the output file
        """
        with self.lock:
            metrics_data = []
            for metric in self.metrics_history:
                metrics_data.append({
                    "operation_name": metric.operation_name,
                    "execution_time": metric.execution_time,
                    "timestamp": metric.timestamp.isoformat(),
                    "success": metric.success,
                    "error_message": metric.error_message,
                    "input_size": metric.input_size,
                    "output_size": metric.output_size
                })
            
            try:
                with open(filepath, 'w') as f:
                    json.dump(metrics_data, f, indent=2)
                logger.info(f"Exported {len(metrics_data)} metrics to {filepath}")
            except Exception as e:
                logger.error(f"Error exporting metrics: {e}")


class PerformanceTimer:
    """Context manager for timing operations."""
    
    def __init__(self, monitor: PerformanceMonitor, operation_name: str, 
                 input_size: Optional[int] = None):
        """
        Initialize the performance timer.
        
        Args:
            monitor: Performance monitor instance
            operation_name: Name of the operation being timed
            input_size: Size of input data (optional)
        """
        self.monitor = monitor
        self.operation_name = operation_name
        self.input_size = input_size
        self.start_time = None
        self.success = True
        self.error_message = None
        self.output_size = None
    
    def __enter__(self):
        """Start timing the operation."""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Record the operation metrics."""
        if self.start_time is not None:
            execution_time = time.time() - self.start_time
            
            # Check if there was an exception
            if exc_type is not None:
                self.success = False
                self.error_message = str(exc_val)
            
            # Record the operation
            self.monitor.record_operation(
                operation_name=self.operation_name,
                execution_time=execution_time,
                success=self.success,
                error_message=self.error_message,
                input_size=self.input_size,
                output_size=self.output_size
            )
    
    def set_output_size(self, size: int):
        """
        Set the output size for the operation.
        
        Args:
            size: Size of output data
        """
        self.output_size = size


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


def get_global_monitor() -> PerformanceMonitor:
    """
    Get the global performance monitor instance.
    
    Returns:
        Global performance monitor instance
    """
    return performance_monitor