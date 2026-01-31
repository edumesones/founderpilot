"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import inbox_pilot, webhooks
from src.core.config import settings
from src.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    # await init_db()  # Uncomment to auto-create tables (use Alembic in prod)
    yield
    # Shutdown
    pass


app = FastAPI(
    title=settings.app_name,
    description="Autonomous agents for founders: InboxPilot, InvoicePilot, MeetingPilot",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    inbox_pilot.router,
    prefix=f"{settings.api_v1_prefix}/inbox-pilot",
    tags=["InboxPilot"],
)

app.include_router(
    webhooks.router,
    prefix="/webhooks",
    tags=["Webhooks"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": settings.app_name}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "docs": "/docs",
    }
