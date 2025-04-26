import sys
from loguru import logger

def setup_logging():
    """Configure logging for the application"""
    logger.remove()  # Remove default handler
    
    # Add custom handlers
    logger.add(
        sys.stdout,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        level="INFO"
    )
    logger.add(
        "logs/app.log",
        rotation="100 MB",
        retention="30 days",
        level="DEBUG"
    )

    return logger
