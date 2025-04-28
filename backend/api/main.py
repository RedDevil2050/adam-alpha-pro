from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .endpoints.auth import router as auth_router
from backend.config.settings import get_settings

settings = get_settings()

app = FastAPI()

# Restrict CORS to trusted origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

# Include authentication router
app.include_router(auth_router, prefix="/auth", tags=["auth"])
