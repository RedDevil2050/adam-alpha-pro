"""
Enhanced Base Agent Infrastructure
==================================

Provides standardized base classes and utilities for all agents in the Zion platform.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta
import asyncio
import time
import json
from loguru import logger

class AgentCategory(Enum):
    """Categories for agent classification"""
    DATA_COLLECTOR = "data_collector"
    DATA_PROCESSOR = "data_processor"
    DATA_VALIDATOR = "data_validator"
    NOTIFICATION = "notification"
    STORAGE = "storage"
    MONITORING = "monitoring"
    ANALYSIS = "analysis"
    INTELLIGENCE = "intelligence"
    EXECUTION = "execution"
    RISK_MANAGEMENT = "risk_management"

class AgentStatus(Enum):
    """Agent operational status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    MAINTENANCE = "maintenance"
    INITIALIZING = "initializing"

class TaskPriority(Enum):
    """Task priority levels"""
    CRITICAL = 1    # Real-time price updates
    HIGH = 2        # Technical indicators
    MEDIUM = 3      # Fundamental data
    LOW = 4         # Historical data backfill

@dataclass
class AgentTask:
    """Standardized task structure for all agents"""
    task_id: str
    agent_id: str
    priority: TaskPriority
    symbols: List[str]
    parameters: Dict[str, Any]
    created_at: datetime
    deadline: Optional[datetime] = None

@dataclass
class AgentResult:
    """Standardized result structure for all agents"""
    task_id: str
    agent_id: str
    success: bool
    data: Dict[str, Any]
    error: Optional[str] = None
    execution_time: float = 0.0
    timestamp: datetime = None
    confidence: float = 1.0

@dataclass
class HealthStatus:
    """Agent health status"""
    agent_id: str
    status: AgentStatus
    last_successful_execution: Optional[datetime]
    error_count: int
    success_rate: float
    response_time: float
    uptime: float

class PerformanceTracker:
    """Tracks agent performance metrics"""
    
    def __init__(self):
        self.execution_times = []
        self.success_count = 0
        self.error_count = 0
        self.start_time = time.time()
    
    def record_execution(self, execution_time: float, success: bool):
        """Record execution metrics"""
        self.execution_times.append(execution_time)
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
        
        # Keep only recent executions
        if len(self.execution_times) > 1000:
            self.execution_times = self.execution_times[-500:]
    
    def get_metrics(self) -> Dict[str, float]:
        """Get performance metrics"""
        total_executions = self.success_count + self.error_count
        return {
            "success_rate": self.success_count / max(total_executions, 1),
            "average_response_time": sum(self.execution_times) / max(len(self.execution_times), 1),
            "total_executions": total_executions,
            "uptime": time.time() - self.start_time
        }

class CircuitBreaker:
    """Circuit breaker for agent protection"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 300):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func):
        """Call function with circuit breaker protection"""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func()
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
            
            raise e

class EnhancedBaseAgent(ABC):
    """Enhanced base class for all agents in the Zion platform"""
    
    def __init__(self, agent_id: str, category: AgentCategory):
        self.agent_id = agent_id
        self.category = category
        self.status = AgentStatus.INITIALIZING
        self.performance_tracker = PerformanceTracker()
        self.circuit_breaker = CircuitBreaker()
        self.config = {}
        self.last_heartbeat = datetime.now()
        
        logger.info(f"🚀 Initializing agent: {agent_id} [{category.value}]")
    
    @abstractmethod
    async def execute(self, task: AgentTask) -> AgentResult:
        """Execute a task - must be implemented by each agent"""
        pass
    
    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """Perform health check - must be implemented by each agent"""
        pass
    
    async def initialize(self) -> bool:
        """Initialize the agent"""
        try:
            await self._setup()
            self.status = AgentStatus.ACTIVE
            logger.success(f"✅ Agent {self.agent_id} initialized successfully")
            return True
        except Exception as e:
            self.status = AgentStatus.ERROR
            logger.error(f"❌ Agent {self.agent_id} initialization failed: {e}")
            return False
    
    async def _setup(self):
        """Override in subclasses for specific setup"""
        pass
    
    async def execute_with_monitoring(self, task: AgentTask) -> AgentResult:
        """Execute task with performance monitoring and circuit breaker"""
        start_time = time.time()
        
        try:
            def execute_task():
                return asyncio.create_task(self.execute(task))
            
            result_task = self.circuit_breaker.call(execute_task)
            result = await result_task
            
            execution_time = time.time() - start_time
            self.performance_tracker.record_execution(execution_time, result.success)
            
            result.execution_time = execution_time
            result.timestamp = datetime.now()
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.performance_tracker.record_execution(execution_time, False)
            
            logger.error(f"❌ Agent {self.agent_id} execution failed: {e}")
            
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=False,
                data={},
                error=str(e),
                execution_time=execution_time,
                timestamp=datetime.now()
            )
    
    async def heartbeat(self):
        """Send heartbeat signal"""
        self.last_heartbeat = datetime.now()
        health = await self.health_check()
        return health
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get agent performance metrics"""
        metrics = self.performance_tracker.get_metrics()
        metrics.update({
            "agent_id": self.agent_id,
            "category": self.category.value,
            "status": self.status.value,
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "circuit_breaker_state": self.circuit_breaker.state
        })
        return metrics
    
    async def shutdown(self):
        """Gracefully shutdown the agent"""
        self.status = AgentStatus.INACTIVE
        logger.info(f"🔴 Agent {self.agent_id} shutdown complete")

class AgentRegistry:
    """Central registry for all agents"""
    
    def __init__(self):
        self.agents: Dict[str, EnhancedBaseAgent] = {}
        self.category_index: Dict[AgentCategory, List[str]] = {}
    
    def register(self, agent: EnhancedBaseAgent):
        """Register an agent"""
        self.agents[agent.agent_id] = agent
        
        if agent.category not in self.category_index:
            self.category_index[agent.category] = []
        
        self.category_index[agent.category].append(agent.agent_id)
        
        logger.info(f"📝 Registered agent: {agent.agent_id} [{agent.category.value}]")
    
    def get_agent(self, agent_id: str) -> Optional[EnhancedBaseAgent]:
        """Get agent by ID"""
        return self.agents.get(agent_id)
    
    def get_agents_by_category(self, category: AgentCategory) -> List[EnhancedBaseAgent]:
        """Get all agents in a category"""
        agent_ids = self.category_index.get(category, [])
        return [self.agents[agent_id] for agent_id in agent_ids if agent_id in self.agents]
    
    def get_active_agents(self) -> List[EnhancedBaseAgent]:
        """Get all active agents"""
        return [agent for agent in self.agents.values() if agent.status == AgentStatus.ACTIVE]
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get health summary of all agents"""
        total_agents = len(self.agents)
        active_agents = len([a for a in self.agents.values() if a.status == AgentStatus.ACTIVE])
        error_agents = len([a for a in self.agents.values() if a.status == AgentStatus.ERROR])
        
        return {
            "total_agents": total_agents,
            "active_agents": active_agents,
            "error_agents": error_agents,
            "health_percentage": (active_agents / max(total_agents, 1)) * 100,
            "categories": {cat.value: len(agents) for cat, agents in self.category_index.items()}
        }

# Global agent registry instance
agent_registry = AgentRegistry()
