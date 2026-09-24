"""
Unit tests for JWTService.
"""

import time
from datetime import timedelta
from uuid import uuid4

import pytest

from src.core.exceptions import InvalidTokenError, TokenExpiredError
from src.services.jwt import JWTService


class TestJWTService:
    """Tests for JWTService."""

    def test_create_and_verify_token(self, rsa_keys: tuple[str, str]):
        """Test that creating and verifying a token works."""
        private_key, public_key = rsa_keys
        service = JWTService(
            private_key=private_key,
            public_key=public_key,
        )
        user_id = uuid4()

        token = service.create_access_token(user_id)
        payload = service.verify_token(token)

        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"

    def test_token_contains_required_claims(self, rsa_keys: tuple[str, str]):
        """Test that token contains all required claims."""
        private_key, public_key = rsa_keys
        service = JWTService(
            private_key=private_key,
            public_key=public_key,
        )
        user_id = uuid4()

        token = service.create_access_token(user_id)
        payload = service.verify_token(token)

        assert "sub" in payload
        assert "exp" in payload
        assert "iat" in payload
        assert "type" in payload

    def test_get_user_id_from_token(self, rsa_keys: tuple[str, str]):
        """Test extracting user ID from token."""
        private_key, public_key = rsa_keys
        service = JWTService(
            private_key=private_key,
            public_key=public_key,
        )
        user_id = uuid4()

        token = service.create_access_token(user_id)
        extracted_id = service.get_user_id_from_token(token)

        assert extracted_id == user_id

    def test_expired_token_raises_error(self, rsa_keys: tuple[str, str]):
        """Test that expired token raises TokenExpiredError."""
        private_key, public_key = rsa_keys
        # Create service with very short expiration
        service = JWTService(
            private_key=private_key,
            public_key=public_key,
            access_token_expire_minutes=0,  # Expires immediately
        )
        user_id = uuid4()

        token = service.create_access_token(user_id)
        time.sleep(1)  # Wait for expiration

        with pytest.raises(TokenExpiredError):
            service.verify_token(token)

    def test_invalid_token_raises_error(self, rsa_keys: tuple[str, str]):
        """Test that invalid token raises InvalidTokenError."""
        private_key, public_key = rsa_keys
        service = JWTService(
            private_key=private_key,
            public_key=public_key,
        )

        with pytest.raises(InvalidTokenError):
            service.verify_token("not-a-valid-token")

    def test_tampered_token_raises_error(self, rsa_keys: tuple[str, str]):
        """Test that tampered token raises InvalidTokenError."""
        private_key, public_key = rsa_keys
        service = JWTService(
            private_key=private_key,
            public_key=public_key,
        )
        user_id = uuid4()

        token = service.create_access_token(user_id)
        # Tamper with the token
        tampered = token[:-5] + "XXXXX"

        with pytest.raises(InvalidTokenError):
            service.verify_token(tampered)

    def test_token_with_wrong_key_raises_error(self, rsa_keys: tuple[str, str]):
        """Test that token signed with different key raises error."""
        private_key1, public_key1 = rsa_keys
        # Generate different key pair
        from tests.conftest import generate_rsa_keys
        private_key2, public_key2 = generate_rsa_keys()

        service1 = JWTService(private_key=private_key1, public_key=public_key1)
        service2 = JWTService(private_key=private_key2, public_key=public_key2)

        token = service1.create_access_token(uuid4())

        with pytest.raises(InvalidTokenError):
            service2.verify_token(token)

    def test_additional_claims_included(self, rsa_keys: tuple[str, str]):
        """Test that additional claims are included in token."""
        private_key, public_key = rsa_keys
        service = JWTService(
            private_key=private_key,
            public_key=public_key,
        )
        user_id = uuid4()
        additional = {"role": "admin", "org_id": "org-123"}

        token = service.create_access_token(user_id, additional_claims=additional)
        payload = service.verify_token(token)

        assert payload["role"] == "admin"
        assert payload["org_id"] == "org-123"

    def test_get_token_expiration(self, rsa_keys: tuple[str, str]):
        """Test getting token expiration time."""
        private_key, public_key = rsa_keys
        service = JWTService(
            private_key=private_key,
            public_key=public_key,
            access_token_expire_minutes=60,
        )
        user_id = uuid4()

        token = service.create_access_token(user_id)
        expiration = service.get_token_expiration(token)

        # Should expire roughly 60 minutes from now
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        diff = (expiration - now).total_seconds()
        assert 3500 < diff < 3700  # Allow some variance

    def test_user_id_string_accepted(self, rsa_keys: tuple[str, str]):
        """Test that user ID as string is accepted."""
        private_key, public_key = rsa_keys
        service = JWTService(
            private_key=private_key,
            public_key=public_key,
        )
        user_id = str(uuid4())

        token = service.create_access_token(user_id)
        payload = service.verify_token(token)

        assert payload["sub"] == user_id
