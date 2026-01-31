"""
FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import auth
from src.core.config import settings
from src.core.database import close_db, init_db
from src.core.exceptions import (
    AuthenticationError,
    FounderPilotError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)
from src.middleware.rate_limit import RateLimitMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan handler.

    Initializes and cleans up resources on startup/shutdown.
    """
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI instance
    """
    app = FastAPI(
        title="FounderPilot API",
        description="Backend API for FounderPilot - AI-powered productivity for founders",
        version="0.1.0",
        docs_url="/api/docs" if settings.debug else None,
        redoc_url="/api/redoc" if settings.debug else None,
        openapi_url="/api/openapi.json" if settings.debug else None,
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            settings.frontend_url,
            "http://localhost:3000",  # Development
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add rate limiting middleware
    app.add_middleware(RateLimitMiddleware)

    # Register exception handlers
    register_exception_handlers(app)

    # Include routers
    app.include_router(auth.router)

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint for load balancers."""
        return {"status": "healthy", "version": "0.1.0"}

    return app


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
        # Log the error in production
        if not settings.debug:
            # TODO: Add proper logging
            pass

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
