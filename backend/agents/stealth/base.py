class StealthAgentBase:
    """Base class for stealth agents."""
    def execute(self, symbol: str) -> dict:
        """Execute the stealth agent logic."""
        raise NotImplementedError("Subclasses must implement the execute method.")