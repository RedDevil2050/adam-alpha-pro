from backend.agents.stealth.enhanced_stealth_base import EnhancedStealthAgentBase
from backend.agents.stealth.advanced_base import QuadChannelData
from backend.agents.stealth.safe_data_utils import (
    safe_numeric_compare, safe_get_price, safe_get_volume, safe_get_float,
    safe_rsi_score, validate_indian_market_data
)
import httpx, numpy as np
import asyncio
import random
import pandas_ta as ta
from bs4 import BeautifulSoup
from loguru import logger
from typing import Optional, Dict, List

agent_name = "tradingview_agent"
category = "stealth"


class TradingViewAgent(EnhancedStealthAgentBase):
    def __init__(self):
        super().__init__()
        self.agent_name = agent_name
    
    def _get_url_patterns(self) -> Dict[str, List[str]]:
        """URL patterns for TradingView with fallbacks"""
        return {
            'tradingview': [
                'https://www.tradingview.com/symbols/NSE-{symbol}/',
                'https://tradingview.com/symbols/NSE-{symbol}',
                'https://www.tradingview.com/symbols/BSE-{symbol}/',
                'https://in.tradingview.com/symbols/NSE-{symbol}/',
                'https://www.tradingview.com/chart/NSE:{symbol}/',
                'https://tradingview.com/chart/{symbol}',
                'https://www.tradingview.com/symbols/{symbol_lower}'
            ]
        }
    
    async def _fetch_primary_source(self, symbol: str) -> Optional[Dict]:
        """Enhanced TradingView primary source with fallback URLs and circuit breakers."""
        
        async def _fetch_tradingview_data():
            headers = {
                "User-Agent": random.choice(self.user_agents),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Referer": "https://www.google.com/",
                "Upgrade-Insecure-Requests": "1",
                "Cache-Control": "no-cache",
            }
            
            # Add adaptive delay
            await asyncio.sleep(random.uniform(0.8, 2.5))
            
            async with httpx.AsyncClient(timeout=15, headers=headers) as client:
                # Try to find working URL with fallback
                working_url = await self._find_working_url('tradingview', symbol, client)
                
                if not working_url:
                    # Fallback to default URL
                    working_url = f"https://www.tradingview.com/symbols/NSE-{symbol}/"
                
                response = await client.get(working_url)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")
                    
                    # Enhanced data extraction with safe utilities
                    price = self._extract_price_from_tradingview(soup)
                    volume = self._extract_volume_from_tradingview(soup)
                    technicals = self._extract_technicals_from_tradingview(soup)
                    chart_data = self._extract_chart_data_from_tradingview(soup)
                    
                    # Validate extracted data
                    if price is None or price <= 0:
                        logger.warning(f"TradingView: Invalid price data for {symbol}")
                        return None
                    
                    result = {
                        "price": price,
                        "volume": volume,
                        "technicals": technicals,
                        "chart_data": chart_data,
                        "oscillators": technicals.get("oscillators", {}) if technicals else {},
                        "moving_averages": technicals.get("moving_averages", {}) if technicals else {},
                        "source": "tradingview_primary",
                        "url_used": working_url
                    }
                    
                    return result
                elif response.status_code == 429:
                    logger.warning(f"TradingView: Rate limited for {symbol}")
                    raise Exception("Rate limit exceeded")
                elif response.status_code == 403:
                    logger.warning(f"TradingView: Access forbidden for {symbol}")
                    raise Exception("Access forbidden - possible bot detection")
                else:
                    logger.warning(f"TradingView: HTTP {response.status_code} for {symbol}")
                    return None
                    
        return await self._enhanced_fetch_with_fallback(
            "tradingview_primary", symbol, _fetch_tradingview_data
        )
        
        return None
    
    def _extract_price_from_tradingview(self, soup) -> Optional[float]:
        """Extract current price from TradingView page."""
        try:
            # TradingView specific price selectors
            price_selectors = [
                "[data-symbol-short] .tv-symbol-price-quote__value",
                ".tv-symbol-header__price",
                ".js-symbol-last",
                ".tv-symbol-price-quote",
                ".last-price",
                "[data-field='last_price']"
            ]
            
            for selector in price_selectors:
                element = soup.select_one(selector)
                if element:
                    price_text = element.get_text().strip()
                    # Clean TradingView price format
                    price_text = price_text.replace(",", "").replace("₹", "").replace("$", "")
                    try:
                        return float(price_text)
                    except ValueError:
                        continue
                        
            # Fallback: JSON data extraction from script tags
            import re
            import json
            
            scripts = soup.find_all("script")
            for script in scripts:
                if script.string and "last_price" in script.string:
                    try:
                        # Extract JSON data
                        json_match = re.search(r'({.*"last_price".*?})', script.string)
                        if json_match:
                            data = json.loads(json_match.group(1))
                            return float(data.get("last_price", 0))
                    except (json.JSONDecodeError, ValueError):
                        continue
                
        except Exception as e:
            logger.warning(f"TradingView price extraction failed: {e}")
        return None
    
    def _extract_volume_from_tradingview(self, soup) -> Optional[int]:
        """Extract volume from TradingView page."""
        try:
            volume_selectors = [
                "[data-field='volume']",
                ".tv-symbol-header__volume",
                ".js-symbol-volume",
                ".volume-value"
            ]
            
            for selector in volume_selectors:
                element = soup.select_one(selector)
                if element:
                    volume_text = element.get_text().strip()
                    # Handle TradingView volume notation
                    volume_text = volume_text.replace(",", "")
                    if "M" in volume_text:
                        return int(float(volume_text.replace("M", "")) * 1000000)
                    elif "K" in volume_text:
                        return int(float(volume_text.replace("K", "")) * 1000)
                    elif "B" in volume_text:
                        return int(float(volume_text.replace("B", "")) * 1000000000)
                    else:
                        try:
                            return int(float(volume_text))
                        except ValueError:
                            continue
        except Exception as e:
            logger.warning(f"TradingView volume extraction failed: {e}")
        return None
    
    def _extract_technicals_from_tradingview(self, soup) -> Dict:
        """Extract technical indicators from TradingView page."""
        try:
            technicals = {
                "oscillators": {},
                "moving_averages": {},
                "indicators": {}
            }
            
            # Extract technical indicators panel
            tech_selectors = {
                "rsi": [".rsi-value", "[data-name='RSI']"],
                "macd": [".macd-value", "[data-name='MACD']"],
                "stoch": [".stoch-value", "[data-name='Stoch']"],
                "cci": [".cci-value", "[data-name='CCI']"],
                "adx": [".adx-value", "[data-name='ADX']"],
                "williams_r": [".williams-value", "[data-name='Williams %R']"]
            }
            
            for indicator, selectors in tech_selectors.items():
                for selector in selectors:
                    element = soup.select_one(selector)
                    if element:
                        try:
                            value_text = element.get_text().strip()
                            technicals["indicators"][indicator] = float(value_text)
                            break
                        except (ValueError, AttributeError):
                            continue
            
            # Extract moving averages
            ma_periods = ["5", "10", "20", "50", "100", "200"]
            for period in ma_periods:
                ma_selector = f"[data-name='MA{period}']"
                element = soup.select_one(ma_selector)
                if element:
                    try:
                        technicals["moving_averages"][f"ma_{period}"] = float(element.get_text().strip())
                    except (ValueError, AttributeError):
                        continue
            
            return technicals
        except Exception as e:
            logger.warning(f"TradingView technicals extraction failed: {e}")
        return {"oscillators": {}, "moving_averages": {}, "indicators": {}}
    
    def _extract_chart_data_from_tradingview(self, soup) -> Dict:
        """Extract chart/candlestick data from TradingView page."""
        try:
            chart_data = {
                "highs": [],
                "lows": [],
                "opens": [],
                "closes": [],
                "volumes": []
            }
            
            # Try to extract from embedded chart data in script tags
            import re
            import json
            
            scripts = soup.find_all("script")
            for script in scripts:
                if script.string and ("ohlc" in script.string or "candle" in script.string):
                    try:
                        # Look for chart data patterns
                        ohlc_pattern = r'"o":(\d+(?:\.\d+)?).*?"h":(\d+(?:\.\d+)?).*?"l":(\d+(?:\.\d+)?).*?"c":(\d+(?:\.\d+)?)'
                        matches = re.findall(ohlc_pattern, script.string)
                        
                        for match in matches[-10:]:  # Get last 10 candles
                            open_price, high, low, close = map(float, match)
                            chart_data["opens"].append(open_price)
                            chart_data["highs"].append(high)
                            chart_data["lows"].append(low)
                            chart_data["closes"].append(close)
                        
                        if chart_data["closes"]:
                            break
                    except (json.JSONDecodeError, ValueError):
                        continue
            
            return chart_data
        except Exception as e:
            logger.warning(f"TradingView chart data extraction failed: {e}")
        return {"highs": [], "lows": [], "opens": [], "closes": [], "volumes": []}

    async def _execute_analysis(self, symbol: str, agent_outputs: dict, fused_data: QuadChannelData) -> Dict:
        """Execute TradingView-specific analysis with quad-channel fused data."""
        try:
            # Extract data from fused channels
            price = self._extract_best_price(fused_data)
            volume = self._extract_best_volume(fused_data)
            technicals = self._extract_best_technicals(fused_data)
            chart_data = self._extract_best_chart_data(fused_data)
            
            if not price or price <= 0:
                return self._error_response(symbol, "No valid price data from any channel")
            
            # Perform advanced TradingView-style technical analysis
            candlestick_patterns = self._analyze_candlestick_patterns(chart_data)
            fibonacci_levels = self._calculate_fibonacci_levels(chart_data)
            pivot_points = self._calculate_pivot_points(chart_data)
            elliott_waves = self._detect_elliott_waves(chart_data)
            
            # Enhanced signal processing
            signals = self._process_advanced_signals(
                technicals, candlestick_patterns, fibonacci_levels, 
                pivot_points, elliott_waves, fused_data
            )
            
            verdict = self._get_tradingview_verdict(signals)
            confidence = self._calculate_tradingview_confidence(signals, fused_data)
            
            return {
                "symbol": symbol,
                "verdict": verdict,
                "confidence": confidence,
                "value": round(signals["composite_score"], 2),
                "details": {
                    "price_analysis": {
                        "current_price": price,
                        "volume": volume,
                        "price_sources": self._get_price_sources(fused_data)
                    },
                    "technical_indicators": technicals.get("indicators", {}),
                    "oscillators": technicals.get("oscillators", {}),
                    "moving_averages": technicals.get("moving_averages", {}),
                    "pattern_analysis": {
                        "candlestick_patterns": candlestick_patterns,
                        "fibonacci_levels": fibonacci_levels,
                        "pivot_points": pivot_points,
                        "elliott_wave_position": elliott_waves
                    },
                    "tradingview_signals": {
                        "composite_score": signals["composite_score"],
                        "trend_strength": signals.get("trend_strength", 0.5),
                        "momentum": signals.get("momentum", 0.5),
                        "volatility": signals.get("volatility", 0.5)
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
            logger.error(f"❌ TradingView quad-channel analysis error for {symbol}: {e}")
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
    
    def _extract_best_volume(self, fused_data: QuadChannelData) -> int:
        """Extract the best volume from available channels, never return None."""
        for channel in ["primary", "secondary", "tertiary", "emergency"]:
            channel_data = getattr(fused_data, channel)
            if channel_data and "volume" in channel_data:
                volume = channel_data["volume"]
                if isinstance(volume, (int, float)) and volume > 0:
                    return int(volume)
        return 0  # Return 0 instead of None to prevent NoneType errors
    
    def _extract_best_technicals(self, fused_data: QuadChannelData) -> Dict:
        """Extract and merge technical indicators from all channels."""
        merged_technicals = {
            "indicators": {},
            "oscillators": {},
            "moving_averages": {}
        }
        
        for channel in ["primary", "secondary", "tertiary", "emergency"]:
            channel_data = getattr(fused_data, channel)
            if channel_data and "technicals" in channel_data:
                technicals = channel_data["technicals"]
                if isinstance(technicals, dict):
                    # Merge indicators
                    if "indicators" in technicals:
                        merged_technicals["indicators"].update(technicals["indicators"])
                    if "oscillators" in technicals:
                        merged_technicals["oscillators"].update(technicals["oscillators"])
                    if "moving_averages" in technicals:
                        merged_technicals["moving_averages"].update(technicals["moving_averages"])
        
        return merged_technicals
    
    def _extract_best_chart_data(self, fused_data: QuadChannelData) -> Dict:
        """Extract and merge chart data from all channels."""
        best_chart_data = {"highs": [], "lows": [], "opens": [], "closes": [], "volumes": []}
        
        for channel in ["primary", "secondary", "tertiary", "emergency"]:
            channel_data = getattr(fused_data, channel)
            if channel_data and "chart_data" in channel_data:
                chart_data = channel_data["chart_data"]
                if isinstance(chart_data, dict) and chart_data.get("closes"):
                    # Use the first complete chart data found
                    return chart_data
        
        return best_chart_data
    
    def _get_price_sources(self, fused_data: QuadChannelData) -> List[str]:
        """Get list of sources that provided price data."""
        sources = []
        for channel in ["primary", "secondary", "tertiary", "emergency"]:
            channel_data = getattr(fused_data, channel)
            if channel_data and "price" in channel_data and channel_data["price"] > 0:
                source = channel_data.get("source", channel)
                sources.append(source)
        return sources

    def _analyze_candlestick_patterns(self, chart_data: Dict) -> Dict:
        """Analyze candlestick patterns from chart data."""
        try:
            if not chart_data.get("closes"):
                return {}
                
            highs = np.array(chart_data.get("highs", []))
            lows = np.array(chart_data.get("lows", []))
            opens = np.array(chart_data.get("opens", []))
            closes = np.array(chart_data.get("closes", []))

            if len(closes) < 3:  # Need at least 3 periods for patterns
                return {}

            patterns = {}

            # Simple pattern detection
            last_close = closes[-1]
            last_open = opens[-1]
            last_high = highs[-1]
            last_low = lows[-1]

            # Doji pattern (open ≈ close)
            body_size = abs(last_close - last_open)
            total_range = last_high - last_low
            patterns["doji"] = body_size < (total_range * 0.1) if total_range > 0 else False

            # Hammer pattern (small body, long lower wick)
            upper_wick = last_high - max(last_open, last_close)
            lower_wick = min(last_open, last_close) - last_low
            patterns["hammer"] = (lower_wick > body_size * 2) and (upper_wick < body_size)

            # Engulfing pattern (requires previous candle)
            if len(closes) >= 2:
                prev_close = closes[-2]
                prev_open = opens[-2]
                bullish_engulfing = (prev_close < prev_open) and (last_close > last_open) and \
                                  (last_open < prev_close) and (last_close > prev_open)
                patterns["bullish_engulfing"] = bullish_engulfing

            return patterns
        except Exception as e:
            logger.warning(f"Candlestick pattern analysis failed: {e}")
            return {}

    def _calculate_fibonacci_levels(self, chart_data: Dict) -> Dict:
        """Calculate Fibonacci retracement levels."""
        try:
            highs = chart_data.get("highs", [])
            lows = chart_data.get("lows", [])

            if not highs or not lows:
                return {}

            high = max(highs)
            low = min(lows)
            diff = high - low
            
            if diff <= 0:
                return {}
                
            return {
                "level_0.236": low + diff * 0.236,
                "level_0.382": low + diff * 0.382,
                "level_0.5": low + diff * 0.5,
                "level_0.618": low + diff * 0.618,
                "level_0.786": low + diff * 0.786,
                "resistance": high,
                "support": low
            }
        except Exception as e:
            logger.warning(f"Fibonacci calculation failed: {e}")
            return {}

    def _calculate_pivot_points(self, chart_data: Dict) -> Dict:
        """Calculate pivot points from recent price data."""
        try:
            highs = chart_data.get("highs", [])
            lows = chart_data.get("lows", [])
            closes = chart_data.get("closes", [])
            
            if not (highs and lows and closes):
                return {}
                
            # Use last complete period
            high = highs[-1]
            low = lows[-1]
            close = closes[-1]
            
            pivot = (high + low + close) / 3
            return {
                "pivot": pivot,
                "resistance_1": (2 * pivot) - low,
                "support_1": (2 * pivot) - high,
                "resistance_2": pivot + (high - low),
                "support_2": pivot - (high - low)
            }
        except Exception as e:
            logger.warning(f"Pivot points calculation failed: {e}")
            return {}

    def _detect_elliott_waves(self, chart_data: Dict) -> str:
        """Detect Elliott Wave patterns (simplified implementation)."""
        try:
            closes = chart_data.get("closes", [])
            if len(closes) < 8:  # Need at least 8 periods for wave analysis
                return "Insufficient Data"
                
            # Simple wave detection based on trend changes
            recent_prices = closes[-8:]
            trend_changes = 0
            
            for i in range(1, len(recent_prices) - 1):
                if (recent_prices[i] > recent_prices[i-1] and recent_prices[i] > recent_prices[i+1]) or \
                   (recent_prices[i] < recent_prices[i-1] and recent_prices[i] < recent_prices[i+1]):
                    trend_changes += 1
            
            # Map trend changes to wave positions
            if trend_changes >= 4:
                return "Wave 5 (Completion)"
            elif trend_changes >= 3:
                return "Wave 4 (Correction)"
            elif trend_changes >= 2:
                return "Wave 3 (Impulse)"
            elif trend_changes >= 1:
                return "Wave 2 (Correction)"
            else:
                return "Wave 1 (Start)"
                
        except Exception as e:
            logger.warning(f"Elliott wave detection failed: {e}")
            return "Analysis Failed"

    def _process_advanced_signals(self, technicals: Dict, candlestick_patterns: Dict, 
                                 fibonacci_levels: Dict, pivot_points: Dict, 
                                 elliott_waves: str, fused_data: QuadChannelData) -> Dict:
        """Process and combine all technical signals into composite score."""
        try:
            score = 0.5  # Start neutral
            signals = {}
            
            # Technical indicators analysis
            indicators = technicals.get("indicators", {})
            
            # RSI analysis with safe comparison
            rsi = safe_get_float(indicators, "rsi", 0)
            rsi_score = safe_rsi_score(rsi, 0.0)
            score += rsi_score
            
            # MACD analysis with safe comparison
            macd = safe_get_float(indicators, "macd", 0)
            if macd > 0:  # Above signal line
                score += 0.1
            elif macd < 0:
                score -= 0.1
                score -= 0.1
            
            # Moving averages analysis
            mas = technicals.get("moving_averages", {})
            ma_signals = 0
            current_price = self._extract_best_price(fused_data)  # Extract once outside loop
            
            for ma_name, ma_value in mas.items():
                if ma_value and isinstance(ma_value, (int, float)):
                    # Use safe comparison with current price
                    if safe_numeric_compare(current_price, ma_value, 0):
                        ma_signals += 1
                    elif current_price is not None and current_price <= ma_value:
                        ma_signals -= 1
            
            if len(mas) > 0:
                ma_score = ma_signals / len(mas) * 0.1
                score += ma_score
            
            # Candlestick patterns analysis
            pattern_boost = 0
            if candlestick_patterns.get("hammer") or candlestick_patterns.get("bullish_engulfing"):
                pattern_boost += 0.1
            if candlestick_patterns.get("doji"):
                pattern_boost -= 0.05  # Indecision
                
            score += pattern_boost
            
            # Elliott wave analysis
            if "Wave 3" in elliott_waves or "Wave 5" in elliott_waves:
                score += 0.05  # Momentum waves
            elif "Wave 4" in elliott_waves or "Wave 2" in elliott_waves:
                score -= 0.03  # Correction waves
            
            # Calculate additional metrics
            signals["trend_strength"] = min(1.0, abs(score - 0.5) * 2)
            signals["momentum"] = self._calculate_momentum(technicals)
            signals["volatility"] = self._calculate_volatility(fibonacci_levels, pivot_points)
            
            # Data quality bonus
            quality_bonus = fused_data.validation_score * 0.1
            score += quality_bonus
            
            signals["composite_score"] = max(0.0, min(1.0, score))
            return signals
            
        except Exception as e:
            logger.warning(f"Signal processing failed: {e}")
            return {"composite_score": 0.5, "trend_strength": 0.5, "momentum": 0.5, "volatility": 0.5}
    
    def _calculate_momentum(self, technicals: Dict) -> float:
        """Calculate momentum score from technical indicators."""
        momentum = 0.5
        indicators = technicals.get("indicators", {})
        
        # RSI momentum
        rsi = indicators.get("rsi")
        if rsi:
            if rsi > 50:
                momentum += (rsi - 50) / 100
            else:
                momentum -= (50 - rsi) / 100
        
        # MACD momentum
        macd = indicators.get("macd")
        if macd:
            momentum += min(0.2, max(-0.2, macd / 100))
            
        return max(0.0, min(1.0, momentum))
    
    def _calculate_volatility(self, fibonacci_levels: Dict, pivot_points: Dict) -> float:
        """Calculate volatility score from price levels."""
        volatility = 0.5
        
        # Fibonacci range analysis
        if fibonacci_levels.get("resistance") and fibonacci_levels.get("support"):
            price_range = fibonacci_levels["resistance"] - fibonacci_levels["support"]
            if price_range > 0:
                # Higher range = higher volatility
                range_ratio = price_range / fibonacci_levels["support"]
                volatility = min(1.0, 0.3 + range_ratio * 5)
        
        return volatility
    
    def _get_tradingview_verdict(self, signals: Dict) -> str:
        """Get TradingView-specific verdict based on composite signals."""
        score = signals["composite_score"]
        
        if score >= 0.8:
            return "STRONG_BUY"
        elif score >= 0.65:
            return "BUY"
        elif score >= 0.55:
            return "HOLD"
        elif score >= 0.45:
            return "NEUTRAL"
        elif score >= 0.3:
            return "WEAK_SIGNALS"
        else:
            return "SELL"
    
    def _calculate_tradingview_confidence(self, signals: Dict, fused_data: QuadChannelData) -> float:
        """Calculate confidence with TradingView-specific factors."""
        base_confidence = signals["composite_score"] * 0.7
        
        # Technical completeness boost
        trend_strength = signals.get("trend_strength", 0.5)
        completeness_boost = trend_strength * 0.2
        
        # Quad-channel boost
        quad_boost = len(fused_data.channels_used) * 0.03
        
        return min(1.0, base_confidence + completeness_boost + quad_boost)


async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    agent = TradingViewAgent()
    return await agent.execute(symbol, agent_outputs=agent_outputs)
