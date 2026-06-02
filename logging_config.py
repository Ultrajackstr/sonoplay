"""Centralized logging configuration for SonoPlay."""

import logging
import os
import sys


def configure_logging(level: str | None = None) -> None:
    """Configure the root logger with a consistent format.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR). When omitted, the
            LOG_LEVEL environment variable is used (default INFO). Set
            LOG_LEVEL=DEBUG to surface DLNA transport/state detail for
            troubleshooting.
    """
    if level is None:
        level = os.environ.get("LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,
    )

    # Reduce noise from chatty libraries
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


__all__ = ["configure_logging"]
