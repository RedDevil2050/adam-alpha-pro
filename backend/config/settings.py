import os
from typing import Dict, Any, Optional, List
from pydantic import BaseSettings, Field, validator
from pydantic.env_settings import SettingsSourceCallable
import logging
from pathlib import Path
import json

logger = logging.getLogger(__name__)

def get_secret_value(secret_name: str, default: Any = None) -> Any:
    """Get secret value from appropriate source based on environment"""
    try:
        from backend.security.secrets_manager import get_secrets_manager
        return get_secrets_manager().get_secret(secret_name) or default
    except ImportError:
        # During initial setup, secrets_manager might not be available
        return os.getenv(secret_name, default)

class BaseSecretHandlingConfig:
    """Base class for Pydantic Config inner classes needing secret handling."""
    env_file = ".env"
    case_sensitive = True
    secrets_dir = None # Disable pydantic's default secrets handling

    @classmethod
    def customise_sources(
        cls,
        init_settings: SettingsSourceCallable,
        env_settings: SettingsSourceCallable,
        file_secret_settings: SettingsSourceCallable,
    ) -> tuple[SettingsSourceCallable, ...]:
        """
        Override Pydantic settings sources to prioritize our SecretsManager
        for fields defined in the inheriting class.
        """
        return (
            init_settings,
            env_settings,
            # Custom source using get_secret_value
            lambda settings_cls: { # Use settings_cls passed by Pydantic
                field_name: get_secret_value(
                    # Get env var name from Field extra if specified, otherwise use uppercase field name
                    settings_cls.__fields__[field_name].field_info.extra.get('env') or field_name.upper(),
                    settings_cls.__fields__[field_name].default # Provide default value from Field
                )
                for field_name in settings_cls.__fields__
                # Assumes all fields in the inheriting class might use secrets
            },
            # file_secret_settings, # Keep disabled
        )

class APIKeys(BaseSettings):
    """API keys for various data providers"""
    ALPHA_VANTAGE_KEY: Optional[str] = Field(None, env="ALPHA_VANTAGE_KEY")
    POLYGON_API_KEY: Optional[str] = Field(None, env="POLYGON_API_KEY")
    FINNHUB_API_KEY: Optional[str] = Field(None, env="FINNHUB_API_KEY")
    YAHOO_FINANCE_API_KEY: Optional[str] = Field(None, env="YAHOO_FINANCE_API_KEY")
    TIINGO_API_KEY: Optional[str] = Field(None, env="TIINGO_API_KEY")
    QUANDL_API_KEY: Optional[str] = Field(None, env="QUANDL_API_KEY")
    IEX_CLOUD_API_KEY: Optional[str] = Field(None, env="IEX_CLOUD_API_KEY")
    MARKETSTACK_API_KEY: Optional[str] = Field(None, env="MARKETSTACK_API_KEY")
    
    class Config(BaseSecretHandlingConfig):
        pass # customise_sources and other settings are inherited

class DataProviderSettings(BaseSettings):
    """Settings for data providers"""
    PRIMARY_PROVIDER: str = Field("yahoo_finance", env="PRIMARY_PROVIDER")
    FALLBACK_PROVIDERS: List[str] = ["alpha_vantage", "polygon", "finnhub", "web_scraper"]
    CACHE_TTL: int = Field(3600, env="CACHE_TTL")  # seconds
    REQUEST_TIMEOUT: int = Field(10, env="REQUEST_TIMEOUT")  # seconds
    MAX_RETRIES: int = Field(3, env="MAX_RETRIES")
    RETRY_BACKOFF: float = Field(2.0, env="RETRY_BACKOFF")
    CIRCUIT_BREAKER_THRESHOLD: int = Field(5, env="CIRCUIT_BREAKER_THRESHOLD")
    CIRCUIT_BREAKER_TIMEOUT: int = Field(300, env="CIRCUIT_BREAKER_TIMEOUT")  # seconds
    # Added fields for Beta Agent
    MARKET_INDEX_SYMBOL: str = Field("^NSEI", env="MARKET_INDEX_SYMBOL")
    RISK_FREE_RATE: float = Field(0.04, env="RISK_FREE_RATE")

class LoggingSettings(BaseSettings):
    """Logging configuration"""
    LEVEL: str = Field("INFO", env="LOG_LEVEL")
    FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: Optional[str] = Field("logs/app.log", env="LOG_FILE")

class SecuritySettings(BaseSettings):
    """Security-related settings"""
    JWT_SECRET: str = Field(..., env="JWT_SECRET_KEY")
    TOKEN_EXPIRATION: int = Field(3600, env="JWT_TOKEN_EXPIRATION")  # seconds
    ALGORITHM: str = Field("HS256", env="JWT_ALGORITHM")
    
    @validator("JWT_SECRET")
    def validate_jwt_secret(cls, v):
        if not v or v == "your-secret-key-here":
            raise ValueError("JWT_SECRET must be set to a secure random value")
        return v

    class Config(BaseSecretHandlingConfig):
        pass # customise_sources and other settings are inherited

class DatabaseSettings(BaseSettings):
    """Database configuration"""
    URL: str = Field(..., env="DATABASE_URL")
    POOL_SIZE: int = Field(5, env="DATABASE_POOL_SIZE")
    MAX_OVERFLOW: int = Field(10, env="DATABASE_MAX_OVERFLOW")
    
    @validator("URL")
    def validate_database_url(cls, v):
        if not v or "your-database-url" in v:
            raise ValueError("DATABASE_URL must be set to a valid connection string")
        return v

    class Config(BaseSecretHandlingConfig):
        pass # customise_sources and other settings are inherited

# Added BetaAgentSettings
class BetaAgentSettings(BaseSettings):
    """Settings specific to the Beta Agent"""
    VAR_CONFIDENCE_LEVEL: float = Field(0.95, env="BETA_VAR_CONFIDENCE_LEVEL")
    SHARPE_ANNUALIZATION_FACTOR: int = Field(252, env="BETA_SHARPE_ANNUALIZATION_FACTOR")
    COMPOSITE_WEIGHT_BETA: float = Field(0.4, env="BETA_COMPOSITE_WEIGHT_BETA")
    COMPOSITE_WEIGHT_VAR: float = Field(0.3, env="BETA_COMPOSITE_WEIGHT_VAR")
    COMPOSITE_WEIGHT_SHARPE: float = Field(0.3, env="BETA_COMPOSITE_WEIGHT_SHARPE")
    VERDICT_THRESHOLD_LOW_RISK: float = Field(0.7, env="BETA_VERDICT_THRESHOLD_LOW_RISK")
    VERDICT_THRESHOLD_MODERATE_RISK: float = Field(0.4, env="BETA_VERDICT_THRESHOLD_MODERATE_RISK")

# Added AgentSettings to group agent-specific settings
class AgentSettings(BaseSettings):
    """Container for all agent-specific settings"""
    beta: BetaAgentSettings = BetaAgentSettings()
    # Add other agent settings here as needed
    # e.g., esg: ESGScoreAgentSettings = ESGScoreAgentSettings()

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
    database: DatabaseSettings = DatabaseSettings()
    agent_settings: AgentSettings = AgentSettings() # Added agent settings group

    @property
    def is_production(self) -> bool:
        return self.ENV.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        return self.ENV.lower() == "development"
    
    @property
    def is_testing(self) -> bool:
        return self.ENV.lower() == "testing"
    
    def get_api_key(self, provider: str) -> Optional[str]:
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