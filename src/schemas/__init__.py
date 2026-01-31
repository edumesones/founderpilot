# Schemas package
from src.schemas.common import BaseSchema, ErrorResponse, SuccessResponse
from src.schemas.user import UserBase, UserCreate, UserResponse, UserProfile
from src.schemas.auth import (
    TokenResponse,
    TokenPair,
    RefreshTokenRequest,
    LoginResponse,
    OAuthState,
    GoogleUserInfo,
    LogoutResponse,
)
from src.schemas.integration import (
    IntegrationStatus,
    IntegrationsStatusResponse,
    IntegrationConnect,
    IntegrationCallback,
    DisconnectResponse,
)
from src.schemas.onboarding import (
    OnboardingStep,
    OnboardingStatus,
    OnboardingCompleteResponse,
)

__all__ = [
    # Common
    "BaseSchema",
    "ErrorResponse",
    "SuccessResponse",
    # User
    "UserBase",
    "UserCreate",
    "UserResponse",
    "UserProfile",
    # Auth
    "TokenResponse",
    "TokenPair",
    "RefreshTokenRequest",
    "LoginResponse",
    "OAuthState",
    "GoogleUserInfo",
    "LogoutResponse",
    # Integration
    "IntegrationStatus",
    "IntegrationsStatusResponse",
    "IntegrationConnect",
    "IntegrationCallback",
    "DisconnectResponse",
    # Onboarding
    "OnboardingStep",
    "OnboardingStatus",
    "OnboardingCompleteResponse",
]
