"""
Real-time Stealth Data Streaming API
===================================

WebSocket and HTTP endpoints for streaming live stealth agent data
with background collection orchestration.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Set, List, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from loguru import logger
import uvicorn
from backend.agents.stealth.background_manager import background_manager
from backend.agents.stealth.moneycontrol_agent import MoneyControlAgent
from backend.agents.stealth.moneycontrol_agent import MoneyControlAgent
from backend.agents.stealth.trendlyne_agent import TrendlyneAgent
from backend.agents.stealth.stockedge_agent import StockEdgeAgent

# Create router for stealth streaming endpoints
stealth_router = APIRouter(prefix="/api/stealth", tags=["stealth-streaming"])

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.symbol_subscribers: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"📡 New WebSocket connection established (total: {len(self.active_connections)})")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        # Remove from symbol subscriptions
        for symbol, subscribers in self.symbol_subscribers.items():
            subscribers.discard(websocket)
        
        logger.info(f"📡 WebSocket connection closed (remaining: {len(self.active_connections)})")
    
    async def subscribe_to_symbol(self, websocket: WebSocket, symbol: str):
        if symbol not in self.symbol_subscribers:
            self.symbol_subscribers[symbol] = set()
        self.symbol_subscribers[symbol].add(websocket)
        logger.debug(f"📊 Client subscribed to {symbol}")
    
    async def unsubscribe_from_symbol(self, websocket: WebSocket, symbol: str):
        if symbol in self.symbol_subscribers:
            self.symbol_subscribers[symbol].discard(websocket)
        logger.debug(f"📊 Client unsubscribed from {symbol}")
    
    async def broadcast_to_symbol(self, symbol: str, data: dict):
        if symbol not in self.symbol_subscribers:
            return
        
        message = json.dumps({
            "type": "symbol_update",
            "symbol": symbol,
            "data": data,
            "timestamp": time.time()
        })
        
        disconnected = []
        for websocket in self.symbol_subscribers[symbol]:
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected clients
        for ws in disconnected:
            self.symbol_subscribers[symbol].discard(ws)
    
    async def broadcast_to_all(self, data: dict):
        if not self.active_connections:
            return
        
        message = json.dumps({
            "type": "broadcast",
            "data": data,
            "timestamp": time.time()
        })
        
        disconnected = []
        for websocket in self.active_connections:
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to broadcast to WebSocket: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected clients
        for ws in disconnected:
            self.disconnect(ws)

# Global connection manager
manager = ConnectionManager()

# Initialize background manager with stealth agents
async def initialize_background_system():
    """Initialize the background collection system."""
    try:
        # Register enhanced agents
        agents = [
            ("moneycontrol", MoneyControlAgent()),
            ("moneycontrol", MoneyControlAgent()),
            ("trendlyne", TrendlyneAgent()),
            ("stockedge", StockEdgeAgent())
        ]
        
        for agent_name, agent_instance in agents:
            background_manager.register_agent(agent_name, agent_instance)
            logger.info(f"✅ Registered {agent_name} for background collection")
        
        # Subscribe to data updates for WebSocket streaming
        def data_subscriber(data):
            """Handle background collection data updates."""
            asyncio.create_task(handle_background_data_update(data))
        
        def performance_subscriber(performance_data):
            """Handle performance updates."""
            asyncio.create_task(handle_performance_update(performance_data))
        
        background_manager.subscribe_to_data(data_subscriber)
        background_manager.subscribe_to_performance(performance_subscriber)
        
        # Start monitoring
        await background_manager.start_monitoring()
        
        logger.success("🚀 Background stealth system initialized")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize background system: {e}")

async def handle_background_data_update(data: Dict):
    """Handle background data updates and stream to WebSocket clients."""
    try:
        symbol = data.get("symbol")
        if symbol:
            # Stream to symbol subscribers
            await manager.broadcast_to_symbol(symbol, {
                "type": "live_data",
                "successful_agents": data.get("successful_agents", []),
                "failed_agents": data.get("failed_agents", []),
                "timestamp": data.get("timestamp"),
                "session_id": data.get("session_id")
            })
        
        # Also broadcast summary to all clients
        await manager.broadcast_to_all({
            "type": "data_update",
            "symbol": symbol,
            "agent_count": len(data.get("successful_agents", [])),
            "timestamp": data.get("timestamp")
        })
        
    except Exception as e:
        logger.error(f"❌ Error handling background data update: {e}")

async def handle_performance_update(performance_data: Dict):
    """Handle performance updates and stream to clients."""
    try:
        await manager.broadcast_to_all({
            "type": "performance_update",
            "system_health": performance_data.get("overall_health"),
            "active_sessions": performance_data.get("system_status", {}).get("active_sessions", 0),
            "agent_performance": performance_data.get("agent_performance", {}),
            "timestamp": performance_data.get("timestamp")
        })
    except Exception as e:
        logger.error(f"❌ Error handling performance update: {e}")

# WebSocket endpoint for real-time streaming
@stealth_router.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time stealth data streaming."""
    await manager.connect(websocket)
    
    try:
        # Send welcome message
        await websocket.send_text(json.dumps({
            "type": "welcome",
            "message": "Connected to Zion Stealth Data Stream",
            "timestamp": time.time(),
            "available_commands": [
                "subscribe:SYMBOL",
                "unsubscribe:SYMBOL", 
                "get_performance",
                "list_sessions"
            ]
        }))
        
        while True:
            # Receive messages from client
            message = await websocket.receive_text()
            
            try:
                if message.startswith("subscribe:"):
                    symbol = message.split(":", 1)[1].upper()
                    await manager.subscribe_to_symbol(websocket, symbol)
                    await websocket.send_text(json.dumps({
                        "type": "subscribed",
                        "symbol": symbol,
                        "message": f"Subscribed to {symbol} updates"
                    }))
                
                elif message.startswith("unsubscribe:"):
                    symbol = message.split(":", 1)[1].upper()
                    await manager.unsubscribe_from_symbol(websocket, symbol)
                    await websocket.send_text(json.dumps({
                        "type": "unsubscribed", 
                        "symbol": symbol,
                        "message": f"Unsubscribed from {symbol} updates"
                    }))
                
                elif message == "get_performance":
                    performance = background_manager.get_comprehensive_performance_report()
                    await websocket.send_text(json.dumps({
                        "type": "performance_report",
                        "data": performance
                    }))
                
                elif message == "list_sessions":
                    sessions = list(background_manager.active_sessions.keys())
                    await websocket.send_text(json.dumps({
                        "type": "active_sessions",
                        "sessions": sessions
                    }))
                
                else:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": f"Unknown command: {message}"
                    }))
                    
            except Exception as e:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Command processing error: {str(e)}"
                }))
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# HTTP endpoints for background collection management

