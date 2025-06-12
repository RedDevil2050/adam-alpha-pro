"""
Legacy routes file - DEPRECATED
===============================

This file has been superseded by the modular endpoint structure:
- backend/api/endpoints/market.py - Market-related endpoints
- backend/api/endpoints/analysis.py - Analysis endpoints  
- backend/api/endpoints/portfolio.py - Portfolio endpoints

The endpoints from this file have been moved to the appropriate modules
and are included in the main FastAPI app via routers.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
import pandas as pd

# Import the required classes
from backend.data.data_service import DataService
from backend.quant.core import QuantCore
from backend.quant.strategies import QuantStrategies

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/market-state")
async def get_market_state():
    """DEPRECATED: Use /api/market/market-state instead"""
    try:
        data_service = DataService()
        market_data = await data_service.get_market_data(["SPY", "QQQ", "IWM"])
        
        # Extract returns data for analysis
        returns_data = {}
        for symbol, data in market_data.get("data", {}).items():
            if "price" in data:
                returns_data[symbol] = data["price"]
        
        # Create a simple market state since we don't have VIX data
        market_state = {
            "trend": 0.5,
            "volatility": 0.3,
            "momentum": 0.6,
            "market_quality": 0.7
        }
        
        return {"status": "success", "data": market_state}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/optimize-portfolio")
async def optimize_portfolio(request: Dict):
    """DEPRECATED: Use /api/market/optimize-portfolio instead"""
    try:
        symbols = request.get("symbols", [])
        if not symbols:
            raise HTTPException(status_code=400, detail="No symbols provided")
            
        data_service = DataService()
        market_data = await data_service.get_market_data(symbols)
        
        # Simple equal weight allocation as fallback
        allocation = {}
        equal_weight = 100.0 / len(symbols)
        
        for symbol in symbols:
            allocation[symbol] = round(equal_weight, 2)
        
        return {"status": "success", "allocation": allocation}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
