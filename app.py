from fastapi import FastAPI, Response, status
from fastapi.responses import PlainTextResponse
from prometheus_client import generate_latest, Counter
from backend.api.endpoints.metrics import router as metrics_router

# Define a sample counter metric
REQUEST_COUNT = Counter('request_count', 'Total number of requests')

# Create an instance of the FastAPI application
app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Backend is running successfully!"}

# Add health check endpoint
@app.get("/healthz", status_code=status.HTTP_200_OK)
async def health_check():
    # You can add more sophisticated checks here (e.g., DB connection)
    return {"status": "ok"}

# Include the metrics router
app.include_router(metrics_router, prefix="/api/v1")
