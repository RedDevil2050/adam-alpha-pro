from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from prometheus_client import generate_latest, Counter

# Define a sample counter metric
REQUEST_COUNT = Counter('request_count', 'Total number of requests')

# Create an instance of the FastAPI application
app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Backend is running successfully!"}

@app.get("/api/v1/metrics", response_class=PlainTextResponse)
def get_metrics():
    """Endpoint to expose Prometheus metrics."""
    REQUEST_COUNT.inc()  # Increment the counter for each request
    return generate_latest().decode("utf-8")
