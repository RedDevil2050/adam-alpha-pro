import os
from typing import Dict, Any, Optional, List, Callable, Tuple
from pydantic_settings import BaseSettings, SettingsConfigDict  # Updated import for Pydantic v2
from pydantic import Field, validator, field_validator  # Keep these imports from pydantic
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

    ALPHA_VANTAGE_KEY: Optional[str] = Field(None, json_schema_extra={"env":"ALPHA_VANTAGE_KEY"})
    POLYGON_API_KEY: Optional[str] = Field(None, json_schema_extra={"env":"POLYGON_API_KEY"})
    FINNHUB_API_KEY: Optional[str] = Field(None, json_schema_extra={"env":"FINNHUB_API_KEY"})
    YAHOO_FINANCE_API_KEY: Optional[str] = Field(None, json_schema_extra={"env":"YAHOO_FINANCE_API_KEY"})
    TIINGO_API_KEY: Optional[str] = Field(None, json_schema_extra={"env":"TIINGO_API_KEY"})
    QUANDL_API_KEY: Optional[str] = Field(None, json_schema_extra={"env":"QUANDL_API_KEY"})
    IEX_CLOUD_API_KEY: Optional[str] = Field(None, json_schema_extra={"env":"IEX_CLOUD_API_KEY"})
    MARKETSTACK_API_KEY: Optional[str] = Field(None, json_schema_extra={"env":"MARKETSTACK_API_KEY"})
    REACT_APP_BACKEND_URL: Optional[str] = Field(None, json_schema_extra={"env":"REACT_APP_BACKEND_URL"})
    REDIS_URL: Optional[str] = Field(None, json_schema_extra={"env":"REDIS_URL"})
    METRICS_PORT: Optional[int] = Field(None, json_schema_extra={"env":"METRICS_PORT"})
    LOG_LEVEL: Optional[str] = Field(None, json_schema_extra={"env":"LOG_LEVEL"})
    JWT_SECRET: Optional[str] = Field(None, json_schema_extra={"env":"JWT_SECRET"})
    API_PASS: Optional[str] = Field(None, json_schema_extra={"env":"API_PASS"})
    API_PASS_HASH: Optional[str] = Field(None, json_schema_extra={"env":"API_PASS_HASH"})
    TWITTER_BEARER_TOKEN: Optional[str] = Field(None, json_schema_extra={"env":"TWITTER_BEARER_TOKEN"}) # Added

    # Additional fields to resolve validation errors
    ENV: Optional[str] = Field(None, json_schema_extra={"env":"ENV"})
    PRIMARY_PROVIDER: Optional[str] = Field(None, json_schema_extra={"env":"PRIMARY_PROVIDER"})
    FALLBACK_PROVIDERS: Optional[str] = Field(None, json_schema_extra={"env":"FALLBACK_PROVIDERS"})
    MARKET_INDEX_SYMBOL: Optional[str] = Field(None, json_schema_extra={"env":"MARKET_INDEX_SYMBOL"})
    CACHE_TTL: Optional[int] = Field(None, json_schema_extra={"env":"CACHE_TTL"})
    REQUEST_TIMEOUT: Optional[int] = Field(None, json_schema_extra={"env":"REQUEST_TIMEOUT"})
    MAX_RETRIES: Optional[int] = Field(None, json_schema_extra={"env":"MAX_RETRIES"})
    RETRY_BACKOFF: Optional[float] = Field(None, json_schema_extra={"env":"RETRY_BACKOFF"})
    MARKET_HOURS_START: Optional[str] = Field(None, json_schema_extra={"env":"MARKET_HOURS_START"})
    MARKET_HOURS_END: Optional[str] = Field(None, json_schema_extra={"env":"MARKET_HOURS_END"})
    DB_HOST: Optional[str] = Field(None, json_schema_extra={"env":"DB_HOST"})
    DB_PORT: Optional[int] = Field(None, json_schema_extra={"env":"DB_PORT"})
    DB_NAME: Optional[str] = Field(None, json_schema_extra={"env":"DB_NAME"})
    DB_USER: Optional[str] = Field(None, json_schema_extra={"env":"DB_USER"})
    DB_PASSWORD: Optional[str] = Field(None, json_schema_extra={"env":"DB_PASSWORD"})

    model_config = BaseSecretHandlingConfig.get_config_dict()


