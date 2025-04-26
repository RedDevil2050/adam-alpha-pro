import asyncio
import aiohttp
from loguru import logger

async def test_pipeline():
    """End-to-end pipeline test"""
    try:
        async with aiohttp.ClientSession() as session:
            # System health check
            async with session.get("http://localhost:8000/health") as response:
                health = await response.json()
                assert health["status"] == "healthy", "System not healthy"
                
            # Test symbol analysis
            async with session.get("http://localhost:8000/api/v1/analyze/AAPL") as response:
                result = await response.json()
                assert "analysis_id" in result, "Analysis failed"
                
            logger.info("Pipeline test successful")
            return True
                
    except Exception as e:
        logger.error(f"Pipeline test failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_pipeline())
