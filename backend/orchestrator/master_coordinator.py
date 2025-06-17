"""
Master Orchestrator for Zion Market Analysis Platform
======================================================

Central coordination system for all agents, data flow, and system operations.
"""

import asyncio
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json
from loguru import logger

from backend.agents.core.base_agent import (
    EnhancedBaseAgent, AgentTask, AgentResult, AgentCategory, 
    TaskPriority, AgentStatus, agent_registry
)

class SystemState(Enum):
    """Overall system operational state"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    EMERGENCY = "emergency"

@dataclass
class SystemMetrics:
    """System-wide performance metrics"""
    total_agents: int
    active_agents: int
    failed_agents: int
    tasks_completed: int
    tasks_failed: int
    average_response_time: float
    data_collection_rate: float
    system_uptime: float

class TaskScheduler:
    """Intelligent task scheduling and distribution"""
    
    def __init__(self):
        self.task_queue: Dict[TaskPriority, List[AgentTask]] = {
            priority: [] for priority in TaskPriority
        }
        self.active_tasks: Dict[str, AgentTask] = {}
        self.completed_tasks: List[AgentResult] = []
    
    def add_task(self, task: AgentTask):
        """Add task to appropriate priority queue"""
        self.task_queue[task.priority].append(task)
        logger.debug(f"📋 Task {task.task_id} added to {task.priority.name} queue")
    
    def get_next_task(self, agent_category: AgentCategory) -> Optional[AgentTask]:
        """Get next task for agent category based on priority"""
        # Process tasks in priority order
        for priority in TaskPriority:
            for task in self.task_queue[priority]:
                # Check if task is suitable for agent category
                if self._is_task_suitable(task, agent_category):
                    self.task_queue[priority].remove(task)
                    self.active_tasks[task.task_id] = task
                    return task
        return None
    
    def _is_task_suitable(self, task: AgentTask, agent_category: AgentCategory) -> bool:
        """Check if task is suitable for agent category"""
        # Task routing logic based on category
        task_category_mapping = {
            "data_collection": [AgentCategory.DATA_COLLECTOR],
            "data_processing": [AgentCategory.DATA_PROCESSOR],
            "data_validation": [AgentCategory.DATA_VALIDATOR],
            "analysis": [AgentCategory.ANALYSIS],
            "intelligence": [AgentCategory.INTELLIGENCE]
        }
        
        return agent_category in task_category_mapping.get(task.agent_id.split('_')[0], [])
    
    def complete_task(self, result: AgentResult):
        """Mark task as completed"""
        if result.task_id in self.active_tasks:
            del self.active_tasks[result.task_id]
            self.completed_tasks.append(result)
            
            # Keep only recent completed tasks
            if len(self.completed_tasks) > 1000:
                self.completed_tasks = self.completed_tasks[-500:]
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        return {
            "queued_tasks": {priority.name: len(tasks) for priority, tasks in self.task_queue.items()},
            "active_tasks": len(self.active_tasks),
            "completed_tasks": len(self.completed_tasks)
        }

class LoadBalancer:
    """Agent load balancing and optimization"""
    
    def __init__(self):
        self.agent_loads: Dict[str, int] = {}
        self.agent_performance: Dict[str, float] = {}
    
    def select_best_agent(self, category: AgentCategory) -> Optional[EnhancedBaseAgent]:
        """Select best agent for task based on load and performance"""
        available_agents = agent_registry.get_agents_by_category(category)
        active_agents = [a for a in available_agents if a.status == AgentStatus.ACTIVE]
        
        if not active_agents:
            return None
        
        # Simple load balancing - select agent with lowest current load
        best_agent = min(active_agents, key=lambda a: self.agent_loads.get(a.agent_id, 0))
        return best_agent
    
    def assign_task(self, agent_id: str):
        """Record task assignment to agent"""
        self.agent_loads[agent_id] = self.agent_loads.get(agent_id, 0) + 1
    
    def complete_task(self, agent_id: str, execution_time: float):
        """Record task completion"""
        self.agent_loads[agent_id] = max(0, self.agent_loads.get(agent_id, 0) - 1)
        self.agent_performance[agent_id] = execution_time

class HealthMonitor:
    """System and agent health monitoring"""
    
    def __init__(self):
        self.health_history: List[Dict[str, Any]] = []
        self.alert_thresholds = {
            "success_rate": 0.8,
            "response_time": 30.0,
            "error_rate": 0.2
        }
    
    async def check_system_health(self) -> SystemMetrics:
        """Perform comprehensive system health check"""
        all_agents = list(agent_registry.agents.values())
        active_agents = [a for a in all_agents if a.status == AgentStatus.ACTIVE]
        failed_agents = [a for a in all_agents if a.status == AgentStatus.ERROR]
        
        total_tasks = 0
        failed_tasks = 0
        total_response_time = 0.0
        
        for agent in all_agents:
            metrics = agent.get_performance_metrics()
            total_tasks += metrics.get("total_executions", 0)
            failed_tasks += metrics.get("total_executions", 0) * (1 - metrics.get("success_rate", 1))
            total_response_time += metrics.get("average_response_time", 0)
        
        avg_response_time = total_response_time / max(len(all_agents), 1)
        
        return SystemMetrics(
            total_agents=len(all_agents),
            active_agents=len(active_agents),
            failed_agents=len(failed_agents),
            tasks_completed=total_tasks - failed_tasks,
            tasks_failed=failed_tasks,
            average_response_time=avg_response_time,
            data_collection_rate=0.0,  # To be calculated
            system_uptime=0.0  # To be calculated
        )
    
    async def check_agent_health(self, agent: EnhancedBaseAgent) -> bool:
        """Check individual agent health"""
        try:
            health_status = await agent.health_check()
            metrics = agent.get_performance_metrics()
            
            # Check against thresholds
            success_rate = metrics.get("success_rate", 0)
            response_time = metrics.get("average_response_time", float('inf'))
            
            is_healthy = (
                success_rate >= self.alert_thresholds["success_rate"] and
                response_time <= self.alert_thresholds["response_time"] and
                agent.status == AgentStatus.ACTIVE
            )
            
            return is_healthy
            
        except Exception as e:
            logger.error(f"❌ Health check failed for agent {agent.agent_id}: {e}")
            return False

class MasterCoordinator:
    """Central coordination system for the Zion platform"""
    
    def __init__(self):
        self.system_state = SystemState.INITIALIZING
        self.task_scheduler = TaskScheduler()
        self.load_balancer = LoadBalancer()
        self.health_monitor = HealthMonitor()
        self.active_collections: Set[str] = set()
        self.start_time = datetime.now()
        
        logger.info("🎼 Master Coordinator initialized")
    
    async def initialize(self):
        """Initialize the master coordinator and all registered agents"""
        logger.info("🚀 Starting Master Coordinator initialization...")
        
        try:
            # Initialize all registered agents
            initialization_tasks = []
            for agent in agent_registry.agents.values():
                initialization_tasks.append(agent.initialize())
            
            results = await asyncio.gather(*initialization_tasks, return_exceptions=True)
            
            # Count successful initializations
            successful = sum(1 for result in results if result is True)
            total = len(results)
            
            if successful >= total * 0.8:  # 80% success threshold
                self.system_state = SystemState.ACTIVE
                logger.success(f"✅ Master Coordinator initialized: {successful}/{total} agents active")
            else:
                self.system_state = SystemState.DEGRADED
                logger.warning(f"⚠️ System in degraded mode: {successful}/{total} agents active")
            
            # Start background monitoring
            asyncio.create_task(self._background_monitoring())
            
        except Exception as e:
            self.system_state = SystemState.EMERGENCY
            logger.error(f"❌ Master Coordinator initialization failed: {e}")
            raise
    
    async def orchestrate_data_collection(self, symbols: List[str]) -> Dict[str, Any]:
        """Orchestrate data collection for given symbols"""
        collection_id = f"collection_{int(datetime.now().timestamp())}"
        self.active_collections.add(collection_id)
        
        logger.info(f"🎯 Starting data collection for {len(symbols)} symbols")
        
        try:
            # Create data collection tasks
            tasks = self._create_collection_tasks(symbols)
            
            # Distribute tasks to appropriate agents
            results = await self._execute_parallel_tasks(tasks)
            
            # Aggregate and validate results
            aggregated_data = await self._aggregate_results(results)
            
            return {
                "collection_id": collection_id,
                "symbols": symbols,
                "results": aggregated_data,
                "success_rate": self._calculate_success_rate(results),
                "execution_time": (datetime.now() - self.start_time).total_seconds()
            }
            
        except Exception as e:
            logger.error(f"❌ Data collection failed: {e}")
            raise
        finally:
            self.active_collections.discard(collection_id)
    
    def _create_collection_tasks(self, symbols: List[str]) -> List[AgentTask]:
        """Create collection tasks for symbols"""
        tasks = []
        
        # Create high-priority tasks for real-time data
        for symbol in symbols:
            task = AgentTask(
                task_id=f"realtime_{symbol}_{int(datetime.now().timestamp())}",
                agent_id="data_collection",
                priority=TaskPriority.CRITICAL,
                symbols=[symbol],
                parameters={"data_type": "realtime", "symbol": symbol},
                created_at=datetime.now(),
                deadline=datetime.now() + timedelta(seconds=30)
            )
            tasks.append(task)
        
        return tasks
    
    async def _execute_parallel_tasks(self, tasks: List[AgentTask]) -> List[AgentResult]:
        """Execute tasks in parallel with load balancing"""
        results = []
        
        # Group tasks by category for efficient distribution
        execution_tasks = []
        
        for task in tasks:
            # Select best agent for task
            suitable_agents = agent_registry.get_agents_by_category(AgentCategory.DATA_COLLECTOR)
            if suitable_agents:
                agent = self.load_balancer.select_best_agent(AgentCategory.DATA_COLLECTOR)
                if agent:
                    self.load_balancer.assign_task(agent.agent_id)
                    execution_tasks.append(agent.execute_with_monitoring(task))
        
        if execution_tasks:
            results = await asyncio.gather(*execution_tasks, return_exceptions=True)
        
        return [r for r in results if isinstance(r, AgentResult)]
    
    async def _aggregate_results(self, results: List[AgentResult]) -> Dict[str, Any]:
        """Aggregate results from multiple agents"""
        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]
        
        aggregated = {
            "successful_collections": len(successful_results),
            "failed_collections": len(failed_results),
            "data": {},
            "errors": [r.error for r in failed_results if r.error]
        }
        
        # Aggregate successful data
        for result in successful_results:
            if result.data:
                aggregated["data"].update(result.data)
        
        return aggregated
    
    def _calculate_success_rate(self, results: List[AgentResult]) -> float:
        """Calculate success rate of results"""
        if not results:
            return 0.0
        
        successful = sum(1 for r in results if r.success)
        return successful / len(results)
    
    async def _background_monitoring(self):
        """Background monitoring and health checks"""
        while self.system_state != SystemState.EMERGENCY:
            try:
                # Perform system health check
                system_metrics = await self.health_monitor.check_system_health()
                
                # Log metrics periodically
                logger.debug(f"📊 System metrics: {system_metrics.active_agents}/{system_metrics.total_agents} agents active")
                
                # Check for degraded state
                if system_metrics.active_agents < system_metrics.total_agents * 0.5:
                    self.system_state = SystemState.DEGRADED
                    logger.warning("⚠️ System in degraded mode - less than 50% agents active")
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"❌ Background monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        system_metrics = await self.health_monitor.check_system_health()
        queue_status = self.task_scheduler.get_queue_status()
        agent_summary = agent_registry.get_health_summary()
        
        return {
            "system_state": self.system_state.value,
            "uptime": (datetime.now() - self.start_time).total_seconds(),
            "metrics": {
                "total_agents": system_metrics.total_agents,
                "active_agents": system_metrics.active_agents,
                "failed_agents": system_metrics.failed_agents,
                "average_response_time": system_metrics.average_response_time
            },
            "queue_status": queue_status,
            "agent_summary": agent_summary,
            "active_collections": len(self.active_collections)
        }
    
    async def shutdown(self):
        """Gracefully shutdown the entire system"""
        logger.info("🔴 Starting system shutdown...")
        self.system_state = SystemState.MAINTENANCE
        
        # Shutdown all agents
        shutdown_tasks = []
        for agent in agent_registry.agents.values():
            shutdown_tasks.append(agent.shutdown())
        
        await asyncio.gather(*shutdown_tasks, return_exceptions=True)
        
        logger.success("✅ System shutdown complete")

# Global master coordinator instance
master_coordinator = MasterCoordinator()
