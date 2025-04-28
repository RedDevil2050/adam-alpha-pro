import os
from typing import Dict, Any, Optional, List
from pydantic import BaseSettings, Field, validator
import logging
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class APIKeys(BaseSettings):
    """API keys for various data providers"""
    ALPHA_VANTAGE_KEY: Optional[str] = None
    POLYGON_API_KEY: Optional[str] = None
    FINNHUB_API_KEY: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True

class DataProviderSettings(BaseSettings):
    """Settings for data providers"""
    PRIMARY_PROVIDER: str = "yahoo_finance"
    FALLBACK_PROVIDERS: List[str] = ["alpha_vantage", "polygon", "finnhub", "web_scraper"]
    CACHE_TTL: int = 3600  # seconds
    REQUEST_TIMEOUT: int = 10  # seconds
    MAX_RETRIES: int = 3
    RETRY_BACKOFF: float = 2.0
    CIRCUIT_BREAKER_THRESHOLD: int = 5
    CIRCUIT_BREAKER_TIMEOUT: int = 300  # seconds

class LoggingSettings(BaseSettings):
    """Logging configuration"""
    LEVEL: str = "INFO"
    FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: Optional[str] = "logs/app.log"

class SecuritySettings(BaseSettings):
    """Security-related settings"""
    JWT_SECRET: str = Field(..., env="JWT_SECRET_KEY")
    TOKEN_EXPIRATION: int = 3600  # seconds
    ALGORITHM: str = "HS256"
    
    @validator("JWT_SECRET")
    def validate_jwt_secret(cls, v):
        if not v or v == "your-secret-key-here":
            raise ValueError("JWT_SECRET must be set to a secure random value")
        return v

class Settings(BaseSettings):
    """Main settings class"""
    ENV: str = Field(default="development", env="ENV")
    DEBUG: bool = Field(default=True, env="DEBUG")
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    
    # Nested settings
    api_keys: APIKeys = APIKeys()
    data_provider: DataProviderSettings = DataProviderSettings()
    logging: LoggingSettings = LoggingSettings()
    security: SecuritySettings = SecuritySettings()
    
    # Helper methods
    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.ENV.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.ENV.lower() == "development"
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment"""
        return self.ENV.lower() == "testing"
        
    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for specified provider"""
        provider = provider.upper()
        if hasattr(self.api_keys, f"{provider}_KEY"):
            return getattr(self.api_keys, f"{provider}_KEY")
        return None
        
    class Config:
        env_file = ".env"
        case_sensitive = True

# Global settings instance
_settings = None

def get_settings() -> Settings:
    """Get settings singleton instance"""
    global _settings
    if _settings is None:
        try:
            _settings = Settings()
            logger.debug("Settings initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing settings: {str(e)}")
            # Provide default settings if there's an error
            _settings = Settings(
                ENV="development", 
                DEBUG=True,
                api_keys=APIKeys(), 
                security=SecuritySettings(JWT_SECRET="temporary-jwt-secret-for-development-only")
            )
            logger.warning("Using default settings due to initialization error")
    return _settings

def create_env_template() -> str:
    """
    Create a template for the .env file.
    
    Returns:
        String content for .env template file
    """
    template = """# Zion Market Analysis Platform - Environment Configuration
# --------------------------------------------------
# This file contains configuration parameters for the application.
# Copy this file to .env and fill in appropriate values.

# Environment (development, testing, production)
ENV=development
DEBUG=true
HOST=0.0.0.0
PORT=8000

# Security
JWT_SECRET_KEY=replace-with-your-secure-random-string

# API Keys for Financial Data Providers
# --------------------------------------------------
# Obtain these keys from the respective provider websites

# Alpha Vantage (https://www.alphavantage.co/support/#api-key)
ALPHA_VANTAGE_KEY=your_alpha_vantage_key_here

# Polygon.io (https://polygon.io/dashboard/api-keys)
POLYGON_API_KEY=your_polygon_key_here

# Finnhub (https://finnhub.io/dashboard/api-keys)
FINNHUB_API_KEY=your_finnhub_key_here
"""
    return template

def write_env_template(path: str = ".env.template") -> None:
    """
    Write the environment template file to disk.
    
    Args:
        path: Path where the template should be written
    """
    with open(path, "w") as f:
        f.write(create_env_template())
    logger.info(f"Environment template written to {path}")