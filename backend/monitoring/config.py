from prometheus_client import start_http_server
import logging
from typing import Dict, Any
import json

logger = logging.getLogger(__name__)

METRICS_PORT = 9090
METRICS_CONFIG = {
    "data_collection": {
        "targets": ["data_collection_attempts", "data_source_switches", "data_quality", "collection_latency"],
        "labels": ["symbol", "data_type", "source"],
        "thresholds": {
            "collection_latency": 30.0,  # Maximum acceptable latency in seconds
            "quality_minimum": 0.5,      # Minimum acceptable data quality score
            "api_failure_rate": 0.2      # Maximum acceptable API failure rate
        }
    },
    "providers": {
        "primary": ["alpha_vantage", "polygon"],
        "secondary": ["yahoo_finance", "finnhub"],
        "fallback": ["web_scraper"]
    },
    "alerts": {
        "collection_failures": {
            "threshold": 5,              # Number of consecutive failures
            "window": 300,              # Time window in seconds
            "channels": ["slack", "email"]
        },
        "quality_degradation": {
            "threshold": 0.3,           # Quality score drop threshold
            "window": 600,              # Time window in seconds
            "channels": ["slack"]
        }
    }
}

def setup_metrics_reporting():
    """Initialize metrics reporting"""
    try:
        start_http_server(METRICS_PORT)
        logger.info(f"Started metrics server on port {METRICS_PORT}")
        
        # Log configuration for observability
        logger.info("Metrics configuration loaded:")
        logger.info(f"Data collection metrics: {json.dumps(METRICS_CONFIG['data_collection'], indent=2)}")
        logger.info(f"Provider hierarchy: {json.dumps(METRICS_CONFIG['providers'], indent=2)}")
        
    except Exception as e:
        logger.error(f"Failed to start metrics reporting: {e}")
        raise

def get_metric_threshold(metric_name: str) -> float:
    """Get threshold value for a specific metric"""
    thresholds = METRICS_CONFIG["data_collection"]["thresholds"]
    return thresholds.get(metric_name, 0.0)

def is_primary_provider(provider: str) -> bool:
    """Check if a provider is in the primary tier"""
    return provider in METRICS_CONFIG["providers"]["primary"]

def get_provider_tier(provider: str) -> str:
    """Get the tier (primary, secondary, fallback) of a provider"""
    for tier, providers in METRICS_CONFIG["providers"].items():
        if provider in providers:
            return tier
    return "unknown"

def should_alert(metric_name: str, value: float) -> bool:
    """Determine if a metric value should trigger an alert"""
    if metric_name in METRICS_CONFIG["alerts"]:
        alert_config = METRICS_CONFIG["alerts"][metric_name]
        return value >= alert_config["threshold"]
    return False

def get_alert_channels(alert_type: str) -> list:
    """Get configured alert channels for an alert type"""
    if alert_type in METRICS_CONFIG["alerts"]:
        return METRICS_CONFIG["alerts"][alert_type]["channels"]
    return []