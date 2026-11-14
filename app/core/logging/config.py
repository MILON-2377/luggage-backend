import logging
import logging.config
import sys

from app.core.config import settings


class RequestIDFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        from app.core.middleware.request_id import request_id_context

        record.request_id = request_id_context.get()
        return True


def setup_logging() -> None:
    log_level = settings.LOG_LEVEL.upper()

    valid_levels = {
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    }

    if log_level not in valid_levels:
        raise ValueError(f"Invalid LOG_LEVEL: {settings.LOG_LEVEL}")

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": ("%(asctime)s | %(levelname)s | %(name)s | %(message)s"),
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "standard",
                "stream": sys.stdout,
            },
        },
        "root": {
            "level": log_level,
            "handlers": ["console"],
        },
        "loggers": {
            "uvicorn": {
                "level": log_level,
                "handlers": [],
                "propagate": True,
            },
            "uvicorn.error": {
                "level": log_level,
                "handlers": [],
                "propagate": True,
            },
            "uvicorn.access": {
                "level": "WARNING",
                "handlers": [],
                "propagate": True,
            },
            "sqlalchemy.engine": {
                "level": "WARNING",
                "handlers": [],
                "propagate": True,
            },
            "sqlalchemy.pool": {
                "level": "WARNING",
                "handlers": [],
                "propagate": True,
            },
        },
    }

    logging.config.dictConfig(logging_config)
