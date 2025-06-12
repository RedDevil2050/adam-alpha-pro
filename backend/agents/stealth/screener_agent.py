from backend.agents.stealth.advanced_base import AdvancedStealthAgentBase, QuadChannelData
import httpx
import asyncio
import random
import re
from bs4 import BeautifulSoup
from loguru import logger
from typing import Optional, Dict, List

agent_name = "screener_agent"


class ScreenerAgent(AdvancedStealthAgentBase):
    
    def __init__(self):
        super().__init__()
        self.screener_base_url = "https://www.screener.in"
    
    async def _fetch_primary_source(self, symbol: str) -> Optional[Dict]:
        """Fetch from screener.in as primary source with stealth techniques."""
        try:
            headers = {
                "User-Agent": random.choice(self.user_agents),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Referer": "https://www.google.com/",
            }
            
            await asyncio.sleep(random.uniform(0.5, 2.0))
            
            url_patterns = [
                f"{self.screener_base_url}/company/{symbol}/consolidated/",
                f"{self.screener_base_url}/company/{symbol}/",
                f"{self.screener_base_url}/stocks/{symbol}/"
            ]
            
            async with httpx.AsyncClient(timeout=8, headers=headers) as client:
                for url in url_patterns:
                    try:
                        response = await client.get(url)
                        if response.status_code == 200:
                            return await self._parse_screener_page(response, symbol)
                    except Exception as e:
                        logger.warning(f"Screener URL {url} failed: {e}")
                        continue
                        
        except Exception as e:
            logger.warning(f"Screener primary source failed for {symbol}: {e}")
            
        return None
    
    async def _parse_screener_page(self, response: httpx.Response, symbol: str) -> Optional[Dict]:
        """Parse screener.in page for financial data."""
        try:
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract price
            price = self._extract_screener_price(soup)
            
            # Extract financial metrics
            pe_ratio = self._extract_screener_metric(soup, ["P/E", "PE"])
            market_cap = self._extract_screener_metric(soup, ["Market Cap", "Mkt Cap"])
            debt_to_equity = self._extract_screener_metric(soup, ["Debt to equity", "D/E"])
            roe = self._extract_screener_metric(soup, ["ROE", "Return on Equity"])
            
            if price and price > 0:
                return {
                    "price": price,
                    "pe_ratio": pe_ratio,
                    "market_cap": market_cap,
                    "debt_to_equity": debt_to_equity,
                    "roe": roe,
                    "source": "screener_primary"
                }
                
        except Exception as e:
            logger.warning(f"Failed to parse screener page: {e}")
        
        return None
    
    def _extract_screener_price(self, soup) -> Optional[float]:
        """Extract current price from screener page."""
        try:
            # Common price selectors for screener.in
            price_selectors = [
                "#top-ratios .number", ".price", ".current-price",
                "[data-source='price']", ".stock-price"
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
                        
        except Exception as e:
            logger.warning(f"Screener price extraction failed: {e}")
        return None
    
    def _extract_screener_metric(self, soup, metric_names: List[str]) -> Optional[float]:
        """Extract financial metrics from screener page."""
        try:
            for metric_name in metric_names:
                # Look for table rows or divs containing the metric
                elements = soup.find_all(text=re.compile(metric_name, re.IGNORECASE))
                
                for element in elements:
                    parent = element.parent
                    if parent:
                        # Try to find associated value
                        siblings = parent.find_next_siblings()
                        for sibling in siblings[:3]:  # Check next few siblings
                            value_text = sibling.get_text().strip()
                            # Extract numeric value
                            numeric_match = re.search(r'([\d,]+\.?\d*)', value_text)
                            if numeric_match:
                                try:
                                    value = float(numeric_match.group(1).replace(',', ''))
                                    return value
                                except ValueError:
                                    continue
                                    
        except Exception as e:
            logger.warning(f"Screener metric extraction failed: {e}")
        return None
    
    async def _execute_analysis(self, symbol: str, agent_outputs: dict, fused_data: QuadChannelData) -> Dict:
        """Execute screener-specific fundamental analysis."""
        try:
            # Extract data from fused channels
            price = self._extract_best_price(fused_data)
            financial_data = self._extract_financial_metrics(fused_data)
            
            if not price or price <= 0:
                return self._error_response(symbol, "No valid price data from any channel")
            
            # Calculate screener-specific analysis
            fundamental_score = self._calculate_fundamental_score(financial_data)
            verdict = self._get_screener_verdict(fundamental_score, financial_data)
            confidence = self._calculate_screener_confidence(financial_data, fused_data)
            
            return {
                "symbol": symbol,
                "verdict": verdict,
                "confidence": confidence,
                "value": price,
                "details": {
                    "fundamental_analysis": {
                        "fundamental_score": fundamental_score,
                        "pe_ratio": financial_data.get("pe_ratio"),
                        "market_cap": financial_data.get("market_cap"),
                        "debt_to_equity": financial_data.get("debt_to_equity"),
                        "roe": financial_data.get("roe")
                    },
                    "screener_metrics": {
                        "valuation_grade": self._get_valuation_grade(financial_data),
                        "financial_health": self._assess_financial_health(financial_data),
                        "growth_potential": self._assess_growth_potential(financial_data)
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
            logger.error(f"❌ Screener analysis error for {symbol}: {e}")
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
    
    def _extract_financial_metrics(self, fused_data: QuadChannelData) -> Dict:
        """Extract financial metrics from all channels."""
        metrics = {}
        
        for channel in ["primary", "secondary", "tertiary", "emergency"]:
            channel_data = getattr(fused_data, channel)
            if channel_data:
                for metric in ["pe_ratio", "market_cap", "debt_to_equity", "roe"]:
                    if metric in channel_data and channel_data[metric] is not None:
                        metrics[metric] = channel_data[metric]
        
        return metrics
    
    def _calculate_fundamental_score(self, financial_data: Dict) -> float:
        """Calculate fundamental analysis score based on screener metrics."""
        score = 0.5  # Base score
        
        # PE ratio scoring
        pe_ratio = financial_data.get("pe_ratio")
        if pe_ratio:
            if 5 <= pe_ratio <= 15:
                score += 0.2
            elif 15 < pe_ratio <= 25:
                score += 0.1
            elif pe_ratio > 40:
                score -= 0.2
        
        # ROE scoring
        roe = financial_data.get("roe")
        if roe:
            if roe > 20:
                score += 0.2
            elif roe > 15:
                score += 0.15
            elif roe > 10:
                score += 0.1
            elif roe < 5:
                score -= 0.1
        
        # Debt to equity scoring
        debt_to_equity = financial_data.get("debt_to_equity")
        if debt_to_equity is not None:
            if debt_to_equity < 0.3:
                score += 0.1
            elif debt_to_equity > 1.0:
                score -= 0.15
        
        return max(0.0, min(1.0, score))
    
    def _get_screener_verdict(self, fundamental_score: float, financial_data: Dict) -> str:
        """Get verdict based on fundamental analysis."""
        if fundamental_score >= 0.8:
            return "STRONG_BUY"
        elif fundamental_score >= 0.65:
            return "BUY"
        elif fundamental_score >= 0.45:
            return "HOLD"
        else:
            return "WEAK_FUNDAMENTALS"
    
    def _calculate_screener_confidence(self, financial_data: Dict, fused_data: QuadChannelData) -> float:
        """Calculate confidence based on data completeness and quality."""
        base_confidence = 0.6
        
        # Data completeness boost
        key_metrics = ["pe_ratio", "market_cap", "roe", "debt_to_equity"]
        available_metrics = sum(1 for metric in key_metrics if financial_data.get(metric) is not None)
        completeness_boost = (available_metrics / len(key_metrics)) * 0.2
        
        # Quad-channel boost
        quad_boost = len(fused_data.channels_used) * 0.05
        
        return min(1.0, base_confidence + completeness_boost + quad_boost)
    
    def _get_valuation_grade(self, financial_data: Dict) -> str:
        """Assign valuation grade based on PE ratio."""
        pe_ratio = financial_data.get("pe_ratio")
        if not pe_ratio:
            return "Unknown"
        elif pe_ratio < 10:
            return "Undervalued"
        elif pe_ratio < 20:
            return "Fair"
        elif pe_ratio < 30:
            return "Expensive"
        else:
            return "Overvalued"
    
    def _assess_financial_health(self, financial_data: Dict) -> str:
        """Assess overall financial health."""
        debt_to_equity = financial_data.get("debt_to_equity")
        roe = financial_data.get("roe")
        
        if debt_to_equity is not None and debt_to_equity < 0.3 and roe and roe > 15:
            return "Excellent"
        elif debt_to_equity is not None and debt_to_equity < 0.6 and roe and roe > 10:
            return "Good"
        elif debt_to_equity is not None and debt_to_equity > 1.0:
            return "Poor"
        else:
            return "Average"
    
    def _assess_growth_potential(self, financial_data: Dict) -> str:
        """Assess growth potential based on available metrics."""
        roe = financial_data.get("roe")
        
        if roe and roe > 20:
            return "High"
        elif roe and roe > 15:
            return "Medium"
        elif roe and roe > 10:
            return "Low"
        else:
            return "Unknown"


async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    agent = ScreenerAgent()
    return await agent.execute(symbol, agent_outputs=agent_outputs)