class DataProviderSettings(BaseSettings):
    """Settings for data providers"""

    PRIMARY_PROVIDER: str = Field("yahoo_finance", json_schema_extra={"env":"PRIMARY_PROVIDER"})
    FALLBACK_PROVIDERS: List[str] = [
        "alpha_vantage",
        "polygon",
        "finnhub",
        "web_scraper",
    ]
    CACHE_TTL: int = Field(3600, json_schema_extra={"env":"CACHE_TTL"})  # seconds
    REQUEST_TIMEOUT: int = Field(10, json_schema_extra={"env":"REQUEST_TIMEOUT"})  # seconds
    MAX_RETRIES: int = Field(3, json_schema_extra={"env":"MAX_RETRIES"})
    RETRY_BACKOFF: float = Field(2.0, json_schema_extra={"env":"RETRY_BACKOFF"})
    CIRCUIT_BREAKER_THRESHOLD: int = Field(5, json_schema_extra={"env":"CIRCUIT_BREAKER_THRESHOLD"})
    CIRCUIT_BREAKER_TIMEOUT: int = Field(300, json_schema_extra={"env":"CIRCUIT_BREAKER_TIMEOUT"})  # seconds
    # Added fields for Beta Agent
    MARKET_INDEX_SYMBOL: str = Field("^NSEI", json_schema_extra={"env":"MARKET_INDEX_SYMBOL"})
    RISK_FREE_RATE: float = Field(0.04, json_schema_extra={"env":"RISK_FREE_RATE"})


class LoggingSettings(BaseSettings):
    """Logging configuration"""

    LEVEL: str = Field("INFO", json_schema_extra={"env":"LOG_LEVEL"})
    FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: Optional[str] = Field("logs/app.log", json_schema_extra={"env":"LOG_FILE"})


class SecuritySettings(BaseSettings):
    """Security-related settings"""

    # Use JWT_SECRET_KEY directly for consistency
    JWT_SECRET_KEY: str = Field("test-jwt-secret-for-market-deployment-checks", json_schema_extra={"env":"JWT_SECRET_KEY"})
    TOKEN_EXPIRATION: int = Field(3600, json_schema_extra={"env":"JWT_TOKEN_EXPIRATION"})  # seconds
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(60, json_schema_extra={"env":"JWT_ACCESS_TOKEN_EXPIRE_MINUTES"}) # Added field, default 60 mins
    ALGORITHM: str = Field("HS256", json_schema_extra={"env":"JWT_ALGORITHM"})

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"  # Allow extra fields without validation errors
    )


