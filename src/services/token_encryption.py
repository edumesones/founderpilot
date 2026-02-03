"""
Token encryption service using Fernet symmetric encryption.
Used to encrypt OAuth tokens before storing in database.
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from src.core.config import settings
from src.core.exceptions import FounderPilotError


class TokenEncryptionError(FounderPilotError):
    """Raised when token encryption/decryption fails."""

    def __init__(self, message: str = "Token encryption error"):
        super().__init__(
            message=message,
            error_code="encryption_error",
            status_code=500,
        )


class TokenEncryptionService:
    """
    Service for encrypting and decrypting OAuth tokens.

    Uses Fernet symmetric encryption (AES-128-CBC with HMAC).
    The encryption key should be a URL-safe base64-encoded 32-byte key.

    Example:
        >>> from cryptography.fernet import Fernet
        >>> key = Fernet.generate_key()
        >>> print(key.decode())  # Use this as ENCRYPTION_KEY env var
    """

    def __init__(self, encryption_key: str | None = None):
        """
        Initialize the encryption service.

        Args:
            encryption_key: Fernet encryption key. If not provided,
                           uses the key from settings.
        """
        key = encryption_key or settings.encryption_key
        try:
            self.fernet = Fernet(key.encode() if isinstance(key, str) else key)
        except Exception as e:
            raise TokenEncryptionError(f"Invalid encryption key: {e}")

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string.

        Args:
            plaintext: The string to encrypt (e.g., OAuth token)

        Returns:
            The encrypted string (base64-encoded)

        Raises:
            TokenEncryptionError: If encryption fails
        """
        if not plaintext:
            raise TokenEncryptionError("Cannot encrypt empty string")

        try:
            encrypted = self.fernet.encrypt(plaintext.encode("utf-8"))
            return encrypted.decode("utf-8")
        except Exception as e:
            raise TokenEncryptionError(f"Encryption failed: {e}")

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt a ciphertext string.

        Args:
            ciphertext: The encrypted string to decrypt

        Returns:
            The decrypted plaintext string

        Raises:
            TokenEncryptionError: If decryption fails (invalid key or corrupted data)
        """
        if not ciphertext:
            raise TokenEncryptionError("Cannot decrypt empty string")

        try:
            decrypted = self.fernet.decrypt(ciphertext.encode("utf-8"))
            return decrypted.decode("utf-8")
        except InvalidToken:
            raise TokenEncryptionError(
                "Decryption failed: invalid token or wrong key"
            )
        except Exception as e:
            raise TokenEncryptionError(f"Decryption failed: {e}")


# Singleton instance
_token_encryption_service: TokenEncryptionService | None = None


def get_token_encryption_service() -> TokenEncryptionService:
    """
    Get the token encryption service singleton.

    Returns:
        TokenEncryptionService instance
    """
    global _token_encryption_service
    if _token_encryption_service is None:
        _token_encryption_service = TokenEncryptionService()
    return _token_encryption_service
