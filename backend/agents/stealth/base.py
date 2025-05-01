class StealthAgentBase:
    """Base class for stealth agents."""

    async def execute(self, symbol: str) -> dict:
        """Execute the stealth agent logic."""
        # This method should still be implemented by subclasses
        raise NotImplementedError("Subclasses must implement the execute method.")
