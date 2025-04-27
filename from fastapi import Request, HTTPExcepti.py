from fastapi import Request, HTTPException
from typing import Dict, Optional
import time
import asyncio
from ..config.settings import get_settings

settings = get_settings()

class RateLimiter:
    def __init__(self):
        self.requests: Dict[str, list] = {}
        self.lock = asyncio.Lock()
    
    async def check_rate_limit(self, key: str, limit: int, window: int = 60) -> None:
        async with self.lock:
            now = time.time()
            if key not in self.requests:
                self.requests[key] = []
            
            # Remove old requests
            self.requests[key] = [ts for ts in self.requests[key] if ts > now - window]
            
            if len(self.requests[key]) >= limit:
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded"
                )
            
            self.requests[key].append(now)

rate_limiter = RateLimiter()
