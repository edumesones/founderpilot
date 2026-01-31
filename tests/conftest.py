"""Pytest configuration and fixtures."""

import os
from datetime import datetime, timedelta
from typing import Generator
from unittest.mock import MagicMock, patch
from uuid import uuid4, UUID

import pytest
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# =============================================================================
# RSA Key Generation (FEAT-001)
# =============================================================================

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


# =============================================================================
# Environment Setup
# =============================================================================

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

# SQLite for testing
TEST_DATABASE_URL = "sqlite:///:memory:"


# =============================================================================
# Auth Fixtures (FEAT-001)
# =============================================================================

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


# =============================================================================
# Database Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def db_session():
    """Create a test database session."""
    from src.core.database import Base

    engine = create_engine(TEST_DATABASE_URL, echo=False)
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def mock_db():
    """Mock database session (for unit tests without real DB)."""
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    return db


# =============================================================================
# Common Fixtures
# =============================================================================

@pytest.fixture
def sample_user_id():
    """Sample user ID for testing."""
    return UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture
def user_id():
    """Generate a user ID for testing."""
    return uuid4()


# =============================================================================
# Slack Fixtures (FEAT-006)
# =============================================================================

@pytest.fixture
def mock_slack_client():
    """Mock Slack WebClient."""
    with patch("slack_sdk.WebClient") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client
