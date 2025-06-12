"""
Continuous Live Data Collection Service
======================================

Ensures uninterrupted data flow via both API and stealth agents with:
- Auto-starting default collection sessions
- Failover between API and stealth sources
- Health monitoring and automatic recovery
- Data persistence and streaming
- Real-time alerts for interruptions
"""

import asyncio
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Callable
from dataclasses import dataclass
from loguru import logger

from backend.agents.stealth.background_manager import background_manager
from backend.agents.stealth.moneycontrol_agent import MoneyControlAgent
from backend.agents.stealth.trendlyne_agent import TrendlyneAgent
from backend.agents.stealth.stockedge_agent import StockEdgeAgent
from backend.data_providers import ZerodhaProvider, AlphaVantageProvider, YahooFinanceProvider

@dataclass
class DataSource:
    """Configuration for a data source"""
    name: str
    type: str  # 'api' or 'stealth'
    priority: int  # Lower number = higher priority
    enabled: bool = True
    last_success: Optional[float] = None
    consecutive_failures: int = 0
    max_failures: int = 3

@dataclass
class ContinuousSession:
    """Configuration for continuous data collection"""
    session_id: str
    symbols: Set[str]
    data_sources: List[DataSource]
    collection_interval: int
    auto_restart: bool = True
    health_check_interval: int = 60
    created_at: float = None
    is_active: bool = True

