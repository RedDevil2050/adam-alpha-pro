from backend.agents.stealth.base import StealthAgentBase
import httpx
from bs4 import BeautifulSoup
import lxml  # Faster parser
from loguru import logger

agent_name = "zerodha_agent"


class ZerodhaAgent(StealthAgentBase):
    async def execute(self, symbol: str, agent_outputs: dict = {}) -> dict:  # Modified signature
        return await self._execute(symbol, agent_outputs=agent_outputs) # Pass agent_outputs

    async def _execute(self, symbol: str, agent_outputs: dict) -> dict:
        try:
            data = await self._fetch_stealth_data(symbol)
            if not data:
                return self._error_response(symbol, "No data available")

            score = self._analyze_data(data)
            verdict = self._get_verdict(score)
            confidence = min(
                score * 0.85, 1.0
            )  # Cap confidence due to data reliability

            return {
                "symbol": symbol,
                "verdict": verdict,
                "confidence": confidence,
                "value": round(score, 2),
                "details": {
                    "metrics": data.get("metrics", {}),
                    "margins": data.get("margins", {}),
                    "source": "zerodha",
                },
                "error": None,
                "agent_name": agent_name,
            }

        except Exception as e:
            logger.error(f"Zerodha scraping error: {e}")
            return self._error_response(symbol, str(e))

    async def _fetch_stealth_data(self, symbol: str) -> dict:
        url = f"https://kite.zerodha.com/quote/{symbol}"
        headers = {"User-Agent": "Mozilla/5.0"}
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, headers=headers)
            soup = BeautifulSoup(response.text, "lxml")

            return {
                "metrics": self._extract_metrics(soup),
                "margins": self._extract_margins(soup),
            }

    def _analyze_data(self, data: dict) -> float:
        metrics = data.get("metrics", {})
        margins = data.get("margins", {})

        # Use list comprehension for better performance
        score_components = [
            (
                min(float(metrics["delivery_percentage"].strip("%")) / 70, 1.0)
                if "delivery_percentage" in metrics
                else None
            ),
            (
                1.0
                if float(margins.get("margin_required", "0").replace(",", "")) < 100000
                else 0.5 if "margin_required" in margins else None
            ),
        ]

        # Filter None values and calculate average
        valid_scores = [s for s in score_components if s is not None]
        return sum(valid_scores) / max(len(valid_scores), 1)

    def _get_verdict(self, score: float) -> str:
        if score > 0.7:
            return "FAVORABLE_CONDITIONS"
        elif score > 0.4:
            return "NEUTRAL_CONDITIONS"
        return "UNFAVORABLE_CONDITIONS"

    def _extract_metrics(self, soup) -> dict:
        metrics = {}
        try:
            # Use CSS selector once and cache results
            metrics_div = soup.select_one(".market-metrics")
            if metrics_div:
                # Use dictionary comprehension for better performance
                metrics = {
                    row.select_one(".label")
                    .text.strip()
                    .lower()
                    .replace(" ", "_"): row.select_one(".value")
                    .text.strip()
                    for row in metrics_div.select(".metric-row")
                    if row.select_one(".label") and row.select_one(".value")
                }
        except Exception as e:
            logger.warning(f"Metrics extraction failed: {e}")
        return metrics

    def _extract_margins(self, soup) -> dict:
        margins = {}
        try:
            # Use CSS selector once and cache results
            margin_div = soup.select_one(".margin-details")
            if margin_div:
                # Use dictionary comprehension for better performance
                margins = {
                    row.select_one(".label")
                    .text.strip()
                    .lower()
                    .replace(" ", "_"): row.select_one(".value")
                    .text.strip()
                    for row in margin_div.select(".margin-row")
                    if row.select_one(".label") and row.select_one(".value")
                }
        except Exception as e:
            logger.warning(f"Margins extraction failed: {e}")
        return margins


async def run(symbol: str, agent_outputs: dict = {}) -> dict:  # Modified signature
    agent = ZerodhaAgent()
    return await agent.execute(symbol, agent_outputs=agent_outputs) # Modified call
