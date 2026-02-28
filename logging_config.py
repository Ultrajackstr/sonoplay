"""COMPATIBILITY SHIM - Use sonoplay.core.logging instead."""

# Re-export from new canonical location
from sonoplay.core.logging import configure_logging

__all__ = ["configure_logging"]
