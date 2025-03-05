"""Test cases for the encryption module."""

import os
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet

from agentorchestrator.security.encryption import (
    Encryptor,
    EncryptionError,
    initialize_encryption,
    EncryptedField,
    DataProtectionService,
)


@pytest.fixture
def encryption_key():
    """Fixture to provide a valid Fernet key."""
    return Fernet.generate_key().decode()


@pytest.fixture
def encryptor(encryption_key):
    """Fixture to provide an initialized Encryptor."""
    return Encryptor(encryption_key)


@pytest.fixture
def encrypted_field(encryptor):
    """Fixture to provide an initialized EncryptedField."""
    return EncryptedField(encryptor)


@pytest.fixture
def data_protection_service(encryptor):
    """Fixture to provide an initialized DataProtectionService."""
    return DataProtectionService(encryptor)


class TestEncryptor:
    """Tests for the Encryptor class."""

    def test_encryptor_initialization(self, encryption_key):
        """Test Encryptor initialization."""
        # Test with provided key
        encryptor = Encryptor(encryption_key)
        assert encryptor.fernet is not None

    def test_encryptor_initialization_invalid_key(self):
        """Test Encryptor initialization with invalid key."""
        with pytest.raises(ValueError):
            Encryptor("invalid_key")

    def test_encryptor_initialization_empty_key(self):
        """Test Encryptor initialization with empty key."""
        with pytest.raises(ValueError, match="Encryption key cannot be empty"):
            Encryptor("")

    def test_encryptor_initialization_no_key(self):
        """Test Encryptor initialization without key."""
        encryptor = Encryptor()
        assert encryptor.fernet is not None
        assert encryptor.key is not None

    def test_encrypt_decrypt(self, encryptor):
        """Test encryption and decryption."""
        original_data = "sensitive data"
        encrypted = encryptor.encrypt(original_data)
        decrypted = encryptor.decrypt(encrypted)

        assert encrypted != original_data
        assert decrypted == original_data

    def test_encrypt_decrypt_empty(self, encryptor):
        """Test encryption and decryption of empty string."""
        original_data = ""
        encrypted = encryptor.encrypt(original_data)
        decrypted = encryptor.decrypt(encrypted)

        assert encrypted != original_data
        assert decrypted == original_data

    def test_encrypt_decrypt_different_keys(self):
        """Test that different keys produce different results."""
        key1 = Fernet.generate_key().decode()
        key2 = Fernet.generate_key().decode()

        encryptor1 = Encryptor(key1)
        encryptor2 = Encryptor(key2)

        original = "This is a secret message!"
        encrypted1 = encryptor1.encrypt(original)
        encrypted2 = encryptor2.encrypt(original)

        assert encrypted1 != encrypted2
        assert encryptor1.decrypt(encrypted1) == original
        assert encryptor2.decrypt(encrypted2) == original

    def test_get_key(self, encryptor):
        """Test getting the encryption key."""
        key = encryptor.get_key()
        assert isinstance(key, str)
        assert len(key) > 0


class TestEncryptedField:
    """Tests for the EncryptedField class."""

    def test_encrypt_decrypt(self, encrypted_field):
        """Test field encryption and decryption."""
        original_value = "sensitive value"
        encrypted = encrypted_field.encrypt(original_value)
        decrypted = encrypted_field.decrypt(encrypted)

        assert encrypted != original_value
        assert decrypted == original_value

    def test_encrypt_decrypt_json(self, encrypted_field):
        """Test field encryption and decryption of JSON data."""
        original_value = {"key": "value"}
        encrypted = encrypted_field.encrypt(original_value)
        decrypted = encrypted_field.decrypt(encrypted)

        assert encrypted != str(original_value)
        assert decrypted == str(original_value)

    def test_decrypt_invalid_data(self, encrypted_field):
        """Test decrypting invalid data."""
        with pytest.raises(ValueError):
            encrypted_field.decrypt("invalid_data")


class TestDataProtectionService:
    """Tests for the DataProtectionService class."""

    def test_encrypt_sensitive_data(self, data_protection_service):
        """Test encrypting sensitive data."""
        data = {
            "name": "John Doe",
            "ssn": "123-45-6789",
            "credit_card": "4111-1111-1111-1111",
        }
        sensitive_fields = ["ssn", "credit_card"]

        encrypted_data = data_protection_service.encrypt_sensitive_data(
            data, sensitive_fields
        )

        assert encrypted_data["name"] == "John Doe"
        assert encrypted_data["ssn"] != "123-45-6789"
        assert encrypted_data["credit_card"] != "4111-1111-1111-1111"

    def test_decrypt_sensitive_data(self, data_protection_service):
        """Test decrypting sensitive data."""
        # First encrypt the data
        data = {
            "name": "John Doe",
            "ssn": "123-45-6789",
            "credit_card": "4111-1111-1111-1111",
        }
        sensitive_fields = ["ssn", "credit_card"]
        encrypted_data = data_protection_service.encrypt_sensitive_data(
            data, sensitive_fields
        )

        # Then decrypt it
        decrypted_data = data_protection_service.decrypt_sensitive_data(
            encrypted_data, sensitive_fields
        )

        assert decrypted_data["name"] == "John Doe"
        assert decrypted_data["ssn"] == "123-45-6789"
        assert decrypted_data["credit_card"] == "4111-1111-1111-1111"

    def test_decrypt_sensitive_data_invalid(self, data_protection_service):
        """Test decrypting invalid data."""
        data = {
            "name": "John Doe",
            "ssn": "invalid_encrypted_data",
            "credit_card": "invalid_encrypted_data",
        }
        sensitive_fields = ["ssn", "credit_card"]

        decrypted_data = data_protection_service.decrypt_sensitive_data(
            data, sensitive_fields
        )

        assert decrypted_data["name"] == "John Doe"
        assert decrypted_data["ssn"] is None
        assert decrypted_data["credit_card"] is None

    def test_mask_pii(self, data_protection_service):
        """Test PII masking."""
        text = "SSN: 123-45-6789, CC: 4111-1111-1111-1111"
        masked = data_protection_service.mask_pii(text)

        assert "123-45-6789" not in masked
        assert "4111-1111-1111-1111" not in masked
        assert len(masked) == len(text)

    def test_mask_pii_custom_char(self, data_protection_service):
        """Test PII masking with custom mask character."""
        text = "SSN: 123-45-6789, CC: 4111-1111-1111-1111"
        masked = data_protection_service.mask_pii(text, mask_char="#")

        assert "123-45-6789" not in masked
        assert "4111-1111-1111-1111" not in masked
        assert "#" in masked


def test_initialize_encryption():
    """Test encryption initialization."""
    # Test successful initialization
    test_key = Fernet.generate_key().decode()
    with patch.dict(os.environ, {"ENCRYPTION_KEY": test_key}):
        encryptor = initialize_encryption()
        assert encryptor is not None

    # Test missing key
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(EncryptionError):
            initialize_encryption()

    # Test invalid key
    with patch.dict(os.environ, {"ENCRYPTION_KEY": "invalid_key"}):
        with pytest.raises(EncryptionError):
            initialize_encryption()
