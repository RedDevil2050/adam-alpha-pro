import sys
from loguru import logger
import json


def setup_logging():
    config = {
        "handlers": [
            {
                "sink": sys.stdout,
                "format": "{time} | {level} | {message}",
                "serialize": True,
                "level": "INFO",
            },
            {
                "sink": "logs/error.log",
                "format": "{time} | {level} | {message}",
                "serialize": True,
                "level": "ERROR",
                "rotation": "100 MB",
            },
        ]
    }

    logger.configure(**config)
    return logger
