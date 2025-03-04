"""Test cases for the encryption module."""

import os
from unittest.mock import MagicMock, patch

import pytest

from agentorchestrator.security.encryption import (
    DataProtectionService,
    EncryptedField,
    EncryptionError,
    EncryptionManager,
    initialize_encryption,
)


@pytest.fixture
def encryption_key() -> str:
    """Fixture to provide a test encryption key."""
    return os.urandom(32).hex()


@pytest.fixture
def encryption_manager(encryption_key: str) -> EncryptionManager:
    """Fixture to provide an initialized EncryptionManager with a test key."""
    return EncryptionManager(encryption_key)


@pytest.fixture
def data_protection() -> DataProtectionService:
    """Fixture to provide a DataProtectionService instance."""
    return DataProtectionService()


class TestEncryptionManager:
    """Tests for the EncryptionManager class."""

    def test_generate_key(self) -> None:
        """Test generating an encryption key."""
        key1 = EncryptionManager.generate_key()
        key2 = EncryptionManager.generate_key()
        key3 = EncryptionManager.generate_key()

        # Verify keys are different
        assert key1 != key2
        assert key2 != key3
        assert key1 != key3

    def test_derive_key_from_password(self) -> None:
        """Test deriving a key from a password."""
        password = "strong-password-123"
        salt = os.urandom(16)

        key1 = EncryptionManager.derive_key_from_password(password, salt)
        key2 = EncryptionManager.derive_key_from_password(password, salt)

        # Same password and salt should produce the same key
        assert key1 == key2

        # Different salt should produce a different key
        key3 = EncryptionManager.derive_key_from_password(password, os.urandom(16))
        assert key1 != key3

    def test_encrypt_decrypt_string(
        self, encryption_manager: EncryptionManager,
    ) -> None:
        """Test encrypting and decrypting a string."""
        original = "This is a secret message!"
        encrypted = encryption_manager.encrypt_string(original)
        decrypted = encryption_manager.decrypt_string(encrypted)

        # Verify decrypted matches original
        assert decrypted == original

        # Verify encrypted is different from original
        assert encrypted != original
        assert isinstance(encrypted, str)

    def test_encrypt_decrypt_different_keys(
        self, encryption_key: str,
    ) -> None:
        """Test that different keys produce different results."""
        original = "This is a secret message!"

        # Create two managers with different keys
        manager1 = EncryptionManager(encryption_key)
        manager2 = EncryptionManager(EncryptionManager.generate_key())

        # Encrypt with first manager
        encrypted = manager1.encrypt_string(original)

        # Decrypting with second manager should fail
        with pytest.raises(EncryptionError, match="Decryption failed"):
            manager2.decrypt_string(encrypted)

        # Decrypting with first manager should succeed
        decrypted = manager1.decrypt_string(encrypted)
        assert decrypted == original

    def test_encrypt_decrypt_bytes(
        self, encryption_manager: EncryptionManager,
    ) -> None:
        """Test encrypting and decrypting bytes."""
        original = b"This is a secret binary message!"
        encrypted = encryption_manager.encrypt_bytes(original)
        decrypted = encryption_manager.decrypt_bytes(encrypted)

        # Verify decrypted matches original
        assert decrypted == original

        # Verify encrypted is different from original
        assert encrypted != original
        assert isinstance(encrypted, bytes)

    def test_encrypt_decrypt_dict(
        self, encryption_manager: EncryptionManager,
    ) -> None:
        """Test encrypting and decrypting a dictionary."""
        original = {
            "name": "John Doe",
            "ssn": "123-45-6789",
            "account": "1234567890",
            "balance": 1000.50,
        }

        encrypted = encryption_manager.encrypt(original)
        decrypted = encryption_manager.decrypt(encrypted)

        # Verify decrypted matches original
        assert decrypted == original

        # Verify encrypted is different from original
        assert encrypted != original
        assert isinstance(encrypted, str)

    def test_encrypt_decrypt_list(
        self, encryption_manager: EncryptionManager,
    ) -> None:
        """Test encrypting and decrypting a list."""
        original = ["John", "123-45-6789", "1234567890", 1000.50]
        encrypted = encryption_manager.encrypt(original)
        decrypted = encryption_manager.decrypt(encrypted)

        # Verify decrypted matches original
        assert decrypted == original

        # Verify encrypted is different from original
        assert encrypted != original
        assert isinstance(encrypted, str)


