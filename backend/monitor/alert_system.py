from typing import List, Dict
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import asyncio
from loguru import logger

class AlertSystem:
    def __init__(self):
        self.alert_levels = {
            "critical": 1,
            "warning": 2,
            "info": 3
        }
        self.alert_queue = asyncio.Queue()
        self.subscribers = self._load_subscribers()

    async def start(self):
        while True:
            alert = await self.alert_queue.get()
            await self._process_alert(alert)

    async def send_alert(self, level: str, message: str, details: Dict = None):
        alert = {
            "level": level,
            "message": message,
            "details": details,
            "timestamp": datetime.now()
        }
        await self.alert_queue.put(alert)
        logger.warning(f"Alert queued: {message}")

    async def _process_alert(self, alert: Dict):
        try:
            if alert["level"] == "critical":
                await self._send_email_alert(alert)
                await self._send_slack_alert(alert)
            elif alert["level"] == "warning":
                await self._send_slack_alert(alert)
            
            logger.info(f"Alert processed: {alert['message']}")
        except Exception as e:
            logger.error(f"Alert processing failed: {e}")
