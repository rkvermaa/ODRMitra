"""Loguru logging configuration"""

import sys
from pathlib import Path
from loguru import logger

logger.remove()


def setup_logging(debug: bool = False, log_format: str = "pretty") -> None:
    """Configure loguru for the application."""
    logger.remove()

    if log_format == "pretty" or debug:
        logger.add(
            sys.stderr,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level>"
            ),
            level="DEBUG" if debug else "INFO",
            colorize=True,
        )
    else:
        logger.add(
            sys.stderr,
            format="{message}",
            level="INFO",
            serialize=True,
        )

    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    logger.add(
        logs_dir / "app_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="30 days",
        compression="gz",
        level="INFO",
    )


log = logger
