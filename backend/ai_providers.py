from abc import ABC, abstractmethod
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from circuitbreaker import circuit


class AIProvider(ABC):
    @abstractmethod
    async def call(self, prompt: str, **kwargs) -> dict:
        """Send prompt to the model and return the response."""
        pass


class OpenAIProvider(AIProvider):
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.api_key = api_key
        self.model = model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
    @circuit(failure_threshold=2, recovery_timeout=60)
    async def call(self, prompt: str, **kwargs) -> dict:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        json_data = {"model": self.model, "prompt": prompt, **kwargs}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "https://api.openai.com/v1/completions", json=json_data, headers=headers
            )
            resp.raise_for_status()
            return resp.json()


class GeminiProvider(AIProvider):
    def __init__(self, api_key: str, model: str = "gemini-pro"):
        self.api_key = api_key
        self.model = model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
    @circuit(failure_threshold=2, recovery_timeout=60)
    async def call(self, prompt: str, **kwargs) -> dict:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"https://api.gemini.example/v1/{self.model}/completions",
                json={"prompt": prompt, **kwargs},
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()


class LovableProvider(AIProvider):
    def __init__(self, api_key: str, model: str = "lovable-ai"):
        self.api_key = api_key
        self.model = model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
    @circuit(failure_threshold=2, recovery_timeout=60)
    async def call(self, prompt: str, **kwargs) -> dict:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"https://api.lovable.ai/v1/{self.model}/completions",
                json={"prompt": prompt, **kwargs},
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()


# Additional providers can be added similarly
PROVIDERS = {
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
    "lovable": LovableProvider,
    # "perplexity": PerplexityProvider,
    # "depseek": DepseekProvider,
    # "aistudio": AIStudioProvider,
    # "firebase": FirebaseMLProvider,
    # "redisai": RedisAIProvider,
}
