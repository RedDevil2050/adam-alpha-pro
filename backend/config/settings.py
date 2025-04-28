import os
from typing import Dict, Any, Optional, List, Callable, Tuple
from pydantic_settings import BaseSettings, SettingsConfigDict  # Updated import for Pydantic v2
from pydantic import Field, validator  # Keep these imports from pydantic
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


# Type aliases for Pydantic v2 compatibility
SettingsSourceCallable = Callable[[type[BaseSettings]], dict[str, Any]]


class BaseSecretHandlingConfig:
    """Base class for Pydantic Config inner classes needing secret handling."""
    env_file = ".env"
    case_sensitive = True
    secrets_dir = None  # Disable pydantic's default secrets handling
    
    # For Pydantic v2, we'll define the customise_sources method to be used in model_config
    @classmethod
    def get_config_dict(cls):
        return SettingsConfigDict(
            env_file=cls.env_file,
            case_sensitive=cls.case_sensitive,
            secrets_dir=cls.secrets_dir,
        )


# Custom settings source that uses get_secret_value
def custom_settings_source(settings_cls) -> Dict[str, Any]:
    """Custom settings source function for Pydantic v2."""
    result = {}
    for field_name, field in settings_cls.model_fields.items():
        env_name = field.json_schema_extra.get("env") if field.json_schema_extra else None
        env_name = env_name or field_name.upper()
        default_value = field.default
        result[field_name] = get_secret_value(env_name, default_value)
    return result


class APIKeys(BaseSettings):
    """API keys for various data providers and additional security settings"""

    ALPHA_VANTAGE_KEY: Optional[str] = Field(None, env="ALPHA_VANTAGE_KEY")
    POLYGON_API_KEY: Optional[str] = Field(None, env="POLYGON_API_KEY")
    FINNHUB_API_KEY: Optional[str] = Field(None, env="FINNHUB_API_KEY")
    YAHOO_FINANCE_API_KEY: Optional[str] = Field(None, env="YAHOO_FINANCE_API_KEY")
    TIINGO_API_KEY: Optional[str] = Field(None, env="TIINGO_API_KEY")
    QUANDL_API_KEY: Optional[str] = Field(None, env="QUANDL_API_KEY")
    IEX_CLOUD_API_KEY: Optional[str] = Field(None, env="IEX_CLOUD_API_KEY")
    MARKETSTACK_API_KEY: Optional[str] = Field(None, env="MARKETSTACK_API_KEY")

    # Additional fields to resolve validation errors
    JWT_SECRET_KEY: Optional[str] = Field(None, env="JWT_SECRET_KEY")
    JWT_ALGORITHM: Optional[str] = Field(None, env="JWT_ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: Optional[int] = Field(None, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REDIS_URL: Optional[str] = Field(None, env="REDIS_URL")
    SLACK_WEBHOOK_URL: Optional[str] = Field(None, env="SLACK_WEBHOOK_URL")
    EMAIL_NOTIFICATIONS: Optional[str] = Field(None, env="EMAIL_NOTIFICATIONS")
    METRICS_PORT: Optional[int] = Field(None, env="METRICS_PORT")
    LOG_LEVEL: Optional[str] = Field(None, env="LOG_LEVEL")

    model_config = BaseSecretHandlingConfig.get_config_dict()


class DataProviderSettings(BaseSettings):
    """Settings for data providers"""

    PRIMARY_PROVIDER: str = Field("yahoo_finance", env="PRIMARY_PROVIDER")
    FALLBACK_PROVIDERS: List[str] = [
        "alpha_vantage",
        "polygon",
        "finnhub",
        "web_scraper",
    ]
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

    # Use JWT_SECRET_KEY directly for consistency
    JWT_SECRET_KEY: str = Field("test-jwt-secret-for-market-deployment-checks", env="JWT_SECRET_KEY")
    TOKEN_EXPIRATION: int = Field(3600, env="JWT_TOKEN_EXPIRATION")  # seconds
    ALGORITHM: str = Field("HS256", env="JWT_ALGORITHM")

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"  # Allow extra fields without validation errors
    )


