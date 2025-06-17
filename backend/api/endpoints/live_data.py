"""
Live Data Collection Endpoints
=============================

HTTP endpoints for managing live data collection sessions with stealth agents.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from loguru import logger
import time
from backend.agents.data_collectors.web_scrapers.background_manager import background_manager

router = APIRouter(prefix="/api/live", tags=["live-data"])

class CollectionSessionRequest(BaseModel):
    symbols: List[str]
    agents: Optional[List[str]] = ["enhanced_moneycontrol", "moneycontrol", "zerodha"]
    interval: Optional[int] = 30
    session_name: Optional[str] = None

class SymbolSubscriptionRequest(BaseModel):
    symbol: str
    subscribe: bool = True

@router.post("/sessions/start")
async def start_live_collection(
    request: CollectionSessionRequest,
    background_tasks: BackgroundTasks
):
    """Start a live data collection session for specified symbols."""
    try:
        session_id = f"live_session_{int(time.time())}"
        if request.session_name:
            session_id = f"{request.session_name}_{int(time.time())}"
        
        # Validate symbols
        if not request.symbols:
            raise HTTPException(status_code=400, detail="At least one symbol is required")
        
        # Clean and validate symbols
        symbols = [symbol.upper().strip() for symbol in request.symbols if symbol.strip()]
        
        logger.info(f"🚀 Starting live collection session: {session_id}")
        logger.info(f"📊 Symbols: {symbols}")
        logger.info(f"🤖 Agents: {request.agents}")
        logger.info(f"⏰ Interval: {request.interval}s")
        
        # Start the background collection session
        success = await background_manager.start_collection_session(
            session_id=session_id,
            symbols=symbols,
            agent_names=request.agents,
            collection_interval=request.interval
        )
        
        if success:
            return JSONResponse({
                "status": "success",
                "message": f"Live collection session started successfully",
                "session_id": session_id,
                "symbols": symbols,
                "agents": request.agents,
                "interval": request.interval,
                "estimated_data_points_per_hour": len(symbols) * len(request.agents) * (3600 // request.interval)
            })
        else:
            raise HTTPException(status_code=500, detail="Failed to start collection session")
            
    except Exception as e:
        logger.error(f"❌ Error starting live collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions")
async def list_live_sessions():
    """List all active live data collection sessions."""
    try:
        sessions = {}
        for session_id, session in background_manager.active_sessions.items():
            runtime = time.time() - session.start_time
            sessions[session_id] = {
                "session_id": session_id,
                "symbols": list(session.symbols),
                "agents": session.agents,
                "interval": session.collection_interval,
                "start_time": session.start_time,
                "runtime_seconds": runtime,
                "runtime_formatted": f"{int(runtime // 3600)}h {int((runtime % 3600) // 60)}m {int(runtime % 60)}s",
                "total_collections": session.total_collections,
                "successful_collections": session.successful_collections,
                "success_rate": f"{(session.successful_collections / max(session.total_collections, 1)) * 100:.1f}%",
                "status": "active"
            }
        
        return JSONResponse({
            "status": "success",
            "total_sessions": len(sessions),
            "active_sessions": sessions
        })
        
    except Exception as e:
        logger.error(f"❌ Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sessions/{session_id}/stop")
async def stop_live_session(session_id: str):
    """Stop a specific live data collection session."""
    try:
        success = await background_manager.stop_collection_session(session_id)
        
        if success:
            return JSONResponse({
                "status": "success",
                "message": f"Session '{session_id}' stopped successfully",
                "session_id": session_id
            })
        else:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
            
    except Exception as e:
        logger.error(f"❌ Error stopping session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/data/{symbol}")
async def get_live_symbol_data(
    symbol: str, 
    max_age: int = 300,
    limit: int = 50
):
    """Get recent live data for a specific symbol."""
    try:
        symbol = symbol.upper()
        live_data = []
        
        # Get data from the background manager's live stream
        async for data in background_manager.get_live_data_stream(symbol, max_age):
            live_data.append(data)
            if len(live_data) >= limit:
                break
        
        return JSONResponse({
            "status": "success",
            "symbol": symbol,
            "data_points": len(live_data),
            "max_age_seconds": max_age,
            "live_data": live_data
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting live data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/symbols/active")
async def get_active_symbols():
    """Get list of symbols currently being tracked."""
    try:
        active_symbols = set()
        for session in background_manager.active_sessions.values():
            active_symbols.update(session.symbols)
        
        return JSONResponse({
            "status": "success",
            "total_symbols": len(active_symbols),
            "symbols": sorted(list(active_symbols))
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting active symbols: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agents/status")
async def get_agents_status():
    """Get status and performance of all registered agents."""
    try:
        agents_status = {}
        
        for agent_name, metrics in background_manager.agent_metrics.items():
            agents_status[agent_name] = {
                "name": agent_name,
                "total_executions": metrics.total_executions,
                "successful_executions": metrics.successful_executions,
                "failed_executions": metrics.failed_executions,
                "success_rate": f"{metrics.success_rate:.1f}%",
                "avg_execution_time": f"{metrics.avg_execution_time:.2f}s",
                "last_execution": metrics.last_execution,
                "status": "active" if metrics.total_executions > 0 else "inactive"
            }
        
        return JSONResponse({
            "status": "success",
            "total_agents": len(agents_status),
            "agents": agents_status
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting agents status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance")
async def get_system_performance():
    """Get comprehensive system performance metrics."""
    try:
        performance_report = background_manager.get_comprehensive_performance_report()
        
        return JSONResponse({
            "status": "success",
            "timestamp": time.time(),
            "performance": performance_report
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting performance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test/single-collection")
async def test_single_collection(
    symbol: str = "RELIANCE",
    agents: List[str] = ["enhanced_moneycontrol", "zerodha"]
):
    """Test single data collection for debugging purposes."""
    try:
        logger.info(f"🧪 Testing single collection for {symbol}")
        
        results = {}
        for agent_name in agents:
            if agent_name in background_manager.agent_registry:
                agent = background_manager.agent_registry[agent_name]
                start_time = time.time()
                
                try:
                    result = await agent.execute(symbol)
                    execution_time = time.time() - start_time
                    
                    results[agent_name] = {
                        "success": True,
                        "execution_time": f"{execution_time:.2f}s",
                        "result": result
                    }
                    
                except Exception as e:
                    execution_time = time.time() - start_time
                    results[agent_name] = {
                        "success": False,
                        "execution_time": f"{execution_time:.2f}s",
                        "error": str(e)
                    }
            else:
                results[agent_name] = {
                    "success": False,
                    "error": "Agent not registered"
                }
        
        return JSONResponse({
            "status": "success",
            "test_symbol": symbol,
            "agents_tested": len(agents),
            "results": results
        })
        
    except Exception as e:
        logger.error(f"❌ Error in single collection test: {e}")
        raise HTTPException(status_code=500, detail=str(e))
