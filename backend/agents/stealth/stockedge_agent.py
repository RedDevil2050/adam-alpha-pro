from backend.agents.stealth.advanced_base import AdvancedStealthAgentBase, QuadChannelData
import httpx
import asyncio
import random
from bs4 import BeautifulSoup
from loguru import logger
from typing import Optional, Dict, List

agent_name = "stockedge_agent"


class StockEdgeAgent(AdvancedStealthAgentBase):
    def __init__(self):
        super().__init__()
        self.agent_name = agent_name
    
    async def _fetch_primary_source(self, symbol: str) -> Optional[Dict]:
        """Fetch data from StockEdge primary source with stealth scraping."""
        try:
            headers = {
                "User-Agent": random.choice(self.user_agents),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
            
            # Add random delay for stealth
            await asyncio.sleep(random.uniform(0.5, 2.0))
            
            async with httpx.AsyncClient(timeout=8, headers=headers) as client:
                # Try StockEdge URL pattern
                url = f"https://web.stockedge.com/share/{symbol}/NSE"
                response = await client.get(url)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")
                    
                    # Extract price data
                    price = self._extract_price_from_stockedge(soup)
                    volume = self._extract_volume_from_stockedge(soup)
                    technicals = self._extract_technicals_from_stockedge(soup)
                    
                    return {
                        "price": price,
                        "volume": volume,
                        "technicals": technicals,
                        "market_cap": None,
                        "pe_ratio": None,
                        "source": "stockedge_primary"
                    }
                    
        except Exception as e:
            logger.warning(f"StockEdge primary source failed for {symbol}: {e}")
            return None
        
        return None
    
    def _extract_price_from_stockedge(self, soup) -> Optional[float]:
        """Extract current price from StockEdge page."""
        try:
            # Try various price selectors
            price_selectors = [
                ".current-price", ".stock-price", ".ltp", ".price-current",
                "[data-testid='current-price']", ".price-value"
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
                price_text = matches[0].replace(",", "")
                return float(price_text)
                
        except Exception as e:
            logger.warning(f"Price extraction failed: {e}")
        return None
    
    def _extract_volume_from_stockedge(self, soup) -> Optional[int]:
        """Extract volume from StockEdge page."""
        try:
            volume_selectors = [
                ".volume", ".trade-volume", "[data-testid='volume']"
            ]
            
            for selector in volume_selectors:
                element = soup.select_one(selector)
                if element:
                    volume_text = element.get_text().strip()
                    # Handle K, M, B suffixes
                    volume_text = volume_text.replace(",", "")
                    if "K" in volume_text:
                        return int(float(volume_text.replace("K", "")) * 1000)
                    elif "M" in volume_text:
                        return int(float(volume_text.replace("M", "")) * 1000000)
                    elif "B" in volume_text:
                        return int(float(volume_text.replace("B", "")) * 1000000000)
                    else:
                        try:
                            return int(volume_text)
                        except ValueError:
                            continue
        except Exception as e:
            logger.warning(f"Volume extraction failed: {e}")
        return None
    
    def _extract_technicals_from_stockedge(self, soup) -> Dict:
        """Extract technical indicators from StockEdge page."""
        try:
            technicals = {}
            
            # Try to extract RSI, MACD, etc.
            indicator_selectors = {
                "rsi": [".rsi-value", "[data-indicator='rsi']"],
                "macd": [".macd-value", "[data-indicator='macd']"],
                "moving_average": [".ma-value", "[data-indicator='ma']"]
            }
            
            for indicator, selectors in indicator_selectors.items():
                for selector in selectors:
                    element = soup.select_one(selector)
                    if element:
                        try:
                            technicals[indicator] = float(element.get_text().strip())
                            break
                        except (ValueError, AttributeError):
                            continue
            
            return technicals
        except Exception as e:
            logger.warning(f"Technicals extraction failed: {e}")
        return {}

    async def _execute_analysis(self, symbol: str, agent_outputs: dict, fused_data: QuadChannelData) -> Dict:
        """Execute StockEdge-specific analysis with quad-channel fused data."""
        try:
            # Extract data from fused channels
            price = self._extract_best_price(fused_data)
            volume = self._extract_best_volume(fused_data)
            technicals = self._extract_best_technicals(fused_data)
            
            if not price or price <= 0:
                return self._error_response(symbol, "No valid price data from any channel")
            
            # Calculate StockEdge-specific score
            score = self._analyze_stockedge_scores(price, volume, technicals, fused_data)
            verdict = self._get_stockedge_verdict(score)
            
            # Calculate confidence with quad-channel boost
            base_confidence = score * 0.8
            quad_boost = len(fused_data.channels_used) * 0.05  # 5% per channel
            confidence = min(base_confidence + quad_boost, 1.0)
            
            return {
                "symbol": symbol,
                "verdict": verdict,
                "confidence": confidence,
                "value": round(score, 2),
                "details": {
                    "price_analysis": {
                        "current_price": price,
                        "volume": volume,
                        "price_sources": self._get_price_sources(fused_data)
                    },
                    "technical_analysis": technicals,
                    "stockedge_metrics": {
                        "quality_score": score * 100,
                        "trend_strength": self._calculate_trend_strength(technicals),
                        "momentum": self._calculate_momentum(price, technicals)
                    },
                    "quad_channel_performance": {
                        "channels_used": fused_data.channels_used,
                        "fusion_confidence": fused_data.fusion_confidence,
                        "validation_score": fused_data.validation_score
                    }
                },
                "error": None,
                "agent_name": agent_name,
            }

        except Exception as e:
            logger.error(f"❌ StockEdge quad-channel analysis error for {symbol}: {e}")
            return self._error_response(symbol, str(e))
    
    def _extract_best_price(self, fused_data: QuadChannelData) -> Optional[float]:
        """Extract the best price from available channels with priority."""
        for channel in ["primary", "secondary", "tertiary", "emergency"]:
            channel_data = getattr(fused_data, channel)
            if channel_data and "price" in channel_data:
                price = channel_data["price"]
                if isinstance(price, (int, float)) and price > 0:
                    return float(price)
        
        # If no valid price found, try to extract from any available data
        for channel in ["primary", "secondary", "tertiary", "emergency"]:
            channel_data = getattr(fused_data, channel)
            if channel_data:
                # Look for any numeric value that could be a price
                for key, value in channel_data.items():
                    if key in ['close', 'last', 'current_price', 'ltp', 'quote'] and value:
                        try:
                            price = float(str(value).replace(',', '').replace('₹', '').replace('$', ''))
                            if 10 <= price <= 100000:  # Reasonable price range for Indian stocks
                                return price
                        except (ValueError, TypeError):
                            continue
        
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
    
    def _extract_best_technicals(self, fused_data: QuadChannelData) -> Dict:
        """Extract and merge technical indicators from all channels."""
        merged_technicals = {}
        
        for channel in ["primary", "secondary", "tertiary", "emergency"]:
            channel_data = getattr(fused_data, channel)
            if channel_data and "technicals" in channel_data:
                technicals = channel_data["technicals"]
                if isinstance(technicals, dict):
                    merged_technicals.update(technicals)
        
        return merged_technicals
    
    def _get_price_sources(self, fused_data: QuadChannelData) -> List[str]:
        """Get list of sources that provided price data."""
        sources = []
        for channel in ["primary", "secondary", "tertiary", "emergency"]:
            channel_data = getattr(fused_data, channel)
            if channel_data and "price" in channel_data and channel_data["price"] > 0:
                source = channel_data.get("source", channel)
                sources.append(source)
        return sources
    
    def _analyze_stockedge_scores(self, price: float, volume: Optional[int], technicals: Dict, fused_data: QuadChannelData) -> float:
        """Analyze StockEdge-specific scoring with quad-channel data."""
        score = 0.5  # Base score
        
        # Price momentum analysis
        if price > 100:
            score += 0.1
        if price > 500:
            score += 0.1
        if price > 1000:
            score += 0.1
            
        # Volume analysis
        if volume is not None and volume > 100000:
            score += 0.1
        if volume is not None and volume > 1000000:
            score += 0.1
            
        # Technical indicators boost
        if technicals.get("rsi"):
            rsi = technicals["rsi"]
            if 30 <= rsi <= 70:  # Neutral zone
                score += 0.05
            elif rsi < 30:  # Oversold - potential buy
                score += 0.15
            elif rsi > 70:  # Overbought - potential sell
                score -= 0.1
                
        # Data quality bonus from quad-channel
        quality_bonus = fused_data.validation_score * 0.2
        score += quality_bonus
        
        return max(0.0, min(1.0, score))
    
    def _get_stockedge_verdict(self, score: float) -> str:
        """Get StockEdge-specific verdict based on score."""
        if score >= 0.8:
            return "STRONG_BUY"
        elif score >= 0.65:
            return "BUY"
        elif score >= 0.55:
            return "HOLD"
        elif score >= 0.4:
            return "WEAK_SIGNALS"
        else:
            return "SELL"
    
    def _calculate_trend_strength(self, technicals: Dict) -> float:
        """Calculate trend strength from technical indicators."""
        if not technicals:
            return 0.5
            
        strength = 0.5
        if "rsi" in technicals:
            rsi = technicals["rsi"]
            # Higher RSI deviation from 50 = stronger trend
            strength += abs(rsi - 50) / 100
            
        return min(1.0, strength)
    
    def _calculate_momentum(self, price: float, technicals: Dict) -> float:
        """Calculate price momentum indicator."""
        momentum = 0.5
        
        # Simple momentum based on price level
        if price > 500:
            momentum += 0.2
        if price > 1000:
            momentum += 0.2
            
        # Technical momentum
        if technicals.get("macd", 0) > 0:
            momentum += 0.1
            
        return min(1.0, momentum)

    async def _fetch_stealth_data(self, symbol: str) -> dict:
        url = f"https://web.stockedge.com/share/{symbol}/overview"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
        soup = BeautifulSoup(resp.text, "html.parser")

        return {
            "quality_score": self._extract_quality_score(soup),
            "technicals": self._extract_technicals(soup),
            "metrics": self._extract_key_metrics(soup),
            "source": "stockedge",
        }

    def _analyze_scores(self, data: dict) -> float:
        quality = data.get("quality_score", 50) / 100
        tech_score = self._calculate_technical_score(data.get("technicals", {}))
        return (quality + tech_score) / 2

    def _get_verdict(self, score: float) -> str:
        if score > 0.7:
            return "HIGH_QUALITY"
        elif score > 0.4:
            return "AVERAGE_QUALITY"
        return "LOW_QUALITY"

    def _extract_quality_score(self, soup) -> float:
        try:
            score_elem = soup.select_one(".quality-score")
            return float(score_elem.text.strip()) if score_elem else 50.0
        except:
            return 50.0

    def _extract_technicals(self, soup) -> dict:
        technicals = {}
        try:
            tech_div = soup.select_one(".technical-indicators")
            if tech_div:
                for indicator in tech_div.select(".indicator"):
                    name = indicator.select_one(".name").text.strip()
                    value = indicator.select_one(".value").text.strip()
                    technicals[name] = value
        except:
            pass
        return technicals

    def _extract_key_metrics(self, soup) -> dict:
        metrics = {}
        try:
            metrics_div = soup.select_one(".key-metrics")
            if metrics_div:
                for metric in metrics_div.select(".metric"):
                    name = metric.select_one(".name").text.strip()
                    value = metric.select_one(".value").text.strip()
                    metrics[name] = value
        except:
            pass
        return metrics

    def _calculate_technical_score(self, technicals: dict) -> float:
        positive_signals = len([v for v in technicals.values() if "buy" in v.lower()])
        total_signals = len(technicals) or 1
        return positive_signals / total_signals

async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    agent = StockEdgeAgent()
    # Pass agent_outputs to execute
    return await agent.execute(symbol, agent_outputs=agent_outputs)
