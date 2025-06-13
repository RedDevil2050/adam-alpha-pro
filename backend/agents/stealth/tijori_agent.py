from backend.agents.stealth.advanced_base import AdvancedStealthAgentBase, QuadChannelData
from backend.utils.data_provider import fetch_price_alpha_vantage
import httpx
import asyncio
import random
from bs4 import BeautifulSoup
from loguru import logger
from typing import Optional, Dict, List

agent_name = "tijori_agent"


class TijoriAgent(AdvancedStealthAgentBase):
    async def _fetch_primary_source(self, symbol: str) -> Optional[Dict]:
        """Fetch data from Tijori primary source with stealth scraping."""
        try:
            headers = {
                "User-Agent": random.choice(self.user_agents),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Referer": "https://www.google.com/",
                "Upgrade-Insecure-Requests": "1",
            }
            
            # Add random delay for stealth
            await asyncio.sleep(random.uniform(0.5, 2.0))
            
            async with httpx.AsyncClient(timeout=8, headers=headers) as client:
                # Try updated Tijori URL patterns (2024/2025)
                potential_urls = [
                    f"https://tijori.finance/stock/{symbol.lower()}",
                    f"https://www.tijori.finance/stocks/{symbol.lower()}",
                    f"https://tijori.finance/equity/{symbol.lower()}",
                    f"https://app.tijori.com/stocks/{symbol}",
                    f"https://tijori.com/nse/{symbol}",
                    f"https://tijori.finance/nse/{symbol.lower()}"
                ]
                
                for url in potential_urls:
                    try:
                        response = await client.get(url)
                        
                        if response.status_code == 200:
                            soup = BeautifulSoup(response.text, "html.parser")
                            
                            # Extract data
                            price = self._extract_price_from_tijori(soup)
                            volume = self._extract_volume_from_tijori(soup)
                            market_data = self._extract_market_data_from_tijori(soup)
                            
                            if price and price > 0:
                                return {
                                    "price": price,
                                    "volume": volume,
                                    "market_cap": market_data.get("market_cap"),
                                    "pe_ratio": market_data.get("pe_ratio"),
                                    "day_high": market_data.get("day_high"),
                                    "day_low": market_data.get("day_low"),
                                    "source": "tijori_primary"
                                }
                        elif response.status_code == 403:
                            logger.warning(f"Tijori 403 Forbidden for {url}")
                            continue
                    except Exception as e:
                        logger.warning(f"Tijori URL {url} failed: {e}")
                        continue
                        
            # If all URLs fail, try fallback approach
            return await self._fetch_tijori_fallback(symbol)
                    
        except Exception as e:
            logger.warning(f"Tijori primary source failed for {symbol}: {e}")
            return None
        
        return None
    
    async def _fetch_tijori_fallback(self, symbol: str) -> Optional[Dict]:
        """Fallback method with basic price data."""
        try:
            # Use Alpha Vantage as fallback (from original implementation)
            price_data = await fetch_price_alpha_vantage(symbol)
            if price_data and "price" in price_data:
                return {
                    "price": price_data["price"],
                    "volume": price_data.get("volume"),
                    "source": "tijori_fallback_alpha_vantage"
                }
        except Exception as e:
            logger.warning(f"Tijori fallback failed for {symbol}: {e}")
        return None
    
    def _extract_price_from_tijori(self, soup) -> Optional[float]:
        """Extract current price from Tijori page."""
        try:
            # Try various price selectors for Tijori
            price_selectors = [
                ".current-price", ".stock-price", ".ltp", ".price-value",
                "[data-testid='price']", ".price-current", ".live-price",
                ".quote-price", ".equity-price"
            ]
            
            for selector in price_selectors:
                element = soup.select_one(selector)
                if element:
                    price_text = element.get_text().strip()
                    # Clean and extract numeric value
                    price_text = price_text.replace(",", "").replace("₹", "").replace("$", "")
                    try:
                        return float(price_text)
                    except ValueError:
                        continue
                        
            # Fallback: search for price patterns in text
            import re
            price_pattern = r'₹?(\d{1,6}(?:,\d{3})*(?:\.\d{2})?)'
            matches = re.findall(price_pattern, soup.get_text())
            if matches:
                # Filter reasonable price values (10-100000 range for Indian stocks)
                for match in matches:
                    price_text = match.replace(",", "")
                    try:
                        price = float(price_text)
                        if 10 <= price <= 100000:  # Reasonable range
                            return price
                    except ValueError:
                        continue
                
        except Exception as e:
            logger.warning(f"Tijori price extraction failed: {e}")
        return None
    
    def _extract_volume_from_tijori(self, soup) -> Optional[int]:
        """Extract volume from Tijori page."""
        try:
            volume_selectors = [
                ".volume", ".trade-volume", "[data-testid='volume']", 
                ".vol-value", ".trading-volume"
            ]
            
            for selector in volume_selectors:
                element = soup.select_one(selector)
                if element:
                    volume_text = element.get_text().strip()
                    # Handle Indian notation (Cr, L, K)
                    volume_text = volume_text.replace(",", "")
                    if "Cr" in volume_text or "cr" in volume_text:
                        return int(float(volume_text.replace("Cr", "").replace("cr", "")) * 10000000)
                    elif "L" in volume_text or "l" in volume_text:
                        return int(float(volume_text.replace("L", "").replace("l", "")) * 100000)
                    elif "K" in volume_text:
                        return int(float(volume_text.replace("K", "")) * 1000)
                    elif "M" in volume_text:
                        return int(float(volume_text.replace("M", "")) * 1000000)
                    else:
                        try:
                            return int(float(volume_text))
                        except ValueError:
                            continue
        except Exception as e:
            logger.warning(f"Tijori volume extraction failed: {e}")
        return None
    
    def _extract_market_data_from_tijori(self, soup) -> Dict:
        """Extract additional market data from Tijori page."""
        try:
            market_data = {}
            
            # Try to extract market metrics
            data_selectors = {
                "market_cap": [".market-cap", "[data-testid='market-cap']", ".mcap"],
                "pe_ratio": [".pe-ratio", "[data-testid='pe']", ".pe-value"],
                "day_high": [".day-high", "[data-testid='day-high']", ".high"],
                "day_low": [".day-low", "[data-testid='day-low']", ".low"],
                "volume": [".volume", "[data-testid='volume']"]
            }
            
            for data_name, selectors in data_selectors.items():
                for selector in selectors:
                    element = soup.select_one(selector)
                    if element:
                        try:
                            value_text = element.get_text().strip()
                            # Handle market cap with Cr, L notations
                            if data_name == "market_cap":
                                if "Cr" in value_text:
                                    market_data[data_name] = float(value_text.replace("Cr", "").replace(",", "")) * 10000000
                                elif "L" in value_text:
                                    market_data[data_name] = float(value_text.replace("L", "").replace(",", "")) * 100000
                                else:
                                    market_data[data_name] = float(value_text.replace(",", ""))
                            else:
                                market_data[data_name] = float(value_text.replace(",", ""))
                            break
                        except (ValueError, AttributeError):
                            continue
            
            return market_data
        except Exception as e:
            logger.warning(f"Tijori market data extraction failed: {e}")
        return {}

    async def _execute_analysis(self, symbol: str, agent_outputs: dict, fused_data: QuadChannelData) -> Dict:
        """Execute Tijori-specific analysis with quad-channel fused data."""
        try:
            # Extract data from fused channels
            price = self._extract_best_price(fused_data)
            volume = self._extract_best_volume(fused_data)
            market_data = self._extract_best_market_data(fused_data)
            
            if not price or price <= 0:
                return self._error_response(symbol, "No valid price data from any channel")
            
            # Calculate Tijori-specific analysis
            verdict = self._get_tijori_verdict(price, market_data)
            confidence = self._calculate_tijori_confidence(price, volume, market_data, fused_data)
            
            # Tijori uses price as value
            value = price
            
            return {
                "symbol": symbol,
                "verdict": verdict,
                "confidence": confidence,
                "value": value,
                "details": {
                    "price_analysis": {
                        "current_price": price,
                        "volume": volume,
                        "day_high": market_data.get("day_high"),
                        "day_low": market_data.get("day_low"),
                        "price_sources": self._get_price_sources(fused_data)
                    },
                    "market_metrics": {
                        "market_cap": market_data.get("market_cap"),
                        "pe_ratio": market_data.get("pe_ratio"),
                        "price_position": self._calculate_price_position(price, market_data)
                    },
                    "tijori_analysis": {
                        "price_trend": self._analyze_price_trend(price, market_data),
                        "volume_analysis": self._analyze_volume_strength(volume),
                        "valuation_assessment": self._assess_valuation(price, market_data)
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
            logger.error(f"❌ Tijori quad-channel analysis error for {symbol}: {e}")
            return self._error_response(symbol, str(e))
    
    def _extract_best_price(self, fused_data: QuadChannelData) -> Optional[float]:
        """Extract the best price from available channels with priority."""
        for channel in ["primary", "secondary", "tertiary", "emergency"]:
            channel_data = getattr(fused_data, channel)
            if channel_data and "price" in channel_data:
                price = channel_data["price"]
                if isinstance(price, (int, float)) and price > 0:
                    return float(price)
        return None
    
    def _extract_best_volume(self, fused_data: QuadChannelData) -> Optional[int]:
        """Extract the best volume from available channels."""
        for channel in ["primary", "secondary", "tertiary", "emergency"]:
            channel_data = getattr(fused_data, channel)
            if channel_data and "volume" in channel_data:
                volume = channel_data["volume"]
                if isinstance(volume, (int, float)) and volume > 0:
                    return int(volume)
        return None
    
    def _extract_best_market_data(self, fused_data: QuadChannelData) -> Dict:
        """Extract and merge market data from all channels."""
        merged_data = {}
        
        for channel in ["primary", "secondary", "tertiary", "emergency"]:
            channel_data = getattr(fused_data, channel)
            if channel_data:
                # Merge various market data fields
                for field in ["market_cap", "pe_ratio", "day_high", "day_low"]:
                    if field in channel_data and channel_data[field] is not None:
                        merged_data[field] = channel_data[field]
        
        return merged_data
    
    def _get_price_sources(self, fused_data: QuadChannelData) -> List[str]:
        """Get list of sources that provided price data."""
        sources = []
        for channel in ["primary", "secondary", "tertiary", "emergency"]:
            channel_data = getattr(fused_data, channel)
            if channel_data and "price" in channel_data and channel_data["price"] > 0:
                source = channel_data.get("source", channel)
                sources.append(source)
        return sources
    
    def _get_tijori_verdict(self, price: float, market_data: Dict) -> str:
        """Get Tijori-specific verdict based on comprehensive analysis."""
        # Tijori specializes in fundamental analysis
        score = 0.5
        
        # Price level analysis
        if price > 1000:
            score += 0.15  # High-value stock
        elif price > 500:
            score += 0.1
        elif price < 50:
            score -= 0.1  # Penny stock risk
            
        # PE ratio analysis
        pe_ratio = market_data.get("pe_ratio")
        if pe_ratio:
            if 8 <= pe_ratio <= 20:  # Good PE range
                score += 0.2
            elif pe_ratio < 8:  # Potentially undervalued
                score += 0.25
            elif pe_ratio > 30:  # Potentially overvalued
                score -= 0.15
                
        # Day range analysis
        day_high = market_data.get("day_high")
        day_low = market_data.get("day_low")
        if day_high and day_low and day_high > day_low:
            price_position = (price - day_low) / (day_high - day_low)
            if price_position > 0.8:  # Near day high
                score += 0.1
            elif price_position < 0.2:  # Near day low
                score -= 0.1
        
        # Convert score to verdict
        if score >= 0.8:
            return "STRONG_BUY"
        elif score >= 0.65:
            return "BUY"
        elif score >= 0.45:
            return "HOLD"
        else:
            return "WEAK_SIGNALS"
    
    def _calculate_tijori_confidence(self, price: float, volume: Optional[int], 
                                   market_data: Dict, fused_data: QuadChannelData) -> float:
        """Calculate confidence with Tijori-specific factors."""
        base_confidence = 0.7  # Start with high confidence for Tijori
        
        # Volume boost
        if volume and volume > 100000:
            base_confidence += 0.1
        if volume and volume > 1000000:
            base_confidence += 0.1
            
        # Market data completeness boost
        data_fields = ["market_cap", "pe_ratio", "day_high", "day_low"]
        complete_fields = sum(1 for field in data_fields if market_data.get(field) is not None)
        completeness_boost = (complete_fields / len(data_fields)) * 0.1
        base_confidence += completeness_boost
        
        # Quad-channel boost
        quad_boost = len(fused_data.channels_used) * 0.03
        
        return min(1.0, base_confidence + quad_boost)
    
    def _calculate_price_position(self, price: float, market_data: Dict) -> float:
        """Calculate where current price sits in day's range."""
        day_high = market_data.get("day_high")
        day_low = market_data.get("day_low")
        
        if day_high and day_low and day_high > day_low:
            return (price - day_low) / (day_high - day_low)
        return 0.5  # Neutral if no range data
    
    def _analyze_price_trend(self, price: float, market_data: Dict) -> str:
        """Analyze price trend from available data."""
        position = self._calculate_price_position(price, market_data)
        
        if position > 0.8:
            return "Strong Uptrend"
        elif position > 0.6:
            return "Uptrend"
        elif position < 0.2:
            return "Strong Downtrend"
        elif position < 0.4:
            return "Downtrend"
        else:
            return "Sideways"
    
    def _analyze_volume_strength(self, volume: Optional[int]) -> str:
        """Analyze volume strength."""
        if volume is None:
            return "Unknown"
        elif volume > 2000000:
            return "Very High"
        elif volume > 1000000:
            return "High"
        elif volume > 500000:
            return "Medium"
        elif volume > 100000:
            return "Low"
        else:
            return "Very Low"
    
    def _assess_valuation(self, price: float, market_data: Dict) -> str:
        """Assess valuation based on available metrics."""
        pe_ratio = market_data.get("pe_ratio")
        
        if not pe_ratio:
            return "Insufficient Data"
        elif pe_ratio < 10:
            return "Potentially Undervalued"
        elif pe_ratio < 20:
            return "Fairly Valued"
        elif pe_ratio < 30:
            return "Slightly Overvalued"
        else:
            return "Potentially Overvalued"

    async def _fetch_stealth_data(self, symbol: str) -> dict:
        url = f"https://www.tijorifinance.com/stock/{symbol.lower()}/"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            price_elem = soup.find("span", class_="price-text")
            if price_elem:
                try:
                    price = float(price_elem.text.replace(",", "").strip())
                    return {"price": price}
                except (ValueError, TypeError):
                    pass
        return {}

    def _get_verdict(self, price: float) -> str:
        if price > 200:
            return "STRONG_BUY"
        elif price > 100:
            return "BUY"
        return "HOLD"

    def _calculate_confidence(self, price: float) -> float:
        return round(min(price / 200, 1.0), 2)

async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    agent = TijoriAgent()
    return await agent.execute(symbol, agent_outputs=agent_outputs)
