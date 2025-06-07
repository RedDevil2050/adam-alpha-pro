# backend/api/endpoints/analysis.py
from fastapi import APIRouter, Depends, HTTPException, status
# Import the run_full_cycle function instead of the Orchestrator class directly
from backend.orchestrator import run_full_cycle 
from backend.security.jwt_auth import verify_token
from backend.security.validate import SymbolRequest, EnhancedSymbolRequest
from backend.config.settings import Settings, get_settings
from loguru import logger
from pydantic import ValidationError

router = APIRouter()

@router.get("/analyze/{symbol}", 
            summary="Run comprehensive analysis for a given stock symbol")
            # Temporarily remove JWT dependency for live testing
            # dependencies=[Depends(verify_token)])
async def analyze_symbol(symbol: str, settings: Settings = Depends(get_settings)):
    """
    Endpoint to trigger a full analysis workflow for a specific stock symbol.
    Live testing mode - authentication temporarily disabled.
    """
    # Add entry logging
    logger.info(f"[/api/analyze/{symbol}] Endpoint hit.") 
    logger.info(f"Received analysis request for symbol: {symbol}")
    
    # Validate symbol using existing validation infrastructure
    try:
        # Use the existing SymbolRequest validation
        validated_symbol = SymbolRequest(symbol=symbol)
        logger.info(f"Symbol {symbol} passed validation")
    except ValidationError as ve:
        logger.warning(f"Symbol validation failed for {symbol}: {ve}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid symbol format: {str(ve)}"
        )
    except ValueError as ve:
        logger.warning(f"Symbol validation failed for {symbol}: {ve}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid symbol: {str(ve)}"
        )
    
    try:
        # Call the run_full_cycle function with the validated symbol
        result = await run_full_cycle(validated_symbol.symbol)
        
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

@router.post("/analyze/enhanced", 
             summary="Run comprehensive analysis with provider-specific symbol normalization")
             # Temporarily remove JWT dependency for live testing
             # dependencies=[Depends(verify_token)])
async def analyze_symbol_enhanced(request: EnhancedSymbolRequest, settings: Settings = Depends(get_settings)):
    """
    Enhanced endpoint that supports provider-specific symbol normalization.
    Allows specifying data provider and exchange for optimal symbol format.
    """
    logger.info(f"[/api/analyze/enhanced] Enhanced analysis requested for symbol: {request.symbol}")
    logger.info(f"Provider: {request.provider}, Exchange: {request.exchange}")
    
    try:
        # Get the normalized symbol for the specified provider
        normalized_symbol = request.normalized_symbol
        logger.info(f"Symbol normalized from {request.symbol} to {normalized_symbol} for provider {request.provider}")
        
        # Call the run_full_cycle function with the normalized symbol
        result = await run_full_cycle(normalized_symbol)
        
        # Add metadata about the normalization
        if result and isinstance(result, dict):
            result["symbol_metadata"] = {
                "original_symbol": request.symbol,
                "normalized_symbol": normalized_symbol,
                "provider": request.provider,
                "exchange": request.exchange,
                "detected_exchange": request.exchange or "auto-detected"
            }
        
        # Check if the result indicates an error or is empty/invalid
        if result is None or result.get("status") == "failed" or not result.get("brain"):
             logger.error(f"Enhanced analysis failed for symbol: {request.symbol}. Result: {result}")
             status_code = status.HTTP_404_NOT_FOUND if result and "invalid symbol" in result.get("error", "").lower() else status.HTTP_503_SERVICE_UNAVAILABLE
             detail = result.get("error", f"Analysis failed for symbol: {request.symbol}")
             raise HTTPException(
                 status_code=status_code, 
                 detail=detail
             )
             
        logger.success(f"Successfully completed enhanced analysis for symbol: {request.symbol}")
        return result
        
    except ValidationError as ve:
        logger.warning(f"Enhanced symbol validation failed for {request.symbol}: {ve}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid symbol request: {str(ve)}"
        )
    except HTTPException as http_exc:
        # Re-raise HTTPExceptions
        raise http_exc
    except Exception as e:
        logger.exception(f"Unexpected error during enhanced analysis for symbol {request.symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal error occurred during enhanced analysis for {request.symbol}."
        )


@router.get("/symbols/validate/{symbol}", 
            summary="Validate symbol format and get normalization info")
async def validate_symbol(symbol: str):
    """
    Validate a symbol and return normalization information for different providers.
    """
    logger.info(f"[/api/symbols/validate/{symbol}] Symbol validation requested")
    
    try:
        # Validate using basic validation
        validated_symbol = SymbolRequest(symbol=symbol)
        
        # Get normalization info for different providers
        from backend.utils.symbol_normalizer_fixed import IndianEquitySymbolNormalizer
        
        normalizer = IndianEquitySymbolNormalizer()
        
        validation_info = {
            "symbol": validated_symbol.symbol,
            "is_valid": True,
            "is_indian_symbol": normalizer.is_indian_symbol(symbol),
            "detected_exchange": normalizer.detect_exchange(symbol),
            "base_symbol": normalizer.get_base_symbol(symbol),
            "provider_formats": {
                "yahoo_finance": normalizer.get_provider_symbol(symbol, "yahoo"),
                "alpha_vantage": normalizer.get_provider_symbol(symbol, "alpha_vantage"),
                "polygon": normalizer.get_provider_symbol(symbol, "polygon"),
                "finnhub": normalizer.get_provider_symbol(symbol, "finnhub")
            }
        }
        
        logger.info(f"Symbol validation successful for: {symbol}")
        return validation_info
        
    except ValidationError as ve:
        logger.warning(f"Symbol validation failed for {symbol}: {ve}")
        return {
            "symbol": symbol,
            "is_valid": False,
            "error": str(ve),
            "provider_formats": {}
        }
    except Exception as e:
        logger.exception(f"Error during symbol validation for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation error for symbol {symbol}"
        )
