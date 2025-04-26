import sys
from loguru import logger
from pathlib import Path

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

def setup_logging():
    # Remove default handler
    logger.remove()
    
    # Add production handlers
    logger.add(
        sys.stderr,
        level="WARNING",
        backtrace=True,
        diagnose=True
    )
    
    logger.add(
        LOG_DIR / "app.log",
        rotation="100 MB",
        retention="30 days",
        compression="zip",
        level="INFO",
        backtrace=True,
        diagnose=True
    )
    
    logger.add(
        LOG_DIR / "error.log",
        rotation="100 MB",
        retention="30 days",
        compression="zip",
        level="ERROR",
        backtrace=True,
        diagnose=True
    )
