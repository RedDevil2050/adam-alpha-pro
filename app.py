from fastapi import FastAPI, Response, status
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest, Counter
from contextlib import asynccontextmanager
from backend.api.endpoints.metrics import router as metrics_router
from backend.api.endpoints.health import router as health_router
from backend.api.endpoints.analysis import router as analysis_router
from backend.api.endpoints.market import router as market_router
from backend.api.stealth_streaming import stealth_router
from backend.services.enhanced_websocket_service import continuous_data_service

# Debug: Print router information
print("🔍 Debug: Market router imported successfully")
print(f"🔍 Debug: Market router type: {type(market_router)}")
print(f"🔍 Debug: Market router routes: {len(market_router.routes) if hasattr(market_router, 'routes') else 'No routes attribute'}")

# Define a sample counter metric
REQUEST_COUNT = Counter('request_count', 'Total number of requests')

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager to handle startup and shutdown"""
    # Startup
    try:
        await continuous_data_service.initialize()
        print("✅ Continuous Data Collection Service started")
    except Exception as e:
        print(f"❌ Failed to start Continuous Data Service: {e}")
    
    yield
    
    # Shutdown
    try:
        await continuous_data_service.shutdown()
        print("✅ Continuous Data Collection Service stopped")
    except Exception as e:
        print(f"❌ Error during shutdown: {e}")

# Create an instance of the FastAPI application
app = FastAPI(
    title="Zion Market Analysis Platform - Live Data System",
    lifespan=lifespan
)

# Configure CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Zion Live Data System is running successfully!"}

# Add a simple test endpoint to verify app is working
@app.get("/api/simple-test")
async def simple_test():
    """Simple test endpoint added directly to app.py"""
    return {
        "status": "success",
        "message": "Direct app.py endpoint working!",
        "timestamp": "2025-06-12"
    }

# Add health check endpoint
@app.get("/healthz", status_code=status.HTTP_200_OK)
async def health_check():
    # You can add more sophisticated checks here (e.g., DB connection)
    return {"status": "ok"}

@app.get("/api/health", status_code=status.HTTP_200_OK)
async def api_health_check():
    return {"status": "healthy", "service": "zion-live-data"}

# Continuous Data Service endpoints
@app.get("/api/continuous/status")
async def get_continuous_status():
    """Get status of continuous data collection service"""
    return continuous_data_service.get_session_status()

@app.get("/api/continuous/sessions/{session_id}")
async def get_session_status(session_id: str):
    """Get status of a specific session"""
    return continuous_data_service.get_session_status(session_id)

@app.post("/api/continuous/sessions")
async def start_custom_session(session_data: dict):
    """Start a custom continuous collection session"""
    session_id = session_data.get("session_id")
    symbols = session_data.get("symbols", [])
    data_sources = session_data.get("data_sources")
    interval = session_data.get("interval", 30)
    
    success = await continuous_data_service.start_custom_session(
        session_id, symbols, data_sources, interval
    )
    
    if success:
        return {"status": "success", "message": f"Session {session_id} started"}
    else:
        return {"status": "error", "message": f"Failed to start session {session_id}"}

@app.delete("/api/continuous/sessions/{session_id}")
async def stop_session(session_id: str):
    """Stop a continuous collection session"""
    success = await continuous_data_service.stop_session(session_id)
    
    if success:
        return {"status": "success", "message": f"Session {session_id} stopped"}
    else:
        return {"status": "error", "message": f"Failed to stop session {session_id}"}

# Include all routers
app.include_router(metrics_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api")
app.include_router(analysis_router, prefix="/api")
app.include_router(market_router, prefix="/api")
app.include_router(stealth_router)  # This includes the /api/stealth prefix

# Debug: Print all registered routes
print("🔍 Debug: All registered routes:")
for route in app.routes:
    if hasattr(route, 'path') and hasattr(route, 'methods'):
        print(f"  {route.methods} {route.path}")
    elif hasattr(route, 'path'):
        print(f"  {route.path}")

print("✅ Zion Live Data System startup complete!")
