import logging
import sys
import os
from logging.handlers import TimedRotatingFileHandler, RotatingFileHandler
import json
from pathlib import Path

from ..config.settings import get_settings

settings = get_settings()


def configure_logging():
    """
    Configure application-wide logging.
    Returns the configured logger instance.
    """
    # Create logs directory if it doesn't exist
    log_dir = Path(settings.logging.LOG_FILE).parent
    os.makedirs(log_dir, exist_ok=True)

    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.logging.LEVEL))
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Configure console handler for development environment
    if settings.is_development:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, settings.logging.LEVEL))
        console_formatter = logging.Formatter(settings.logging.FORMAT)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # Configure file handler for production and development
    if settings.logging.LOG_FILE:
        # Use timed rotating file handler for daily log rotation
        file_handler = TimedRotatingFileHandler(
            settings.logging.LOG_FILE,
            when="midnight",
            interval=1,
            backupCount=30
        )
        file_handler.setLevel(getattr(logging, settings.logging.LEVEL))
        file_formatter = logging.Formatter(settings.logging.FORMAT)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    # In production, also add a JSON formatter for structured logging
    # which can be parsed by log analysis tools like ELK stack
    if settings.is_production:
        class JsonFormatter(logging.Formatter):
            def format(self, record):
                log_data = {
                    "timestamp": self.formatTime(record, self.datefmt),
                    "level": record.levelname,
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno,
                    "message": record.getMessage(),
                }
                
                if hasattr(record, 'request_id'):
                    log_data["request_id"] = record.request_id
                    
                if record.exc_info:
                    log_data["exception"] = self.formatException(record.exc_info)
                
                return json.dumps(log_data)
        
        # Create a separate JSON log file
        json_log_path = settings.logging.LOG_FILE.replace('.log', '.json.log')
        json_handler = RotatingFileHandler(
            json_log_path,
            maxBytes=10*1024*1024,  # 10 MB
            backupCount=10
        )
        json_handler.setLevel(getattr(logging, settings.logging.LEVEL))
        json_handler.setFormatter(JsonFormatter())
        logger.addHandler(json_handler)
    
    # Disable propagation for some noisy libraries
    for lib_logger in ['urllib3', 'asyncio']:
        logging.getLogger(lib_logger).setLevel(logging.WARNING)
    
    logger.info(f"Logging configured with level: {settings.logging.LEVEL}")
    return logger


# Create a global logger instance
logger = configure_logging()


def get_logger(name: str = None):
    """
    Get a logger with an optional name.
    If no name is provided, returns the root logger.
    """
    if name is None:
        return logger
    return logging.getLogger(name)


class RequestIdFilter(logging.Filter):
    """
    Filter that adds request_id to log records.
    """
    def __init__(self, request_id=None):
        super().__init__()
        self.request_id = request_id
    
    def filter(self, record):
        record.request_id = self.request_id
        return True
