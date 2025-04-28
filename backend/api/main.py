from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import time
from .endpoints.auth import router as auth_router
from .endpoints.health import router as health_router
from .endpoints.metrics import router as metrics_router
from backend.config.settings import get_settings

settings = get_settings()

app = FastAPI(
    title="Zion Market Analysis Platform API",
    description="API for advanced market analysis and portfolio optimization",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Restrict CORS to trusted origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(health_router, prefix="/api/v1", tags=["system"])
app.include_router(metrics_router, prefix="/api/v1", tags=["system"])

# Add request metrics middleware
@app.middleware("http")
async def add_metrics_middleware(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    # Import here to avoid circular imports
    from .endpoints.metrics import track_request_metrics
    track_request_metrics(request, response, duration)
    
    return response

# Root endpoint
@app.get("/", tags=["system"])
async def root():
    """
    Root endpoint that provides basic API information.
    """
    return {
        "name": "Zion Market Analysis Platform API",
        "version": "1.0.0",
        "documentation": "/api/docs",
        "status": "online"
    }
