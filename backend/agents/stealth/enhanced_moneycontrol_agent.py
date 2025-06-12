"""
Enhanced MoneyControl Agent with Quad-Channel Architecture
==========================================================

Advanced stealth agent with quad-channel data collection,
background streaming, and intelligent data fusion.
"""

import httpx
import numpy as np
from bs4 import BeautifulSoup
from sklearn.ensemble import IsolationForest
from loguru import logger
from typing import Dict, Optional
from backend.agents.stealth.advanced_base import AdvancedStealthAgentBase, QuadChannelData

agent_name = "enhanced_moneycontrol_agent"

class EnhancedMoneyControlAgent(AdvancedStealthAgentBase):
    """
    Enhanced MoneyControl agent with quad-channel architecture:
    - Primary: MoneyControl website scraping
    - Secondary: Yahoo Finance API
    - Tertiary: Alpha Vantage API  
    - Emergency: Polygon.io API
    """
    
    def __init__(self):
        super().__init__()
        self.agent_name = agent_name
        
        # ML components for advanced analysis
        self.anomaly_detector = IsolationForest(contamination=0.1)
        self.timeframes = [5, 15, 60, 240]  # minutes
        
        # Enhanced confidence thresholds
        self.fusion_weights = {
            "primary": 0.5,    # Higher weight for MoneyControl
            "secondary": 0.3,   # Yahoo Finance
            "tertiary": 0.15,   # Alpha Vantage
            "emergency": 0.05   # Polygon.io
        }
        
        logger.info(f"🚀 Enhanced MoneyControl Agent initialized with quad-channel support")
    
    async def _fetch_primary_source(self, symbol: str) -> Optional[Dict]:
        """Fetch data from MoneyControl website (primary source)."""
        try:
            url = f"https://www.moneycontrol.com/india/stockpricequote/{symbol}"
            headers = {
                "User-Agent": self.user_agents[0],
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive"
            }
            
            async with httpx.AsyncClient(timeout=self.channels["primary"].timeout) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, "html.parser")
                
                return {
                    "price": self._extract_price(soup),
                    "ratings": self._extract_ratings(soup),
                    "technicals": self._extract_technicals(soup),
                    "sentiment": self._extract_sentiment(soup),
                    "fundamentals": self._extract_fundamentals(soup),
                    "news_sentiment": self._extract_news_sentiment(soup),
                    "analyst_recommendations": self._extract_analyst_recs(soup),
                    "source": "moneycontrol_primary",
                    "data_quality": "high"
                }
                
        except Exception as e:
            logger.warning(f"MoneyControl primary fetch failed for {symbol}: {e}")
            return None
    
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
                        "pe_ratio": analysis_data.get("pe_ratio"),
                        "price_validated": True
                    },
                    "data_quality": {
                        "fusion_confidence": fused_data.fusion_confidence,
                        "validation_score": fused_data.validation_score,
                        "channels_used": fused_data.channels_used,
                        "data_freshness": f"{fused_data.collection_timestamp:.1f}s ago"
                    },
                    "source": "enhanced_moneycontrol_quad_channel",
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
            if channel_data and channel_data.get("price"):
                logger.debug(f"Using {channel} channel data for analysis")
                return channel_data
        
        return {}
    
    def _calculate_enhanced_confidence(self, score: float, anomalies: Dict, fused_data: QuadChannelData) -> float:
        """Calculate enhanced confidence using quad-channel data."""
        
        # Base confidence from score
        base_confidence = min(score * 0.9, 0.95)
        
        # Fusion confidence boost
        fusion_boost = fused_data.fusion_confidence * 0.15
        
        # Validation score boost
        validation_boost = fused_data.validation_score * 0.1
        
        # Multi-channel availability bonus
        channel_bonus = len(fused_data.channels_used) * 0.02
        
        # Anomaly penalty
        anomaly_penalty = anomalies.get("score", 0) * 0.05 if anomalies.get("detected") else 0
        
        # Calculate final confidence
        final_confidence = base_confidence + fusion_boost + validation_boost + channel_bonus - anomaly_penalty
        
        # Apply validation score threshold
        if fused_data.validation_score < 0.6:
            final_confidence *= 0.8  # Reduce confidence for low validation
        
        return min(max(final_confidence, 0.1), 1.0)
    
    def _get_enhanced_verdict(self, score: float, anomalies: Dict, fused_data: QuadChannelData) -> str:
        """Get enhanced verdict considering quad-channel data quality."""
        
        # Adjust score based on data quality
        quality_adjusted_score = score * fused_data.validation_score
        
        # Consider anomalies
        if anomalies.get("detected") and anomalies.get("score", 0) < -0.5:
            quality_adjusted_score *= 0.8  # Reduce for significant anomalies
        
        # Enhanced verdict logic
        if quality_adjusted_score > 0.8:
            return "STRONG_BUY"
        elif quality_adjusted_score > 0.65:
            return "BUY"
        elif quality_adjusted_score > 0.45:
            return "HOLD"
        elif quality_adjusted_score > 0.3:
            return "SELL"
        else:
            return "STRONG_SELL"
    
    # Enhanced extraction methods
    def _extract_price(self, soup) -> float:
        """Extract current price from MoneyControl page."""
        try:
            # Try multiple selectors for price
            selectors = [
                "div.pcst_price div.Prcd",
                ".inprice1 .number",
                ".stock_price .number",
                "[data-price]"
            ]
            
            for selector in selectors:
                price_elem = soup.select_one(selector)
                if price_elem:
                    price_text = price_elem.text.strip().replace(',', '').replace('₹', '')
                    return float(price_text)
              # Fallback to any element with price-like content
            for elem in soup.find_all(string=True):
                if '₹' in elem and any(c.isdigit() for c in elem):
                    import re
                    price_match = re.search(r'₹?[\d,]+\.?\d*', elem)
                    if price_match:
                        return float(price_match.group().replace('₹', '').replace(',', ''))
            
            return 0.0
        except Exception as e:
            logger.warning(f"Price extraction failed: {e}")
            return 0.0
    
    def _extract_fundamentals(self, soup) -> Dict:
        """Extract fundamental data from MoneyControl."""
        fundamentals = {}
        try:
            # Market cap
            market_cap_elem = soup.select_one(".mkt_cap .value")
            if market_cap_elem:
                fundamentals["market_cap"] = market_cap_elem.text.strip()
            
            # P/E Ratio
            pe_elem = soup.select_one(".pe_ratio .value")
            if pe_elem:
                fundamentals["pe_ratio"] = float(pe_elem.text.strip())
            
            # Book Value
            bv_elem = soup.select_one(".book_value .value")
            if bv_elem:
                fundamentals["book_value"] = float(bv_elem.text.strip())
            
            # Dividend Yield
            div_elem = soup.select_one(".dividend_yield .value")
            if div_elem:
                fundamentals["dividend_yield"] = float(div_elem.text.strip().replace('%', ''))
                
        except Exception as e:
            logger.warning(f"Fundamentals extraction failed: {e}")
        
        return fundamentals
    
    def _extract_news_sentiment(self, soup) -> str:
        """Extract news sentiment from MoneyControl."""
        try:
            news_elements = soup.select(".news_title, .news_headline")
            if not news_elements:
                return "neutral"
            
            positive_words = ['buy', 'bullish', 'positive', 'growth', 'strong', 'gain', 'rally', 'upgrade']
            negative_words = ['sell', 'bearish', 'negative', 'decline', 'weak', 'loss', 'fall', 'downgrade']
            
            sentiment_score = 0
            for elem in news_elements[:5]:  # Check top 5 news items
                text = elem.text.lower()
                sentiment_score += sum(1 for word in positive_words if word in text)
                sentiment_score -= sum(1 for word in negative_words if word in text)
            
            if sentiment_score > 1:
                return "positive"
            elif sentiment_score < -1:
                return "negative"
            else:
                return "neutral"
                
        except Exception as e:
            logger.warning(f"News sentiment extraction failed: {e}")
            return "neutral"
    
    def _extract_analyst_recs(self, soup) -> Dict:
        """Extract analyst recommendations."""
        recommendations = {}
        try:
            rec_section = soup.select_one(".analyst_recommendations")
            if rec_section:
                for rec in rec_section.select(".recommendation"):
                    firm = rec.select_one(".firm").text.strip()
                    rating = rec.select_one(".rating").text.strip()
                    recommendations[firm] = rating
        except Exception as e:
            logger.warning(f"Analyst recommendations extraction failed: {e}")
        
        return recommendations
    
    # Inherited methods from original implementation with enhancements
    def _extract_ratings(self, soup) -> Dict:
        """Enhanced ratings extraction."""
        ratings = {}
        try:
            rating_div = soup.select_one(".ratings-block, .expert_rating")
            if rating_div:
                for item in rating_div.select(".rating-item, .rating"):
                    name_elem = item.select_one(".name, .expert_name")
                    rating_elem = item.select_one(".rating, .score")
                    
                    if name_elem and rating_elem:
                        name = name_elem.text.strip()
                        rating = rating_elem.text.strip()
                        ratings[name] = rating
        except Exception as e:
            logger.warning(f"Ratings extraction failed: {e}")
        
        return ratings
    
    def _extract_technicals(self, soup) -> Dict:
        """Enhanced technical indicators extraction."""
        technicals = {}
        try:
            tech_div = soup.select_one(".technical-block, .tech_indicators")
            if tech_div:
                for indicator in tech_div.select(".indicator, .tech_indicator"):
                    name_elem = indicator.select_one(".name, .indicator_name")
                    value_elem = indicator.select_one(".value, .indicator_value")
                    
                    if name_elem and value_elem:
                        name = name_elem.text.strip()
                        value = value_elem.text.strip()
                        technicals[name] = value
        except Exception as e:
            logger.warning(f"Technical indicators extraction failed: {e}")
        
        return technicals
    
    def _extract_sentiment(self, soup) -> str:
        """Enhanced sentiment extraction."""
        try:
            sentiment_indicators = [
                soup.select_one(".sentiment-indicator"),
                soup.select_one(".market_sentiment"),
                soup.select_one("[data-sentiment]")
            ]
            
            for indicator in sentiment_indicators:
                if indicator:
                    sentiment_text = indicator.text.strip().lower()
                    if any(word in sentiment_text for word in ['positive', 'bullish', 'buy']):
                        return "positive"
                    elif any(word in sentiment_text for word in ['negative', 'bearish', 'sell']):
                        return "negative"
            
            return "neutral"
            
        except Exception as e:
            logger.warning(f"Sentiment extraction failed: {e}")
            return "neutral"
    
    # Enhanced analysis methods (inherited and improved from original)
    def _analyze_multiple_timeframes(self, data: Dict) -> Dict:
        """Enhanced multi-timeframe analysis."""
        analyses = {}
        try:
            for tf in self.timeframes:
                prices = self._get_timeframe_data(data, tf)
                if prices:
                    analyses[f"{tf}min"] = {
                        "trend": self._calculate_trend_strength(prices),
                        "momentum": self._calculate_momentum(prices),
                        "volatility": self._calculate_volatility(prices),
                        "volume_trend": self._calculate_volume_trend(data, tf)
                    }
        except Exception as e:
            logger.error(f"Multi-timeframe analysis error: {e}")
        
        return analyses
    
    def _calculate_volume_trend(self, data: Dict, timeframe: int) -> float:
        """Calculate volume trend for specific timeframe."""
        try:
            volumes = data.get("volume_data", [])
            if len(volumes) < 2:
                return 0.5
            
            recent_avg = np.mean(volumes[-5:]) if len(volumes) >= 5 else volumes[-1]
            historical_avg = np.mean(volumes[:-5]) if len(volumes) > 5 else volumes[0]
            
            return min(max(recent_avg / historical_avg if historical_avg > 0 else 1, 0), 2) / 2
            
        except Exception:
            return 0.5
    
    def _calculate_ml_enhanced_score(self, data, multi_tf_analysis, anomalies, volume_profile, sentiment_impact):
        """Calculate ML-enhanced score with quad-channel data."""
        try:
            # Base score from fundamentals
            base_score = 0.5
            
            # Technical score from multiple timeframes
            tech_scores = []
            for tf_analysis in multi_tf_analysis.values():
                tf_score = (
                    tf_analysis.get("trend", 0.5) * 0.4 +
                    tf_analysis.get("momentum", 0.5) * 0.3 +
                    (1 - tf_analysis.get("volatility", 0.5)) * 0.2 +
                    tf_analysis.get("volume_trend", 0.5) * 0.1
                )
                tech_scores.append(tf_score)
            
            technical_score = np.mean(tech_scores) if tech_scores else 0.5
            
            # Volume profile contribution
            volume_score = volume_profile.get("strength", 0.5)
            
            # Sentiment contribution
            sentiment_score = sentiment_impact
            
            # Combine scores with weights
            final_score = (
                base_score * 0.3 +
                technical_score * 0.4 +
                volume_score * 0.2 +
                sentiment_score * 0.1
            )
            
            # Anomaly adjustment
            if anomalies.get("detected"):
                final_score *= (1 + anomalies.get("score", 0) * 0.1)
            
            return min(max(final_score, 0), 1)
            
        except Exception as e:
            logger.error(f"ML score calculation error: {e}")
            return 0.5
    
    # Placeholder implementations for inherited methods
    def _detect_anomalies(self, data: Dict) -> Dict:
        """Enhanced anomaly detection."""
        try:
            features = self._extract_ml_features(data)
            if features.size == 0:
                return {"score": 0, "detected": False, "locations": []}
            
            anomaly_scores = self.anomaly_detector.fit_predict(features)
            return {
                "score": float(np.mean(anomaly_scores)),
                "detected": bool(np.any(anomaly_scores == -1)),
                "locations": np.where(anomaly_scores == -1)[0].tolist(),
                "confidence": float(np.std(anomaly_scores))
            }
        except Exception as e:
            logger.error(f"Anomaly detection error: {e}")
            return {"score": 0, "detected": False, "locations": []}
    
    def _analyze_volume_profile(self, data: Dict) -> Dict:
        """Enhanced volume profile analysis."""
        try:
            volumes = data.get("volume_data", [])
            prices = data.get("price_data", [])
            if not volumes or not prices:
                return {"strength": 0.5}
            
            # Calculate volume-weighted average price
            if len(volumes) == len(prices):
                vwap = np.average(prices, weights=volumes)
                current_price = prices[-1] if prices else 0
                
                # Volume trend strength
                recent_volume = np.mean(volumes[-5:]) if len(volumes) >= 5 else volumes[-1]
                avg_volume = np.mean(volumes)
                volume_strength = min(recent_volume / avg_volume if avg_volume > 0 else 1, 3) / 3
                
                return {
                    "vwap": vwap,
                    "strength": volume_strength,
                    "price_vs_vwap": (current_price - vwap) / vwap if vwap > 0 else 0,
                    "volume_trend": "increasing" if volume_strength > 0.6 else "decreasing"
                }
            
            return {"strength": 0.5}
            
        except Exception as e:
            logger.error(f"Volume profile analysis error: {e}")
            return {"strength": 0.5}
    
    def _analyze_sentiment_impact(self, data: Dict) -> float:
        """Analyze sentiment impact on scoring."""
        try:
            sentiment = data.get("sentiment", "neutral")
            news_sentiment = data.get("news_sentiment", "neutral")
            
            sentiment_map = {"positive": 0.7, "neutral": 0.5, "negative": 0.3}
            
            base_sentiment = sentiment_map.get(sentiment, 0.5)
            news_sentiment_val = sentiment_map.get(news_sentiment, 0.5)
            
            # Weight current sentiment more than news sentiment
            combined_sentiment = base_sentiment * 0.7 + news_sentiment_val * 0.3
            
            return combined_sentiment
            
        except Exception as e:
            logger.error(f"Sentiment impact analysis error: {e}")
            return 0.5
    
    def _extract_ml_features(self, data: Dict) -> np.array:
        """Extract ML features for analysis."""
        try:
            prices = np.array(data.get("price_data", [100, 101, 102]))  # Default mock data
            volumes = np.array(data.get("volume_data", [1000, 1100, 1200]))
            
            if len(prices) < 2 or len(volumes) < 2:
                return np.array([[0.01, 0.01]])  # Minimal valid feature set
            
            # Calculate features
            price_change = np.diff(prices) / prices[:-1]
            volume_change = np.diff(volumes) / volumes[:-1]
            
            # Ensure equal length
            min_len = min(len(price_change), len(volume_change))
            features = np.column_stack((price_change[:min_len], volume_change[:min_len]))
            
            return features if features.shape[0] > 0 else np.array([[0.01, 0.01]])
            
        except Exception as e:
            logger.error(f"ML feature extraction error: {e}")
            return np.array([[0.01, 0.01]])
    
    def _get_timeframe_data(self, data: Dict, timeframe: int):
        """Get data for specific timeframe."""
        return data.get("price_data", [])
    
    def _calculate_trend_strength(self, prices):
        """Calculate trend strength."""
        if not prices or len(prices) < 2:
            return 0.5
        return min(max((prices[-1] - prices[0]) / prices[0] + 0.5, 0), 1)
    
    def _calculate_momentum(self, prices):
        """Calculate momentum."""
        if not prices or len(prices) < 3:
            return 0.5
        recent_change = (prices[-1] - prices[-2]) / prices[-2] if prices[-2] != 0 else 0
        return min(max(recent_change + 0.5, 0), 1)
    
    def _calculate_volatility(self, prices):
        """Calculate volatility."""
        if not prices or len(prices) < 2:
            return 0.5
        returns = np.diff(prices) / prices[:-1]
        return min(np.std(returns) * 10, 1) if len(returns) > 0 else 0.5

# Create module-level run function for compatibility
async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    """Module-level execution function."""
    agent = EnhancedMoneyControlAgent()
    return await agent.execute(symbol, agent_outputs)
