class StealthAgentBase:
    """Base class for stealth agents."""

    async def execute(self, symbol: str) -> dict:
        """Execute the stealth agent logic."""
        # This method should still be implemented by subclasses
        raise NotImplementedError("Subclasses must implement the execute method.")

    def _error_response(self, symbol: str, error_message: str) -> dict:
        """Standard error response format for stealth agents."""
        # Try to get agent_name from instance, then class, then default
        agent_name = getattr(self, 'agent_name', None)
        if agent_name is None:
            agent_name = getattr(self.__class__, 'agent_name', 'stealth_agent_base')
        return {
            "symbol": symbol,
            "verdict": "ERROR",
            "confidence": 0.0,
            "value": None,
            "details": {},
            "error": error_message,
            "agent_name": agent_name,
        }
