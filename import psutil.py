import psutil
from datetime import datetime
import aioredis
from backend.config.settings import get_settings

class SystemMonitor:
    def __init__(self):
        self.settings = get_settings()
        self.thresholds = {
            'cpu_percent': 80.0,
            'memory_percent': 85.0,
            'disk_percent': 90.0
        }

    async def check_system_health(self) -> dict:
        cpu_usage = psutil.cpu_percent()
        memory_usage = psutil.virtual_memory().percent
        disk_usage = psutil.disk_usage('/').percent
        
        # Update metrics
        # self.metrics.system_cpu.set(cpu_usage)
        # self.metrics.system_memory.set(memory_usage)
        
        # Check component health
        components = {
            'cpu': self._check_threshold('cpu_percent', cpu_usage),
            'memory': self._check_threshold('memory_percent', memory_usage),
            'disk': self._check_threshold('disk_percent', disk_usage),
            'redis': await self._check_redis_connection(),
        }
        
        return {
            'status': 'healthy' if all(components.values()) else 'unhealthy',
            'components': components,
            'timestamp': datetime.now(datetime.UTC).isoformat()
        }

    def _check_threshold(self, metric: str, value: float) -> bool:
        return value < self.thresholds[metric]

    async def _check_redis_connection(self) -> bool:
        try:
            redis = await aioredis.from_url(self.settings.REDIS_URL)
            await redis.ping()
            return True
        except Exception:
            return False