class ContinuousDataCollectionService:
    """
    Service that ensures continuous data flow with multiple redundant sources
    """
    
    def __init__(self):
        self.active_sessions: Dict[str, ContinuousSession] = {}
        self.api_providers = {}
        self.stealth_agents = {}
        self.health_monitors = {}
        self.alert_callbacks: List[Callable] = []
        
        # Alert suppression to prevent spam
        self.last_alerts: Dict[str, float] = {}  # alert_key -> timestamp
        self.alert_suppression_time = 300  # 5 minutes between same alerts
        
        # Default configuration
        self.default_symbols = [
            'RELIANCE', 'TCS', 'HDFCBANK', 'ICICIBANK', 'HINDUNILVR',
            'INFY', 'KOTAKBANK', 'SBIN', 'BHARTIARTL', 'ITC'        ]
        
        self.default_data_sources = [
            DataSource("zerodha_api", "api", 1, True),
            DataSource("alpha_vantage_api", "api", 2, True),
            DataSource("yahoo_finance_api", "api", 3, True),
            DataSource("moneycontrol", "stealth", 4, True),
            DataSource("trendlyne", "stealth", 5, True),
            DataSource("stockedge", "stealth", 6, True),
        ]
        
        logger.info("🔄 Continuous Data Collection Service initialized")
    
    async def initialize(self):
        """Initialize all data sources and providers"""
        try:
            # Initialize API providers
            await self._initialize_api_providers()
            # Initialize stealth agents
            await self._initialize_stealth_agents()
            
            # Start default continuous collection session
            await self._start_default_session()
            
            # Start health monitoring
            await self._start_health_monitoring()
            
            logger.success("✅ Continuous Data Collection Service fully initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Continuous Data Service: {e}")
            raise
    
    async def _initialize_api_providers(self):
        """Initialize API data providers"""
        try:
            # Initialize Zerodha API provider
            self.api_providers["zerodha_api"] = ZerodhaProvider()
            await self.api_providers["zerodha_api"].initialize()
            logger.info("✅ Zerodha API provider initialized")
            
            # Initialize Alpha Vantage provider
            self.api_providers["alpha_vantage_api"] = AlphaVantageProvider()
            await self.api_providers["alpha_vantage_api"].initialize()
            logger.info("✅ Alpha Vantage API provider initialized")
            
            # Initialize Yahoo Finance provider (fallback)
            self.api_providers["yahoo_finance_api"] = YahooFinanceProvider()
            await self.api_providers["yahoo_finance_api"].initialize()
            logger.info("✅ Yahoo Finance API provider initialized")
            
        except Exception as e:
            logger.warning(f"⚠️ Some API providers failed to initialize: {e}")
    
    async def _initialize_stealth_agents(self):
        """Initialize stealth agents through background manager"""
        try:            # Register stealth agents with background manager
            stealth_configs = [
                ("moneycontrol", MoneyControlAgent()),
                ("trendlyne", TrendlyneAgent()),
                ("stockedge", StockEdgeAgent())
            ]
            
            for agent_name, agent_instance in stealth_configs:
                background_manager.register_agent(agent_name, agent_instance)
                self.stealth_agents[agent_name] = agent_instance
                logger.info(f"✅ Registered stealth agent: {agent_name}")
            
            # Start background manager monitoring
            await background_manager.start_monitoring()
            logger.info("✅ Background stealth manager started")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize stealth agents: {e}")
            raise
    
    async def _start_default_session(self):
        """Start the default continuous collection session"""
        try:
            session_id = "default_continuous_session"
            
            session = ContinuousSession(
                session_id=session_id,
                symbols=set(self.default_symbols),
                data_sources=self.default_data_sources.copy(),
                collection_interval=30,  # 30 seconds
                auto_restart=True,
                health_check_interval=60,  # 1 minute
                created_at=time.time()
            )
            
            self.active_sessions[session_id] = session
            
            # Start the collection loop
            asyncio.create_task(self._continuous_collection_loop(session_id))
            
            logger.success(f"🚀 Started default continuous session for {len(session.symbols)} symbols")
            
        except Exception as e:
            logger.error(f"❌ Failed to start default session: {e}")
            raise
    
    async def _continuous_collection_loop(self, session_id: str):
        """Main continuous collection loop for a session"""
        session = self.active_sessions.get(session_id)
        if not session:
            logger.error(f"❌ Session {session_id} not found")
            return
        
        logger.info(f"🔄 Starting continuous collection loop for session {session_id}")
        
        while session.is_active:
            try:
                collection_start = time.time()
                
                # Collect data from all symbols using best available source
                for symbol in session.symbols:
                    await self._collect_symbol_data(session_id, symbol)
                
                # Calculate sleep time
                collection_duration = time.time() - collection_start
                sleep_time = max(session.collection_interval - collection_duration, 5)
                
                logger.debug(f"📊 Collection cycle completed in {collection_duration:.2f}s, sleeping {sleep_time:.2f}s")
                await asyncio.sleep(sleep_time)
                
            except asyncio.CancelledError:
                logger.info(f"🛑 Collection loop cancelled for session {session_id}")
                break
            except Exception as e:
                logger.error(f"❌ Collection loop error for session {session_id}: {e}")
                await asyncio.sleep(30)  # Wait before retry
    
    async def _collect_symbol_data(self, session_id: str, symbol: str):
        """Collect data for a symbol using the best available source"""
        session = self.active_sessions.get(session_id)
        if not session:
            return
        
        # Sort sources by priority and filter enabled ones
        available_sources = [
            source for source in session.data_sources 
            if source.enabled and source.consecutive_failures < source.max_failures
        ]
        available_sources.sort(key=lambda x: x.priority)
        
        # Try each source until successful
        for source in available_sources:
            try:
                if source.type == "api":
                    data = await self._collect_via_api(source.name, symbol)
                elif source.type == "stealth":
                    data = await self._collect_via_stealth(source.name, symbol)
                else:
                    continue
                
                if data and not data.get("error"):
                    # Success - reset failure count
                    source.consecutive_failures = 0
                    source.last_success = time.time()
                    
                    # Stream the data
                    await self._stream_collected_data(session_id, symbol, source.name, data)
                    
                    logger.debug(f"✅ {symbol} data collected via {source.name}")
                    return
                else:
                    raise Exception(f"No valid data from {source.name}")
                    
            except Exception as e:
                source.consecutive_failures += 1
                logger.warning(f"⚠️ {source.name} failed for {symbol}: {e} (failures: {source.consecutive_failures})")
                
                # Alert if source is failing frequently
                if source.consecutive_failures >= source.max_failures:
                    await self._send_alert(f"Data source {source.name} has exceeded max failures", "source_failure")
        
        # If all sources failed, send critical alert
        await self._send_alert(f"All data sources failed for symbol {symbol}", "critical_failure")
    
    async def _collect_via_api(self, provider_name: str, symbol: str) -> Dict:
        """Collect data via API provider"""
        provider = self.api_providers.get(provider_name)
        if not provider:
            raise Exception(f"API provider {provider_name} not available")
        
        # Use provider's get_live_price or similar method
        if hasattr(provider, 'get_live_price'):
            data = await provider.get_live_price(symbol)
        elif hasattr(provider, 'get_quote'):
            data = await provider.get_quote(symbol)
        else:
            raise Exception(f"Provider {provider_name} doesn't support live data")
        
        return data
    
    async def _collect_via_stealth(self, agent_name: str, symbol: str) -> Dict:
        """Collect data via stealth agent"""
        agent = self.stealth_agents.get(agent_name)
        if not agent:
            raise Exception(f"Stealth agent {agent_name} not available")
        
        # Execute the stealth agent
        data = await agent.execute(symbol)
        return data
    
    async def _stream_collected_data(self, session_id: str, symbol: str, source: str, data: Dict):
        """Stream collected data to subscribers"""
        try:
            stream_data = {
                "type": "continuous_data",
                "session_id": session_id,
                "symbol": symbol,
                "source": source,
                "data": data,
                "timestamp": time.time(),
                "collection_type": "continuous"
            }
            
            # Stream via background manager if it has subscribers
            if hasattr(background_manager, 'data_subscribers'):
                for subscriber in background_manager.data_subscribers:
                    try:
                        if asyncio.iscoroutinefunction(subscriber):
                            await subscriber(stream_data)
                        else:
                            subscriber(stream_data)
                    except Exception as e:
                        logger.warning(f"Subscriber error: {e}")
            
        except Exception as e:
            logger.warning(f"Failed to stream data: {e}")
    async def _start_health_monitoring(self):
        """Start health monitoring for all sessions"""
        asyncio.create_task(self._health_monitoring_loop())
        logger.info("📊 Health monitoring started")
    
    async def _health_monitoring_loop(self):
        """Continuous health monitoring loop with adaptive frequency"""
        base_interval = 60  # Base check interval (1 minute)
        extended_interval = 300  # Extended interval when healthy (5 minutes)
        
        while True:
            try:
                # Determine monitoring interval based on system health
                healthy_sessions = 0
                total_sessions = len(self.active_sessions)
                
                for session_id, session in self.active_sessions.items():
                    session_health = await self._check_session_health(session_id, session)
                    if session_health:  # If session is healthy
                        healthy_sessions += 1
                
                await self._check_system_health()
                
                # Adaptive interval: longer interval when everything is healthy
                if total_sessions > 0 and healthy_sessions == total_sessions:
                    sleep_interval = extended_interval
                    logger.debug(f"📊 All sessions healthy, using extended monitoring interval ({extended_interval}s)")
                else:
                    sleep_interval = base_interval
                    if total_sessions > 0:
                        logger.debug(f"📊 Health issues detected, using base monitoring interval ({base_interval}s)")
                
                await asyncio.sleep(sleep_interval)
                
            except Exception as e:
                logger.error(f"❌ Health monitoring error: {e}")
                await asyncio.sleep(base_interval)  # Fallback to base interval on error
    
    async def _check_session_health(self, session_id: str, session: ContinuousSession) -> bool:
        """Check health of a specific session. Returns True if session is healthy."""
        current_time = time.time()
        
        # Check data source health
        unhealthy_sources = []
        primary_source_working = False
        
        for source in session.data_sources:
            if source.last_success:
                time_since_success = current_time - source.last_success
                if time_since_success > 300:  # 5 minutes without success
                    unhealthy_sources.append(source.name)
                else:
                    # Check if this is the primary source (priority 1)
                    if source.priority == 1:
                        primary_source_working = True
            elif source.enabled:  # Never had success but enabled
                unhealthy_sources.append(source.name)
        
        # Only alert about unhealthy sources if:
        # 1. Primary source is not working, OR
        # 2. More than half of all sources are unhealthy, OR  
        # 3. All sources are unhealthy
        should_alert = (
            not primary_source_working or 
            len(unhealthy_sources) > len(session.data_sources) / 2 or
            len(unhealthy_sources) == len(session.data_sources)
        )
        
        if unhealthy_sources and should_alert:
            alert_level = "critical" if not primary_source_working else "session_health"
            alert_msg = f"Session {session_id} has unhealthy sources: {unhealthy_sources}"
            if primary_source_working:
                alert_msg += " (Primary source working, backup sources idle)"
            
            await self._send_alert(alert_msg, alert_level)
        
        # Auto-restart if needed and all sources are failing
        if session.auto_restart and len(unhealthy_sources) == len(session.data_sources):
            logger.warning(f"🔄 Auto-restarting session {session_id} due to source failures")
            await self._restart_session(session_id)
        
        # Return True if session is healthy (primary working or no critical issues)
        return primary_source_working or len(unhealthy_sources) < len(session.data_sources) / 2
    
    async def _check_system_health(self):
        """Check overall system health"""
        try:
            # Check background manager health
            if hasattr(background_manager, 'get_comprehensive_performance_report'):
                report = background_manager.get_comprehensive_performance_report()
                overall_health = report.get('overall_health', 'Unknown')
                
                if overall_health in ['Critical', 'Poor']:
                    await self._send_alert(
                        f"System health is {overall_health}",
                        "system_health"
                    )
            
        except Exception as e:
            logger.warning(f"System health check failed: {e}")
    
    async def _restart_session(self, session_id: str):
        """Restart a failed session"""
        try:
            session = self.active_sessions.get(session_id)
            if not session:
                return
            
            # Reset all source failure counts
            for source in session.data_sources:
                source.consecutive_failures = 0
            
            logger.info(f"🔄 Session {session_id} restarted with reset failure counts")
            
        except Exception as e:
            logger.error(f"❌ Failed to restart session {session_id}: {e}")
    async def _send_alert(self, message: str, alert_type: str):
        """Send alert to registered callbacks with suppression to prevent spam"""
        # Create a unique key for this alert type and message
        alert_key = f"{alert_type}:{hash(message)}"
        current_time = time.time()
        
        # Check if we should suppress this alert
        if alert_key in self.last_alerts:
            time_since_last = current_time - self.last_alerts[alert_key]
            if time_since_last < self.alert_suppression_time:
                # Suppress duplicate alert
                logger.debug(f"🔇 Suppressing duplicate alert: {alert_type} (last sent {time_since_last:.0f}s ago)")
                return
        
        # Record this alert
        self.last_alerts[alert_key] = current_time
        
        alert_data = {
            "type": alert_type,
            "message": message,
            "timestamp": current_time,
            "service": "continuous_data_collection"
        }
        
        logger.warning(f"🚨 ALERT [{alert_type}]: {message}")
        
        # Send to registered alert callbacks
        for callback in self.alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert_data)
                else:
                    callback(alert_data)
            except Exception as e:
                logger.warning(f"Alert callback error: {e}")
    
    def subscribe_to_alerts(self, callback: Callable):
        """Subscribe to system alerts"""
        self.alert_callbacks.append(callback)
        logger.info("📢 New alert subscriber registered")
    
    async def start_custom_session(
        self,
        session_id: str,
        symbols: List[str],
        data_sources: List[str] = None,
        collection_interval: int = 30
    ) -> bool:
        """Start a custom continuous collection session"""
        try:
            if session_id in self.active_sessions:
                logger.warning(f"⚠️ Session {session_id} already exists")
                return False
            
            # Use default sources if none specified
            if not data_sources:
                sources = self.default_data_sources.copy()
            else:
                sources = [
                    source for source in self.default_data_sources
                    if source.name in data_sources
                ]
            
            session = ContinuousSession(
                session_id=session_id,
                symbols=set(symbols),
                data_sources=sources,
                collection_interval=collection_interval,
                auto_restart=True,
                created_at=time.time()
            )
            
            self.active_sessions[session_id] = session
            
            # Start collection loop
            asyncio.create_task(self._continuous_collection_loop(session_id))
            
            logger.success(f"🚀 Started custom session {session_id} for {len(symbols)} symbols")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start custom session: {e}")
            return False
    
    async def stop_session(self, session_id: str) -> bool:
        """Stop a continuous collection session"""
        try:
            session = self.active_sessions.get(session_id)
            if not session:
                logger.warning(f"⚠️ Session {session_id} not found")
                return False
            
            session.is_active = False
            del self.active_sessions[session_id]
            
            logger.success(f"🛑 Stopped session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to stop session {session_id}: {e}")
            return False
    
    def get_session_status(self, session_id: str = None) -> Dict:
        """Get status of sessions"""
        if session_id:
            session = self.active_sessions.get(session_id)
            if not session:
                return {"error": "Session not found"}
            
            return {
                "session_id": session.session_id,
                "symbols": list(session.symbols),
                "sources": len(session.data_sources),
                "active": session.is_active,
                "created_at": session.created_at,
                "uptime": time.time() - session.created_at if session.created_at else 0
            }
        else:
            return {
                "active_sessions": len(self.active_sessions),
                "sessions": {
                    sid: {
                        "symbols": len(session.symbols),
                        "active": session.is_active,
                        "uptime": time.time() - session.created_at if session.created_at else 0
                    }
                    for sid, session in self.active_sessions.items()
                }
            }
    
    async def shutdown(self):
        """Gracefully shutdown the service"""
        logger.info("🛑 Shutting down Continuous Data Collection Service...")
        
        # Stop all sessions
        session_ids = list(self.active_sessions.keys())
        for session_id in session_ids:
            await self.stop_session(session_id)
        
        # Shutdown background manager
        if hasattr(background_manager, 'shutdown'):
            await background_manager.shutdown()
        
        logger.success("✅ Continuous Data Collection Service shutdown complete")

# Global service instance
continuous_data_service = ContinuousDataCollectionService()
