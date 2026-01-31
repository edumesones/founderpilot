"""
Test configuration and fixtures.
"""

import os
from typing import Generator
from unittest.mock import MagicMock

import pytest
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def generate_rsa_keys() -> tuple[str, str]:
    """Generate RSA key pair for testing."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    return private_pem, public_pem


# Generate test RSA keys
TEST_PRIVATE_KEY, TEST_PUBLIC_KEY = generate_rsa_keys()

# Set test environment variables before importing settings
os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["GOOGLE_CLIENT_ID"] = "test-google-client-id"
os.environ["GOOGLE_CLIENT_SECRET"] = "test-google-client-secret"
os.environ["SLACK_CLIENT_ID"] = "test-slack-client-id"
os.environ["SLACK_CLIENT_SECRET"] = "test-slack-client-secret"
os.environ["SLACK_SIGNING_SECRET"] = "test-slack-signing-secret"
os.environ["JWT_PRIVATE_KEY"] = TEST_PRIVATE_KEY
os.environ["JWT_PUBLIC_KEY"] = TEST_PUBLIC_KEY


@pytest.fixture
def encryption_key() -> str:
    """Generate a fresh encryption key for tests."""
    return Fernet.generate_key().decode()


@pytest.fixture
def rsa_keys() -> tuple[str, str]:
    """Generate fresh RSA key pair for tests."""
    return generate_rsa_keys()


@pytest.fixture
def mock_redis() -> Generator[MagicMock, None, None]:
    """Create a mock Redis client."""
    mock = MagicMock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = True
    mock.setex.return_value = True
    yield mock
