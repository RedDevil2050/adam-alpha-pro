from backend.agents.stealth.base import StealthAgentBase
import httpx
from bs4 import BeautifulSoup
from loguru import logger

agent_name = "zerodha_agent"

class ZerodhaAgent(StealthAgentBase):
    async def _execute(self, symbol: str, agent_outputs: dict) -> dict:
        try:
            data = await self._fetch_stealth_data(symbol)
            if not data:
                return self._error_response(symbol, "No data available")
            
            score = self._analyze_data(data)
            verdict = self._get_verdict(score)
            confidence = min(score * 0.85, 1.0)  # Cap confidence due to data reliability

            return {
                "symbol": symbol,
                "verdict": verdict,
                "confidence": confidence,
                "value": round(score, 2),
                "details": {
                    "metrics": data.get("metrics", {}),
                    "margins": data.get("margins", {}),
                    "source": "zerodha"
                },
                "error": None,
                "agent_name": agent_name
            }

        except Exception as e:
            logger.error(f"Zerodha scraping error: {e}")
            return self._error_response(symbol, str(e))

    async def _fetch_stealth_data(self, symbol: str) -> dict:
        url = f"https://kite.zerodha.com/quote/{symbol}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            return {
                "metrics": self._extract_metrics(soup),
                "margins": self._extract_margins(soup)
            }

    def _analyze_data(self, data: dict) -> float:
        metrics = data.get("metrics", {})
        margins = data.get("margins", {})
        
        # Calculate composite score based on available metrics
        score_components = []
        
        if "delivery_percentage" in metrics:
            del_pct = float(metrics["delivery_percentage"].strip("%"))
            score_components.append(min(del_pct / 70, 1.0))
            
        if "margin_required" in margins:
            margin = float(margins["margin_required"].replace(",", ""))
            score_components.append(1.0 if margin < 100000 else 0.5)
            
        return sum(score_components) / max(len(score_components), 1)

    def _get_verdict(self, score: float) -> str:
        if score > 0.7:
            return "FAVORABLE_CONDITIONS"
        elif score > 0.4:
            return "NEUTRAL_CONDITIONS"
        return "UNFAVORABLE_CONDITIONS"

    def _extract_metrics(self, soup) -> dict:
        metrics = {}
        try:
            metrics_div = soup.select_one('.market-metrics')
            if metrics_div:
                for row in metrics_div.select('.metric-row'):
                    label = row.select_one('.label').text.strip()
                    value = row.select_one('.value').text.strip()
                    metrics[label.lower().replace(" ", "_")] = value
        except Exception:
            pass
        return metrics

    def _extract_margins(self, soup) -> dict:
        margins = {}
        try:
            margin_div = soup.select_one('.margin-details')
            if margin_div:
                for row in margin_div.select('.margin-row'):
                    label = row.select_one('.label').text.strip()
                    value = row.select_one('.value').text.strip()
                    margins[label.lower().replace(" ", "_")] = value
        except Exception:
            pass
        return margins

async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    agent = ZerodhaAgent()
    return await agent.execute(symbol, agent_outputs)
