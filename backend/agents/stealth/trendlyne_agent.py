from backend.agents.stealth.advanced_base import AdvancedStealthAgentBase, QuadChannelData
import httpx
from bs4 import BeautifulSoup
from loguru import logger
from typing import Dict, Optional

agent_name = "trendlyne_agent"


class TrendlyneAgent(AdvancedStealthAgentBase):
    """
    Enhanced TrendLyne agent with quad-channel architecture:
    - Primary: TrendLyne website scraping
    - Secondary: Yahoo Finance API
    - Tertiary: Alpha Vantage API  
    - Emergency: Polygon.io API
    """
    
    def __init__(self):
        super().__init__()
        self.agent_name = agent_name
        
        # Enhanced confidence thresholds for TrendLyne
        self.fusion_weights = {
            "primary": 0.5,    # Higher weight for TrendLyne
            "secondary": 0.3,   # Yahoo Finance
            "tertiary": 0.15,   # Alpha Vantage
            "emergency": 0.05   # Polygon.io
        }
        
        logger.info(f"🚀 Enhanced TrendLyne Agent initialized with quad-channel support")
    
    async def _fetch_primary_source(self, symbol: str) -> Optional[Dict]:
        """Fetch data from TrendLyne website (primary source)."""
        try:
            url = f"https://trendlyne.com/equity/{symbol}/"
            headers = {
                "User-Agent": self.user_agents[0],
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Referer": "https://trendlyne.com/",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
            
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")
                    
                    return {
                        "price": self._extract_price(soup),
                        "technicals": self._extract_technicals(soup),
                        "signals": self._extract_signals(soup),
                        "volume": self._extract_volume(soup),
                        "ratings": self._extract_ratings(soup),
                        "source": "trendlyne_primary"
                    }
                else:
                    logger.warning(f"TrendLyne returned status {response.status_code} for {symbol}")
                    return None
                    
        except Exception as e:
            logger.warning(f"TrendLyne primary fetch failed for {symbol}: {e}")
            return None
    
    async def _execute_analysis(self, symbol: str, agent_outputs: dict, fused_data: QuadChannelData) -> Dict:
        """Execute enhanced analysis using quad-channel fused data."""
        try:
            logger.info(f"🔬 Starting enhanced TrendLyne analysis for {symbol}")
            
            # Extract data from the best available channel
            analysis_data = self._extract_best_data(fused_data)
            
            if not analysis_data:
                return self._error_response(symbol, "No usable data from any channel")
            
            # Calculate enhanced score using quad-channel data
            score = self._calculate_enhanced_score(analysis_data, fused_data)
            verdict = self._get_enhanced_verdict(score, analysis_data)
            
            # Calculate confidence with quad-channel boost
            confidence = self._calculate_enhanced_confidence(score, fused_data)
            
            return {
                "symbol": symbol,
                "verdict": verdict,
                "confidence": confidence,
                "value": round(score, 3),
                "details": {
                    "technicals": analysis_data.get("technicals", {}),
                    "signals": analysis_data.get("signals", []),
                    "ratings": analysis_data.get("ratings", {}),
                    "price_data": {
                        "current_price": analysis_data.get("price"),
                        "volume": analysis_data.get("volume"),
                        "price_validated": True
                    },
                    "data_quality": {
                        "fusion_confidence": fused_data.fusion_confidence,
                        "validation_score": fused_data.validation_score,
                        "channels_used": fused_data.channels_used,
                        "data_freshness": f"{fused_data.collection_timestamp:.1f}s ago"
                    },
                    "source": "enhanced_trendlyne_quad_channel",
                },
                "error": None,
                "agent_name": self.agent_name,
            }
            
        except Exception as e:
            logger.error(f"❌ Enhanced TrendLyne analysis error for {symbol}: {e}")
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
    
    def _calculate_enhanced_score(self, analysis_data: Dict, fused_data: QuadChannelData) -> float:
        """Calculate enhanced score using quad-channel data."""
        base_score = self._calculate_score(analysis_data)
        
        # Fusion confidence boost
        fusion_boost = fused_data.fusion_confidence * 0.1
        
        # Data quality boost
        quality_boost = fused_data.validation_score * 0.05
        
        enhanced_score = min(base_score + fusion_boost + quality_boost, 1.0)
        
        logger.debug(f"Score enhanced: {base_score:.3f} -> {enhanced_score:.3f} (fusion: +{fusion_boost:.3f}, quality: +{quality_boost:.3f})")
        return enhanced_score
    
    def _get_enhanced_verdict(self, score: float, analysis_data: Dict) -> str:
        """Get enhanced verdict considering additional factors."""
        base_verdict = self._get_verdict(score)
        
        # Consider signals for enhancement
        signals = analysis_data.get("signals", [])
        buy_signals = len([s for s in signals if "buy" in s.lower() or "bullish" in s.lower()])
        sell_signals = len([s for s in signals if "sell" in s.lower() or "bearish" in s.lower()])
        
        # Enhance verdict based on signals
        if buy_signals > sell_signals and score > 0.6:
            return "STRONG_BUY" if score > 0.8 else "BUY"
        elif sell_signals > buy_signals and score < 0.4:
            return "STRONG_SELL" if score < 0.2 else "SELL"
        
        return base_verdict
    
    def _calculate_enhanced_confidence(self, score: float, fused_data: QuadChannelData) -> float:
        """Calculate enhanced confidence using quad-channel data."""
        
        # Base confidence from score
        base_confidence = min(score * 0.9, 0.95)
        
        # Fusion confidence boost
        fusion_boost = fused_data.fusion_confidence * 0.15
        
        # Validation score boost
        validation_boost = fused_data.validation_score * 0.1
        
        # Multi-channel bonus
        channel_bonus = len(fused_data.channels_used) * 0.02  # 2% per additional channel
        
        enhanced_confidence = min(
            base_confidence + fusion_boost + validation_boost + channel_bonus, 
            1.0
        )
        
        logger.debug(f"Confidence enhanced: {base_confidence:.3f} -> {enhanced_confidence:.3f}")
        return enhanced_confidence

    async def _execute(self, symbol: str, agent_outputs: dict, validated_data: dict) -> dict:
        try:
            # Use pre-validated dual-channel data instead of fetching again
            if not validated_data:
                return self._error_response(symbol, "No validated data available")

            score = self._calculate_score(validated_data)
            verdict = self._get_verdict(score)
            confidence = score * 0.9  # Base confidence
            
            # Boost confidence if dual-channel data is available
            if validated_data.get("has_dual_channel"):
                confidence = min(confidence * 1.1, 1.0)
                logger.debug(f"📈 Confidence boosted due to dual-channel data: {confidence:.2f}")

            return {
                "symbol": symbol,
                "verdict": verdict,
                "confidence": confidence,
                "value": round(score, 2),
                "details": {
                    "signals": validated_data.get("signals", []),
                    "technicals": validated_data.get("technicals", {}),
                    "price_data": {
                        "current_price": validated_data.get("price"),
                        "price_validated": validated_data.get("price_validated", False)
                    },
                    "data_quality": {
                        "confidence_score": validated_data.get("data_confidence", 0.0),
                        "sources_used": validated_data.get("data_sources", []),
                        "cross_validated": validated_data.get("has_dual_channel", False)
                    },
                    "source": "trendlyne_enhanced",
                },
                "error": None,
                "agent_name": agent_name,
            }

        except Exception as e:
            logger.error(f"❌ Trendlyne enhanced analysis error for {symbol}: {e}")
            return self._error_response(symbol, str(e))

    def _extract_volume(self, soup) -> int:
        """Extract volume from soup."""
        try:
            volume_elem = soup.select_one(".volume-value")
            if volume_elem:
                volume_text = volume_elem.text.strip().replace(",", "")
                return int(float(volume_text))
        except:
            pass
        return 0
    
    def _extract_ratings(self, soup) -> dict:
        """Extract analyst ratings from soup."""
        ratings = {}
        try:
            ratings_div = soup.select_one(".analyst-ratings")
            if ratings_div:
                for rating in ratings_div.select(".rating-item"):
                    analyst = rating.select_one(".analyst-name")
                    rating_val = rating.select_one(".rating-value")
                    if analyst and rating_val:
                        ratings[analyst.text.strip()] = rating_val.text.strip()
        except:
            pass
        return ratings
        
    # Legacy methods for backward compatibility
    async def _fetch_stealth_data(self, symbol: str) -> dict:
        """Legacy method for backward compatibility."""
        result = await self._fetch_primary_source(symbol)
        return result or {}
    
    def _calculate_score(self, data: dict) -> float:
        signals = data.get("signals", [])
        buy_signals = len([s for s in signals if "buy" in s.lower()])
        return min(buy_signals / max(len(signals), 1), 1.0)

    def _get_verdict(self, score: float) -> str:
        if score > 0.7:
            return "STRONG_SIGNALS"
        elif score > 0.4:
            return "MIXED_SIGNALS"
        return "WEAK_SIGNALS"

    def _extract_price(self, soup) -> float:
        try:
            price_elem = soup.select_one(".price-value")
            return float(price_elem.text.strip()) if price_elem else 0.0
        except:
            return 0.0

    def _extract_technicals(self, soup) -> dict:
        technicals = {}
        try:
            tech_table = soup.select_one(".technical-indicators")
            if tech_table:
                for row in tech_table.select("tr"):
                    cols = row.select("td")
                    if len(cols) >= 2:
                        technicals[cols[0].text.strip()] = cols[1].text.strip()
        except:
            pass
        return technicals

    def _extract_signals(self, soup) -> list:
        signals = []
        try:
            signal_div = soup.select_one(".signal-indicators")
            if signal_div:
                signals = [s.text.strip() for s in signal_div.select(".signal")]
        except:
            pass
        return signals


async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    agent = TrendlyneAgent()
    # Pass agent_outputs to execute
    return await agent.execute(symbol, agent_outputs=agent_outputs)