class DatabaseSettings(BaseSettings):
    """Database configuration"""

    URL: str = Field("sqlite:///./test.db", json_schema_extra={"env":"DATABASE_URL"})
    POOL_SIZE: int = Field(5, json_schema_extra={"env":"DATABASE_POOL_SIZE"})
    MAX_OVERFLOW: int = Field(10, json_schema_extra={"env":"DATABASE_MAX_OVERFLOW"})

    @field_validator("URL")
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

    VAR_CONFIDENCE_LEVEL: float = Field(0.95, json_schema_extra={"env":"BETA_VAR_CONFIDENCE_LEVEL"})
    SHARPE_ANNUALIZATION_FACTOR: int = Field(
        252, json_schema_extra={"env":"BETA_SHARPE_ANNUALIZATION_FACTOR"}
    )
    COMPOSITE_WEIGHT_BETA: float = Field(0.4, json_schema_extra={"env":"BETA_COMPOSITE_WEIGHT_BETA"})
    COMPOSITE_WEIGHT_VAR: float = Field(0.3, json_schema_extra={"env":"BETA_COMPOSITE_WEIGHT_VAR"})
    COMPOSITE_WEIGHT_SHARPE: float = Field(0.3, json_schema_extra={"env":"BETA_COMPOSITE_WEIGHT_SHARPE"})
    VERDICT_THRESHOLD_LOW_RISK: float = Field(
        0.7, json_schema_extra={"env":"BETA_VERDICT_THRESHOLD_LOW_RISK"}
    )
    VERDICT_THRESHOLD_MODERATE_RISK: float = Field(
        0.4, json_schema_extra={"env":"BETA_VERDICT_THRESHOLD_MODERATE_RISK"}
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
    HISTORICAL_YEARS: int = 5  # Added missing attribute


class BookToMarketAgentSettings(BaseSettings):
    HISTORICAL_YEARS: int = 5
    PERCENTILE_UNDERVALUED: float = 75.0  # High B/M (>75th percentile) is undervalued
    PERCENTILE_OVERVALUED: float = 25.0  # Low B/M (<25th percentile) is overvalued


class DividendYieldAgentSettings(BaseSettings):
    THRESHOLD_HIGH: float = 5.0
    THRESHOLD_ATTRACTIVE: float = 2.5
    THRESHOLD_MODERATE: float = 1.0


# Add EarningsSurpriseAgentSettings
class EarningsSurpriseAgentSettings(BaseSettings):
    SURPRISE_THRESHOLD_PCT: float = 5.0


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
# Add DCF Agent Settings
class ValuationAgentSettings(BaseSettings):
    DCF_GROWTH_STAGE1: int = 5  # Years of high growth
    DCF_GROWTH_STAGE2: int = 5  # Years of stable growth
    DCF_DISCOUNT_RATE: float = 0.10  # WACC or required rate of return
    DCF_TERMINAL_GROWTH_RATE: float = 0.025  # Perpetual growth rate
    MARKET_RISK_PREMIUM: float = 0.06 # Added missing field (Example value)
    DCF_DEFAULT_TERMINAL_PE: float = 15.0 # Added missing field (Example value)
    DCF_MARGIN_OF_SAFETY_STRONG_BUY: float = 0.30  # 30% MoS for Strong Buy
    DCF_MARGIN_OF_SAFETY_BUY: float = 0.15  # 15% MoS for Buy
    DCF_MARGIN_OF_SAFETY_SELL: float = -0.10 # -10% MoS (overvalued) for Sell
    DCF_MARGIN_OF_SAFETY_STRONG_SELL: float = -0.25 # -25% MoS for Strong Sell
    DCF_SIMULATION_RUNS: int = 1000 # Number of runs for Monte Carlo
    DCF_UNCERTAINTY_PENALTY_FACTOR: float = 0.5 # How much relative std dev impacts confidence


class AgentSettings(BaseSettings):
    """Container for all agent-specific settings"""

    # Added fields to support common agent configurations passed during initialization
    agent_name: Optional[str] = Field(default=None, description="Name of the agent")
    agent_cache_enabled: bool = Field(default=True, description="Whether caching is enabled for the agent")
    agent_cache_ttl_seconds: int = Field(default=3600, description="Cache TTL in seconds for the agent")
    agent_cache_db_index: int = Field(default=0, description="Redis DB index for agent cache")
    agent_data_lookback_period: Optional[int] = Field(default=None, description="Default data lookback period for the agent")

    beta: BetaAgentSettings = BetaAgentSettings()
    # Add other agent settings here as needed
    pe_ratio: PeRatioAgentSettings = PeRatioAgentSettings()
    pb_ratio: PbRatioAgentSettings = PbRatioAgentSettings()
    peg_ratio: PegRatioAgentSettings = PegRatioAgentSettings()
    ev_ebitda: EvEbitdaAgentSettings = EvEbitdaAgentSettings()
    book_to_market: BookToMarketAgentSettings = BookToMarketAgentSettings()
    dividend_yield: DividendYieldAgentSettings = DividendYieldAgentSettings()
    earnings_surprise: EarningsSurpriseAgentSettings = EarningsSurpriseAgentSettings()  # Added earnings surprise
    esg_score: EsgScoreAgentSettings = EsgScoreAgentSettings()
    momentum: MomentumAgentSettings = MomentumAgentSettings()  # Added momentum settings
    correlation: CorrelationAgentSettings = (
        CorrelationAgentSettings()
    )  # Added correlation settings
    valuation: ValuationAgentSettings = ValuationAgentSettings() # Added valuation settings
    # Add missing market_regime settings for tests/agents
    market_regime: dict = Field(default_factory=lambda: {"thresholds": {"bull": 0.7, "bear": 0.3}}) # Modified to use Field and default_factory
    sector_pe_averages: Dict[str, float] = Field(default_factory=dict, json_schema_extra={"env":"SECTOR_PE_AVERAGES"}) # Added

    # If AgentSettings needs its own model_config (e.g., for env_prefix for the new fields),
    # it can be added here. For example:
    # model_config = SettingsConfigDict(env_prefix='ZION_AGENT_DEFAULT_')
    # For now, assuming BaseSettings provides suitable defaults or these are set programmatically


# --- Main Application Settings ---
class Settings(BaseSettings):
    """Global application settings"""
    is_testing: bool = Field(default=False, description="Set to true when running tests. Controls DB setup, etc.", json_schema_extra={"env": "IS_TESTING"})
    DATABASE_URL: str = Field(default="sqlite+aiosqlite:///./default_app.db", description="Default database URL, should be async for production.", json_schema_extra={"env": "DATABASE_URL"})
    
    # You can compose other specific settings classes here if needed, for example:
    api_keys: APIKeys = APIKeys()
    data_provider: DataProviderSettings = DataProviderSettings() # Changed data_provider_settings to data_provider
    logging: LoggingSettings = LoggingSettings() # Changed logging_settings to logging
    security: SecuritySettings = SecuritySettings() # Changed security_settings to security
    agent_settings: AgentSettings = AgentSettings() # Changed agent_specific_settings to agent_settings

    model_config = SettingsConfigDict(
        env_file=".env",    # Load .env file
        extra="ignore"      # Ignore extra fields that might come from environment
    )

# Global cached settings instance
_cached_settings: Optional[Settings] = None

def get_settings() -> Settings:
    """
    Retrieves the cached global settings.
    Initializes settings on first call.
    """
    global _cached_settings
    if _cached_settings is None:
        _cached_settings = Settings()
        # Optional: Log for debugging, ensure logger is configured
        # logger.info(f"Settings initialized. Effective is_testing: {_cached_settings.is_testing}, DATABASE_URL: '{_cached_settings.DATABASE_URL}'")
    return _cached_settings
