from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from backend.core.orchestrator import SystemOrchestrator
from backend.utils.monitoring import SystemMonitor
from backend.utils.system_check import SystemCheck
from backend.config.settings import settings
from loguru import logger

api_key_header = APIKeyHeader(name="X-API-Key")
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Zion Market Analysis API", version="1.0.0")

# Security middleware
async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != settings.API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

# Add CORS and rate limiting
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/market/status")
async def get_market_status():
    """Get current market system status"""
    monitor = app.state.monitor
    market_status = monitor.check_market_readiness()
    production_metrics = monitor.get_production_metrics()
    
    return {
        "market_ready": market_status["market_ready"],
        "market_hours": market_status["market_status"],
        "system_health": market_status["system_health"],
        "metrics": production_metrics,
        "components": monitor.components
    }

@app.get("/api/v1/analyze/{symbol}")
@limiter.limit("60/minute")
async def analyze_stock(symbol: str, api_key: str = Depends(verify_api_key)):
    market_status = app.state.monitor.check_market_readiness()
    if not market_status["market_ready"]:
        raise HTTPException(503, "Market system not ready")
        
    orchestrator = app.state.orchestrator
    monitor = app.state.monitor
    try:
        health = monitor.check_system_health()
        if health["status"] == "critical":
            raise HTTPException(503, "System under maintenance")
        return await orchestrator.analyze_symbol(symbol)
    except Exception as e:
        logger.error(f"Analysis failed for {symbol}: {e}")
        raise HTTPException(500, str(e))

@app.get("/health")
async def health_check():
    """System health and readiness check"""
    monitor = app.state.monitor
    readiness = monitor.is_ready()
    if not readiness["ready"]:
        raise HTTPException(status_code=503, detail="System not ready")
    return {
        "status": "healthy",
        "readiness": readiness,
        "metrics": monitor.get_health_metrics()
    }

@app.get("/system/diagnostics")
async def system_diagnostics():
    """Full system diagnostic check"""
    connections = await SystemCheck.verify_connections()
    health = system_monitor.check_system_health()
    readiness = system_monitor.is_ready()
    
    return {
        "connections": connections,
        "health": health,
        "readiness": readiness,
        "components": app.state.monitor.components
    }

@app.post("/pipeline/test")
async def run_pipeline_test():
    """Run end-to-end pipeline test"""
    try:
        test_symbol = "AAPL"
        
        # System check
        health = system_monitor.check_system_health()
        if health["status"] != "healthy":
            raise HTTPException(503, "System unhealthy")
            
        # Test analysis
        result = await app.state.orchestrator.analyze_symbol(test_symbol)
        
        return {
            "status": "success",
            "pipeline_health": health,
            "test_result": result,
            "execution_time": result.get("execution_metrics", {}).get("total_time", 0)
        }
    except Exception as e:
        logger.error(f"Pipeline test failed: {e}")
        raise HTTPException(500, str(e))

@app.get("/status")
async def get_status():
    """Get complete system status"""
    monitor = app.state.monitor
    health = monitor.check_system_health()
    readiness = monitor.is_ready()
    production_metrics = monitor.get_production_metrics()
    
    return {
        "status": "operational" if readiness["ready"] else "degraded",
        "health": health,
        "metrics": production_metrics,
        "uptime": monitor._calculate_uptime()
    }

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "path": request.url.path}
    )

async def startup_event():
    """Execute on API startup"""
    if not hasattr(app.state, "monitor"):
        # Handle case when running API directly
        orchestrator, monitor = await initialize_system()
        app.state.orchestrator = orchestrator
        app.state.monitor = monitor
    logger.info("API startup complete")

async def shutdown_event():
    """Execute on API shutdown"""
    logger.info("Shutting down API")
    # Add cleanup if needed

app.add_event_handler("startup", startup_event)
app.add_event_handler("shutdown", shutdown_event)
