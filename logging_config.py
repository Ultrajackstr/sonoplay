"""Centralized logging configuration for Sonoplex."""

import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    """Configure root logger with consistent format.
    
    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR)
    """
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True
    )
    
    # Reduce noise from chatty libraries
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


__all__ = ["configure_logging"]
