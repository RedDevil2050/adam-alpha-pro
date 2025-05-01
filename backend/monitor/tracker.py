import logging
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import asyncio
import json
import os
from prometheus_client import Counter, Histogram, Gauge, Summary

logger = logging.getLogger(__name__)

# Initialize Prometheus metrics
REQUEST_COUNT = Counter(
    "zion_requests_total",
    "Total number of requests processed",
    ["endpoint", "method", "status"]
)

REQUEST_LATENCY = Histogram(
    "zion_request_latency_seconds",
    "Request latency in seconds",
    ["endpoint", "method"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

AGENT_EXECUTION_TIME = Histogram(
    "zion_agent_execution_time_seconds",
    "Agent execution time in seconds",
    ["agent_type", "agent_name"],
    buckets=(0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0)
)

AGENT_EXECUTION_COUNT = Counter(
    "zion_agent_executions_total",
    "Total number of agent executions",
    ["agent_type", "agent_name", "status"]
)

OPERATION_COUNT = Counter(
    "zion_operations_total",
    "Total number of operations",
    ["operation_type", "status"]
)

DATA_PROVIDER_CALLS = Counter(
    "zion_data_provider_calls_total",
    "Total number of data provider API calls",
    ["provider", "endpoint", "status"]
)

DATA_PROVIDER_LATENCY = Histogram(
    "zion_data_provider_latency_seconds",
    "Data provider call latency in seconds",
    ["provider", "endpoint"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0)
)

ACTIVE_USERS = Gauge(
    "zion_active_users",
    "Number of active users"
)

SYSTEM_MEMORY_USAGE = Gauge(
    "zion_system_memory_usage_bytes",
    "Memory usage in bytes"
)

SYSTEM_CPU_USAGE = Gauge(
    "zion_system_cpu_usage_percent",
    "CPU usage percentage"
)

# Central tracking registry
_tracking_registry = {}

# Event history for debugging
_event_history = []
_max_event_history = 1000


class TrackingEvent:
    """Class representing a tracking event"""
    
    def __init__(
        self,
        event_type: str,
        event_name: str,
        start_time: float = None,
        end_time: float = None,
        duration: float = None,
        metadata: Dict[str, Any] = None,
        status: str = "success"
    ):
        self.event_type = event_type
        self.event_name = event_name
        self.start_time = start_time or time.time()
        self.end_time = end_time
        self.duration = duration
        self.metadata = metadata or {}
        self.status = status
        self.timestamp = datetime.now().isoformat()
    
    def complete(self, status: str = "success", additional_metadata: Dict[str, Any] = None):
        """Mark the event as complete"""
        if not self.end_time:
            self.end_time = time.time()
            self.duration = self.end_time - self.start_time
        
        self.status = status
        
        if additional_metadata:
            self.metadata.update(additional_metadata)
        
        # Update metrics based on event type
        if self.event_type == "request":
            REQUEST_COUNT.labels(
                endpoint=self.event_name,
                method=self.metadata.get("method", "unknown"),
                status=self.status
            ).inc()
            
            if self.duration:
                REQUEST_LATENCY.labels(
                    endpoint=self.event_name,
                    method=self.metadata.get("method", "unknown")
                ).observe(self.duration)
        
        elif self.event_type == "agent":
            AGENT_EXECUTION_COUNT.labels(
                agent_type=self.metadata.get("agent_type", "unknown"),
                agent_name=self.event_name,
                status=self.status
            ).inc()
            
            if self.duration:
                AGENT_EXECUTION_TIME.labels(
                    agent_type=self.metadata.get("agent_type", "unknown"),
                    agent_name=self.event_name
                ).observe(self.duration)
        
        elif self.event_type == "operation":
            OPERATION_COUNT.labels(
                operation_type=self.event_name,
                status=self.status
            ).inc()
        
        elif self.event_type == "data_provider":
            DATA_PROVIDER_CALLS.labels(
                provider=self.event_name,
                endpoint=self.metadata.get("endpoint", "unknown"),
                status=self.status
            ).inc()
            
            if self.duration:
                DATA_PROVIDER_LATENCY.labels(
                    provider=self.event_name,
                    endpoint=self.metadata.get("endpoint", "unknown")
                ).observe(self.duration)
        
        # Add to event history
        _add_to_event_history(self)
        
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            "event_type": self.event_type,
            "event_name": self.event_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "metadata": self.metadata,
            "status": self.status,
            "timestamp": self.timestamp,
        }


def _add_to_event_history(event: TrackingEvent):
    """Add event to history with size limit"""
    global _event_history
    _event_history.append(event.to_dict())
    
    # Trim if needed
    if len(_event_history) > _max_event_history:
        _event_history = _event_history[-_max_event_history:]


def track_request(endpoint: str, method: str, metadata: Dict[str, Any] = None) -> TrackingEvent:
    """Track a new API request"""
    metadata = metadata or {}
    metadata["method"] = method
    
    event = TrackingEvent(
        event_type="request",
        event_name=endpoint,
        metadata=metadata
    )
    
    request_id = metadata.get("request_id", f"{int(time.time() * 1000)}")
    _tracking_registry[request_id] = event
    
    return event


def track_agent_execution(
    agent_name: str,
    agent_type: str,
    metadata: Dict[str, Any] = None
) -> TrackingEvent:
    """Track an agent execution"""
    metadata = metadata or {}
    metadata["agent_type"] = agent_type
    
    event = TrackingEvent(
        event_type="agent",
        event_name=agent_name,
        metadata=metadata
    )
    
    execution_id = metadata.get("execution_id", f"agent_{agent_name}_{int(time.time() * 1000)}")
    _tracking_registry[execution_id] = event
    
    return event


def track_operation(
    operation_name: str,
    metadata: Dict[str, Any] = None
) -> TrackingEvent:
    """Track a general operation"""
    event = TrackingEvent(
        event_type="operation",
        event_name=operation_name,
        metadata=metadata or {}
    )
    
    operation_id = f"op_{operation_name}_{int(time.time() * 1000)}"
    _tracking_registry[operation_id] = event
    
    return event


def track_data_provider_call(
    provider_name: str,
    endpoint: str,
    metadata: Dict[str, Any] = None
) -> TrackingEvent:
    """Track a data provider API call"""
    metadata = metadata or {}
    metadata["endpoint"] = endpoint
    
    event = TrackingEvent(
        event_type="data_provider",
        event_name=provider_name,
        metadata=metadata
    )
    
    call_id = f"dp_{provider_name}_{int(time.time() * 1000)}"
    _tracking_registry[call_id] = event
    
    return event


def get_event(event_id: str) -> Optional[TrackingEvent]:
    """Get an event by ID"""
    return _tracking_registry.get(event_id)


def get_event_history(
    event_type: str = None,
    limit: int = 100,
    status: str = None
) -> List[Dict[str, Any]]:
    """Get event history with filters"""
    filtered_events = _event_history
    
    if event_type:
        filtered_events = [e for e in filtered_events if e["event_type"] == event_type]
    
    if status:
        filtered_events = [e for e in filtered_events if e["status"] == status]
    
    # Sort by timestamp (most recent first)
    filtered_events = sorted(filtered_events, key=lambda e: e["timestamp"], reverse=True)
    
    # Apply limit
    return filtered_events[:limit]


def update_system_metrics():
    """Update system-level metrics (CPU, memory)"""
    try:
        import psutil
        
        # Update memory usage
        memory = psutil.virtual_memory()
        SYSTEM_MEMORY_USAGE.set(memory.used)
        
        # Update CPU usage
        cpu_percent = psutil.cpu_percent(interval=None)
        SYSTEM_CPU_USAGE.set(cpu_percent)
    except ImportError:
        logger.warning("psutil not available for system metrics monitoring")
    except Exception as e:
        logger.error(f"Error updating system metrics: {str(e)}")


def start_metrics_updater(interval: int = 15):
    """Start background task to update system metrics periodically"""
    async def updater_task():
        while True:
            update_system_metrics()
            await asyncio.sleep(interval)
    
    # Return the task for the caller to start
    return updater_task()


def set_active_users(count: int):
    """Set the current number of active users"""
    ACTIVE_USERS.set(count)


def increment_active_users():
    """Increment the active user count by 1"""
    ACTIVE_USERS.inc()


def decrement_active_users():
    """Decrement the active user count by 1"""
    # Ensure we don't go below zero
    if ACTIVE_USERS._value.get() > 0:
        ACTIVE_USERS.dec()


def export_metrics(output_path: str) -> bool:
    """Export current metrics to a JSON file"""
    try:
        # Create a simple representation of current metrics
        metrics_data = {
            "timestamp": datetime.now().isoformat(),
            "metrics": {
                "request_count": {
                    "total": sum(REQUEST_COUNT._metrics.values())
                },
                "agent_executions": {
                    "total": sum(AGENT_EXECUTION_COUNT._metrics.values()),
                    "by_type": {}
                },
                "data_provider_calls": {
                    "total": sum(DATA_PROVIDER_CALLS._metrics.values()),
                    "by_provider": {}
                },
                "active_users": ACTIVE_USERS._value.get(),
                "system": {
                    "memory_usage": SYSTEM_MEMORY_USAGE._value.get(),
                    "cpu_usage": SYSTEM_CPU_USAGE._value.get()
                }
            }
        }
        
        # Write to file
        with open(output_path, "w") as f:
            json.dump(metrics_data, f, indent=2)
            
        return True
    except Exception as e:
        logger.error(f"Error exporting metrics: {str(e)}")
        return False


# Function decorators for easy tracking

def track_agent(agent_type: str):
    """Decorator for tracking agent functions"""
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            agent_name = func.__name__
            event = track_agent_execution(agent_name, agent_type)
            
            try:
                result = await func(*args, **kwargs)
                event.complete(
                    status="success",
                    additional_metadata={"args_count": len(args)}
                )
                return result
            except Exception as e:
                event.complete(
                    status="error",
                    additional_metadata={"error": str(e)}
                )
                raise
                
        return wrapper
    return decorator


def track_data_provider(provider_name: str):
    """Decorator for tracking data provider calls"""
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            # Try to determine endpoint from args or kwargs
            endpoint = kwargs.get("endpoint", args[0] if args else "unknown")
            
            event = track_data_provider_call(
                provider_name,
                endpoint,
                metadata={"args_count": len(args)}
            )
            
            try:
                result = await func(*args, **kwargs)
                event.complete(status="success")
                return result
            except Exception as e:
                event.complete(
                    status="error",
                    additional_metadata={"error": str(e)}
                )
                raise
                
        return wrapper
    return decorator


# Initialize export directory
def init_metrics_export(export_dir: str = "logs/metrics", interval: int = 3600):
    """Initialize periodic metrics export"""
    os.makedirs(export_dir, exist_ok=True)
    
    async def export_task():
        while True:
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filepath = os.path.join(export_dir, f"metrics_{timestamp}.json")
                export_metrics(filepath)
                
                # Clean up old export files (keep last 24)
                files = sorted([
                    os.path.join(export_dir, f) 
                    for f in os.listdir(export_dir)
                    if f.startswith("metrics_") and f.endswith(".json")
                ])
                
                if len(files) > 24:
                    for old_file in files[:-24]:
                        try:
                            os.remove(old_file)
                        except:
                            pass
                            
            except Exception as e:
                logger.error(f"Error in metrics export task: {str(e)}")
                
            await asyncio.sleep(interval)
    
    # Return the task for the caller to start
    return export_task()


# Add the get_tracker function for backward compatibility
def get_tracker():
    """Returns a singleton tracker instance to maintain backward compatibility"""
    class Tracker:
        def track_agent_execution(self, agent_name, agent_type, metadata=None):
            return track_agent_execution(agent_name, agent_type, metadata)
            
        def track_operation(self, operation_name, metadata=None):
            return track_operation(operation_name, metadata)
            
        def track_data_provider_call(self, provider_name, endpoint, metadata=None):
            return track_data_provider_call(provider_name, endpoint, metadata)

        # Add the missing update_agent_status method
        async def update_agent_status(self, category: str, agent_name: str, symbol: str, status: str, details: Optional[Any] = None):
            """Update agent execution status using Prometheus metrics."""
            try:
                # Use Prometheus Counter to track status
                AGENT_EXECUTION_COUNT.labels(
                    agent_type=category, # Use category as agent_type
                    agent_name=agent_name,
                    status=status
                ).inc()
                logger.debug(f"Tracker: Agent {category}/{agent_name} for {symbol} status updated to {status}. Details: {details}")
            except Exception as e:
                logger.error(f"Failed to update agent status metrics for {category}/{agent_name}: {e}")
            # This method is async to match the expected signature, but doesn't need to await anything internally here.
            await asyncio.sleep(0) # Minimal await to make it a valid coroutine
    
    # Return an instance of the inner Tracker class
    # Note: This isn't a true singleton pattern but matches the existing structure.
    # If a real singleton is needed, the implementation should change.
    return Tracker()