"""
Live Data API Endpoints
=======================

Real-time stock market data endpoints for the frontend.
Provides live quotes, market indices, and streaming data.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import JSONResponse
from loguru import logger

from backend.data.data_service import DataService
from backend.data.providers.unified_provider import get_unified_provider
from backend.utils.symbol_normalizer import normalize_indian_symbol
from backend.agents.stealth.background_manager import background_manager

# Create router for live data endpoints
live_router = APIRouter(prefix="/api/live", tags=["live-data"])

# Global data service instance
data_service = DataService()
provider = get_unified_provider()

# WebSocket connection manager for live data
class LiveDataManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.symbol_subscribers: Dict[str, List[WebSocket]] = {}
        self.update_task: Optional[asyncio.Task] = None
        self.is_running = False

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"📡 Live data WebSocket connected (total: {len(self.active_connections)})")
        
        # Start update task if not running
        if not self.is_running:
            self.start_live_updates()

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        # Remove from symbol subscriptions
        for symbol, subscribers in self.symbol_subscribers.items():
            if websocket in subscribers:
                subscribers.remove(websocket)
        
        logger.info(f"📡 Live data WebSocket disconnected (remaining: {len(self.active_connections)})")

    async def subscribe_to_symbol(self, websocket: WebSocket, symbol: str):
        if symbol not in self.symbol_subscribers:
            self.symbol_subscribers[symbol] = []
        if websocket not in self.symbol_subscribers[symbol]:
            self.symbol_subscribers[symbol].append(websocket)
        logger.debug(f"📊 Client subscribed to live data for {symbol}")

    async def broadcast_to_symbol(self, symbol: str, data: dict):
        if symbol not in self.symbol_subscribers:
            return
        
        message = json.dumps({
            "type": "live_quote",
            "symbol": symbol,
            "data": data,
            "timestamp": time.time()
        })
        
        disconnected = []
        for websocket in self.symbol_subscribers[symbol]:
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send live data to WebSocket: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected clients
        for ws in disconnected:
            self.disconnect(ws)

    def start_live_updates(self):
        """Start background task for live data updates"""
        if not self.is_running:
            self.is_running = True
            self.update_task = asyncio.create_task(self._live_update_loop())

    async def _live_update_loop(self):
        """Background loop to fetch and broadcast live data"""
        while self.is_running and self.active_connections:
            try:
                # Get all subscribed symbols
                symbols = list(self.symbol_subscribers.keys())
                if not symbols:
                    await asyncio.sleep(5)
                    continue

                # Fetch live data for subscribed symbols
                for symbol in symbols:
                    try:
                        data = await get_live_quote_data(symbol)
                        if data:
                            await self.broadcast_to_symbol(symbol, data)
                    except Exception as e:
                        logger.warning(f"Error fetching live data for {symbol}: {e}")

                # Wait before next update (5 seconds for real-time feel)
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Error in live update loop: {e}")
                await asyncio.sleep(10)
        
        self.is_running = False

# Global live data manager
live_manager = LiveDataManager()

@live_router.get("/quote/{symbol}")
async def get_live_quote(symbol: str):
    """Get live quote data for a symbol"""
    try:
        symbol = symbol.upper()
        data = await get_live_quote_data(symbol)
        
        return JSONResponse({
            "status": "success",
            "symbol": symbol,
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "source": "live"
        })
    
    except Exception as e:
        logger.error(f"Error getting live quote for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@live_router.get("/indices")
async def get_live_indian_indices():
    """Get live Indian market indices data"""
    try:
        # Major Indian indices
        indices_symbols = ['^NSEI', '^BSESN', '^NSEBANK', '^NSEIT']
        indices_data = []
        
        for symbol in indices_symbols:
            try:
                data = await get_live_quote_data(symbol)
                if data:
                    indices_data.append({
                        "symbol": symbol,
                        "name": get_index_name(symbol),
                        **data
                    })
            except Exception as e:
                logger.warning(f"Error fetching index data for {symbol}: {e}")
        
        return JSONResponse({
            "status": "success",
            "indices": indices_data,
            "timestamp": datetime.now().isoformat(),
            "source": "live"
        })
    
    except Exception as e:
        logger.error(f"Error getting live indices: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@live_router.get("/stocks/indian")
async def get_live_indian_stocks():
    """Get live data for major Indian stocks"""
    try:
        # Major Indian stocks
        stock_symbols = [
            'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK',
            'KOTAKBANK', 'HINDUNILVR', 'SBIN', 'BHARTIARTL', 'ITC'
        ]
        
        stocks_data = []
        
        for symbol in stock_symbols:
            try:
                data = await get_live_quote_data(symbol)
                if data:
                    stocks_data.append({
                        "symbol": symbol,
                        "name": get_stock_name(symbol),
                        "sector": get_stock_sector(symbol),
                        **data
                    })
            except Exception as e:
                logger.warning(f"Error fetching stock data for {symbol}: {e}")
        
        return JSONResponse({
            "status": "success",
            "stocks": stocks_data,
            "timestamp": datetime.now().isoformat(),
            "source": "live"
        })
    
    except Exception as e:
        logger.error(f"Error getting live Indian stocks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@live_router.get("/market-status")
async def get_live_market_status():
    """Get current market status and trading hours"""
    try:
        now = datetime.now()
        
        # NSE trading hours: 9:15 AM to 3:30 PM IST (Monday to Friday)
        market_open_time = now.replace(hour=9, minute=15, second=0, microsecond=0)
        market_close_time = now.replace(hour=15, minute=30, second=0, microsecond=0)
        
        is_weekday = now.weekday() < 5  # Monday = 0, Friday = 4
        is_trading_hours = market_open_time <= now <= market_close_time
        
        market_status = "OPEN" if (is_weekday and is_trading_hours) else "CLOSED"
        
        return JSONResponse({
            "status": "success",
            "market_status": market_status,
            "trading_hours": {
                "open": "09:15",
                "close": "15:30",
                "timezone": "IST"
            },
            "next_open": get_next_market_open().isoformat() if market_status == "CLOSED" else None,
            "timestamp": now.isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error getting market status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@live_router.websocket("/stream")
async def websocket_live_data(websocket: WebSocket):
    """WebSocket endpoint for real-time data streaming"""
    await live_manager.connect(websocket)
    
    try:
        # Send welcome message
        await websocket.send_text(json.dumps({
            "type": "welcome",
            "message": "Connected to Zion Live Data Stream",
            "timestamp": time.time(),
            "commands": [
                "subscribe:SYMBOL",
                "unsubscribe:SYMBOL",
                "get_status"
            ]
        }))
        
        while True:
            message = await websocket.receive_text()
            
            try:
                if message.startswith("subscribe:"):
                    symbol = message.split(":", 1)[1].upper()
                    await live_manager.subscribe_to_symbol(websocket, symbol)
                    await websocket.send_text(json.dumps({
                        "type": "subscribed",
                        "symbol": symbol,
                        "message": f"Subscribed to live data for {symbol}"
                    }))
                
                elif message.startswith("unsubscribe:"):
                    symbol = message.split(":", 1)[1].upper()
                    if symbol in live_manager.symbol_subscribers:
                        if websocket in live_manager.symbol_subscribers[symbol]:
                            live_manager.symbol_subscribers[symbol].remove(websocket)
                    await websocket.send_text(json.dumps({
                        "type": "unsubscribed",
                        "symbol": symbol,
                        "message": f"Unsubscribed from {symbol}"
                    }))
                
                elif message == "get_status":
                    await websocket.send_text(json.dumps({
                        "type": "status",
                        "connected_clients": len(live_manager.active_connections),
                        "subscribed_symbols": list(live_manager.symbol_subscribers.keys()),
                        "is_running": live_manager.is_running
                    }))
                
                else:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": f"Unknown command: {message}"
                    }))
                    
            except Exception as e:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Command error: {str(e)}"
                }))
    
    except WebSocketDisconnect:
        live_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error in live data stream: {e}")
        live_manager.disconnect(websocket)

# Helper functions

async def get_live_quote_data(symbol: str) -> Optional[Dict[str, Any]]:
    """Fetch live quote data for a symbol from multiple sources"""
    try:
        # Normalize symbol for different providers
        normalized_symbol = normalize_indian_symbol(symbol, 'yahoo')
        
        # Try to get from stealth agents first (most recent)
        if hasattr(background_manager, 'get_latest_data'):
            stealth_data = await background_manager.get_latest_data(symbol)
            if stealth_data:
                return format_quote_data(stealth_data)
        
        # Fallback to data providers
        data = await provider.fetch_data_resilient(normalized_symbol, "price")
        if data and data.get("data"):
            quote_data = data["data"]
            
            # Enhance with additional market data if available
            try:
                volume_data = await provider.fetch_data_resilient(normalized_symbol, "volume")
                if volume_data and volume_data.get("data"):
                    quote_data.update(volume_data["data"])
            except:
                pass
            
            return format_quote_data(quote_data, data.get("source"))
        
        return None
    
    except Exception as e:
        logger.warning(f"Error fetching live quote for {symbol}: {e}")
        return None

def format_quote_data(raw_data: Dict[str, Any], source: str = "live") -> Dict[str, Any]:
    """Format raw quote data into standardized format"""
    try:
        price = raw_data.get("price", 0)
        previous_close = raw_data.get("previous_close", price)
        
        change = price - previous_close if previous_close else 0
        change_percent = (change / previous_close * 100) if previous_close else 0
        
        return {
            "price": round(price, 2),
            "change": round(change, 2),
            "changePercent": round(change_percent, 2),
            "volume": raw_data.get("volume", 0),
            "high": raw_data.get("high", price),
            "low": raw_data.get("low", price),
            "open": raw_data.get("open", price),
            "previousClose": raw_data.get("previous_close", price),
            "marketCap": raw_data.get("market_cap"),
            "source": source,
            "lastUpdate": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.warning(f"Error formatting quote data: {e}")
        return {"price": 0, "change": 0, "changePercent": 0, "source": "error"}

def get_index_name(symbol: str) -> str:
    """Get display name for index symbols"""
    index_names = {
        '^NSEI': 'Nifty 50',
        '^BSESN': 'Sensex',
        '^NSEBANK': 'Bank Nifty',
        '^NSEIT': 'Nifty IT',
        '^NSEAUTO': 'Nifty Auto',
        '^NSEFMCG': 'Nifty FMCG'
    }
    return index_names.get(symbol, symbol)

def get_stock_name(symbol: str) -> str:
    """Get display name for stock symbols"""
    stock_names = {
        'RELIANCE': 'Reliance Industries Ltd',
        'TCS': 'Tata Consultancy Services Ltd',
        'HDFCBANK': 'HDFC Bank Ltd',
        'INFY': 'Infosys Ltd',
        'ICICIBANK': 'ICICI Bank Ltd',
        'KOTAKBANK': 'Kotak Mahindra Bank Ltd',
        'HINDUNILVR': 'Hindustan Unilever Ltd',
        'SBIN': 'State Bank of India',
        'BHARTIARTL': 'Bharti Airtel Ltd',
        'ITC': 'ITC Ltd'
    }
    return stock_names.get(symbol, f"{symbol} Ltd")

def get_stock_sector(symbol: str) -> str:
    """Get sector for stock symbols"""
    stock_sectors = {
        'RELIANCE': 'Oil & Gas',
        'TCS': 'IT Services',
        'HDFCBANK': 'Banking',
        'INFY': 'IT Services',
        'ICICIBANK': 'Banking',
        'KOTAKBANK': 'Banking',
        'HINDUNILVR': 'FMCG',
        'SBIN': 'Banking',
        'BHARTIARTL': 'Telecom',
        'ITC': 'FMCG'
    }
    return stock_sectors.get(symbol, 'Unknown')

def get_next_market_open() -> datetime:
    """Calculate next market opening time"""
    now = datetime.now()
    
    # If it's weekend, next open is Monday 9:15 AM
    if now.weekday() >= 5:  # Saturday or Sunday
        days_until_monday = 7 - now.weekday()
        next_open = now + timedelta(days=days_until_monday)
        return next_open.replace(hour=9, minute=15, second=0, microsecond=0)
    
    # If it's after market close, next open is tomorrow 9:15 AM
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    if now > market_close:
        next_open = now + timedelta(days=1)
        return next_open.replace(hour=9, minute=15, second=0, microsecond=0)
    
    # If it's before market open, next open is today 9:15 AM
    return now.replace(hour=9, minute=15, second=0, microsecond=0)
