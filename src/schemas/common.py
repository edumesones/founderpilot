"""
Common Pydantic schemas used across the application.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class ErrorResponse(BaseModel):
    """Standard error response schema."""

    error: str
    message: str
    details: Optional[Dict[str, Any]] = None


class SuccessResponse(BaseModel):
    """Standard success response schema."""

    message: str
    data: Optional[Dict[str, Any]] = None
