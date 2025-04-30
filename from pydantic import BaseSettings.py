from pydantic import BaseSettings
from jose import jwt
from datetime import datetime, timedelta

def create_access_token(data: dict, secret_key: str, algorithm: str, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.now(datetime.UTC) + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    return encoded_jwt
