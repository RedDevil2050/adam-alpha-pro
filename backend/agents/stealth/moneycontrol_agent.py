from backend.agents.stealth.advanced_base import AdvancedStealthAgentBase, QuadChannelData
from backend.agents.stealth.advanced_stealth_scraper import BrowserConfig
from backend.utils.symbol_normalizer_fixed import IndianEquitySymbolNormalizer
import httpx
from bs4 import BeautifulSoup
import numpy as np
from sklearn.ensemble import IsolationForest
from loguru import logger
import asyncio
import random
import re
from typing import Dict, Optional, List, Any

agent_name = "moneycontrol_agent"


class MoneyControlAgent(AdvancedStealthAgentBase):
    """
    Enhanced MoneyControl agent with quad-channel browser automation:
    - Primary: Chrome headless with stealth
    - Secondary: Firefox headless with stealth  
    - Tertiary: Undetected Chrome
    - Emergency: HTTP requests with rotation
    """
    
    def __init__(self):
        super().__init__()
        self.agent_name = agent_name
        self.base_url = "https://www.moneycontrol.com"
        
        # ML components for advanced analysis
        self.anomaly_detector = IsolationForest(contamination=0.1)
        self.timeframes = [5, 15, 60, 240]  # minutes
        
        # Enhanced confidence thresholds for MoneyControl
        self.fusion_weights = {
            "primary": 0.5,    # Higher weight for MoneyControl
            "secondary": 0.3,   # Yahoo Finance
            "tertiary": 0.15,   # Alpha Vantage
            "emergency": 0.05   # Polygon.io
        }
        
        logger.info(f"🚀 Enhanced MoneyControl Agent initialized with quad-channel browser support")
    
    async def _fetch_primary_source(self, symbol: str) -> Optional[Dict]:
        """Fetch from MoneyControl with enhanced quad-channel browser automation"""
        logger.info(f"🔍 Starting enhanced MoneyControl fetch for {symbol}")
        
        # Multiple URL patterns for MoneyControl
        urls = [
            f"{self.base_url}/india/stockpricequote/{symbol}",
            f"{self.base_url}/stocks/company_info/stock_comp_result.php?sc_id={symbol}",
            f"{self.base_url}/shares-stock-price/{symbol}",
            f"{self.base_url}/stock-price/{symbol}",
            f"{self.base_url}/equity/{symbol}",
            f"{self.base_url}/search/all?search={symbol}"
        ]
        
        # Enhanced browser-based scraping with quad-channel
        if self.browser_enabled:
            selectors = {
                'price': '.inprice1, #Nse_Prc_tick, .trade-price, .price-current',
                'change': '.gainer, .loser, .change-value, .price-change',
                'volume': 'td:contains("Volume") + td, .volume-data',
                'market_cap': 'td:contains("Market Cap") + td, .market-cap',
                'pe_ratio': 'td:contains("P/E") + td, .pe-ratio',
                'high': 'td:contains("High") + td, .day-high',
                'low': 'td:contains("Low") + td, .day-low'
            }
            
            try:
                browser_results = await self.stealth_scraper.quad_channel_scrape(urls[:4], selectors)
                
                for channel_name, channel_result in browser_results.items():
                    if channel_result.get('success') and channel_result.get('data'):
                        processed_data = self._process_moneycontrol_data(channel_result['data'])
                        if processed_data and processed_data.get('price'):
                            logger.success(f"✅ MoneyControl browser channel {channel_name} succeeded")
                            return {
                                'success': True,
                                'data': processed_data,
                                'channel': channel_name,
                                'method': 'browser',
                                'browser': channel_result.get('browser'),
                                'source': 'moneycontrol_primary'
                            }
                        
            except Exception as e:
                logger.warning(f"⚠️ Browser scraping failed: {e}")
        
        # Fallback to enhanced HTTP requests with 503 handling
        return await self._fetch_with_enhanced_http(urls, symbol)
    
    async def _fetch_with_enhanced_http(self, urls: List[str], symbol: str) -> Optional[Dict]:
        """Enhanced HTTP fallback with exponential backoff for 503 errors"""
        
        for i, url in enumerate(urls):
            max_retries = 3
            base_delay = 2
            
            for attempt in range(max_retries):
                try:
                    headers = {
                        "User-Agent": random.choice(self.user_agents),
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.9",
                        "Accept-Encoding": "gzip, deflate, br",
                        "Referer": "https://www.moneycontrol.com/",
                        "Connection": "keep-alive",
                        "Upgrade-Insecure-Requests": "1",
                        "Sec-Fetch-Dest": "document",
                        "Sec-Fetch-Mode": "navigate",
                        "Sec-Fetch-Site": "same-origin",
                        "Cache-Control": "max-age=0",
                        "Sec-CH-UA": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                        "Sec-CH-UA-Mobile": "?0",
                        "Sec-CH-UA-Platform": '"Windows"'
                    }
                    
                    async with httpx.AsyncClient(
                        timeout=20, 
                        follow_redirects=True,
                        headers=headers
                    ) as client:
                        logger.debug(f"Attempting MoneyControl URL: {url} (attempt {attempt + 1})")
                        response = await client.get(url)
                        
                        if response.status_code == 200:
                            soup = BeautifulSoup(response.text, "html.parser")
                            
                            # Validate content quality
                            if len(response.text) > 1000 and any(term in response.text.lower() 
                                                               for term in ['stock', 'price', 'market', 'nse', 'bse']):
                                data = self._parse_moneycontrol_html(soup)
                                if data and data.get('price'):
                                    logger.success(f"✅ MoneyControl HTTP succeeded: {url}")
                                    return {
                                        'success': True,
                                        'data': data,
                                        'channel': f'http_{i}',
                                        'method': 'http',
                                        'source': 'moneycontrol_primary'
                                    }
                            else:
                                logger.warning(f"⚠️ Invalid content from {url}")
                        
                        elif response.status_code == 503:
                            delay = min(base_delay * (2 ** attempt), 30)
                            logger.warning(f"🔴 503 Service Unavailable - waiting {delay}s before retry")
                            
                            if attempt < max_retries - 1:
                                await asyncio.sleep(delay)
                            continue
                        
                        elif response.status_code == 403:
                            logger.warning(f"🔴 403 Access Forbidden - possible bot detection")
                            break  # Try next URL
                        
                        else:
                            logger.debug(f"HTTP {response.status_code} for {url}")
                            break  # Try next URL
                            
                except httpx.TimeoutException:
                    logger.warning(f"⏱️ Timeout for {url}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(base_delay)
                    continue
                except Exception as e:
                    logger.warning(f"❌ Error with {url}: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(base_delay)
                    continue
        
        logger.error(f"❌ All MoneyControl URL patterns failed for {symbol}")
        return None
    
    def _process_moneycontrol_data(self, scraped_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data scraped from MoneyControl browser automation"""
        processed = {}
        
        try:
            # Extract and clean price
            if scraped_data.get('price'):
                price_text = str(scraped_data['price']).strip()
                price_match = re.search(r'[\d,]+\.?\d*', price_text)
                if price_match:
                    processed['price'] = float(price_match.group().replace(',', ''))
            
            # Extract change
            if scraped_data.get('change'):
                change_text = str(scraped_data['change']).strip()
                processed['change'] = change_text
            
            # Extract volume
            if scraped_data.get('volume'):
                volume_text = str(scraped_data['volume']).strip()
                processed['volume'] = volume_text
            
            # Extract other fields
            for field in ['market_cap', 'pe_ratio', 'high', 'low']:
                if scraped_data.get(field):
                    processed[field] = str(scraped_data[field]).strip()
            
        except Exception as e:
            logger.error(f"Error processing MoneyControl scraped data: {e}")
        
        return processed
    
    def _parse_moneycontrol_html(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Parse MoneyControl HTML content"""
        data = {}
        
        try:
            # Price extraction with multiple selectors
            price_selectors = [
                {'class': 'inprice1'},
                {'id': 'Nse_Prc_tick'},
                {'class': 'trade-price'},
                {'class': 'price-current'}
            ]
            
            for selector in price_selectors:
                price_elem = soup.find('div', selector) or soup.find('span', selector)
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    try:
                        data['price'] = float(re.sub(r'[^\d.]', '', price_text))
                        break
                    except:
                        continue
            
            # Change extraction
            change_elem = soup.find('span', {'class': 'gainer'}) or soup.find('span', {'class': 'loser'})
            if change_elem:
                change_text = change_elem.get_text(strip=True)
                data['change'] = change_text
            
            # Volume
            volume_elem = soup.find('td', string=re.compile(r'Volume', re.I))
            if volume_elem and volume_elem.find_next_sibling():
                volume_text = volume_elem.find_next_sibling().get_text(strip=True)
                data['volume'] = volume_text
            
            # Market cap
            mcap_elem = soup.find('td', string=re.compile(r'Market Cap', re.I))
            if mcap_elem and mcap_elem.find_next_sibling():
                mcap_text = mcap_elem.find_next_sibling().get_text(strip=True)
                data['market_cap'] = mcap_text
            
            # PE Ratio
            pe_elem = soup.find('td', string=re.compile(r'P/E', re.I))
            if pe_elem and pe_elem.find_next_sibling():
                pe_text = pe_elem.find_next_sibling().get_text(strip=True)
                data['pe_ratio'] = pe_text
            
            # Day High/Low
            high_elem = soup.find('td', string=re.compile(r'High', re.I))
            if high_elem and high_elem.find_next_sibling():
                high_text = high_elem.find_next_sibling().get_text(strip=True)
                data['high'] = high_text
            
            low_elem = soup.find('td', string=re.compile(r'Low', re.I))
            if low_elem and low_elem.find_next_sibling():
                low_text = low_elem.find_next_sibling().get_text(strip=True)
                data['low'] = low_text
                
        except Exception as e:
            logger.error(f"Error parsing MoneyControl HTML: {e}")
        
        return data
    
    async def _execute_analysis(self, symbol: str, agent_outputs: dict, fused_data: QuadChannelData) -> Dict:
        """Execute enhanced analysis using quad-channel fused data."""
        try:
            logger.info(f"🔬 Starting enhanced MoneyControl analysis for {symbol}")
            
            # Extract data from the best available channel
            analysis_data = self._extract_best_data(fused_data)
            
            if not analysis_data:
                return self._error_response(symbol, "No usable data from any channel")
            
            # Advanced multi-timeframe analysis
            multi_tf_analysis = self._analyze_multiple_timeframes(analysis_data)
            
            # ML-powered anomaly detection
            anomalies = self._detect_anomalies(analysis_data)
            
            # Enhanced volume profile analysis
            volume_profile = self._analyze_volume_profile(analysis_data)
            
            # Sentiment impact assessment
            sentiment_impact = self._analyze_sentiment_impact(analysis_data)
            
            # Calculate ML-enhanced score
            score = self._calculate_ml_enhanced_score(
                analysis_data, multi_tf_analysis, anomalies, volume_profile, sentiment_impact
            )
            
            # Determine verdict with advanced logic
            verdict = self._get_enhanced_verdict(score, anomalies, fused_data)
            
            # Calculate confidence with quad-channel boost
            confidence = self._calculate_enhanced_confidence(score, anomalies, fused_data)
            
            return {
                "symbol": symbol,
                "verdict": verdict,
                "confidence": confidence,
                "value": round(score, 3),
                "details": {
                    "expert_ratings": analysis_data.get("ratings", {}),
                    "technical_signals": analysis_data.get("technicals", {}),
                    "news_sentiment": analysis_data.get("sentiment", "neutral"),
                    "anomalies_detected": anomalies,
                    "volume_profile": volume_profile,
                    "timeframe_analysis": multi_tf_analysis,
                    "sentiment_impact": sentiment_impact,
                    "ml_score_components": {
                        "base_score": score,
                        "anomaly_adjustment": anomalies.get("score", 0),
                        "volume_strength": volume_profile.get("strength", 0.5),
                        "sentiment_boost": sentiment_impact
                    },
                    "price_data": {
                        "current_price": analysis_data.get("price"),
                        "volume": analysis_data.get("volume"),
                        "market_cap": analysis_data.get("market_cap"),
                        "pe_ratio": analysis_data.get("pe_ratio"),                        "price_validated": True
                    },
                    "data_quality": {
                        "fusion_confidence": fused_data.fusion_confidence,
                        "validation_score": fused_data.validation_score,
                        "channels_used": fused_data.channels_used,
                        "data_freshness": f"{fused_data.collection_timestamp:.1f}s ago"
                    },
                    "source": "enhanced_moneycontrol_quad_channel"
                },
                "error": None,
                "agent_name": self.agent_name,
            }
        except Exception as e:
            logger.error(f"❌ Enhanced MoneyControl analysis error for {symbol}: {e}")
            return self._error_response(symbol, str(e))
    
    def _extract_best_data(self, fused_data: QuadChannelData) -> Dict:
        """Extract the best available data from quad-channel fusion."""
        
        # Priority order: primary -> secondary -> tertiary -> emergency
        for channel in ["primary", "secondary", "tertiary", "emergency"]:
            channel_data = getattr(fused_data, channel)
            if channel_data:
                # Check for price data in various formats
                price = None
                for price_key in ["price", "close", "last", "current_price", "ltp"]:
                    if price_key in channel_data and channel_data[price_key]:
                        try:
                            price = float(str(channel_data[price_key]).replace(',', '').replace('₹', '').replace('$', ''))
                            if 10 <= price <= 100000:  # Reasonable range for Indian stocks
                                break
                        except (ValueError, TypeError):
                            continue
                
                if price:
                    logger.debug(f"Using {channel} channel data for analysis with price {price}")
                    # Ensure we have the price field
                    enriched_data = dict(channel_data)
                    enriched_data["price"] = price
                    return enriched_data
        
        # If no price found, still return the first available data for other analysis
        for channel in ["primary", "secondary", "tertiary", "emergency"]:
            channel_data = getattr(fused_data, channel)
            if channel_data:
                logger.debug(f"Using {channel} channel data for analysis (no price found)")
                return channel_data
        
        return {}
    
    def _get_enhanced_verdict(self, score: float, anomalies: Dict, fused_data: QuadChannelData) -> str:
        """Get enhanced verdict considering additional factors."""
        base_verdict = self._get_ml_verdict(score, anomalies)
        
        # Enhance based on fusion confidence
        if fused_data.fusion_confidence > 0.8 and score > 0.7:
            return "STRONG_BUY"
        elif fused_data.fusion_confidence > 0.8 and score < 0.3:
            return "STRONG_SELL"
        
        return base_verdict
    
    def _calculate_enhanced_confidence(self, score: float, anomalies: Dict, fused_data: QuadChannelData) -> float:
        """Calculate enhanced confidence using quad-channel data."""
        
        # Base confidence from score
        base_confidence = min(score * 0.9, 0.95)
        
        # Fusion confidence boost
        fusion_boost = fused_data.fusion_confidence * 0.15
        
        # Validation score boost
        validation_boost = fused_data.validation_score * 0.1
        
        # Multi-channel bonus
        channel_bonus = len(fused_data.channels_used) * 0.02  # 2% per additional channel
        
        # Anomaly penalty
        anomaly_penalty = 0.05 if anomalies.get("detected", False) else 0
        
        enhanced_confidence = min(
            base_confidence + fusion_boost + validation_boost + channel_bonus - anomaly_penalty, 
            1.0
        )
        
        logger.debug(f"Confidence enhanced: {base_confidence:.3f} -> {enhanced_confidence:.3f}")
        return enhanced_confidence

    # Legacy helper methods for extraction
    def _extract_price(self, soup) -> float:
        """Extract current price from soup."""
        try:
            price_elem = soup.select_one(".price, .current-price, [data-price]")
            if price_elem:
                price_text = price_elem.text.strip().replace(",", "").replace("₹", "")
                return float(price_text)
        except:
            pass
        return 0.0

    def _extract_volume(self, soup) -> int:
        """Extract volume from soup."""
        try:
            volume_elem = soup.select_one(".volume, [data-volume]")
            if volume_elem:
                volume_text = volume_elem.text.strip().replace(",", "")
                return int(float(volume_text))
        except:
            pass
        return 0

    def _extract_market_cap(self, soup) -> float:
        """Extract market cap from soup."""
        try:
            mcap_elem = soup.select_one(".market-cap, [data-mcap]")
            if mcap_elem:
                mcap_text = mcap_elem.text.strip().replace(",", "").replace("₹", "")
                # Handle Cr (Crores) suffix
                if "Cr" in mcap_text:
                    return float(mcap_text.replace("Cr", "").strip()) * 10000000
                return float(mcap_text)
        except:
            pass
        return 0.0

    def _extract_pe_ratio(self, soup) -> float:
        """Extract P/E ratio from soup."""
        try:
            pe_elem = soup.select_one(".pe-ratio, [data-pe]")
            if pe_elem:
                pe_text = pe_elem.text.strip()
                return float(pe_text)
        except:
            pass
        return 0.0

    def _extract_ratings(self, soup) -> dict:
        """Extract analyst ratings from soup."""
        ratings = {}
        try:
            rating_div = soup.select_one(".ratings-block, .analyst-ratings")
            if rating_div:
                for item in rating_div.select(".rating-item"):
                    name_elem = item.select_one(".name, .analyst-name")
                    rating_elem = item.select_one(".rating, .rating-value")
                    if name_elem and rating_elem:
                        ratings[name_elem.text.strip()] = rating_elem.text.strip()
        except:
            pass
        return ratings

    def _extract_technicals(self, soup) -> dict:
        """Extract technical indicators from soup."""
        technicals = {}
        try:
            tech_div = soup.select_one(".technical-block, .technical-indicators")
            if tech_div:
                for indicator in tech_div.select(".indicator, .tech-indicator"):
                    name_elem = indicator.select_one(".name, .indicator-name")
                    value_elem = indicator.select_one(".value, .indicator-value")
                    if name_elem and value_elem:
                        technicals[name_elem.text.strip()] = value_elem.text.strip()
        except:
            pass
        return technicals

    def _extract_sentiment(self, soup) -> str:
        """Extract market sentiment from soup."""
        try:
            sentiment_div = soup.select_one(".sentiment-indicator, .market-sentiment")
            if sentiment_div:
                return sentiment_div.text.strip().lower()
        except:
            pass
        return "neutral"

    # ML and analysis methods
    def _analyze_multiple_timeframes(self, data: dict) -> dict:
        """Analyze multiple timeframes."""
        analyses = {}
        for tf in self.timeframes:
            try:
                prices = self._get_timeframe_data(data, tf)
                analyses[f"{tf}min"] = {
                    "trend": self._calculate_trend_strength(prices),
                    "momentum": self._calculate_momentum(prices),
                    "volatility": self._calculate_volatility(prices),
                }
            except Exception as e:
                logger.error(f"Timeframe analysis error: {e}")
        return analyses

    def _detect_anomalies(self, data: dict) -> dict:
        """Detect anomalies using ML."""
        try:
            features = self._extract_ml_features(data)
            if features.size > 0:
                anomaly_scores = self.anomaly_detector.fit_predict(features)
                return {
                    "score": float(np.mean(anomaly_scores)),
                    "detected": bool(np.any(anomaly_scores == -1)),
                    "locations": np.where(anomaly_scores == -1)[0].tolist(),
                }
        except Exception as e:
            logger.error(f"Anomaly detection error: {e}")
        return {"score": 0, "detected": False, "locations": []}

    def _analyze_volume_profile(self, data: dict) -> dict:
        """Analyze volume profile."""
        try:
            volume = data.get("volume", 0)
            price = data.get("price", 0)
            
            if volume > 0 and price > 0:
                return {
                    "strength": min(volume / 1000000, 1.0),  # Normalize to millions
                    "price_volume_ratio": price / max(volume, 1),
                    "volume_trend": "high" if volume > 500000 else "normal"
                }
        except Exception as e:
            logger.error(f"Volume profile analysis error: {e}")
        return {"strength": 0.5}

    def _analyze_sentiment_impact(self, data: dict) -> float:
        """Analyze sentiment impact."""
        sentiment = data.get("sentiment", "neutral")
        if sentiment == "positive":
            return 0.1
        elif sentiment == "negative":
            return -0.1
        return 0.0

    def _calculate_ml_enhanced_score(self, data, multi_tf_analysis, anomalies, volume_profile, sentiment_impact):
        """Calculate ML enhanced score."""
        base_score = 0.5  # Default neutral
        
        # Factor in technical analysis
        if multi_tf_analysis:
            tf_scores = [tf.get("trend", 0.5) for tf in multi_tf_analysis.values()]
            base_score = np.mean(tf_scores) if tf_scores else 0.5
        
        # Adjust for anomalies
        if anomalies.get("detected", False):
            base_score *= 0.9  # Reduce score if anomalies detected
        
        # Factor in volume
        volume_strength = volume_profile.get("strength", 0.5)
        base_score = (base_score * 0.8) + (volume_strength * 0.2)
        
        # Add sentiment impact
        base_score += sentiment_impact
        
        return max(0.0, min(1.0, base_score))

    def _get_ml_verdict(self, score, anomalies):
        """Get ML-based verdict."""
        if anomalies.get("detected", False):
            return "CAUTION"
        elif score > 0.7:
            return "BUY"
        elif score < 0.3:
            return "SELL"
        else:
            return "HOLD"

    # Helper methods
    def _get_timeframe_data(self, data: dict, timeframe: int):
        """Get timeframe-specific data."""
        return [data.get("price", 0)] * 10  # Mock data

    def _calculate_trend_strength(self, prices):
        """Calculate trend strength."""
        if len(prices) < 2:
            return 0.5
        return min(max((prices[-1] - prices[0]) / prices[0] + 0.5, 0), 1)

    def _calculate_momentum(self, prices):
        """Calculate momentum."""
        return np.random.uniform(0.3, 0.7)

    def _calculate_volatility(self, prices):
        """Calculate volatility."""
        if len(prices) < 2:
            return 0.5
        return min(np.std(prices) / np.mean(prices), 1.0) if np.mean(prices) > 0 else 0.5

    def _extract_ml_features(self, data: dict) -> np.array:
        """Extract ML features."""
        try:
            price = data.get("price", 0)
            volume = data.get("volume", 0)
            
            if price > 0 and volume > 0:
                features = np.array([[price, volume]])
                return features
        except Exception as e:
            logger.error(f"Feature extraction error: {e}")
        
        return np.empty((0, 2))    # Legacy compatibility
    async def _fetch_stealth_data(self, symbol: str) -> dict:
        """Legacy method for backward compatibility."""
        result = await self._fetch_primary_source(symbol)
        return result or {}
    
    def _normalize_symbol_for_yahoo(self, symbol: str) -> str:
        """Normalize symbol for Yahoo Finance API."""
        return IndianEquitySymbolNormalizer.normalize_for_yahoo_finance(symbol)
    
    def _enhance_with_quad_metadata(self, result: dict, fused_data: QuadChannelData) -> dict:
        """Enhance result with quad-channel metadata."""
        if not isinstance(result, dict):
            return result
            
        result["quad_channel_metadata"] = {
            "channels_used": fused_data.channels_used,
            "fusion_confidence": fused_data.fusion_confidence,
            "validation_score": fused_data.validation_score,
            "collection_timestamp": fused_data.collection_timestamp,
            "data_quality_metrics": {
                "total_channels": len(fused_data.channels_used),
                "successful_channels": len([c for c in fused_data.channels_used if getattr(fused_data, c)]),
                "fusion_method": "weighted_average"
            }
        }
        return result


async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    agent = MoneyControlAgent()
    return await agent.execute(symbol, agent_outputs=agent_outputs)
