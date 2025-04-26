from backend.agents.stealth.base import StealthAgentBase
import httpx
from bs4 import BeautifulSoup
from loguru import logger

agent_name = "trendlyne_agent"

class TrendlyneAgent(StealthAgentBase):
    async def _execute(self, symbol: str, agent_outputs: dict) -> dict:
        try:
            data = await self._fetch_stealth_data(symbol)
            if not data:
                return self._error_response(symbol, "No data available")

            score = self._calculate_score(data)
            verdict = self._get_verdict(score)
            confidence = score * 0.9  # Reduce confidence due to data reliability

            return {
                "symbol": symbol,
                "verdict": verdict,
                "confidence": confidence,
                "value": round(score, 2),
                "details": data,
                "error": None,
                "agent_name": agent_name
            }

        except Exception as e:
            logger.error(f"Trendlyne scraping error: {e}")
            return self._error_response(symbol, str(e))

    async def _fetch_stealth_data(self, symbol: str) -> dict:
        url = f"https://trendlyne.com/equity/{symbol}/"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        return {
            "price": self._extract_price(soup),
            "technicals": self._extract_technicals(soup),
            "signals": self._extract_signals(soup),
            "source": "trendlyne"
        }
    
    def _calculate_score(self, data: dict) -> float:
        signals = data.get('signals', [])
        buy_signals = len([s for s in signals if 'buy' in s.lower()])
        return min(buy_signals / max(len(signals), 1), 1.0)

    def _get_verdict(self, score: float) -> str:
        if score > 0.7:
            return "STRONG_SIGNALS"
        elif score > 0.4:
            return "MIXED_SIGNALS"
        return "WEAK_SIGNALS"

    def _extract_price(self, soup) -> float:
        try:
            price_elem = soup.select_one('.price-value')
            return float(price_elem.text.strip()) if price_elem else 0.0
        except:
            return 0.0

    def _extract_technicals(self, soup) -> dict:
        technicals = {}
        try:
            tech_table = soup.select_one('.technical-indicators')
            if tech_table:
                for row in tech_table.select('tr'):
                    cols = row.select('td')
                    if len(cols) >= 2:
                        technicals[cols[0].text.strip()] = cols[1].text.strip()
        except:
            pass
        return technicals

    def _extract_signals(self, soup) -> list:
        signals = []
        try:
            signal_div = soup.select_one('.signal-indicators')
            if signal_div:
                signals = [s.text.strip() for s in signal_div.select('.signal')]
        except:
            pass
        return signals

async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    agent = TrendlyneAgent()
    return await agent.execute(symbol, agent_outputs)
