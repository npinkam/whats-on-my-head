import logging
import sys

from loguru import logger

from sky_radar.config import settings


class HealthCheckFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return "/health" not in msg and "/ready" not in msg


def setup_logging():
    logger.remove()

    logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())

    log_format = settings.log_format if hasattr(settings, "log_format") else "text"

    if log_format == "json":
        logger.add(sys.stdout, serialize=True, level=settings.log_level)
    else:
        log_format_str = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )

        logger.add(
            sys.stdout,
            format=log_format_str,
            level=settings.log_level,
            colorize=True,
        )

    logger.info(f"Logging initialized with level: {settings.log_level}")
