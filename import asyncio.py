import asyncio
import sys
import httpx
from pathlib import Path

async def verify_deployment(base_url: str = "http://localhost:8000"):
    async with httpx.AsyncClient() as client:
        try:
            # Check health endpoint
            health = await client.get(f"{base_url}/health")
            assert health.status_code == 200
            
            # Verify auth endpoint
            auth = await client.post(f"{base_url}/auth/token", 
                data={"username": "test", "password": "test"})
            assert auth.status_code in (200, 401)
            
            # Test metrics endpoint
            metrics = await client.get(f"{base_url}/metrics")
            assert metrics.status_code == 200
            
            print("✅ Deployment verification successful")
            return True
            
        except Exception as e:
            print(f"❌ Deployment verification failed: {str(e)}")
            return False

if __name__ == "__main__":
    success = asyncio.run(verify_deployment())
    sys.exit(0 if success else 1)
