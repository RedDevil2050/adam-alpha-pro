
from backend.utils.data_provider import fetch_ev_ebitda
from loguru import logger

agent_name = "ev_ebitda_agent"

async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    try:
        ev_ebitda = await fetch_ev_ebitda(symbol)
        if not ev_ebitda or ev_ebitda <= 0:
            return {
                "symbol": symbol,
                "verdict": "NO_DATA",
                "confidence": 0.0,
                "value": None,
                "details": {},
                "error": "Missing EV/EBITDA data",
                "agent_name": agent_name
            }

        if ev_ebitda < 10:
            verdict = "BUY"
        elif ev_ebitda <= 18:
            verdict = "HOLD"
        else:
            verdict = "AVOID"

        confidence = max(0.0, 100.0 - ev_ebitda * 3)

        return {
            "symbol": symbol,
            "verdict": verdict,
            "confidence": confidence,
            "value": round(ev_ebitda, 2),
            "details": {},
            "error": None,
            "agent_name": agent_name
        }

    except Exception as e:
        logger.error(f"EV/EBITDA agent error for {symbol}: {e}")
        return {
            "symbol": symbol,
            "verdict": "ERROR",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "error": str(e),
            "agent_name": agent_name
        }
