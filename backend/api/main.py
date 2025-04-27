from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from ..core.orchestrator import SystemOrchestrator
from ..brain import Brain
from ..config.settings import get_settings
from ..security.dependencies import verify_auth_token, get_current_user
from .endpoints.auth import router as auth_router
import logging
from contextlib import asynccontextmanager
