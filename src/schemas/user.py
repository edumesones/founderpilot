"""
User-related Pydantic schemas.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import EmailStr, Field

from src.schemas.common import BaseSchema


class UserBase(BaseSchema):
    """Base user schema with common fields."""

    email: EmailStr
    name: str = Field(..., min_length=1, max_length=255)
    picture_url: Optional[str] = Field(None, max_length=512)


class UserCreate(UserBase):
    """Schema for creating a new user."""

    google_id: str = Field(..., min_length=1, max_length=255)


class UserResponse(UserBase):
    """Schema for user API responses."""

    id: UUID
    onboarding_completed: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class UserProfile(BaseSchema):
    """Minimal user profile for /me endpoint."""

    id: UUID
    email: EmailStr
    name: str
    picture_url: Optional[str] = None
    onboarding_completed: bool
