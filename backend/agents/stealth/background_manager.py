"""
Background Stealth Agent Manager
===============================

Orchestrates continuous data collection from multiple stealth agents
with real-time streaming, performance monitoring, and intelligent scheduling.
"""

import asyncio
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Set, Optional, Callable, AsyncIterator
from dataclasses import dataclass, asdict
from dataclasses import dataclass, asdict
from loguru import logger
from concurrent.futures import ThreadPoolExecutor
import redis
from backend.utils.cache_utils import get_redis_client
from backend.monitor.tracker import AGENT_EXECUTION_COUNT, ACTIVE_USERS

@dataclass
class AgentPerformanceMetrics:
    """Performance metrics for individual agents"""
    agent_name: str
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    avg_execution_time: float = 0.0
    last_execution: Optional[float] = None
    success_rate: float = 0.0
    uptime_percentage: float = 100.0

@dataclass
class StealthCollectionSession:
    """Session tracking for background collection"""
    session_id: str
    symbols: Set[str]
    agents: List[str]
    start_time: float
    collection_interval: int
    active: bool = True
    total_collections: int = 0
    successful_collections: int = 0

class BackgroundStealthManager:
    """
    Advanced manager for background stealth agent operations with:
    - Continuous multi-agent data collection
    - Real-time performance monitoring
    - Intelligent scheduling and load balancing
    - Circuit breaker integration
    - Data streaming capabilities
    """
    
    def __init__(self):
        self.active_sessions: Dict[str, StealthCollectionSession] = {}
        self.agent_registry: Dict[str, Any] = {}
        self.agent_metrics: Dict[str, AgentPerformanceMetrics] = {}
        self.background_tasks: Dict[str, asyncio.Task] = {}
        
        # Configuration
        self.max_concurrent_agents = 6
        self.default_collection_interval = 30  # seconds
        self.performance_monitoring_interval = 60  # seconds
        self.data_retention_hours = 24
        
        # Streaming and events
        self.data_subscribers: List[Callable] = []
        self.performance_subscribers: List[Callable] = []
          # Redis for coordination and caching (initialize later)
        self.redis_client = None
        
        # Performance monitoring task
        self.monitoring_task = None
        
        logger.info("🎯 Background Stealth Manager initialized")
    
    async def start_monitoring(self):
        """Start the performance monitoring system."""
        if not self.monitoring_task:
            self.monitoring_task = asyncio.create_task(self._performance_monitoring_loop())
            logger.info("📊 Performance monitoring started")
    
    async def stop_monitoring(self):
        """Stop the performance monitoring system."""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            self.monitoring_task = None
            logger.info("📊 Performance monitoring stopped")
    
    def register_agent(self, agent_name: str, agent_instance: Any):
        """Register a stealth agent for background collection."""
        self.agent_registry[agent_name] = agent_instance
        self.agent_metrics[agent_name] = AgentPerformanceMetrics(agent_name=agent_name)
        logger.info(f"🔌 Registered stealth agent: {agent_name}")
    
    def unregister_agent(self, agent_name: str):
        """Unregister a stealth agent."""
        if agent_name in self.agent_registry:
            del self.agent_registry[agent_name]
            del self.agent_metrics[agent_name]
            logger.info(f"🔌 Unregistered stealth agent: {agent_name}")
    
    async def start_collection_session(
        self, 
        session_id: str, 
        symbols: List[str], 
        agent_names: List[str] = None,
        collection_interval: int = None
    ) -> bool:
        """Start a background collection session for specified symbols and agents."""
        
        if session_id in self.active_sessions:
            logger.warning(f"⚠️ Session {session_id} already active")
            return False
        
        # Use all registered agents if none specified
        if not agent_names:
            agent_names = list(self.agent_registry.keys())
        
        # Validate agents
        invalid_agents = [name for name in agent_names if name not in self.agent_registry]
        if invalid_agents:
            logger.error(f"❌ Invalid agent names: {invalid_agents}")
            return False
        
        # Create session
        session = StealthCollectionSession(
            session_id=session_id,
            symbols=set(symbols),
            agents=agent_names,
            start_time=time.time(),
            collection_interval=collection_interval or self.default_collection_interval
        )
        
        self.active_sessions[session_id] = session
        
        # Start background collection tasks
        for symbol in symbols:
            task_id = f"{session_id}:{symbol}"
            task = asyncio.create_task(
                self._symbol_collection_loop(session_id, symbol, agent_names)
            )
            self.background_tasks[task_id] = task
        
        logger.success(f"🚀 Started collection session '{session_id}' for {len(symbols)} symbols using {len(agent_names)} agents")
        return True
    
    async def stop_collection_session(self, session_id: str) -> bool:
        """Stop a background collection session."""
        
        if session_id not in self.active_sessions:
            logger.warning(f"⚠️ Session {session_id} not found")
            return False
        
        # Mark session as inactive
        self.active_sessions[session_id].active = False
        
        # Cancel related tasks
        tasks_to_cancel = [
            task_id for task_id in self.background_tasks.keys() 
            if task_id.startswith(f"{session_id}:")
        ]
        
        for task_id in tasks_to_cancel:
            self.background_tasks[task_id].cancel()
            del self.background_tasks[task_id]
        
        # Remove session
        del self.active_sessions[session_id]
        
        logger.success(f"🛑 Stopped collection session '{session_id}'")
        return True
    
    async def _symbol_collection_loop(self, session_id: str, symbol: str, agent_names: List[str]):
        """Continuous collection loop for a specific symbol using multiple agents."""
        
        logger.debug(f"🔄 Starting collection loop for {symbol} in session {session_id}")
        
        session = self.active_sessions[session_id]
        
        while session.active and session_id in self.active_sessions:
            collection_start = time.time()
            
            try:
                # Execute all agents for this symbol concurrently
                agent_tasks = []
                for agent_name in agent_names:
                    if agent_name in self.agent_registry:
                        task = asyncio.create_task(
                            self._execute_agent_with_metrics(agent_name, symbol)
                        )
                        agent_tasks.append((agent_name, task))
                
                # Wait for all agents to complete
                results = {}
                for agent_name, task in agent_tasks:
                    try:
                        result = await task
                        results[agent_name] = result
                    except Exception as e:
                        logger.error(f"❌ Agent {agent_name} failed for {symbol}: {e}")
                        results[agent_name] = {"error": str(e)}
                
                # Process and stream results
                await self._process_collection_results(session_id, symbol, results)
                
                session.total_collections += 1
                if any(not r.get("error") for r in results.values()):
                    session.successful_collections += 1
                
                collection_time = time.time() - collection_start
                logger.debug(f"📊 Collection for {symbol} completed in {collection_time:.2f}s")
                
                # Dynamic sleep adjustment
                sleep_time = max(session.collection_interval - collection_time, 5)
                await asyncio.sleep(sleep_time)
                
            except asyncio.CancelledError:
                logger.info(f"🛑 Collection loop cancelled for {symbol} in session {session_id}")
                break
            except Exception as e:
                logger.error(f"❌ Collection loop error for {symbol}: {e}")
                await asyncio.sleep(30)  # Wait before retry
    
    async def _execute_agent_with_metrics(self, agent_name: str, symbol: str) -> Dict:
        """Execute an agent with performance metrics tracking."""
        
        start_time = time.time()
        metrics = self.agent_metrics[agent_name]
        agent = self.agent_registry[agent_name]
        
        try:
            # Execute the agent
            result = await agent.execute(symbol)
            
            # Update success metrics
            execution_time = time.time() - start_time
            metrics.total_executions += 1
            metrics.successful_executions += 1
            metrics.last_execution = time.time()
            
            # Update average execution time
            if metrics.total_executions == 1:
                metrics.avg_execution_time = execution_time
            else:
                total = metrics.total_executions
                metrics.avg_execution_time = (metrics.avg_execution_time * (total - 1) + execution_time) / total
            
            metrics.success_rate = metrics.successful_executions / metrics.total_executions * 100
            
            # Track in monitoring system
            AGENT_EXECUTION_COUNT.labels(
                agent_type="stealth", 
                agent_name=agent_name, 
                status="success"
            ).inc()
            
            return result
            
        except Exception as e:
            # Update failure metrics
            execution_time = time.time() - start_time
            metrics.total_executions += 1
            metrics.failed_executions += 1
            metrics.last_execution = time.time()
            
            metrics.success_rate = metrics.successful_executions / metrics.total_executions * 100
            
            # Track in monitoring system
            AGENT_EXECUTION_COUNT.labels(
                agent_type="stealth", 
                agent_name=agent_name, 
                status="failure"
            ).inc()
            
            logger.error(f"❌ Agent {agent_name} execution failed for {symbol}: {e}")
            return {"error": str(e), "execution_time": execution_time}
    
    async def _process_collection_results(self, session_id: str, symbol: str, results: Dict[str, Dict]):
        """Process and distribute collection results."""
        
        # Create consolidated result
        consolidated_result = {
            "session_id": session_id,
            "symbol": symbol,
            "timestamp": time.time(),
            "agent_results": results,
            "successful_agents": [
                name for name, result in results.items() 
                if not result.get("error")
            ],
            "failed_agents": [
                name for name, result in results.items() 
                if result.get("error")
            ]
        }
        
        # Cache result
        await self._cache_collection_result(session_id, symbol, consolidated_result)
        
        # Stream to subscribers
        await self._stream_to_subscribers(consolidated_result)
    
    async def _cache_collection_result(self, session_id: str, symbol: str, result: Dict):
        """Cache collection result with TTL."""
        
        if not self.redis_client:
            return
        
        cache_key = f"stealth:collection:{session_id}:{symbol}:{int(time.time())}"
        
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, 
                self.redis_client.setex, 
                cache_key, 
                3600,  # 1 hour TTL
                json.dumps(result)
            )
        except Exception as e:
            logger.warning(f"Failed to cache collection result: {e}")
    
    async def _stream_to_subscribers(self, data: Dict):
        """Stream data to all registered subscribers."""
        
        for subscriber in self.data_subscribers:
            try:
                if asyncio.iscoroutinefunction(subscriber):
                    await subscriber(data)
                else:
                    subscriber(data)
            except Exception as e:
                logger.error(f"❌ Subscriber error: {e}")
    
    async def _performance_monitoring_loop(self):
        """Continuous performance monitoring and reporting."""
        
        logger.debug("📊 Performance monitoring loop started")
        
        while True:
            try:
                await asyncio.sleep(self.performance_monitoring_interval)
                
                # Generate performance report
                performance_report = self.get_comprehensive_performance_report()
                
                # Stream to performance subscribers
                for subscriber in self.performance_subscribers:
                    try:
                        if asyncio.iscoroutinefunction(subscriber):
                            await subscriber(performance_report)
                        else:
                            subscriber(performance_report)
                    except Exception as e:
                        logger.error(f"❌ Performance subscriber error: {e}")
                
                # Log summary
                total_agents = len(self.agent_registry)
                active_sessions = len(self.active_sessions)
                active_tasks = len(self.background_tasks)
                
                logger.info(f"📊 Performance: {total_agents} agents, {active_sessions} sessions, {active_tasks} active tasks")
                
            except asyncio.CancelledError:
                logger.info("📊 Performance monitoring loop cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Performance monitoring error: {e}")
    
    def subscribe_to_data(self, callback: Callable):
        """Subscribe to real-time data updates."""
        self.data_subscribers.append(callback)
        logger.debug(f"📡 New data subscriber registered")
    
    def subscribe_to_performance(self, callback: Callable):
        """Subscribe to performance updates."""
        self.performance_subscribers.append(callback)
        logger.debug(f"📊 New performance subscriber registered")
    
    def get_comprehensive_performance_report(self) -> Dict:
        """Generate comprehensive performance report."""
        
        current_time = time.time()
        
        # Agent performance
        agent_performance = {}
        for agent_name, metrics in self.agent_metrics.items():
            uptime = 100.0
            if metrics.last_execution:
                time_since_last = current_time - metrics.last_execution
                if time_since_last > 300:  # 5 minutes
                    uptime = max(0, 100 - (time_since_last / 60))  # Degrade by 1% per minute
            
            agent_performance[agent_name] = {
                "total_executions": metrics.total_executions,
                "success_rate": f"{metrics.success_rate:.1f}%",
                "avg_execution_time": f"{metrics.avg_execution_time:.2f}s",
                "uptime_percentage": f"{uptime:.1f}%",
                "last_execution": metrics.last_execution
            }
        
        # Session performance
        session_performance = {}
        for session_id, session in self.active_sessions.items():
            success_rate = (session.successful_collections / max(session.total_collections, 1)) * 100
            runtime = current_time - session.start_time
            
            session_performance[session_id] = {
                "symbols": len(session.symbols),
                "agents": len(session.agents),
                "total_collections": session.total_collections,
                "success_rate": f"{success_rate:.1f}%",
                "runtime_hours": f"{runtime / 3600:.1f}h",
                "active": session.active
            }
        
        return {
            "timestamp": current_time,
            "system_status": {
                "registered_agents": len(self.agent_registry),
                "active_sessions": len(self.active_sessions),
                "background_tasks": len(self.background_tasks),
                "data_subscribers": len(self.data_subscribers),
                "performance_subscribers": len(self.performance_subscribers)
            },
            "agent_performance": agent_performance,
            "session_performance": session_performance,
            "overall_health": self._calculate_overall_health()
        }
    
    def _calculate_overall_health(self) -> str:
        """Calculate overall system health status."""
        
        if not self.agent_metrics:
            return "UNKNOWN"
        
        total_success_rate = sum(m.success_rate for m in self.agent_metrics.values()) / len(self.agent_metrics)
        active_agent_ratio = len([m for m in self.agent_metrics.values() if m.last_execution and time.time() - m.last_execution < 300]) / len(self.agent_metrics)
        
        if total_success_rate >= 90 and active_agent_ratio >= 0.8:
            return "EXCELLENT"
        elif total_success_rate >= 75 and active_agent_ratio >= 0.6:
            return "GOOD"
        elif total_success_rate >= 50 and active_agent_ratio >= 0.4:
            return "FAIR"
        else:
            return "POOR"
    
    async def get_live_data_stream(self, symbol: str, max_age_seconds: int = 300) -> AsyncIterator[Dict]:
        """Get live data stream for a specific symbol."""
        
        if not self.redis_client:
            logger.warning("Redis unavailable for live data streaming")
            return
        
        # Get recent cached data
        pattern = f"stealth:collection:*:{symbol}:*"
        keys = await asyncio.get_event_loop().run_in_executor(
            None, self.redis_client.keys, pattern
        )
        
        current_time = time.time()
        
        for key in sorted(keys, reverse=True):  # Most recent first
            try:
                data_json = await asyncio.get_event_loop().run_in_executor(
                    None, self.redis_client.get, key
                )
                
                if data_json:
                    data = json.loads(data_json)
                    if current_time - data["timestamp"] <= max_age_seconds:
                        yield data
                    
            except Exception as e:
                logger.warning(f"Error reading live data: {e}")
    
    async def shutdown(self):
        """Gracefully shutdown the background manager."""
        
        logger.info("🛑 Shutting down Background Stealth Manager...")
        
        # Stop all sessions
        session_ids = list(self.active_sessions.keys())
        for session_id in session_ids:
            await self.stop_collection_session(session_id)
        
        # Stop monitoring
        await self.stop_monitoring()
        
        # Cancel remaining tasks
        for task in self.background_tasks.values():
            task.cancel()
        
        logger.success("✅ Background Stealth Manager shutdown complete")
    
    async def _initialize_redis(self):
        """Initialize Redis client asynchronously"""
        if self.redis_client is None:
            try:
                self.redis_client = await get_redis_client()
                logger.info("✅ Redis client initialized for background manager")
            except Exception as e:
                logger.warning(f"⚠️ Redis unavailable for coordination: {e}")
                self.redis_client = None

# Global instance
background_manager = BackgroundStealthManager()