class DatabaseSettings(BaseSettings):
    """Database configuration"""

    URL: str = Field("sqlite:///./test.db", env="DATABASE_URL")
    POOL_SIZE: int = Field(5, env="DATABASE_POOL_SIZE")
    MAX_OVERFLOW: int = Field(10, env="DATABASE_MAX_OVERFLOW")

    @validator("URL")
    def validate_database_url(cls, v):
        if not v or "your-database-url" in v:
            raise ValueError("DATABASE_URL must be set to a valid connection string")
        return v

    model_config = SettingsConfigDict(
        env_file=".env", 
        case_sensitive=True,
        extra="ignore"  # Allow extra fields without validation errors
    )


# Added BetaAgentSettings
class BetaAgentSettings(BaseSettings):
    """Settings specific to the Beta Agent"""

    VAR_CONFIDENCE_LEVEL: float = Field(0.95, env="BETA_VAR_CONFIDENCE_LEVEL")
    SHARPE_ANNUALIZATION_FACTOR: int = Field(
        252, env="BETA_SHARPE_ANNUALIZATION_FACTOR"
    )
    COMPOSITE_WEIGHT_BETA: float = Field(0.4, env="BETA_COMPOSITE_WEIGHT_BETA")
    COMPOSITE_WEIGHT_VAR: float = Field(0.3, env="BETA_COMPOSITE_WEIGHT_VAR")
    COMPOSITE_WEIGHT_SHARPE: float = Field(0.3, env="BETA_COMPOSITE_WEIGHT_SHARPE")
    VERDICT_THRESHOLD_LOW_RISK: float = Field(
        0.7, env="BETA_VERDICT_THRESHOLD_LOW_RISK"
    )
    VERDICT_THRESHOLD_MODERATE_RISK: float = Field(
        0.4, env="BETA_VERDICT_THRESHOLD_MODERATE_RISK"
    )


# --- Task 1.2 - 1.8: Define new agent settings classes ---
# Updated PE Ratio Settings
class PeRatioAgentSettings(BaseSettings):
    HISTORICAL_YEARS: int = 5
    PERCENTILE_UNDERVALUED: float = 20.0  # Current P/E below 20th percentile of history
    PERCENTILE_OVERVALUED: float = 80.0  # Current P/E above 80th percentile of history


# Updated PB Ratio Settings
class PbRatioAgentSettings(BaseSettings):
    HISTORICAL_YEARS: int = 5
    PERCENTILE_UNDERVALUED: float = 20.0  # Current P/B below 20th percentile of history
    PERCENTILE_OVERVALUED: float = 80.0  # Current P/B above 80th percentile of history


class PegRatioAgentSettings(BaseSettings):
    THRESHOLD_LOW_PEG: float = 1.0
    THRESHOLD_HIGH_PEG: float = 2.0


class EvEbitdaAgentSettings(BaseSettings):
    THRESHOLD_LOW_EV_EBITDA: float = 10.0
    THRESHOLD_HIGH_EV_EBITDA: float = 15.0


class BookToMarketAgentSettings(BaseSettings):
    HISTORICAL_YEARS: int = 5
    PERCENTILE_UNDERVALUED: float = 75.0  # High B/M (>75th percentile) is undervalued
    PERCENTILE_OVERVALUED: float = 25.0  # Low B/M (<25th percentile) is overvalued


class DividendYieldAgentSettings(BaseSettings):
    THRESHOLD_HIGH: float = 5.0
    THRESHOLD_ATTRACTIVE: float = 2.5
    THRESHOLD_MODERATE: float = 1.0


class EsgScoreAgentSettings(BaseSettings):
    THRESHOLD_STRONG_ESG: float = 70.0
    THRESHOLD_MODERATE_ESG: float = 40.0


# Added Momentum Agent Settings
class MomentumAgentSettings(BaseSettings):
    LOOKBACK_PERIODS: List[int] = [
        21,
        63,
        126,
        252,
    ]  # Approx 1m, 3m, 6m, 12m trading days
    THRESHOLD_STRONG_POSITIVE: float = 0.15  # e.g., > 15% avg return
    THRESHOLD_STRONG_NEGATIVE: float = -0.10  # e.g., < -10% avg return


class CorrelationAgentSettings(BaseSettings):
    MIN_REQUIRED_DAYS: int = 60  # Minimum days of data required
    MIN_DAYS_FOR_30D_CORR: int = 30  # Minimum days needed for 30-day correlation
    THRESHOLD_HIGH_CORRELATION: float = 0.7  # Above this is considered high correlation
    THRESHOLD_LOW_CORRELATION: float = 0.3  # Below this is considered low correlation


