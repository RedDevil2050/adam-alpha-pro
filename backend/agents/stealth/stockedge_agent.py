from backend.agents.stealth.base import StealthAgentBase
import httpx
from bs4 import BeautifulSoup
from loguru import logger

agent_name = "stockedge_agent"


class StockEdgeAgent(StealthAgentBase):
    async def _execute(self, symbol: str, agent_outputs: dict, validated_data: dict) -> dict:
        try:
            # Use pre-validated dual-channel data instead of fetching again
            if not validated_data:
                return self._error_response(symbol, "No validated data available")

            score = self._analyze_scores(validated_data)
            verdict = self._get_verdict(score)
            confidence = score * 0.8  # Base confidence
            
            # Boost confidence if dual-channel data is available
            if validated_data.get("has_dual_channel"):
                confidence = min(confidence * 1.15, 1.0)
                logger.debug(f"📈 Confidence boosted due to dual-channel data: {confidence:.2f}")

            return {
                "symbol": symbol,
                "verdict": verdict,
                "confidence": confidence,
                "value": round(score, 2),
                "details": {
                    "quality_score": validated_data.get("quality_score", 50),
                    "technicals": validated_data.get("technicals", {}),
                    "metrics": validated_data.get("metrics", {}),
                    "price_data": {
                        "current_price": validated_data.get("price"),
                        "price_validated": validated_data.get("price_validated", False)
                    },
                    "data_quality": {
                        "confidence_score": validated_data.get("data_confidence", 0.0),
                        "sources_used": validated_data.get("data_sources", []),
                        "cross_validated": validated_data.get("has_dual_channel", False)
                    },
                    "source": "stockedge_enhanced",
                },
                "error": None,
                "agent_name": agent_name,
            }

        except Exception as e:
            logger.error(f"❌ StockEdge enhanced analysis error for {symbol}: {e}")
            return self._error_response(symbol, str(e))

    async def _fetch_stealth_data(self, symbol: str) -> dict:
        url = f"https://web.stockedge.com/share/{symbol}/overview"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
        soup = BeautifulSoup(resp.text, "html.parser")

        return {
            "quality_score": self._extract_quality_score(soup),
            "technicals": self._extract_technicals(soup),
            "metrics": self._extract_key_metrics(soup),
            "source": "stockedge",
        }

    def _analyze_scores(self, data: dict) -> float:
        quality = data.get("quality_score", 50) / 100
        tech_score = self._calculate_technical_score(data.get("technicals", {}))
        return (quality + tech_score) / 2

    def _get_verdict(self, score: float) -> str:
        if score > 0.7:
            return "HIGH_QUALITY"
        elif score > 0.4:
            return "AVERAGE_QUALITY"
        return "LOW_QUALITY"

    def _extract_quality_score(self, soup) -> float:
        try:
            score_elem = soup.select_one(".quality-score")
            return float(score_elem.text.strip()) if score_elem else 50.0
        except:
            return 50.0

    def _extract_technicals(self, soup) -> dict:
        technicals = {}
        try:
            tech_div = soup.select_one(".technical-indicators")
            if tech_div:
                for indicator in tech_div.select(".indicator"):
                    name = indicator.select_one(".name").text.strip()
                    value = indicator.select_one(".value").text.strip()
                    technicals[name] = value
        except:
            pass
        return technicals

    def _extract_key_metrics(self, soup) -> dict:
        metrics = {}
        try:
            metrics_div = soup.select_one(".key-metrics")
            if metrics_div:
                for metric in metrics_div.select(".metric"):
                    name = metric.select_one(".name").text.strip()
                    value = metric.select_one(".value").text.strip()
                    metrics[name] = value
        except:
            pass
        return metrics

    def _calculate_technical_score(self, technicals: dict) -> float:
        positive_signals = len([v for v in technicals.values() if "buy" in v.lower()])
        total_signals = len(technicals) or 1
        return positive_signals / total_signals

    async def execute(self, symbol: str, agent_outputs: dict = {}) -> dict:
        """Public method to execute the agent's logic."""
        return await self._execute(symbol, agent_outputs)


async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    agent = StockEdgeAgent()
    # Pass agent_outputs to execute
    return await agent.execute(symbol, agent_outputs=agent_outputs)
