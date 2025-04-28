from passlib.context import CryptContext
from datetime import datetime, timedelta
import jwt
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


def create_access_token(data: dict) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    # Ensure ACCESS_TOKEN_EXPIRE_MINUTES is treated as an integer
    expire_minutes = int(ACCESS_TOKEN_EXPIRE_MINUTES) if ACCESS_TOKEN_EXPIRE_MINUTES is not None else 30 # Default to 30 if None
    expire = datetime.utcnow() + timedelta(minutes=expire_minutes)
    to_encode.update({"exp": expire})
    # Ensure SECRET_KEY is not None before encoding
    jwt_secret = SECRET_KEY if SECRET_KEY is not None else "default-secret" # Provide a default or raise error if None is unacceptable
    jwt_algorithm = ALGORITHM if ALGORITHM is not None else "HS256" # Default algorithm
    return jwt.encode(to_encode, jwt_secret, algorithm=jwt_algorithm)

# Add get_password_hash function if it's missing and needed
def get_password_hash(password: str) -> str:
    """Hash a plain password."""
    return pwd_context.hash(password)