# --- Task 1.9 & 1.10: Update AgentSettings ---
class AgentSettings(BaseSettings):
    """Container for all agent-specific settings"""

    beta: BetaAgentSettings = BetaAgentSettings()
    # Add other agent settings here as needed
    pe_ratio: PeRatioAgentSettings = PeRatioAgentSettings()
    pb_ratio: PbRatioAgentSettings = PbRatioAgentSettings()
    peg_ratio: PegRatioAgentSettings = PegRatioAgentSettings()
    ev_ebitda: EvEbitdaAgentSettings = EvEbitdaAgentSettings()
    book_to_market: BookToMarketAgentSettings = BookToMarketAgentSettings()
    dividend_yield: DividendYieldAgentSettings = DividendYieldAgentSettings()
    esg_score: EsgScoreAgentSettings = EsgScoreAgentSettings()
    momentum: MomentumAgentSettings = MomentumAgentSettings()  # Added momentum settings
    correlation: CorrelationAgentSettings = (
        CorrelationAgentSettings()
    )  # Added correlation settings


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
    agent_settings: AgentSettings = AgentSettings()  # Ensure this line exists

    @property
    def is_production(self) -> bool:
        return self.ENV.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.ENV.lower() == "development"

    @property
    def is_testing(self) -> bool:
        return self.ENV.lower() == "testing"

    @property
    def DATABASE_URL(self) -> str:
        """Backward compatibility property for database URL"""
        return self.database.URL
    
    @property
    def REDIS_HOST(self) -> str:
        """Extract Redis host from REDIS_URL for backward compatibility"""
        redis_url = getattr(self, 'REDIS_URL', 'redis://localhost:6379/0')
        # Simple parsing - this could be improved for complex URLs
        if '://' in redis_url:
            parts = redis_url.split('://', 1)[1].split(':')
            return parts[0]
        return 'localhost'
        
    @property
    def REDIS_PORT(self) -> int:
        """Extract Redis port from REDIS_URL for backward compatibility"""
        redis_url = getattr(self, 'REDIS_URL', 'redis://localhost:6379/0')
        # Simple parsing - this could be improved for complex URLs
        if '://' in redis_url:
            parts = redis_url.split('://', 1)[1].split(':')
            if len(parts) > 1:
                port_part = parts[1].split('/')[0]
                try:
                    return int(port_part)
                except ValueError:
                    pass
        return 6379
        
    @property
    def REDIS_URL(self) -> str:
        """Get Redis URL from various possible sources"""
        # First check direct attribute from env vars
        direct_url = getattr(self.api_keys, 'REDIS_URL', None)
        if direct_url:
            return direct_url
        # Default fallback
        return 'redis://localhost:6379/0'

    def get_api_key(self, provider: str) -> Optional[str]:
        provider = provider.upper()
        if hasattr(self.api_keys, f"{provider}_KEY"):
            return getattr(self.api_keys, f"{provider}_KEY")
        return None

    model_config = SettingsConfigDict(
        env_file=".env", 
        case_sensitive=True,
        extra="ignore"  # Allow extra fields without validation errors
    )


# Global settings instance
_settings = None

# Create a singleton instance for backward compatibility
settings = None  # Initialize to None, will be set by get_settings()


def get_settings() -> Settings:
    """Get settings singleton instance"""
    global _settings, settings  # Also update the settings export
    if _settings is None:
        try:
            if os.getenv("ENV") == "testing" or os.getenv("PYTEST_CURRENT_TEST"):
                _settings = Settings(
                    ENV="testing",
                    DEBUG=True,
                    security=SecuritySettings(
                        JWT_SECRET_KEY="secure-test-jwt-secret-for-testing-environment-only"
                    ),
                    api_keys=APIKeys(),
                    database=DatabaseSettings(
                        URL="sqlite:///./test.db"
                    )
                )
                logger.debug("Test settings initialized successfully")
            else:
                _settings = Settings()
                logger.debug("Settings initialized successfully")

            settings = _settings
        except Exception as e:
            logger.error(f"Error initializing settings: {str(e)}")
            _settings = Settings(
                ENV="development",
                DEBUG=True,
                api_keys=APIKeys(),
                security=SecuritySettings(
                    JWT_SECRET_KEY="temporary-jwt-secret-for-development-only"
                ),
                database=DatabaseSettings(
                    URL="sqlite:///./default.db"
                )
            )
            settings = _settings
            logger.warning("Using default settings due to initialization error")
    return _settings
