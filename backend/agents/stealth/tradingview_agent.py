from backend.agents.stealth.base import StealthAgentBase
import httpx, numpy as np
from bs4 import BeautifulSoup
import talib
from loguru import logger

agent_name = "tradingview_agent"

class TradingViewAgent(StealthAgentBase):
    async def _execute(self, symbol: str, agent_outputs: dict) -> dict:
        try:
            data = await self._fetch_stealth_data(symbol)
            if not data:
                return self._error_response(symbol, "No data available")

            # Advanced technical analysis
            candlestick_patterns = self._analyze_candlestick_patterns(data)
            fibonacci_levels = self._calculate_fibonacci_levels(data)
            pivot_points = self._calculate_pivot_points(data)
            elliott_waves = self._detect_elliott_waves(data)
            
            # Enhanced signal processing
            signals = self._process_advanced_signals(
                data, candlestick_patterns, 
                fibonacci_levels, pivot_points,
                elliott_waves
            )
            
            confidence = self._calculate_weighted_confidence(signals)
            verdict = self._get_advanced_verdict(signals)

            return {
                "symbol": symbol,
                "verdict": verdict,
                "confidence": confidence,
                "value": round(signals["composite_score"], 2),
                "details": {
                    "technical_indicators": signals["indicators"],
                    "candlestick_patterns": candlestick_patterns,
                    "fibonacci_levels": fibonacci_levels,
                    "elliott_wave_position": elliott_waves,
                    "pivot_points": pivot_points,
                    "source": "tradingview"
                },
                "error": None,
                "agent_name": agent_name
            }

        except Exception as e:
            logger.error(f"TradingView advanced analysis error: {e}")
            return self._error_response(symbol, str(e))

    def _analyze_candlestick_patterns(self, data: dict) -> dict:
        try:
            highs = np.array(data.get("highs", []))
            lows = np.array(data.get("lows", []))
            opens = np.array(data.get("opens", []))
            closes = np.array(data.get("closes", []))
            
            patterns = {
                "doji": talib.CDLDOJI(opens, highs, lows, closes),
                "engulfing": talib.CDLENGULFING(opens, highs, lows, closes),
                "morning_star": talib.CDLMORNINGSTAR(opens, highs, lows, closes),
                "evening_star": talib.CDLEVENINGSTAR(opens, highs, lows, closes),
                "hammer": talib.CDLHAMMER(opens, highs, lows, closes)
            }
            
            return {k: bool(v[-1]) for k, v in patterns.items()}
        except Exception as e:
            logger.error(f"Pattern analysis error: {e}")
            return {}

    def _calculate_weighted_confidence(self, signals: dict) -> float:
        # Placeholder for a more complex confidence calculation
        return min(signals.get("composite_score", 0) * 0.1, 1.0)

    def _get_advanced_verdict(self, signals: dict) -> str:
        score = signals.get("composite_score", 0)
        if score > 0.7:
            return "STRONG_BUY"
        elif score > 0.5:
            return "BUY"
        elif score > 0.3:
            return "NEUTRAL"
        return "SELL"

    def _extract_technicals(self, soup) -> dict:
        technicals = {}
        try:
            tech_div = soup.select_one('.technicals-content')
            if tech_div:
                for row in tech_div.select('.indicator-row'):
                    name = row.select_one('.name').text.strip()
                    value = row.select_one('.value').text.strip()
                    technicals[name] = value
        except Exception:
            pass
        return technicals

    def _extract_oscillators(self, soup) -> dict:
        oscillators = {}
        try:
            osc_div = soup.select_one('.oscillators-content')
            if osc_div:
                for row in osc_div.select('.oscillator-row'):
                    name = row.select_one('.name').text.strip()
                    value = row.select_one('.value').text.strip()
                    oscillators[name] = value
        except Exception:
            pass
        return oscillators

    def _extract_moving_averages(self, soup) -> dict:
        mas = {}
        try:
            ma_div = soup.select_one('.moving-averages-content')
            if ma_div:
                for row in ma_div.select('.ma-row'):
                    period = row.select_one('.period').text.strip()
                    value = row.select_one('.value').text.strip()
                    mas[period] = value
        except Exception:
            pass
        return mas

async def run(symbol: str, agent_outputs: dict = {}) -> dict:
    agent = TradingViewAgent()
    return await agent.execute(symbol, agent_outputs)