class TestEncryptedField:
    """Tests for the EncryptedField class."""

    def test_encrypted_field(
        self, encryption_manager: EncryptionManager,
    ) -> None:
        """Test the EncryptedField class."""
        # Create an encrypted field
        field = EncryptedField(encryption_manager)

        # Test data
        original = "sensitive data"

        # Test encryption
        encrypted = field.encrypt(original)
        assert encrypted != original
        assert isinstance(encrypted, str)

        # Test decryption
        decrypted = field.decrypt(encrypted)
        assert decrypted == original


class TestDataProtectionService:
    """Tests for the DataProtectionService class."""

    def test_encrypt_decrypt_fields(
        self, data_protection: DataProtectionService,
        encryption_manager: EncryptionManager,
    ) -> None:
        """Test encrypting and decrypting specific fields in a dictionary."""
        # Set the encryption manager
        data_protection.encryption_manager = encryption_manager

        # Test data
        data = {
            "name": "John Doe",
            "ssn": "123-45-6789",
            "account": "1234567890",
            "public_info": "not sensitive",
        }

        sensitive_fields = ["ssn", "account"]

        # Encrypt the fields
        protected_data = data_protection.encrypt_fields(
            data, sensitive_fields,
        )

        # Verify non-sensitive fields are unchanged
        assert protected_data["name"] == data["name"]
        assert protected_data["public_info"] == data["public_info"]

        # Verify sensitive fields are encrypted
        assert protected_data["ssn"] != data["ssn"]
        assert protected_data["account"] != data["account"]

        # Decrypt the fields
        decrypted_data = data_protection.decrypt_fields(
            protected_data, sensitive_fields,
        )

        # Verify decrypted data matches original
        assert decrypted_data == data

    def test_mask_pii(
        self, data_protection: DataProtectionService,
    ) -> None:
        """Test masking personally identifiable information (PII)."""
        # Sample text with PII
        text = """Customer John Doe with SSN 123-45-6789 and
                credit card 4111-1111-1111-1111 has account number 1234567890.
                Contact them at john.doe@example.com or 555-123-4567."""

        # Mask PII
        masked = data_protection.mask_pii(text)

        # Verify PII is masked
        assert "123-45-6789" not in masked
        assert "4111-1111-1111-1111" not in masked
        assert "1234567890" not in masked
        assert "john.doe@example.com" not in masked
        assert "555-123-4567" not in masked

        # Verify non-PII text remains
        assert "Customer" in masked
        assert "with SSN" in masked
        assert "has account number" in masked
        assert "Contact them at" in masked


@patch.dict(os.environ, {})
def test_initialize_encryption_new_key() -> None:
    """Test initializing encryption without an existing key."""
    with patch("agentorchestrator.security.encryption.Encryptor") as mock_manager_class:
        # Mock the manager
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        # Initialize encryption
        manager = initialize_encryption()

        # Verify manager was created with a new key
        assert manager == mock_manager
        mock_manager_class.assert_called_once()
        assert "ENCRYPTION_KEY" in os.environ


@patch.dict(os.environ, {"ENCRYPTION_KEY": "existing-key"})
def test_initialize_encryption_existing_key() -> None:
    """Test initializing encryption with an existing key."""
    with patch("agentorchestrator.security.encryption.Encryptor") as mock_manager_class:
        # Mock the manager
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        # Initialize encryption
        manager = initialize_encryption()

        # Verify manager was created with existing key
        assert manager == mock_manager
        mock_manager_class.assert_called_once_with("existing-key")
