"""
Authentication routes for Google OAuth and session management.
"""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse

from src.api.dependencies import (
    ClientIP,
    CurrentUser,
    DbSession,
    RedisClient,
    UserAgent,
    get_auth_service,
)
from src.core.config import settings
from src.core.exceptions import (
    AuthenticationError,
    OAuthCallbackError,
    OAuthStateError,
    RefreshTokenError,
)
from src.schemas.auth import LogoutResponse
from src.schemas.user import UserProfile
from src.services.auth import AuthService


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/google")
async def google_login(
    request: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> RedirectResponse:
    """
    Initiate Google OAuth2 flow.

    Redirects user to Google's authorization page.
    After authorization, Google redirects back to /auth/google/callback.
    """
    # Build callback URL
    callback_url = str(request.url_for("google_callback"))

    # Get authorization URL with PKCE
    auth_url, state, _ = await auth_service.get_google_auth_url(callback_url)

    # Redirect to Google
    response = RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)

    # Set state cookie for CSRF protection (in addition to Redis storage)
    response.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        secure=not settings.debug,
        samesite="lax",
        max_age=300,  # 5 minutes
    )

    return response


@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="State parameter for CSRF validation"),
    error: Optional[str] = Query(None, description="Error code if authorization failed"),
    error_description: Optional[str] = Query(None, description="Error description"),
    auth_service: AuthService = Depends(get_auth_service),
    ip_address: Optional[str] = Depends(lambda r: r.headers.get("X-Forwarded-For", r.client.host if r.client else None)),
    user_agent: Optional[str] = Depends(lambda r: r.headers.get("User-Agent")),
) -> RedirectResponse:
    """
    Handle Google OAuth2 callback.

    Exchanges authorization code for tokens, creates/updates user,
    and redirects to frontend with session cookies.
    """
    # Check for OAuth errors
    if error:
        error_msg = error_description or error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth error: {error_msg}",
        )

    # Verify state cookie matches
    cookie_state = request.cookies.get("oauth_state")
    if not cookie_state or cookie_state != state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter",
        )

    # Build callback URL (must match the one used in authorization)
    callback_url = str(request.url_for("google_callback"))

    try:
        # Handle callback and get user + tokens
        user, access_token, refresh_token = await auth_service.handle_google_callback(
            code=code,
            state=state,
            redirect_uri=callback_url,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except OAuthStateError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state. Please try logging in again.",
        )
    except OAuthCallbackError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Determine redirect URL based on onboarding status
    if not user.onboarding_completed:
        redirect_url = f"{settings.frontend_url}/onboarding"
    else:
        redirect_url = f"{settings.frontend_url}/dashboard"

    # Create response with redirect
    response = RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

    # Set authentication cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=not settings.debug,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=not settings.debug,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
    )

    # Clear OAuth state cookie
    response.delete_cookie("oauth_state")

    return response


@router.post("/refresh")
async def refresh_token(
    request: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    ip_address: ClientIP,
    user_agent: UserAgent,
):
    """
    Refresh access token using refresh token from cookie.

    Returns new tokens in cookies.
    """
    refresh_token = request.cookies.get("refresh_token")

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required",
        )

    try:
        new_access_token, new_refresh_token = await auth_service.refresh_tokens(
            refresh_token=refresh_token,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except RefreshTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    # Create response
    response = {"message": "Token refreshed successfully"}

    # Create JSON response with new cookies
    from fastapi.responses import JSONResponse
    json_response = JSONResponse(content=response)

    # Set new cookies
    json_response.set_cookie(
        key="access_token",
        value=new_access_token,
        httponly=True,
        secure=not settings.debug,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )
    json_response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=not settings.debug,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
    )

    return json_response


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    current_user: CurrentUser,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    ip_address: ClientIP,
    user_agent: UserAgent,
):
    """
    Logout current user.

    Revokes refresh tokens and blacklists current access token.
    """
    # Get current access token for blacklisting
    access_token = request.cookies.get("access_token")

    await auth_service.logout(
        user_id=current_user.id,
        access_token=access_token,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    # Create response with cookie deletion
    from fastapi.responses import JSONResponse
    response = JSONResponse(content={"message": "Successfully logged out"})

    # Delete auth cookies
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")

    return response


@router.get("/me", response_model=UserProfile)
async def get_current_user_info(current_user: CurrentUser):
    """
    Get current user information.

    Returns the profile of the authenticated user.
    """
    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        picture_url=current_user.picture_url,
        onboarding_completed=current_user.onboarding_completed,
    )
