from pydantic import BaseSettings

class SecuritySettings(BaseSettings):
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

class Settings(BaseSettings):
    security: SecuritySettings = SecuritySettings()

settings = Settings()
