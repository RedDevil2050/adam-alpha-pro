
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Response
from contextlib import asynccontextmanager
from backend.utils.cache_utils import init_redis, redis_client
from backend.utils.loguru_setup import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_redis()
    logger.info("Redis initialized. Application starting.")
    yield
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed.")
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

try:
    from jose import JWTError, jwt
except ImportError:
    class _DummyJWT:
        def encode(self, payload, secret, algorithm): return "dummy"
        def decode(self, token, secret, algorithms): return {}
    jwt = _DummyJWT()
    class JWTError(Exception): pass

from datetime import datetime, timedelta

try:
    from passlib.context import CryptContext
except ImportError:
    class CryptContext:
        def __init__(self, schemes=None, deprecated=None): pass
        def verify(self, pwd, hashed): return True
        def hash(self, pwd): return "hash"

from backend.config.settings import settings
from backend.utils.cache_utils import get_cache, set_cache
from backend.orchestrator import run_orchestration
from backend.api.schemas import SymbolRequest

app = FastAPI(lifespan=lifespan)
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@app.post("/login")
async def login(payload: dict):
    username = payload.get("username")
    password = payload.get("password")
    if username != settings.api_user or not pwd_context.verify(password, settings.api_pass_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode = {"sub": username, "exp": expire}
    token = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.algorithm)
    return {"access_token": token, "token_type": "bearer"}

@app.post("/analyze")
async def analyze(request: SymbolRequest, background_tasks: BackgroundTasks, credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[settings.algorithm])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    background_tasks.add_task(_run_pipeline, request.symbol)
    return {"job_id": request.symbol}

@app.get("/results/{job_id}")
async def get_results(job_id: str, credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[settings.algorithm])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    result = await get_cache(job_id)
    return result or {"status": "PENDING"}

async def _run_pipeline(symbol: str):
    cached = await get_cache(symbol)
    if cached:
        return
    result = await run_orchestration(symbol)
    await set_cache(symbol, result)

from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from backend.brain import Brain


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

async def log_requests(request, call_next):
    logger.info(f"Request: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from backend.brain import Brain
from fastapi import Response

REQUEST_COUNT = Counter("api_requests_total", "Total HTTP requests", ["endpoint"])
AGENT_DURATION = Histogram("agent_execution_duration_seconds", "Duration of agent runs", ["agent"])
AGENT_ERRORS = Counter("agent_errors_total", "Errors from agents", ["agent", "type"])
API_CALLS = Counter("data_provider_api_calls_total", "External API calls", ["provider"])
CACHE_HITS = Counter("cache_hits_total", "Redis cache hits", ["key"])
CACHE_MISSES = Counter("cache_misses_total", "Redis cache misses", ["key"])

@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

if settings.environment == 'dev':
    @app.get('/brain_debug')
    async def brain_debug():
        return {
            'base_weights': Brain.BASE_WEIGHTS,
            'regime_weights': Brain.REGIME_WEIGHTS,
            'last_summary': getattr(Brain, '_last_summary', None)
        }

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    app.openapi_schema = get_openapi(
        title="Adam Alpha Pro API",
        version="1.0.0",
        routes=app.routes,
    )
    return app.openapi_schema
app.openapi = custom_openapi
