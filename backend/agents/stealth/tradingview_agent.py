from backend.agents.stealth.advanced_base import AdvancedStealthAgentBase, QuadChannelData
from backend.agents.stealth.safe_data_utils import (
    safe_numeric_compare, safe_get_price, safe_get_volume, safe_get_float,
    safe_rsi_score, validate_indian_market_data
)
import httpx
import numpy as np
import asyncio
import random
import json
import re
from bs4 import BeautifulSoup
from loguru import logger
from typing import Optional, Dict, List

agent_name = "tradingview_agent"


class TradingViewAgent(AdvancedStealthAgentBase):
    
    def __init__(self):
        super().__init__()
        self.tradingview_base_url = "https://www.tradingview.com"
    
    async def _fetch_primary_source(self, symbol: str) -> Optional[Dict]:
        """Fetch from TradingView as primary source with stealth techniques."""
        try:
            headers = {
                "User-Agent": random.choice(self.user_agents),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Referer": "https://www.google.com/",
            }
            
            await asyncio.sleep(random.uniform(1.0, 3.0))
            
            url_patterns = [
                f"{self.tradingview_base_url}/symbols/NSE-{symbol}/",
                f"{self.tradingview_base_url}/symbols/BSE-{symbol}/",
                f"{self.tradingview_base_url}/chart/?symbol=NSE%3A{symbol}"
            ]
            
            async with httpx.AsyncClient(timeout=10, headers=headers) as client:
                for url in url_patterns:
                    try:
                        response = await client.get(url)
                        if response.status_code == 200:
                            data = await self._parse_tradingview_page(response, symbol)
                            if data:
                                return data
                    except Exception as e:
                        logger.warning(f"TradingView URL {url} failed: {e}")
                        continue
                        
        except Exception as e:
            logger.warning(f"TradingView primary source failed for {symbol}: {e}")
            
        return None
    
    async def _parse_tradingview_page(self, response: httpx.Response, symbol: str) -> Optional[Dict]:
        """Parse TradingView page for technical data."""
        try:
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract price and technical indicators
            price = self._extract_tv_price(soup)
            technical_data = self._extract_tv_technical_data(soup)
            
            if price and price > 0:
                return {
                    "price": price,
                    "rsi": technical_data.get("rsi"),
                    "macd": technical_data.get("macd"),
                    "moving_avg_50": technical_data.get("ma50"),
                    "moving_avg_200": technical_data.get("ma200"),
                    "volume": technical_data.get("volume"),
                    "source": "tradingview_primary"
                }
                
        except Exception as e:
            logger.warning(f"Failed to parse TradingView page: {e}")
        
        return None
    
    def _extract_tv_price(self, soup) -> Optional[float]:
        """Extract current price from TradingView page."""
        try:
            # TradingView price selectors
            price_selectors = [
                "[data-field-key='last_price']",
                ".js-symbol-last",
                "[data-symbol-last]",
                ".tv-symbol-price-quote__value"
            ]
            
            for selector in price_selectors:
                element = soup.select_one(selector)
                if element:
                    price_text = element.get_text().strip()
                    price_text = re.sub(r'[^\d.]', '', price_text)
                    try:
                        return float(price_text)
                    except ValueError:
                        continue
            
            # Look for JSON data containing price
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and 'last_price' in script.string:
                    try:
                        # Extract JSON-like data
                        json_match = re.search(r'\{[^}]*"last_price"[^}]*\}', script.string)
                        if json_match:
                            json_data = json.loads(json_match.group())
                            return float(json_data.get('last_price', 0))
                    except (json.JSONDecodeError, ValueError):
                        continue
                        
        except Exception as e:
            logger.warning(f"TradingView price extraction failed: {e}")
        return None
    
    def _extract_tv_technical_data(self, soup) -> Dict:
        """Extract technical indicators from TradingView page."""
        technical_data = {}
        
        try:
            # Look for technical indicator data in scripts
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    # RSI extraction
                    rsi_match = re.search(r'"rsi[^"]*":\s*([0-9.]+)', script.string)
                    if rsi_match:
                        technical_data['rsi'] = float(rsi_match.group(1))
                    
                    # MACD extraction
                    macd_match = re.search(r'"macd[^"]*":\s*([0-9.-]+)', script.string)
                    if macd_match:
                        technical_data['macd'] = float(macd_match.group(1))
                    
                    # Moving averages
                    ma50_match = re.search(r'"ma50[^"]*":\s*([0-9.]+)', script.string)
                    if ma50_match:
                        technical_data['ma50'] = float(ma50_match.group(1))
                        
                    ma200_match = re.search(r'"ma200[^"]*":\s*([0-9.]+)', script.string)
                    if ma200_match:
                        technical_data['ma200'] = float(ma200_match.group(1))
            
        except Exception as e:
            logger.warning(f"TradingView technical data extraction failed: {e}")
        
        return technical_data
    
    async def _execute_analysis(self, symbol: str, agent_outputs: dict, fused_data: QuadChannelData) -> Dict:
        """Execute TradingView technical analysis."""
        try:
            # Extract data from fused channels
            price = self._extract_best_price(fused_data)
            technical_data = self._extract_technical_indicators(fused_data)
            
            if not price or price <= 0:
                return self._error_response(symbol, "No valid price data from any channel")
            
            # Calculate technical analysis
            technical_score = self._calculate_technical_score(price, technical_data)
            verdict = self._get_tradingview_verdict(technical_score, technical_data)
            confidence = self._calculate_tradingview_confidence(technical_data, fused_data)
            
            return {
                "symbol": symbol,
                "verdict": verdict,
                "confidence": confidence,
                "value": price,
                "details": {
                    "technical_analysis": {
                        "technical_score": technical_score,
                        "rsi": technical_data.get("rsi"),
                        "macd": technical_data.get("macd"),
                        "moving_avg_50": technical_data.get("moving_avg_50"),
                        "moving_avg_200": technical_data.get("moving_avg_200")
                    },
                    "tradingview_signals": {
                        "trend_direction": self._get_trend_direction(price, technical_data),
                        "momentum": self._analyze_momentum(technical_data),
                        "support_resistance": self._analyze_support_resistance(price, technical_data)
                    },
                    "quad_channel_performance": {
                        "channels_used": fused_data.channels_used,
                        "fusion_confidence": fused_data.fusion_confidence,
                        "validation_score": fused_data.validation_score
                    }
                },
                "error": None,
                "agent_name": agent_name
            }
            
        except Exception as e:
            logger.error(f"❌ TradingView analysis error for {symbol}: {e}")
            return self._error_response(symbol, str(e))
    
    def _extract_best_price(self, fused_data: QuadChannelData) -> Optional[float]:
        """Extract the best price from available channels."""
        for channel in ["primary", "secondary", "tertiary", "emergency"]:
            channel_data = getattr(fused_data, channel)
            if channel_data and "price" in channel_data:
                price = channel_data["price"]
                if isinstance(price, (int, float)) and price > 0:
                    return float(price)
        return None
    
    def _extract_technical_indicators(self, fused_data: QuadChannelData) -> Dict:
        """Extract technical indicators from all channels."""
        indicators = {}
        
        for channel in ["primary", "secondary", "tertiary", "emergency"]:
            channel_data = getattr(fused_data, channel)
            if channel_data:
                for indicator in ["rsi", "macd", "moving_avg_50", "moving_avg_200"]:
                    if indicator in channel_data and channel_data[indicator] is not None:
                        indicators[indicator] = channel_data[indicator]
        
        return indicators
    
    def _calculate_technical_score(self, price: float, technical_data: Dict) -> float:
        """Calculate technical analysis score."""
        score = 0.5  # Base score
        
        # RSI analysis
        rsi = technical_data.get("rsi")
        if rsi:
            if 30 <= rsi <= 70:  # Neutral zone
                score += 0.1
            elif rsi < 30:  # Oversold - potential buy
                score += 0.2
            elif rsi > 70:  # Overbought - potential sell
                score -= 0.1
        
        # MACD analysis
        macd = technical_data.get("macd")
        if macd:
            if macd > 0:  # Bullish
                score += 0.15
            else:  # Bearish
                score -= 0.1
        
        # Moving average analysis
        ma50 = technical_data.get("moving_avg_50")
        ma200 = technical_data.get("moving_avg_200")
        
        if ma50 and price > ma50:  # Above 50 MA
            score += 0.1
        if ma200 and price > ma200:  # Above 200 MA
            score += 0.15
        if ma50 and ma200 and ma50 > ma200:  # Golden cross
            score += 0.1
        
        return max(0.0, min(1.0, score))
    
    def _get_tradingview_verdict(self, technical_score: float, technical_data: Dict) -> str:
        """Get verdict based on technical analysis."""
        if technical_score >= 0.8:
            return "STRONG_BUY"
        elif technical_score >= 0.65:
            return "BUY"
        elif technical_score >= 0.45:
            return "HOLD"
        else:
            return "TECHNICAL_WEAKNESS"
    
    def _calculate_tradingview_confidence(self, technical_data: Dict, fused_data: QuadChannelData) -> float:
        """Calculate confidence based on technical indicator availability."""
        base_confidence = 0.7
        
        # Technical indicator completeness
        key_indicators = ["rsi", "macd", "moving_avg_50", "moving_avg_200"]
        available_indicators = sum(1 for indicator in key_indicators if technical_data.get(indicator) is not None)
        completeness_boost = (available_indicators / len(key_indicators)) * 0.2
        
        # Quad-channel boost
        quad_boost = len(fused_data.channels_used) * 0.025
        
        return min(1.0, base_confidence + completeness_boost + quad_boost)
    
    def _get_trend_direction(self, price: float, technical_data: Dict) -> str:
        """Determine trend direction."""
        ma50 = technical_data.get("moving_avg_50")
        ma200 = technical_data.get("moving_avg_200")
        
        if ma50 and ma200:
            if price > ma50 > ma200:
                return "Strong Uptrend"
            elif price > ma50 and ma50 < ma200:
                return "Weak Uptrend"
            elif price < ma50 < ma200:
                return "Strong Downtrend"
            elif price < ma50 and ma50 > ma200:
                return "Weak Downtrend"
        
        return "Sideways"
    
    def _analyze_momentum(self, technical_data: Dict) -> str:
        """Analyze momentum based on RSI and MACD."""
        rsi = technical_data.get("rsi")
        macd = technical_data.get("macd")
        
        if rsi and macd:
            if rsi > 60 and macd > 0:
                return "Strong Bullish"
            elif rsi > 50 and macd > 0:
                return "Bullish"
            elif rsi < 40 and macd < 0:
                return "Bearish"
            elif rsi < 30 and macd < 0:
                return "Strong Bearish"
        
        return "Neutral"
    
    def _analyze_support_resistance(self, price: float, technical_data: Dict) -> Dict:
        """Analyze support and resistance levels."""
        ma50 = technical_data.get("moving_avg_50")
        ma200 = technical_data.get("moving_avg_200")
        
        support_resistance = {}
        
        if ma50:
            if price > ma50:
                support_resistance["support"] = ma50
            else:
                support_resistance["resistance"] = ma50
        
        if ma200:
            if price > ma200:
                if "support" not in support_resistance:
                    support_resistance["support"] = ma200
            else:
                if "resistance" not in support_resistance:
                    support_resistance["resistance"] = ma200
        
        return support_resistance


async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    agent = TradingViewAgent()
    return await agent.execute(symbol, agent_outputs=agent_outputs)
