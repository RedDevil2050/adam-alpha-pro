from backend.agents.stealth.advanced_base import AdvancedStealthAgentBase, QuadChannelData
import httpx
import asyncio
import random
from bs4 import BeautifulSoup
import lxml  # Faster parser
from loguru import logger
from typing import Optional, Dict, List

agent_name = "zerodha_agent"


class ZerodhaAgent(AdvancedStealthAgentBase):
    async def _fetch_primary_source(self, symbol: str) -> Optional[Dict]:
        """Fetch data from Zerodha primary source with stealth scraping."""
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
                # Try Zerodha Coin/Kite URL patterns
                urls = [
                    f"https://kite.zerodha.com/static/build/instruments.csv",  # Instruments data
                    f"https://coin.zerodha.com/funds/{symbol}",  # Mutual fund data
                    f"https://zerodha.com/z-connect/traders-toolkit/{symbol.lower()}"  # General info
                ]
                
                for url in urls:
                    try:
                        response = await client.get(url)
                        if response.status_code == 200:
                            # Try to extract data based on content type
                            if "csv" in url:
                                return self._parse_zerodha_csv_data(response.text, symbol)
                            else:
                                soup = BeautifulSoup(response.text, "html.parser")
                                return self._extract_zerodha_web_data(soup, symbol)
                    except Exception as e:
                        logger.debug(f"Zerodha URL {url} failed: {e}")
                        continue
                        
            # Fallback to general Zerodha page
            url = f"https://zerodha.com"
            response = await client.get(url)
            if response.status_code == 200:
                return {
                    "price": None,  # Zerodha typically doesn't show live prices on main site
                    "platform_data": "zerodha_accessible",
                    "source": "zerodha_primary"
                }
                        
        except Exception as e:
            logger.warning(f"Zerodha primary source failed for {symbol}: {e}")
            return None
        
        return None
    
    def _parse_zerodha_csv_data(self, csv_content: str, symbol: str) -> Optional[Dict]:
        """Parse Zerodha CSV instruments data."""
        try:
            lines = csv_content.strip().split('\n')
            if len(lines) < 2:
                return None
                
            # Find symbol in CSV data
            for line in lines[1:]:  # Skip header
                if symbol.upper() in line.upper():
                    parts = line.split(',')
                    if len(parts) > 3:
                        return {
                            "instrument_token": parts[0] if len(parts) > 0 else None,
                            "exchange_token": parts[1] if len(parts) > 1 else None,
                            "tradingsymbol": parts[2] if len(parts) > 2 else symbol,
                            "name": parts[3] if len(parts) > 3 else None,
                            "exchange": parts[5] if len(parts) > 5 else "NSE",
                            "source": "zerodha_csv"
                        }
            
            # If symbol not found, return basic data
            return {
                "tradingsymbol": symbol,
                "exchange": "NSE",
                "source": "zerodha_csv_fallback"
            }
            
        except Exception as e:
            logger.warning(f"Zerodha CSV parsing failed: {e}")
            return None
    
    def _extract_zerodha_web_data(self, soup, symbol: str) -> Optional[Dict]:
        """Extract data from Zerodha web pages."""
        try:
            # Extract basic information from Zerodha pages
            title = soup.find('title')
            title_text = title.get_text() if title else ""
            
            # Look for any price or financial data
            price_elements = soup.find_all(text=lambda t: t and '₹' in str(t))
            price = None
            
            if price_elements:
                for price_text in price_elements:
                    try:
                        # Extract numeric value from text containing ₹
                        import re
                        price_match = re.search(r'₹\s*(\d+(?:,\d{3})*(?:\.\d{2})?)', str(price_text))
                        if price_match:
                            price = float(price_match.group(1).replace(',', ''))
                            break
                    except:
                        continue
            
            return {
                "price": price,
                "page_title": title_text,
                "platform_status": "accessible",
                "source": "zerodha_web"
            }
            
        except Exception as e:
            logger.warning(f"Zerodha web data extraction failed: {e}")
            return None

    async def _execute_analysis(self, symbol: str, agent_outputs: dict, fused_data: QuadChannelData) -> Dict:
        """Execute Zerodha-specific analysis with quad-channel fused data."""
        try:
            # Extract data from fused channels
            price = self._extract_best_price(fused_data)
            platform_data = self._extract_platform_data(fused_data)
            instrument_data = self._extract_instrument_data(fused_data)
            
            # Calculate Zerodha-specific score
            score = self._calculate_zerodha_score(price, platform_data, instrument_data, fused_data)
            verdict = self._get_zerodha_verdict(score)
            
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
                    "platform_analysis": {
                        "zerodha_accessible": platform_data.get("accessible", False),
                        "instrument_available": bool(instrument_data),
                        "price_data": price
                    },
                    "instrument_info": instrument_data,
                    "zerodha_metrics": {
                        "tradability_score": self._calculate_tradability_score(instrument_data),
                        "platform_score": self._calculate_platform_score(platform_data),
                        "data_availability": len([d for d in [price, platform_data, instrument_data] if d])
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
            logger.error(f"❌ Zerodha quad-channel analysis error for {symbol}: {e}")
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
    
    def _extract_platform_data(self, fused_data: QuadChannelData) -> Dict:
        """Extract platform accessibility data."""
        platform_data = {"accessible": False, "sources": []}
        
        for channel in ["primary", "secondary", "tertiary", "emergency"]:
            channel_data = getattr(fused_data, channel)
            if channel_data:
                if channel_data.get("platform_status") == "accessible":
                    platform_data["accessible"] = True
                if channel_data.get("platform_data"):
                    platform_data["platform_data"] = channel_data.get("platform_data")
                platform_data["sources"].append(channel_data.get("source", channel))
        
        return platform_data
    
    def _extract_instrument_data(self, fused_data: QuadChannelData) -> Dict:
        """Extract instrument and trading data."""
        instrument_data = {}
        
        for channel in ["primary", "secondary", "tertiary", "emergency"]:
            channel_data = getattr(fused_data, channel)
            if channel_data:
                # Merge instrument data from all sources
                for key in ["instrument_token", "exchange_token", "tradingsymbol", "name", "exchange"]:
                    if key in channel_data and channel_data[key]:
                        instrument_data[key] = channel_data[key]
        
        return instrument_data
    
    def _calculate_zerodha_score(self, price: Optional[float], platform_data: Dict, 
                                instrument_data: Dict, fused_data: QuadChannelData) -> float:
        """Calculate Zerodha-specific scoring with quad-channel data."""
        score = 0.4  # Base score
        
        # Platform accessibility bonus
        if platform_data.get("accessible"):
            score += 0.2
        
        # Instrument data availability bonus
        if instrument_data:
            score += 0.1
            if instrument_data.get("instrument_token"):
                score += 0.1  # Instrument token available = tradable on Zerodha
        
        # Price data bonus
        if price and price > 0:
            score += 0.15
        
        # Data quality bonus from quad-channel
        quality_bonus = fused_data.validation_score * 0.1
        score += quality_bonus
        
        # Multi-source verification bonus
        source_bonus = min(len(fused_data.channels_used) * 0.02, 0.08)
        score += source_bonus
        
        return max(0.0, min(1.0, score))
    
    def _calculate_tradability_score(self, instrument_data: Dict) -> float:
        """Calculate how tradable the instrument is on Zerodha platform."""
        score = 0.5
        
        if instrument_data.get("instrument_token"):
            score += 0.3  # Has instrument token = definitely tradable
        if instrument_data.get("exchange") in ["NSE", "BSE"]:
            score += 0.2  # Listed on major exchanges
        if instrument_data.get("tradingsymbol"):
            score += 0.1  # Has trading symbol
            
        return min(1.0, score)
    
    def _calculate_platform_score(self, platform_data: Dict) -> float:
        """Calculate platform accessibility score."""
        score = 0.3
        
        if platform_data.get("accessible"):
            score += 0.4
        if len(platform_data.get("sources", [])) > 1:
            score += 0.2  # Multiple sources confirm accessibility
        if platform_data.get("platform_data"):
            score += 0.1
            
        return min(1.0, score)
    
    def _get_zerodha_verdict(self, score: float) -> str:
        """Get Zerodha-specific verdict based on score."""
        if score >= 0.8:
            return "FULLY_TRADABLE"
        elif score >= 0.65:
            return "TRADABLE"
        elif score >= 0.5:
            return "LIKELY_TRADABLE"
        elif score >= 0.35:
            return "LIMITED_ACCESS"
        else:
            return "NOT_ACCESSIBLE"


async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    agent = ZerodhaAgent()
    return await agent.execute(symbol, agent_outputs=agent_outputs)
