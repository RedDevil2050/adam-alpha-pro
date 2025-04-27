import aiohttp
from typing import Dict, Any
from ..config.settings import get_settings
from loguru import logger

class AlertSystem:
    def __init__(self):
        self.settings = get_settings()
        self.alert_thresholds = {
            'error_rate': 0.1,
            'response_time': 5.0,
            'memory_usage': 0.9
        }

    async def send_alert(self, alert_type: str, details: Dict[str, Any]):
        if self.settings.monitoring.SLACK_WEBHOOK_URL:
            await self._send_slack_alert(alert_type, details)
        
        if self.settings.monitoring.EMAIL_NOTIFICATIONS:
            await self._send_email_alert(alert_type, details)
        
        logger.error(f"Alert: {alert_type} - {details}")

    async def _send_slack_alert(self, alert_type: str, details: Dict[str, Any]):
        webhook_url = self.settings.monitoring.SLACK_WEBHOOK_URL
        message = self._format_alert_message(alert_type, details)
        
        async with aiohttp.ClientSession() as session:
            await session.post(webhook_url, json={'text': message})

    def _format_alert_message(self, alert_type: str, details: Dict[str, Any]) -> str:
        return f"🚨 *Alert: {alert_type}*\n" + \
               "\n".join(f"• {k}: {v}" for k, v in details.items())
