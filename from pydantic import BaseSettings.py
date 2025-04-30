import datetime
from datetime import timezone, timedelta
from jose import jwt

def create_access_token(data: dict, secret_key: str, algorithm: str, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    return encoded_jwt
