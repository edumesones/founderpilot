"""
Google OAuth2 service with PKCE support.
"""

import base64
import hashlib
import secrets
from typing import Optional
from urllib.parse import urlencode

import httpx

from src.core.config import settings
from src.core.exceptions import OAuthCallbackError, OAuthError, ProviderAPIError
from src.schemas.auth import GoogleUserInfo


class GoogleOAuthTokens:
    """Container for Google OAuth tokens."""

    def __init__(
        self,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_in: int = 3600,
        token_type: str = "Bearer",
        scope: Optional[str] = None,
        id_token: Optional[str] = None,
    ):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_in = expires_in
        self.token_type = token_type
        self.scope = scope
        self.id_token = id_token


class GoogleOAuthService:
    """
    Service for Google OAuth2 authentication with PKCE.

    Implements the authorization code flow with PKCE (Proof Key for Code Exchange)
    for enhanced security. PKCE prevents authorization code interception attacks.

    OAuth2 endpoints:
        - Authorization: https://accounts.google.com/o/oauth2/v2/auth
        - Token: https://oauth2.googleapis.com/token
        - UserInfo: https://www.googleapis.com/oauth2/v3/userinfo
    """

    AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

    # Scopes for basic user authentication
    AUTH_SCOPES = [
        "openid",
        "email",
        "profile",
    ]

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        """
        Initialize the Google OAuth service.

        Args:
            client_id: Google OAuth client ID
            client_secret: Google OAuth client secret
        """
        self.client_id = client_id or settings.google_client_id
        self.client_secret = client_secret or settings.google_client_secret

    @staticmethod
    def generate_state() -> str:
        """Generate a cryptographically secure state parameter."""
        return secrets.token_urlsafe(32)

    @staticmethod
    def generate_code_verifier() -> str:
        """Generate a PKCE code verifier."""
        return secrets.token_urlsafe(64)

    @staticmethod
    def generate_code_challenge(code_verifier: str) -> str:
        """
        Generate a PKCE code challenge from the verifier.

        Uses S256 method: BASE64URL(SHA256(code_verifier))
        """
        digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")

    def get_authorization_url(
        self,
        redirect_uri: str,
        state: str,
        code_challenge: str,
        scopes: Optional[list] = None,
    ) -> str:
        """
        Generate the Google OAuth authorization URL.

        Args:
            redirect_uri: URL to redirect to after authorization
            state: CSRF protection state parameter
            code_challenge: PKCE code challenge
            scopes: OAuth scopes to request (defaults to AUTH_SCOPES)

        Returns:
            The authorization URL to redirect the user to
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes or self.AUTH_SCOPES),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "access_type": "offline",  # Request refresh token
            "prompt": "consent",  # Force consent to get refresh token
        }

        return f"{self.AUTHORIZATION_URL}?{urlencode(params)}"

    async def exchange_code(
        self,
        code: str,
        redirect_uri: str,
        code_verifier: str,
    ) -> GoogleOAuthTokens:
        """
        Exchange authorization code for tokens.

        Args:
            code: Authorization code from callback
            redirect_uri: Same redirect URI used in authorization
            code_verifier: PKCE code verifier

        Returns:
            GoogleOAuthTokens with access and refresh tokens

        Raises:
            OAuthCallbackError: If token exchange fails
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.TOKEN_URL,
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "code": code,
                        "code_verifier": code_verifier,
                        "grant_type": "authorization_code",
                        "redirect_uri": redirect_uri,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code != 200:
                    error_data = response.json() if response.content else {}
                    raise OAuthCallbackError(
                        message=f"Token exchange failed: {error_data.get('error_description', 'Unknown error')}",
                        provider="google",
                    )

                data = response.json()
                return GoogleOAuthTokens(
                    access_token=data["access_token"],
                    refresh_token=data.get("refresh_token"),
                    expires_in=data.get("expires_in", 3600),
                    token_type=data.get("token_type", "Bearer"),
                    scope=data.get("scope"),
                    id_token=data.get("id_token"),
                )

            except httpx.RequestError as e:
                raise OAuthCallbackError(
                    message=f"Network error during token exchange: {e}",
                    provider="google",
                )

    async def get_user_info(self, access_token: str) -> GoogleUserInfo:
        """
        Get user information from Google.

        Args:
            access_token: Google OAuth access token

        Returns:
            GoogleUserInfo with user profile data

        Raises:
            ProviderAPIError: If user info request fails
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    self.USERINFO_URL,
                    headers={"Authorization": f"Bearer {access_token}"},
                )

                if response.status_code != 200:
                    raise ProviderAPIError(
                        message="Failed to get user info from Google",
                        provider="google",
                        status_code=response.status_code,
                    )

                data = response.json()
                return GoogleUserInfo(
                    sub=data["sub"],
                    email=data["email"],
                    name=data.get("name", data["email"].split("@")[0]),
                    picture=data.get("picture"),
                    email_verified=data.get("email_verified", False),
                )

            except httpx.RequestError as e:
                raise ProviderAPIError(
                    message=f"Network error getting user info: {e}",
                    provider="google",
                )

    async def refresh_access_token(self, refresh_token: str) -> GoogleOAuthTokens:
        """
        Refresh the access token using a refresh token.

        Args:
            refresh_token: Google OAuth refresh token

        Returns:
            GoogleOAuthTokens with new access token

        Raises:
            OAuthError: If refresh fails
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.TOKEN_URL,
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token",
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code != 200:
                    error_data = response.json() if response.content else {}
                    raise OAuthError(
                        message=f"Token refresh failed: {error_data.get('error_description', 'Unknown error')}",
                        provider="google",
                    )

                data = response.json()
                return GoogleOAuthTokens(
                    access_token=data["access_token"],
                    refresh_token=refresh_token,  # Refresh tokens don't rotate
                    expires_in=data.get("expires_in", 3600),
                    token_type=data.get("token_type", "Bearer"),
                    scope=data.get("scope"),
                )

            except httpx.RequestError as e:
                raise OAuthError(
                    message=f"Network error during token refresh: {e}",
                    provider="google",
                )
