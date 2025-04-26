from pydantic import BaseSettings

class DeploymentConfig(BaseSettings):
    # Circuit breaker settings
    CIRCUIT_BREAKER_THRESHOLD: int = 5
    CIRCUIT_BREAKER_RESET_TIMEOUT: int = 60
    
    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60
    
    # Monitoring
    METRICS_ENABLED: bool = True
    METRICS_PORT: int = 9090
    
    # Performance
    CACHE_ENABLED: bool = True
    CACHE_TTL: int = 3600
    
    # Validation
    MAX_SYMBOL_LENGTH: int = 10
    MAX_BATCH_SIZE: int = 50
    
    class Config:
        env_prefix = "ZION_"
