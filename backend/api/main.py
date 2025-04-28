from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .endpoints.auth import router as auth_router

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include authentication router
app.include_router(auth_router, prefix="/auth", tags=["auth"])
