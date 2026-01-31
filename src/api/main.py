"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.api.routes.slack import router as slack_router

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    Initializes resources on startup and cleans up on shutdown.
    """
    # Startup
    logger.info(f"Starting {settings.APP_NAME}")

    # Initialize Slack Bolt app (registers handlers)
    if settings.slack_configured or settings.SLACK_BOT_TOKEN:
        try:
            from src.integrations.slack.app import create_slack_app
            create_slack_app()
            logger.info("Slack app initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Slack app: {e}")

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME}")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="AI agents for founders - InboxPilot, InvoicePilot, MeetingPilot",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Routes
# ============================================================================

# API v1 prefix
API_V1 = settings.API_V1_PREFIX

# Include routers
app.include_router(slack_router, prefix=API_V1)


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "slack_configured": settings.slack_configured,
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "app": settings.APP_NAME,
        "docs": "/docs",
        "health": "/health",
    }
