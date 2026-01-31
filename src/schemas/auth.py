"""
Authentication-related Pydantic schemas.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from src.schemas.common import BaseSchema
from src.schemas.user import UserProfile


class TokenResponse(BaseSchema):
    """Response schema for token endpoints."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token expiration in seconds")


class TokenPair(BaseSchema):
    """Access and refresh token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Request schema for token refresh (if not using cookies)."""

    refresh_token: str


class LoginResponse(BaseSchema):
    """Response schema for login callback."""

    user: UserProfile
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    onboarding_required: bool


class OAuthState(BaseSchema):
    """OAuth state stored in Redis."""

    state: str
    code_verifier: str
    redirect_uri: str
    created_at: datetime
    user_id: Optional[UUID] = None  # Set for integration OAuth flows


class GoogleUserInfo(BaseSchema):
    """User info from Google OAuth."""

    id: str = Field(..., alias="sub")
    email: str
    name: str
    picture: Optional[str] = None
    email_verified: bool = False


class LogoutResponse(BaseSchema):
    """Response schema for logout."""

    message: str = "Successfully logged out"
