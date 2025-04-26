from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from backend.core.orchestrator import SystemOrchestrator
from backend.utils.monitoring import SystemMonitor

api_key_header = APIKeyHeader(name="X-API-Key")
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Zion Market Analysis API", version="1.0.0")
orchestrator = SystemOrchestrator()
system_monitor = SystemMonitor()

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

@app.get("/api/v1/analyze/{symbol}")
@limiter.limit("60/minute")
async def analyze_stock(symbol: str, api_key: str = Depends(verify_api_key)):
    try:
        health = system_monitor.check_system_health()
        if health["status"] == "critical":
            raise HTTPException(503, "System under maintenance")
        return await orchestrator.analyze_symbol(symbol)
    except Exception as e:
        logger.error(f"Analysis failed for {symbol}: {e}")
        raise HTTPException(500, str(e))
