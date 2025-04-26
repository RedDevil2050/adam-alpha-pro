from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
import pandas as pd

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
    try:
        data_service = DataService()
        market_data = await data_service.get_market_data(["SPY", "QQQ", "IWM"])
        quant_core = QuantCore()
        market_state = quant_core.analyze_market_state(market_data)
        return {"status": "success", "data": market_state}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/optimize-portfolio")
async def optimize_portfolio(symbols: List[str]):
    try:
        data_service = DataService()
        returns = await data_service.get_market_data(symbols)
        strategies = QuantStrategies()
        allocation = strategies.risk_parity_allocation(returns)
        return {"status": "success", "allocation": allocation}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
