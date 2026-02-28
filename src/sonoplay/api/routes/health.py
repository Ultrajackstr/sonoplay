"""Health check endpoint."""

from fastapi import APIRouter
import time

router = APIRouter(tags=["health"])

# Server startup time - set by app startup
_startup_time: float = 0.0


def set_startup_time(t: float) -> None:
    """Set the server startup timestamp."""
    global _startup_time
    _startup_time = t


@router.get("/health")
async def health_check():
    """Health check endpoint for container monitoring.
    
    Returns:
        dict: Health status with uptime
    """
    uptime = time.time() - _startup_time if _startup_time > 0 else 0
    return {
        "status": "healthy",
        "uptime_seconds": round(uptime, 2)
    }
