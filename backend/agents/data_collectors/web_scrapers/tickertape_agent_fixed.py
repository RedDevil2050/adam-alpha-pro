from backend.agents.data_collectors.web_scrapers.advanced_base import AdvancedStealthAgentBase, QuadChannelData
from backend.agents.data_collectors.web_scrapers.safe_data_utils import (
    safe_numeric_compare, safe_get_price, safe_get_volume, safe_get_float,
    validate_indian_market_data
)
import httpx
import asyncio
import random
from bs4 import BeautifulSoup
from loguru import logger
from typing import Optional, Dict, List, Any

agent_name = "tickertape_agent"


class TickertapeAgent(AdvancedStealthAgentBase):
    def __init__(self):
        super().__init__()
        self.agent_name = agent_name
    
    async def _fetch_primary_source(self, symbol: str) -> Optional[Dict]:
        """Enhanced Tickertape primary source with updated URL patterns and better error handling."""
        
        # Try multiple URL patterns for TickerTape
        url_patterns = [
            f"https://www.tickertape.in/stocks/{symbol}",
            f"https://tickertape.in/stocks/{symbol}",
            f"https://www.tickertape.in/stocks/{symbol.lower()}",
            f"https://tickertape.in/stocks/{symbol.lower()}",
            f"https://www.tickertape.in/equity/{symbol}",
            f"https://tickertape.in/equity/{symbol}",
            f"https://www.tickertape.in/stock/{symbol}",
            f"https://tickertape.in/stock/{symbol}"
        ]
        
        # Enhanced headers to avoid bot detection
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Referer": "https://www.tickertape.in/",
            "Origin": "https://www.tickertape.in",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-CH-UA": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "Sec-CH-UA-Mobile": "?0",
            "Sec-CH-UA-Platform": '"Windows"'
        }
        
        for url in url_patterns:
            try:
                # Add random delay to avoid rate limiting
                await asyncio.sleep(random.uniform(0.5, 2.0))
                
                async with httpx.AsyncClient(
                    timeout=15,
                    follow_redirects=True,
                    headers=headers
                ) as client:
                    logger.debug(f"Trying TickerTape URL: {url}")
                    response = await client.get(url)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, "html.parser")
                        
                        # Validate we got actual stock data
                        if len(response.text) > 1000 and any(term in response.text.lower() for term in ['stock', 'price', 'market', 'nse', 'bse']):
                            # Enhanced data extraction with validation
                            price = self._extract_price_from_tickertape(soup)
                            volume = self._extract_volume_from_tickertape(soup)
                            ratios = self._extract_ratios_from_tickertape(soup)
                            recommendations = self._extract_recommendations_from_tickertape(soup)
                            
                            # Validate extracted data
                            if price is None or price <= 0:
                                logger.warning(f"TickerTape: Invalid price data for {symbol} from {url}")
                                continue  # Try next URL pattern
                            
                            result = {
                                "price": price,
                                "volume": volume,
                                "ratios": ratios,
                                "recommendations": recommendations,
                                "market_cap": ratios.get("market_cap") if ratios else None,
                                "pe_ratio": ratios.get("pe_ratio") if ratios else None,
                                "source": "tickertape_primary",
                                "url_used": url
                            }
                            
                            logger.success(f"TickerTape: Successfully fetched data for {symbol} from {url}")
                            return result
                        else:
                            logger.warning(f"TickerTape: Invalid content from {url}")
                    
                    elif response.status_code == 429:
                        logger.warning(f"TickerTape: Rate limited (429) - adding delay")
                        await asyncio.sleep(5)
                        continue
                    
                    elif response.status_code == 500:
                        logger.warning(f"TickerTape: Server error (500) for {url}")
                        continue
                    
                    elif response.status_code == 403:
                        logger.warning(f"TickerTape: Access forbidden (403) for {url}")
                        continue
                    
                    else:
                        logger.debug(f"TickerTape: Status {response.status_code} for {url}")
                        
            except httpx.TimeoutException:
                logger.warning(f"TickerTape: Timeout for {url}")
                continue
            except httpx.RequestError as e:
                logger.warning(f"TickerTape: Request failed for {url}: {e}")
                continue
            except Exception as e:
                logger.warning(f"TickerTape: Unexpected error for {url}: {e}")
                continue
        
        logger.error(f"TickerTape: All URL patterns failed for {symbol}")
        return None
    
    def _extract_price_from_tickertape(self, soup) -> Optional[float]:
        """Extract current price from Tickertape page."""
        try:
            # Try various price selectors for Tickertape
            price_selectors = [
                ".stock-price", ".current-price", ".ltp-price", ".price-value",
                "[data-testid='stock-price']", ".price-current", ".stock-ltp",
                ".price", ".quote-price", "[data-qa='stock-price']"
            ]
            
            for selector in price_selectors:
                element = soup.select_one(selector)
                if element:
                    price_text = element.get_text().strip()
                    # Clean and extract numeric value
                    price_text = price_text.replace(",", "").replace("₹", "").replace("$", "")
                    try:
                        price = float(price_text)
                        if 10 <= price <= 100000:  # Reasonable price range
                            return price
                    except ValueError:
                        continue
                        
            # Fallback: search for price patterns in text
            import re
            price_pattern = r'₹?(\d{1,6}(?:,\d{3})*(?:\.\d{2})?)'
            matches = re.findall(price_pattern, soup.get_text())
            for match in matches:
                try:
                    price = float(match.replace(",", ""))
                    if 10 <= price <= 100000:
                        return price
                except ValueError:
                    continue
                
        except Exception as e:
            logger.warning(f"Tickertape price extraction failed: {e}")
        return None
    
    def _extract_volume_from_tickertape(self, soup) -> Optional[int]:
        """Extract volume from Tickertape page."""
        try:
            volume_selectors = [
                ".volume-value", ".trade-volume", "[data-testid='volume']", ".vol-value",
                ".volume", "[data-qa='volume']"
            ]
            
            for selector in volume_selectors:
                element = soup.select_one(selector)
                if element:
                    volume_text = element.get_text().strip()
                    # Handle K, M, B, Cr suffixes (Indian notation)
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
                            volume = int(float(volume_text))
                            if volume > 0:
                                return volume
                        except ValueError:
                            continue
        except Exception as e:
            logger.warning(f"Tickertape volume extraction failed: {e}")
        return None
    
    def _extract_ratios_from_tickertape(self, soup) -> Dict:
        """Extract financial ratios from Tickertape page."""
        try:
            ratios = {}
            
            # Try to extract common ratios
            ratio_selectors = {
                "pe_ratio": [".pe-ratio", "[data-testid='pe-ratio']", ".ratio-pe", "[data-qa='pe-ratio']"],
                "pb_ratio": [".pb-ratio", "[data-testid='pb-ratio']", ".ratio-pb", "[data-qa='pb-ratio']"],
                "roe": [".roe-value", "[data-testid='roe']", ".ratio-roe", "[data-qa='roe']"],
                "debt_to_equity": [".debt-equity", "[data-testid='debt-equity']", "[data-qa='debt-equity']"],
                "market_cap": [".market-cap", "[data-testid='market-cap']", "[data-qa='market-cap']"]
            }
            
            for ratio_name, selectors in ratio_selectors.items():
                for selector in selectors:
                    element = soup.select_one(selector)
                    if element:
                        try:
                            value_text = element.get_text().strip()
                            # Handle Cr, L notations for market cap
                            if ratio_name == "market_cap":
                                if "Cr" in value_text:
                                    ratios[ratio_name] = float(value_text.replace("Cr", "").replace(",", "")) * 10000000
                                elif "L" in value_text:
                                    ratios[ratio_name] = float(value_text.replace("L", "").replace(",", "")) * 100000
                                else:
                                    ratios[ratio_name] = float(value_text.replace(",", ""))
                            else:
                                ratios[ratio_name] = float(value_text.replace(",", ""))
                            break
                        except (ValueError, AttributeError):
                            continue
            
            return ratios
        except Exception as e:
            logger.warning(f"Tickertape ratios extraction failed: {e}")
        return {}
    
    def _extract_recommendations_from_tickertape(self, soup) -> List[str]:
        """Extract analyst recommendations from Tickertape page."""
        try:
            recommendations = []
            
            # Try to find recommendation elements
            rec_selectors = [
                ".recommendation", ".analyst-recommendation", "[data-testid='recommendation']",
                ".rating", ".analyst-rating", "[data-qa='recommendation']"
            ]
            
            for selector in rec_selectors:
                elements = soup.select(selector)
                for element in elements:
                    rec_text = element.get_text().strip()
                    if rec_text and len(rec_text) < 50:  # Filter out long texts
                        recommendations.append(rec_text)
            
            return recommendations[:5]  # Limit to top 5 recommendations
        except Exception as e:
            logger.warning(f"Tickertape recommendations extraction failed: {e}")
        return []

    async def _execute_analysis(self, symbol: str, agent_outputs: dict, fused_data: QuadChannelData) -> Dict:
        """Execute Tickertape-specific analysis with quad-channel fused data."""
        try:
            # Extract data from fused channels
            price = self._extract_best_price(fused_data)
            volume = self._extract_best_volume(fused_data)
            ratios = self._extract_best_ratios(fused_data)
            recommendations = self._extract_best_recommendations(fused_data)
            
            if not price or price <= 0:
                return self._error_response(symbol, "No valid price data from any channel")
            
            # Calculate Tickertape-specific score
            score = self._calculate_tickertape_score(price, volume, ratios, recommendations, fused_data)
            verdict = self._get_tickertape_verdict(score)
            
            # Calculate confidence with quad-channel boost
            base_confidence = score * 0.85
            quad_boost = len(fused_data.channels_used) * 0.04  # 4% per channel
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
                    "financial_ratios": ratios,
                    "analyst_recommendations": recommendations,
                    "tickertape_metrics": {
                        "valuation_score": self._calculate_valuation_score(ratios),
                        "momentum_score": self._calculate_momentum_score(price, volume),
                        "recommendation_consensus": self._analyze_recommendation_consensus(recommendations)
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
            logger.error(f"❌ Tickertape quad-channel analysis error for {symbol}: {e}")
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
    
    def _extract_best_ratios(self, fused_data: QuadChannelData) -> Dict:
        """Extract and merge financial ratios from all channels."""
        merged_ratios = {}
        
        for channel in ["primary", "secondary", "tertiary", "emergency"]:
            channel_data = getattr(fused_data, channel)
            if channel_data and "ratios" in channel_data:
                ratios = channel_data["ratios"]
                if isinstance(ratios, dict):
                    merged_ratios.update(ratios)
        
        return merged_ratios
    
    def _extract_best_recommendations(self, fused_data: QuadChannelData) -> List[str]:
        """Extract and merge recommendations from all channels."""
        all_recommendations = []
        
        for channel in ["primary", "secondary", "tertiary", "emergency"]:
            channel_data = getattr(fused_data, channel)
            if channel_data and "recommendations" in channel_data:
                recommendations = channel_data["recommendations"]
                if isinstance(recommendations, list):
                    all_recommendations.extend(recommendations)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_recommendations = []
        for rec in all_recommendations:
            if rec not in seen:
                seen.add(rec)
                unique_recommendations.append(rec)
        
        return unique_recommendations[:10]  # Limit to top 10
    
    def _get_price_sources(self, fused_data: QuadChannelData) -> List[str]:
        """Get list of sources that provided price data."""
        sources = []
        for channel in ["primary", "secondary", "tertiary", "emergency"]:
            channel_data = getattr(fused_data, channel)
            if channel_data and "price" in channel_data and channel_data["price"] > 0:
                source = channel_data.get("source", channel)
                sources.append(source)
        return sources
    
    def _calculate_tickertape_score(self, price: float, volume: Optional[int], ratios: Dict, 
                                   recommendations: List[str], fused_data: QuadChannelData) -> float:
        """Calculate Tickertape-specific scoring with quad-channel data."""
        score = 0.5  # Base score
        
        # Valuation analysis
        score += self._calculate_valuation_score(ratios) * 0.3
        
        # Volume analysis
        if volume and volume > 50000:
            score += 0.1
        if volume and volume > 500000:
            score += 0.1
            
        # Recommendation analysis
        rec_score = self._analyze_recommendation_consensus(recommendations)
        score += rec_score * 0.2
        
        # Data quality bonus from quad-channel
        quality_bonus = fused_data.validation_score * 0.15
        score += quality_bonus
        
        return max(0.0, min(1.0, score))
    
    def _calculate_valuation_score(self, ratios: Dict) -> float:
        """Calculate valuation score from financial ratios."""
        val_score = 0.5
        
        # PE ratio analysis
        pe_ratio = ratios.get("pe_ratio")
        if pe_ratio:
            if 10 <= pe_ratio <= 25:  # Good PE range
                val_score += 0.2
            elif pe_ratio < 10:  # Potentially undervalued
                val_score += 0.3
            elif pe_ratio > 40:  # Potentially overvalued
                val_score -= 0.2
        
        # ROE analysis
        roe = ratios.get("roe")
        if roe and roe > 15:  # Good ROE
            val_score += 0.2
        
        return max(0.0, min(1.0, val_score))
    
    def _calculate_momentum_score(self, price: float, volume: Optional[int]) -> float:
        """Calculate momentum score from price and volume."""
        momentum = 0.5
        
        if price > 100:
            momentum += 0.1
        if price > 500:
            momentum += 0.1
            
        if volume is not None:
            if volume > 100000:
                momentum += 0.1
            if volume > 1000000:
                momentum += 0.2
                
        return min(1.0, momentum)
    
    def _analyze_recommendation_consensus(self, recommendations: List[str]) -> float:
        """Analyze consensus from analyst recommendations."""
        if not recommendations:
            return 0.5
            
        buy_words = ["buy", "strong buy", "add", "accumulate", "positive"]
        sell_words = ["sell", "strong sell", "reduce", "negative", "avoid"]
        
        buy_count = sum(1 for rec in recommendations if any(word in rec.lower() for word in buy_words))
        sell_count = sum(1 for rec in recommendations if any(word in rec.lower() for word in sell_words))
        
        total_recs = len(recommendations)
        if total_recs == 0:
            return 0.5
            
        consensus = (buy_count - sell_count) / total_recs
        return max(0.0, min(1.0, 0.5 + consensus * 0.5))
    
    def _get_tickertape_verdict(self, score: float) -> str:
        """Get Tickertape-specific verdict based on score."""
        if score >= 0.85:
            return "STRONG_BUY"
        elif score >= 0.7:
            return "BUY"
        elif score >= 0.55:
            return "HOLD"
        elif score >= 0.45:
            return "MIXED_CONSENSUS"
        else:
            return "SELL"


async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    """Run TickerTape agent analysis"""
    agent = TickertapeAgent()
    return await agent.execute(symbol, agent_outputs=agent_outputs)
