"""FastAPI application factory for Sonoplex."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import time

# Resolve paths relative to project root (where templates/ and static/ live)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "templates"
STATIC_DIR = PROJECT_ROOT / "static"


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI instance with routes and middleware
    """
    app = FastAPI(
        title="Sonoplex",
        description="Plex DLNA Player - Bridge Plex to DLNA/UPnP speakers",
        version="1.0.0",
    )
    
    # Mount static files
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    
    # Register routers
    from sonoplex.api.routes.health import router as health_router, set_startup_time
    app.include_router(health_router)
    
    @app.on_event("startup")
    async def on_startup():
        set_startup_time(time.time())
    
    return app


# Templates instance for use by route handlers
templates = Jinja2Templates(directory=str(TEMPLATES_DIR)) if TEMPLATES_DIR.exists() else None
