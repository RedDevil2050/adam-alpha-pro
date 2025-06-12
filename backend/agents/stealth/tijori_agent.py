from backend.agents.stealth.base import StealthAgentBase
from backend.utils.data_provider import fetch_price_alpha_vantage
import httpx
from bs4 import BeautifulSoup
from loguru import logger

agent_name = "tijori_agent"


class TijoriAgent(StealthAgentBase):
    async def _execute(self, symbol: str, agent_outputs: dict, validated_data: dict) -> dict:
        try:
            # Use pre-validated dual-channel data instead of manual fetching
            if not validated_data:
                return self._error_response(symbol, "No validated data available")

            # Extract price from validated data
            price = validated_data.get("price")
            if not price or not isinstance(price, (int, float)) or price <= 0:
                return self._error_response(symbol, "No valid price data available")

            # Calculate verdict and confidence
            verdict = self._get_verdict(price)
            confidence = self._calculate_confidence(price)
            
            # Boost confidence if dual-channel data is available
            if validated_data.get("has_dual_channel"):
                confidence = min(confidence * 1.08, 1.0)
                logger.debug(f"📈 Confidence boosted due to dual-channel data: {confidence:.2f}")

            return {
                "symbol": symbol,
                "verdict": verdict,
                "confidence": confidence,
                "value": price,
                "details": {
                    "price_data": {
                        "current_price": price,
                        "price_validated": validated_data.get("price_validated", False)
                    },
                    "data_quality": {
                        "confidence_score": validated_data.get("data_confidence", 0.0),
                        "sources_used": validated_data.get("data_sources", []),
                        "cross_validated": validated_data.get("has_dual_channel", False)
                    },
                    "source": "tijori_enhanced",
                },
                "error": None,
                "agent_name": agent_name
            }

        except Exception as e:
            logger.error(f"❌ Tijori enhanced analysis error for {symbol}: {e}")
            return self._error_response(symbol, str(e))

    async def _fetch_stealth_data(self, symbol: str) -> dict:
        url = f"https://www.tijorifinance.com/stock/{symbol.lower()}/"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            price_elem = soup.find("span", class_="price-text")
            if price_elem:
                try:
                    price = float(price_elem.text.replace(",", "").strip())
                    return {"price": price}
                except (ValueError, TypeError):
                    pass
        return {}

    def _get_verdict(self, price: float) -> str:
        if price > 200:
            return "STRONG_BUY"
        elif price > 100:
            return "BUY"
        return "HOLD"

    def _calculate_confidence(self, price: float) -> float:
        return round(min(price / 200, 1.0), 2)

    async def execute(self, symbol: str, agent_outputs: dict = {}) -> dict:
        """Public method to execute the agent's logic."""
        return await self._execute(symbol, agent_outputs)


async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    agent = TijoriAgent()
    return await agent.execute(symbol, agent_outputs=agent_outputs)
