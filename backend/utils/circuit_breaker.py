import time
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class CircuitState:
    is_open: bool = False
    failure_count: int = 0
    last_failure: float = 0
    reset_timeout: float = 60

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5):
        self.circuits: Dict[str, CircuitState] = {}
        self.threshold = failure_threshold
    
    def check_circuit(self, service: str) -> bool:
        if service not in self.circuits:
            self.circuits[service] = CircuitState()
        
        circuit = self.circuits[service]
        if circuit.is_open:
            if time.time() - circuit.last_failure > circuit.reset_timeout:
                circuit.is_open = False
                circuit.failure_count = 0
                return True
            return False
        return True

    def record_failure(self, service: str):
        if service not in self.circuits:
            self.circuits[service] = CircuitState()
        
        circuit = self.circuits[service]
        circuit.failure_count += 1
        circuit.last_failure = time.time()
        
        if circuit.failure_count >= self.threshold:
            circuit.is_open = True
