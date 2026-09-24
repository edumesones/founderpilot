# API v1 module
from fastapi import APIRouter

from src.api.v1.billing import router as billing_router

api_router = APIRouter()
api_router.include_router(billing_router)
