"""Main application factory with SERVICE_MODE routing."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.agents.coordinator_agent import CoordinatorAgent
from app.api import health, routes
from app.config import get_settings
from app.services.session_manager import SessionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler for startup and shutdown.

    Args:
        _app: FastAPI application instance (unused)

    Yields:
        None
    """
    settings = get_settings()
    logger.info("Starting application in %s mode on port %s", settings.SERVICE_MODE, settings.PORT)

    # Initialize shared components
    routes.agent = CoordinatorAgent(settings)
    routes.session_manager = SessionManager(settings.SESSION_STORAGE_PATH)

    logger.info("Application initialized successfully with Coordinator agent")

    yield

    logger.info("Shutting down application")


def create_app() -> FastAPI:
    """Create FastAPI application based on SERVICE_MODE.

    Returns:
        FastAPI application instance configured for api or web mode
    """
    settings = get_settings()

    # Set logging level from settings
    logging.getLogger().setLevel(settings.LOG_LEVEL)

    # Create FastAPI app with lifespan
    app = FastAPI(
        title="SRE Bot Strands",
        description="FastAPI application with AWS Strands framework",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Include health check router (available for both modes)
    app.include_router(health.router, tags=["health"])

    # Include API routes (available for both modes)
    app.include_router(routes.router, tags=["api"])

    # Configure based on SERVICE_MODE
    if settings.SERVICE_MODE == "web":
        logger.info("Configuring web service mode with CORS and static files")

        # Add CORS middleware for web service
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Mount static files for web UI
        app.mount("/", StaticFiles(directory="app/static", html=True), name="static")

        logger.info("Web service configured - UI available at http://localhost:%s", settings.PORT)

    else:  # api mode
        logger.info("Configuring API service mode (no CORS, no static files)")
        logger.info("API service available at http://localhost:%s", settings.PORT)

    return app


# Application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
    )
