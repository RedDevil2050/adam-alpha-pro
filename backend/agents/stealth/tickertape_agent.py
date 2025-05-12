from backend.agents.stealth.base import StealthAgentBase
import httpx
from bs4 import BeautifulSoup
from loguru import logger

agent_name = "tickertape_agent"


class TickertapeAgent(StealthAgentBase):
    async def _execute(self, symbol: str, agent_outputs: dict) -> dict:
        try:
            data = await self._fetch_stealth_data(symbol)
            if not data:
                return await self._error_response(symbol, "No data available")

            score = self._calculate_score(data)
            verdict = self._get_verdict(score)
            confidence = score * 0.85  # Conservative confidence due to data source

            return {
                "symbol": symbol,
                "verdict": verdict,
                "confidence": confidence,
                "value": round(score, 2),
                "details": data,
                "error": None,
                "agent_name": agent_name,
            }

        except Exception as e:
            logger.error(f"Tickertape scraping error: {e}")
            return await self._error_response(symbol, str(e))

    async def _fetch_stealth_data(self, symbol: str) -> dict:
        url = f"https://www.tickertape.in/stocks/{symbol}"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
        soup = BeautifulSoup(resp.text, "html.parser")

        return {
            "ratios": self._extract_ratios(soup),
            "recommendations": self._extract_recommendations(soup),
            "source": "tickertape",
        }

    def _calculate_score(self, data: dict) -> float:
        recs = data.get("recommendations", [])
        buy_count = len([r for r in recs if "buy" in r.lower()])
        if not recs:
            return 0.5
        return buy_count / len(recs)

    def _get_verdict(self, score: float) -> str:
        if score > 0.7:
            return "BULLISH_CONSENSUS"
        elif score > 0.4:
            return "MIXED_CONSENSUS"
        return "BEARISH_CONSENSUS"

    def _extract_ratios(self, soup) -> dict:
        ratios = {}
        try:
            ratio_div = soup.select_one(".key-ratios")
            if ratio_div:
                for item in ratio_div.select(".ratio-item"):
                    label = item.select_one(".label").text.strip()
                    value = item.select_one(".value").text.strip()
                    ratios[label] = value
        except:
            pass
        return ratios

    def _extract_recommendations(self, soup) -> list:
        recs = []
        try:
            rec_div = soup.select_one(".analyst-recommendations")
            if rec_div:
                recs = [r.text.strip() for r in rec_div.select(".recommendation")]
        except:
            pass
        return recs

    async def execute(self, symbol: str, agent_outputs: dict = {}) -> dict:
        """Public method to execute the agent's logic."""
        return await self._execute(symbol, agent_outputs)


async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    agent = TickertapeAgent()
    # Pass agent_outputs to execute
    return await agent.execute(symbol, agent_outputs=agent_outputs)
