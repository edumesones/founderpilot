"""
JWT service for creating and verifying access tokens.
Uses RS256 (RSA + SHA-256) for asymmetric signing.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from uuid import UUID

from jose import JWTError, jwt

from src.core.config import settings
from src.core.exceptions import InvalidTokenError, TokenExpiredError


class JWTService:
    """
    Service for creating and verifying JWT access tokens.

    Uses RS256 algorithm with RSA key pair for signing/verification.
    This allows the public key to be shared for verification while
    keeping the private key secure for signing.

    Token payload structure:
        {
            "sub": "<user_id>",        # Subject (user ID)
            "exp": <timestamp>,        # Expiration time
            "iat": <timestamp>,        # Issued at time
            "type": "access"           # Token type
        }
    """

    def __init__(
        self,
        private_key: str | None = None,
        public_key: str | None = None,
        algorithm: str | None = None,
        access_token_expire_minutes: int | None = None,
    ):
        """
        Initialize the JWT service.

        Args:
            private_key: RSA private key for signing (PEM format)
            public_key: RSA public key for verification (PEM format)
            algorithm: JWT algorithm (default: RS256)
            access_token_expire_minutes: Token expiration in minutes
        """
        self.private_key = private_key or settings.jwt_private_key
        self.public_key = public_key or settings.jwt_public_key
        self.algorithm = algorithm or settings.jwt_algorithm
        self.access_token_expire = timedelta(
            minutes=access_token_expire_minutes or settings.access_token_expire_minutes
        )

    def create_access_token(
        self,
        user_id: UUID | str,
        additional_claims: Dict[str, Any] | None = None,
    ) -> str:
        """
        Create a new access token for a user.

        Args:
            user_id: The user's UUID
            additional_claims: Optional additional claims to include

        Returns:
            The encoded JWT string
        """
        now = datetime.now(timezone.utc)
        expires = now + self.access_token_expire

        payload = {
            "sub": str(user_id),
            "exp": expires,
            "iat": now,
            "type": "access",
        }

        if additional_claims:
            payload.update(additional_claims)

        return jwt.encode(
            payload,
            self.private_key,
            algorithm=self.algorithm,
        )

    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode a JWT token.

        Args:
            token: The JWT string to verify

        Returns:
            The decoded token payload

        Raises:
            TokenExpiredError: If the token has expired
            InvalidTokenError: If the token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=[self.algorithm],
            )

            # Verify token type
            if payload.get("type") != "access":
                raise InvalidTokenError("Invalid token type")

            return payload

        except jwt.ExpiredSignatureError:
            raise TokenExpiredError("Token has expired")
        except JWTError as e:
            raise InvalidTokenError(f"Invalid token: {e}")

    def get_user_id_from_token(self, token: str) -> UUID:
        """
        Extract user ID from a token.

        Args:
            token: The JWT string

        Returns:
            The user's UUID

        Raises:
            TokenExpiredError: If the token has expired
            InvalidTokenError: If the token is invalid or missing user ID
        """
        payload = self.verify_token(token)
        user_id = payload.get("sub")

        if not user_id:
            raise InvalidTokenError("Token missing user ID")

        try:
            return UUID(user_id)
        except ValueError:
            raise InvalidTokenError("Invalid user ID in token")

    def get_token_expiration(self, token: str) -> datetime:
        """
        Get the expiration time of a token.

        Args:
            token: The JWT string

        Returns:
            The token's expiration datetime

        Raises:
            InvalidTokenError: If the token is invalid
        """
        try:
            # Decode without verification to get expiration
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False},
            )
            exp = payload.get("exp")
            if exp:
                return datetime.fromtimestamp(exp, tz=timezone.utc)
            raise InvalidTokenError("Token missing expiration")
        except JWTError as e:
            raise InvalidTokenError(f"Invalid token: {e}")


# Singleton instance
_jwt_service: JWTService | None = None


def get_jwt_service() -> JWTService:
    """
    Get the JWT service singleton.

    Returns:
        JWTService instance
    """
    global _jwt_service
    if _jwt_service is None:
        _jwt_service = JWTService()
    return _jwt_service
