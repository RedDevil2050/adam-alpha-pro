import time
import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)

class CircuitBreakerState(Enum):
    """
    Enum for the possible states of a circuit breaker.
    """
    CLOSED = 1  # Normal operation, requests allowed
    OPEN = 2    # Failing, no requests allowed
    HALF_OPEN = 3  # Testing if service is healthy again

class CircuitBreaker:
    """
    Implements the Circuit Breaker pattern to prevent repeated calls to failing services.
    
    The circuit breaker has three states:
    - CLOSED: Normal operation, requests allowed
    - OPEN: Service is failing, no requests allowed
    - HALF_OPEN: Testing if service is healthy again
    """
    
    def __init__(
        self, 
        name: str,
        failure_threshold: int = 5, 
        recovery_timeout: int = 60,
        half_open_max_calls: int = 1
    ):
        """
        Initialize a new circuit breaker.
        
        Args:
            name: Name identifier for this circuit breaker
            failure_threshold: Number of failures before circuit opens
            recovery_timeout: Time in seconds to wait before attempting recovery
            half_open_max_calls: Maximum number of test calls allowed in half-open state
        """
        self.name = name
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.last_failure_time = 0
        self.half_open_max_calls = half_open_max_calls
        self.half_open_call_count = 0
    
    def is_closed(self) -> bool:
        """
        Check if the circuit is closed or if we can try in half-open state.
        
        Returns:
            True if requests should be allowed, False otherwise
        """
        current_time = time.time()
        
        # If circuit is open, check if recovery timeout has elapsed
        if self.state == CircuitBreakerState.OPEN:
            if current_time - self.last_failure_time >= self.recovery_timeout:
                logger.info(f"Circuit breaker '{self.name}' transitioning from OPEN to HALF_OPEN")
                self.state = CircuitBreakerState.HALF_OPEN
                self.half_open_call_count = 0
            else:
                return False
        
        # If circuit is half-open, check if we've reached max test calls
        if self.state == CircuitBreakerState.HALF_OPEN:
            if self.half_open_call_count >= self.half_open_max_calls:
                return False
            self.half_open_call_count += 1
        
        return True
    
    def record_success(self) -> None:
        """
        Record a successful call.
        
        If in half-open state, this will close the circuit.
        """
        if self.state == CircuitBreakerState.HALF_OPEN:
            logger.info(f"Circuit breaker '{self.name}' transitioning from HALF_OPEN to CLOSED")
            self.state = CircuitBreakerState.CLOSED
        
        self.failure_count = 0
        self.half_open_call_count = 0
    
    def record_failure(self) -> None:
        """
        Record a failed call.
        
        If failure count reaches threshold, or if in half-open state,
        this will open the circuit.
        """
        current_time = time.time()
        self.last_failure_time = current_time
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            logger.warning(f"Circuit breaker '{self.name}' failed in HALF_OPEN state, reopening circuit")
            self.state = CircuitBreakerState.OPEN
            return
        
        self.failure_count += 1
        
        if self.failure_count >= self.failure_threshold and self.state != CircuitBreakerState.OPEN:
            logger.warning(f"Circuit breaker '{self.name}' threshold reached ({self.failure_count} failures), opening circuit")
            self.state = CircuitBreakerState.OPEN
    
    def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0
        self.half_open_call_count = 0
        
    def get_state(self) -> str:
        """
        Get the current state name of the circuit breaker.
        
        Returns:
            String name of current state
        """
        return self.state.name