@stealth_router.post("/sessions/start")
async def start_collection_session(
    session_data: Dict[str, Any],
    background_tasks: BackgroundTasks
):
    """Start a background collection session."""
    try:
        session_id = session_data.get("session_id", f"session_{int(time.time())}")
        symbols = session_data.get("symbols", [])
        agent_names = session_data.get("agents", ["enhanced_moneycontrol", "moneycontrol"])
        interval = session_data.get("interval", 30)
        
        if not symbols:
            raise HTTPException(status_code=400, detail="No symbols provided")
        
        # Ensure background system is initialized
        if not background_manager.agent_registry:
            background_tasks.add_task(initialize_background_system)
            await asyncio.sleep(1)  # Give it a moment to initialize
        
        success = await background_manager.start_collection_session(
            session_id=session_id,
            symbols=symbols,
            agent_names=agent_names,
            collection_interval=interval
        )
        
        if success:
            return JSONResponse({
                "status": "success",
                "message": f"Collection session '{session_id}' started",
                "session_id": session_id,
                "symbols": symbols,
                "agents": agent_names,
                "interval": interval
            })
        else:
            raise HTTPException(status_code=400, detail="Failed to start collection session")
    
    except Exception as e:
        logger.error(f"Error starting collection session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@stealth_router.post("/sessions/{session_id}/stop")
async def stop_collection_session(session_id: str):
    """Stop a background collection session."""
    try:
        success = await background_manager.stop_collection_session(session_id)
        
        if success:
            return JSONResponse({
                "status": "success",
                "message": f"Collection session '{session_id}' stopped"
            })
        else:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    
    except Exception as e:
        logger.error(f"Error stopping collection session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@stealth_router.get("/sessions")
async def list_active_sessions():
    """List all active collection sessions."""
    try:
        sessions = {}
        for session_id, session in background_manager.active_sessions.items():
            sessions[session_id] = {
                "symbols": list(session.symbols),
                "agents": session.agents,
                "start_time": session.start_time,
                "interval": session.collection_interval,
                "total_collections": session.total_collections,
                "successful_collections": session.successful_collections,
                "success_rate": f"{(session.successful_collections / max(session.total_collections, 1)) * 100:.1f}%"
            }
        
        return JSONResponse({
            "status": "success",
            "active_sessions": sessions,
            "total_sessions": len(sessions)
        })
    
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@stealth_router.get("/performance")
async def get_performance_report():
    """Get comprehensive performance report."""
    try:
        report = background_manager.get_comprehensive_performance_report()
        return JSONResponse({
            "status": "success",
            "performance_report": report
        })
    
    except Exception as e:
        logger.error(f"Error getting performance report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@stealth_router.get("/agents")
async def list_registered_agents():
    """List all registered stealth agents."""
    try:
        agents = {}
        for agent_name, metrics in background_manager.agent_metrics.items():
            agents[agent_name] = {
                "total_executions": metrics.total_executions,
                "success_rate": f"{metrics.success_rate:.1f}%",
                "avg_execution_time": f"{metrics.avg_execution_time:.2f}s",
                "last_execution": metrics.last_execution
            }
        
        return JSONResponse({
            "status": "success",
            "registered_agents": agents,
            "total_agents": len(agents)
        })
    
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@stealth_router.post("/agents/test")
async def test_single_agent(test_data: Dict[str, Any]):
    """Test a single stealth agent."""
    try:
        agent_name = test_data.get("agent", "enhanced_moneycontrol")
        symbol = test_data.get("symbol", "RELIANCE")
        
        if agent_name not in background_manager.agent_registry:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
        
        agent = background_manager.agent_registry[agent_name]
        
        start_time = time.time()
        result = await agent.execute(symbol)
        execution_time = time.time() - start_time
        
        return JSONResponse({
            "status": "success",
            "agent": agent_name,
            "symbol": symbol,
            "execution_time": f"{execution_time:.2f}s",
            "result": result
        })
    
    except Exception as e:
        logger.error(f"Error testing agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@stealth_router.get("/live/{symbol}")
async def get_live_symbol_data(symbol: str, max_age: int = 300):
    """Get live cached data for a specific symbol."""
    try:
        symbol = symbol.upper()
        live_data = []
        
        async for data in background_manager.get_live_data_stream(symbol, max_age):
            live_data.append(data)
        
        return JSONResponse({
            "status": "success",
            "symbol": symbol,
            "live_data": live_data,
            "data_points": len(live_data)
        })
    
    except Exception as e:
        logger.error(f"Error getting live data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Initialize background system on startup
@stealth_router.on_event("startup")
async def startup_event():
    """Initialize background system on router startup."""
    await initialize_background_system()

@stealth_router.on_event("shutdown") 
async def shutdown_event():
    """Cleanup on router shutdown."""
    await background_manager.shutdown()

# Standalone server for testing
async def run_streaming_server():
    """Run the streaming server standalone for testing."""
    from fastapi import FastAPI
    
    app = FastAPI(title="Zion Stealth Data Streaming Server")
    app.include_router(stealth_router)
    
    # Initialize background system
    await initialize_background_system()
    
    logger.info("🚀 Starting Zion Stealth Data Streaming Server on http://localhost:8001")
    
    config = uvicorn.Config(app, host="0.0.0.0", port=8001, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(run_streaming_server())
