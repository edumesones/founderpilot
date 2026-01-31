"""
Custom exceptions for the application.
"""

from typing import Any, Dict, Optional


class FounderPilotError(Exception):
    """Base exception for all FounderPilot errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "internal_error",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


# =============================================================================
# Authentication Errors
# =============================================================================


class AuthenticationError(FounderPilotError):
    """Base class for authentication errors."""

    def __init__(
        self,
        message: str = "Authentication failed",
        error_code: str = "authentication_error",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=401,
            details=details,
        )


class TokenExpiredError(AuthenticationError):
    """Raised when a token has expired."""

    def __init__(self, message: str = "Token has expired"):
        super().__init__(
            message=message,
            error_code="token_expired",
        )


class InvalidTokenError(AuthenticationError):
    """Raised when a token is invalid."""

    def __init__(self, message: str = "Token is invalid"):
        super().__init__(
            message=message,
            error_code="invalid_token",
        )


class RefreshTokenError(AuthenticationError):
    """Raised when refresh token is invalid or expired."""

    def __init__(self, message: str = "Invalid or expired refresh token"):
        super().__init__(
            message=message,
            error_code="refresh_token_error",
        )


# =============================================================================
# OAuth Errors
# =============================================================================


class OAuthError(FounderPilotError):
    """Base class for OAuth errors."""

    def __init__(
        self,
        message: str = "OAuth error occurred",
        error_code: str = "oauth_error",
        provider: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        if provider:
            details["provider"] = provider
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=400,
            details=details,
        )


class OAuthStateError(OAuthError):
    """Raised when OAuth state parameter is invalid or missing."""

    def __init__(self, message: str = "Invalid or expired OAuth state"):
        super().__init__(
            message=message,
            error_code="invalid_state",
        )


class OAuthCallbackError(OAuthError):
    """Raised when OAuth callback fails."""

    def __init__(
        self,
        message: str = "OAuth callback failed",
        provider: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            error_code="oauth_callback_error",
            provider=provider,
        )


class OAuthScopeError(OAuthError):
    """Raised when required OAuth scopes are not granted."""

    def __init__(
        self,
        message: str = "Required scopes not granted",
        provider: Optional[str] = None,
        required_scopes: Optional[list] = None,
        granted_scopes: Optional[list] = None,
    ):
        details = {}
        if required_scopes:
            details["required_scopes"] = required_scopes
        if granted_scopes:
            details["granted_scopes"] = granted_scopes
        super().__init__(
            message=message,
            error_code="insufficient_scopes",
            provider=provider,
            details=details,
        )


# =============================================================================
# Integration Errors
# =============================================================================


class IntegrationError(FounderPilotError):
    """Base class for integration errors."""

    def __init__(
        self,
        message: str = "Integration error occurred",
        error_code: str = "integration_error",
        provider: Optional[str] = None,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        if provider:
            details["provider"] = provider
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details,
        )


class IntegrationNotFoundError(IntegrationError):
    """Raised when an integration is not found."""

    def __init__(
        self,
        message: str = "Integration not found",
        provider: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            error_code="integration_not_found",
            provider=provider,
            status_code=404,
        )


class IntegrationExpiredError(IntegrationError):
    """Raised when an integration's tokens have expired."""

    def __init__(
        self,
        message: str = "Integration token expired, reconnection required",
        provider: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            error_code="integration_expired",
            provider=provider,
        )


class ProviderAPIError(IntegrationError):
    """Raised when an external provider API call fails."""

    def __init__(
        self,
        message: str = "Provider API error",
        provider: Optional[str] = None,
        status_code: int = 502,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="provider_api_error",
            provider=provider,
            status_code=status_code,
            details=details,
        )


# =============================================================================
# Rate Limiting Errors
# =============================================================================


class RateLimitError(FounderPilotError):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Too many requests",
        retry_after: Optional[int] = None,
    ):
        details = {}
        if retry_after:
            details["retry_after_seconds"] = retry_after
        super().__init__(
            message=message,
            error_code="rate_limited",
            status_code=429,
            details=details,
        )


# =============================================================================
# Validation Errors
# =============================================================================


class ValidationError(FounderPilotError):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str = "Validation error",
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        if field:
            details["field"] = field
        super().__init__(
            message=message,
            error_code="validation_error",
            status_code=422,
            details=details,
        )


# =============================================================================
# Not Found Errors
# =============================================================================


class NotFoundError(FounderPilotError):
    """Raised when a resource is not found."""

    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ):
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
        super().__init__(
            message=message,
            error_code="not_found",
            status_code=404,
            details=details,
        )
