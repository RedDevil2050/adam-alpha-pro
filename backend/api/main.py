from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .endpoints.health import router as health_router
from .endpoints.metrics import router as metrics_router
# Import the analysis router
from .endpoints.analysis import router as analysis_router 

app = FastAPI(title="Zion Market Analysis Platform")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health_router, prefix="/api", tags=["health"])
app.include_router(metrics_router, prefix="/api/v1", tags=["metrics"])
# Include the analysis router
app.include_router(analysis_router, prefix="/api", tags=["analysis"])
