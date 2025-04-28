import logging
import asyncio
from typing import Dict, Any, List, Tuple, Optional
import aiohttp

from ..config.settings import get_settings
from .data_provider import fetch_price_point

logger = logging.getLogger(__name__)
settings = get_settings()


class HealthCheckError(Exception):
    """Exception raised when a health check fails."""

    pass


async def check_api_keys() -> Dict[str, bool]:
    """
    Check which API keys are configured.

    Returns:
        Dict mapping API names to boolean indicating if they're configured
    """
    result = {}

    apis = {
        "alpha_vantage": settings.api_keys.ALPHA_VANTAGE_KEY,
        "polygon": settings.api_keys.POLYGON_API_KEY,
        "finnhub": settings.api_keys.FINNHUB_API_KEY,
        "yahoo_finance": settings.api_keys.YAHOO_FINANCE_API_KEY,
        "tiingo": settings.api_keys.TIINGO_API_KEY,
        "quandl": settings.api_keys.QUANDL_API_KEY,
        "iex_cloud": settings.api_keys.IEX_CLOUD_API_KEY,
        "marketstack": settings.api_keys.MARKETSTACK_API_KEY,
    }

    for name, key in apis.items():
        result[name] = key is not None and key != ""

    return result


async def check_api_connectivity() -> Dict[str, Dict[str, Any]]:
    """
    Check connectivity to all configured APIs.

    Returns:
        Dict with API health information
    """
    api_configs = await check_api_keys()
    results = {}

    # Define a test symbol
    test_symbol = "AAPL"

    # Test APIs that have keys configured
    for api_name, is_configured in api_configs.items():
        if is_configured:
            try:
                # Try to fetch a test price point
                # The data_provider will handle routing to appropriate API
                price = await fetch_price_point(test_symbol)
                success = price > 0  # Basic validation

                results[api_name] = {
                    "status": "connected" if success else "error",
                    "message": (
                        f"Successfully connected to {api_name}"
                        if success
                        else "Returned invalid data"
                    ),
                    "data_available": success,
                }

            except Exception as e:
                results[api_name] = {
                    "status": "error",
                    "message": f"Error connecting to {api_name}: {str(e)}",
                    "data_available": False,
                }
        else:
            results[api_name] = {
                "status": "unconfigured",
                "message": f"API key for {api_name} not configured",
                "data_available": False,
            }

    return results


async def check_internet_connectivity() -> Dict[str, Any]:
    """
    Check basic internet connectivity to ensure network is available.

    Returns:
        Dict with connectivity status
    """
    test_urls = [
        "https://www.google.com",
        "https://www.yahoo.com",
        "https://www.alphavantage.co",
        "https://finnhub.io",
    ]

    results = {"status": "unknown", "message": "", "connectivity": False}

    try:
        async with aiohttp.ClientSession() as session:
            for url in test_urls:
                try:
                    async with session.get(url, timeout=5) as response:
                        if response.status == 200:
                            results = {
                                "status": "connected",
                                "message": "Internet connectivity verified",
                                "connectivity": True,
                            }
                            return results
                except Exception:
                    continue

        results = {
            "status": "error",
            "message": "Failed to connect to any test URLs",
            "connectivity": False,
        }

    except Exception as e:
        results = {
            "status": "error",
            "message": f"Error checking internet connectivity: {str(e)}",
            "connectivity": False,
        }

    return results


async def run_system_health_check() -> Dict[str, Any]:
    """
    Run a comprehensive system health check.

    Returns:
        Dict with health check results
    """
    results = {
        "timestamp": asyncio.get_running_loop().time(),
        "system_ready": False,
        "can_fetch_live_data": False,
    }

    # Check internet connectivity
    internet_check = await check_internet_connectivity()
    results["internet_connectivity"] = internet_check

    if not internet_check["connectivity"]:
        logger.critical(
            "Internet connectivity check failed! System cannot function without internet."
        )
        results["system_ready"] = False
        results["critical_error"] = "No internet connectivity detected"
        return results

    # Check API keys and connectivity
    api_keys = await check_api_keys()
    results["api_keys_configured"] = api_keys

    # Check if at least one API key is configured
    if not any(api_keys.values()):
        logger.critical("No API keys configured! System cannot fetch live data.")
        results["system_ready"] = False
        results["critical_error"] = "No API keys configured"
        return results

    # Check API connectivity
    api_connectivity = await check_api_connectivity()
    results["api_connectivity"] = api_connectivity

    # Check if at least one API is working
    working_apis = [
        api
        for api, status in api_connectivity.items()
        if status["status"] == "connected" and status["data_available"]
    ]

    results["working_apis"] = working_apis
    results["can_fetch_live_data"] = len(working_apis) > 0

    if not results["can_fetch_live_data"]:
        logger.critical("No working APIs found! System cannot fetch live data.")
        results["system_ready"] = False
        results["critical_error"] = "No working APIs detected"
        return results

    # System is ready if we have internet and at least one working API
    results["system_ready"] = True
    logger.info(f"System health check passed. Working APIs: {', '.join(working_apis)}")

    return results


async def verify_data_providers_on_startup() -> bool:
    """
    Function to be called during application startup to verify data providers.
    Raises an exception if no data providers are available.

    Returns:
        True if system can fetch live data, False otherwise
    """
    health_results = await run_system_health_check()

    if not health_results["system_ready"]:
        logger.warning(
            f"System health check failed: {health_results.get('critical_error', 'Unknown error')}"
        )
        logger.warning("System will start but may not be able to fetch live data!")
        return False

    logger.info(
        f"System ready with {len(health_results['working_apis'])} working APIs: {health_results['working_apis']}"
    )
    return True
