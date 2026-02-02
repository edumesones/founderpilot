"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.core.config import settings
from src.core.database import close_db, init_db
from src.core.exceptions import (
    AuthenticationError,
    FounderPilotError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan handler.

    Initializes and cleans up resources on startup/shutdown.
    """
    # Startup
    logger.info(f"Starting {settings.app_name}")
    await init_db()

    # Initialize Slack Bolt app (registers handlers)
    if settings.slack_configured:
        try:
            from src.integrations.slack.app import create_slack_app

            create_slack_app()
            logger.info("Slack app initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Slack app: {e}")

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.app_name}")
    await close_db()


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI instance
    """
    application = FastAPI(
        title=settings.app_name,
        description="AI agents for founders - InboxPilot, InvoicePilot, MeetingPilot",
        version="0.1.0",
        docs_url="/api/docs" if settings.debug else None,
        redoc_url="/api/redoc" if settings.debug else None,
        openapi_url="/api/openapi.json" if settings.debug else None,
        lifespan=lifespan,
    )

    # Configure CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            settings.frontend_url,
            "http://localhost:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add rate limiting middleware (FEAT-001)
    try:
        from src.middleware.rate_limit import RateLimitMiddleware

        application.add_middleware(RateLimitMiddleware)
    except ImportError:
        logger.warning("Rate limit middleware not available")

    # Register exception handlers
    register_exception_handlers(application)

    # API v1 prefix
    API_V1 = settings.api_v1_prefix

    # Include Auth routers (FEAT-001)
    try:
        from src.api.routes import auth, integrations, onboarding

        application.include_router(auth.router)
        application.include_router(integrations.router)
        application.include_router(onboarding.router)
    except ImportError:
        logger.warning("Auth routes not available")

    # Include Slack router (FEAT-006)
    try:
        from src.api.routes.slack import router as slack_router

        application.include_router(slack_router, prefix=API_V1)
    except ImportError:
        logger.warning("Slack routes not available")

    # Include InboxPilot router (FEAT-003)
    try:
        from src.api.routes import inbox_pilot

        application.include_router(
            inbox_pilot.router,
            prefix=f"{API_V1}/inbox-pilot",
            tags=["InboxPilot"],
        )
    except ImportError:
        logger.warning("InboxPilot routes not available")

    # Include MeetingPilot router (FEAT-005)
    try:
        from src.api.routes import meeting_pilot

        application.include_router(
            meeting_pilot.router,
            prefix=f"{API_V1}/meeting-pilot",
            tags=["MeetingPilot"],
        )
    except ImportError:
        logger.warning("MeetingPilot routes not available")

    # Include Webhooks router (FEAT-003)
    try:
        from src.api.routes import webhooks

        application.include_router(
            webhooks.router,
            prefix="/webhooks",
            tags=["Webhooks"],
        )
    except ImportError:
        logger.warning("Webhook routes not available")

    # Include Agent Audit router (FEAT-007)
    try:
        from src.api.routes import agent_audit

        application.include_router(agent_audit.router)
    except ImportError:
        logger.warning("Agent Audit routes not available")

    # Health check endpoint
    @application.get("/health")
    async def health_check():
        """Health check endpoint for load balancers."""
        return {
            "status": "healthy",
            "app": settings.app_name,
            "version": "0.1.0",
            "slack_configured": settings.slack_configured,
        }

    @application.get("/")
    async def root():
        """Root endpoint."""
        return {
            "app": settings.app_name,
            "version": "0.1.0",
            "docs": "/api/docs" if settings.debug else None,
            "health": "/health",
        }

    return application


def register_exception_handlers(app: FastAPI) -> None:
    """Register custom exception handlers."""

    @app.exception_handler(FounderPilotError)
    async def founderpilot_error_handler(
        request: Request, exc: FounderPilotError
    ) -> JSONResponse:
        """Handle all FounderPilot custom exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            },
        )

    @app.exception_handler(AuthenticationError)
    async def authentication_error_handler(
        request: Request, exc: AuthenticationError
    ) -> JSONResponse:
        """Handle authentication errors with WWW-Authenticate header."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error_code,
                "message": exc.message,
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(RateLimitError)
    async def rate_limit_error_handler(
        request: Request, exc: RateLimitError
    ) -> JSONResponse:
        """Handle rate limit errors with Retry-After header."""
        headers = {}
        if "retry_after_seconds" in exc.details:
            headers["Retry-After"] = str(exc.details["retry_after_seconds"])

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error_code,
                "message": exc.message,
            },
            headers=headers,
        )

    @app.exception_handler(ValidationError)
    async def validation_error_handler(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        """Handle validation errors."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            },
        )

    @app.exception_handler(NotFoundError)
    async def not_found_error_handler(
        request: Request, exc: NotFoundError
    ) -> JSONResponse:
        """Handle not found errors."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle unexpected exceptions."""
        logger.error(f"Unexpected error: {exc}", exc_info=True)

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_error",
                "message": "An unexpected error occurred",
                "details": {"error": str(exc)} if settings.debug else {},
            },
        )


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
