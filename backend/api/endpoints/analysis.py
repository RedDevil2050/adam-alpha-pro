# backend/api/endpoints/analysis.py
from fastapi import APIRouter, Depends, HTTPException, status
# Import the run_full_cycle function instead of the Orchestrator class directly
from backend.orchestrator import run_full_cycle 
from backend.security.jwt_auth import verify_token
from backend.config.settings import Settings, get_settings
from loguru import logger

router = APIRouter()

@router.get("/analyze/{symbol}", 
            summary="Run comprehensive analysis for a given stock symbol",
            dependencies=[Depends(verify_token)]) # Add JWT dependency
async def analyze_symbol(symbol: str, settings: Settings = Depends(get_settings)):
    """
    Endpoint to trigger a full analysis workflow for a specific stock symbol.
    Requires authentication.
    """
    # Add entry logging
    logger.info(f"[/api/analyze/{symbol}] Endpoint hit.") 
    logger.info(f"Received analysis request for symbol: {symbol}")
    try:
        # Call the run_full_cycle function directly
        result = await run_full_cycle(symbol)
        
        # Check if the result indicates an error or is empty/invalid
        if result is None or result.get("status") == "failed" or not result.get("brain"): # Adjusted check
             logger.error(f"Analysis failed or returned invalid result for symbol: {symbol}. Result: {result}")
             # Use 404 if the symbol itself might be invalid, or 500/503 for internal issues
             status_code = status.HTTP_404_NOT_FOUND if result and "invalid symbol" in result.get("error", "").lower() else status.HTTP_503_SERVICE_UNAVAILABLE
             detail = result.get("error", f"Analysis failed for symbol: {symbol}")
             raise HTTPException(
                 status_code=status_code, 
                 detail=detail
             )
             
        logger.success(f"Successfully completed analysis for symbol: {symbol}")
        return result
    except HTTPException as http_exc:
        # Re-raise HTTPExceptions (like 404 from orchestrator/agents)
        raise http_exc
    except Exception as e:
        logger.exception(f"Unexpected error during analysis for symbol {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal error occurred during analysis for {symbol}."
        )
