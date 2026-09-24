"""
Unit tests for TokenEncryptionService.
"""

import pytest
from cryptography.fernet import Fernet

from src.services.token_encryption import (
    TokenEncryptionError,
    TokenEncryptionService,
)


class TestTokenEncryptionService:
    """Tests for TokenEncryptionService."""

    def test_encrypt_decrypt_roundtrip(self, encryption_key: str):
        """Test that encrypt followed by decrypt returns original value."""
        service = TokenEncryptionService(encryption_key)
        original = "my-secret-oauth-token-12345"

        encrypted = service.encrypt(original)
        decrypted = service.decrypt(encrypted)

        assert decrypted == original

    def test_encrypt_produces_different_output(self, encryption_key: str):
        """Test that encrypting the same value twice produces different ciphertexts."""
        service = TokenEncryptionService(encryption_key)
        plaintext = "my-secret-token"

        encrypted1 = service.encrypt(plaintext)
        encrypted2 = service.encrypt(plaintext)

        # Due to Fernet's use of IV, same plaintext produces different ciphertext
        assert encrypted1 != encrypted2

        # But both should decrypt to the same value
        assert service.decrypt(encrypted1) == plaintext
        assert service.decrypt(encrypted2) == plaintext

    def test_encrypted_value_is_different_from_original(self, encryption_key: str):
        """Test that encrypted value is not the same as the original."""
        service = TokenEncryptionService(encryption_key)
        original = "my-secret-token"

        encrypted = service.encrypt(original)

        assert encrypted != original

    def test_decrypt_with_wrong_key_fails(self, encryption_key: str):
        """Test that decryption with wrong key raises error."""
        service1 = TokenEncryptionService(encryption_key)
        different_key = Fernet.generate_key().decode()
        service2 = TokenEncryptionService(different_key)

        encrypted = service1.encrypt("secret")

        with pytest.raises(TokenEncryptionError) as exc_info:
            service2.decrypt(encrypted)

        assert "invalid token or wrong key" in str(exc_info.value).lower()

    def test_encrypt_empty_string_fails(self, encryption_key: str):
        """Test that encrypting empty string raises error."""
        service = TokenEncryptionService(encryption_key)

        with pytest.raises(TokenEncryptionError) as exc_info:
            service.encrypt("")

        assert "empty" in str(exc_info.value).lower()

    def test_decrypt_empty_string_fails(self, encryption_key: str):
        """Test that decrypting empty string raises error."""
        service = TokenEncryptionService(encryption_key)

        with pytest.raises(TokenEncryptionError) as exc_info:
            service.decrypt("")

        assert "empty" in str(exc_info.value).lower()

    def test_decrypt_invalid_ciphertext_fails(self, encryption_key: str):
        """Test that decrypting invalid ciphertext raises error."""
        service = TokenEncryptionService(encryption_key)

        with pytest.raises(TokenEncryptionError):
            service.decrypt("not-a-valid-ciphertext")

    def test_invalid_encryption_key_fails(self):
        """Test that invalid encryption key raises error."""
        with pytest.raises(TokenEncryptionError) as exc_info:
            TokenEncryptionService("not-a-valid-key")

        assert "invalid encryption key" in str(exc_info.value).lower()

    def test_handles_unicode_content(self, encryption_key: str):
        """Test encryption/decryption with unicode content."""
        service = TokenEncryptionService(encryption_key)
        original = "token-with-unicode-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

        encrypted = service.encrypt(original)
        decrypted = service.decrypt(encrypted)

        assert decrypted == original

    def test_handles_long_tokens(self, encryption_key: str):
        """Test encryption/decryption with long tokens."""
        service = TokenEncryptionService(encryption_key)
        # OAuth tokens can be quite long
        original = "a" * 2000

        encrypted = service.encrypt(original)
        decrypted = service.decrypt(encrypted)

        assert decrypted == original
