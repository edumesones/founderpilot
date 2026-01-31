"""Unit tests for SlackService."""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from uuid import UUID
from datetime import datetime

from src.services.slack_service import SlackService, SlackNotConnectedError
from src.models.slack_installation import SlackInstallation
from src.schemas.slack import SlackStatusResponse


class TestSlackServiceGetStatus:
    """Tests for SlackService.get_status()."""

    def test_get_status_not_connected(self, mock_db, sample_user_id):
        """Test status when user has no Slack connection."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        service = SlackService(db=mock_db)
        status = service.get_status(sample_user_id)

        assert status.connected is False
        assert status.team_name is None

    def test_get_status_connected(self, mock_db, sample_user_id):
        """Test status when user has active Slack connection."""
        # Create mock installation
        mock_installation = MagicMock(spec=SlackInstallation)
        mock_installation.is_connected = True
        mock_installation.is_active = True
        mock_installation.team_name = "Test Workspace"
        mock_installation.team_id = "T12345"
        mock_installation.installed_at = datetime.utcnow()
        mock_installation.bot_access_token = "encrypted-token"

        mock_db.query.return_value.filter.return_value.first.return_value = mock_installation

        service = SlackService(db=mock_db)
        status = service.get_status(sample_user_id)

        assert status.connected is True
        assert status.team_name == "Test Workspace"
        assert status.team_id == "T12345"


class TestSlackServiceGetInstallation:
    """Tests for SlackService.get_installation()."""

    def test_get_installation_exists(self, mock_db, sample_user_id):
        """Test getting existing installation."""
        mock_installation = MagicMock(spec=SlackInstallation)
        mock_installation.is_active = True

        mock_db.query.return_value.filter.return_value.first.return_value = mock_installation

        service = SlackService(db=mock_db)
        result = service.get_installation(sample_user_id)

        assert result is not None
        assert result.is_active is True

    def test_get_installation_not_found(self, mock_db, sample_user_id):
        """Test getting non-existent installation."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        service = SlackService(db=mock_db)
        result = service.get_installation(sample_user_id)

        assert result is None


class TestSlackServiceDisconnect:
    """Tests for SlackService.disconnect()."""

    def test_disconnect_success(self, mock_db, sample_user_id):
        """Test successful disconnection."""
        mock_installation = MagicMock(spec=SlackInstallation)
        mock_installation.is_active = True

        mock_db.query.return_value.filter.return_value.first.return_value = mock_installation

        service = SlackService(db=mock_db)
        result = service.disconnect(sample_user_id)

        assert result is True
        assert mock_installation.is_active is False
        mock_db.commit.assert_called_once()

    def test_disconnect_not_found(self, mock_db, sample_user_id):
        """Test disconnection when no installation exists."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        service = SlackService(db=mock_db)
        result = service.disconnect(sample_user_id)

        assert result is False


class TestSlackServiceEncryption:
    """Tests for encryption/decryption."""

    def test_encrypt_decrypt_roundtrip(self):
        """Test that encryption and decryption work correctly."""
        with patch.dict("os.environ", {"ENCRYPTION_KEY": "dGVzdC1lbmNyeXB0aW9uLWtleS0zMi1ieXRlcw=="}):
            from cryptography.fernet import Fernet

            # Generate a valid Fernet key
            key = Fernet.generate_key().decode()

            with patch("src.core.config.settings") as mock_settings:
                mock_settings.ENCRYPTION_KEY = key

                service = SlackService()
                original = "secret-token-12345"

                encrypted = service._encrypt(original)
                assert encrypted != original

                decrypted = service._decrypt(encrypted)
                assert decrypted == original

    def test_encrypt_without_key(self):
        """Test encryption returns original when no key configured."""
        with patch("src.core.config.settings") as mock_settings:
            mock_settings.ENCRYPTION_KEY = None

            service = SlackService()
            original = "secret-token-12345"

            encrypted = service._encrypt(original)
            assert encrypted == original


class TestSlackServiceSendNotification:
    """Tests for SlackService.send_notification()."""

    @pytest.mark.asyncio
    async def test_send_notification_not_connected(self, mock_db, sample_user_id, sample_email_payload):
        """Test sending notification when not connected raises error."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        service = SlackService(db=mock_db)

        with pytest.raises(SlackNotConnectedError):
            await service.send_notification(sample_user_id, sample_email_payload)

    @pytest.mark.asyncio
    async def test_send_notification_success(
        self,
        mock_db,
        mock_slack_client,
        sample_user_id,
        sample_email_payload,
    ):
        """Test successful notification sending."""
        # Setup mock installation
        mock_installation = MagicMock(spec=SlackInstallation)
        mock_installation.is_connected = True
        mock_installation.is_active = True
        mock_installation.bot_access_token = "encrypted-token"
        mock_installation.dm_channel_id = "D12345"
        mock_installation.user_slack_id = "U12345"

        mock_db.query.return_value.filter.return_value.first.return_value = mock_installation

        # Mock Slack client response
        mock_slack_client.chat_postMessage.return_value = {"ts": "1234567890.123456"}

        service = SlackService(db=mock_db)

        # Mock decryption
        with patch.object(service, "_decrypt", return_value="real-token"):
            result = await service.send_notification(sample_user_id, sample_email_payload)

        assert result == "1234567890.123456"
