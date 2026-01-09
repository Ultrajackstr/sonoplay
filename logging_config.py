"""COMPATIBILITY SHIM - Use sonoplex.core.logging instead."""

# Re-export from new canonical location
from sonoplex.core.logging import configure_logging

__all__ = ["configure_logging"]
