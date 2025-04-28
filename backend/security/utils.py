from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
from typing import Optional
from backend.config.settings import get_settings

settings = get_settings()

# Correctly access nested settings
SECRET_KEY = settings.security.JWT_SECRET_KEY
ALGORITHM = settings.security.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.security.ACCESS_TOKEN_EXPIRE_MINUTES

# Initialize CryptContext here if it's used globally in this module
# If verify_password is the only place it's used, it can stay local.
# For clarity, let's define it here if it might be used elsewhere.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)  # Default expiration time
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, "your-secret-key", algorithm="HS256")
    return encoded_jwt


# Add get_password_hash function if it's missing and needed
def get_password_hash(password: str) -> str:
    """Hash a plain password."""
    return pwd_context.hash(password)
