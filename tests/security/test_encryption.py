import pytest
import os
import base64
from unittest.mock import MagicMock, patch

from agentorchestrator.security.encryption import (
    Encryptor, EncryptedField, DataProtectionService,
    initialize_encryption
)


@pytest.fixture
def encryption_key():
    """Fixture to provide a test encryption key."""
    return base64.b64encode(os.urandom(32)).decode('utf-8')


@pytest.fixture
def encryption_manager(encryption_key):
    """Fixture to provide an initialized EncryptionManager with a test key."""
    return Encryptor(encryption_key)


@pytest.fixture
def data_protection():
    """Fixture to provide a DataProtectionService instance."""
    return DataProtectionService()


class TestEncryptionManager:
    """Tests for the EncryptionManager class."""
    
    def test_generate_key(self):
        """Test generating a new encryption key."""
        key = Encryptor.generate_key()
        # Key should be a base64-encoded string
        assert isinstance(key, str)
        # Key should be 44 characters (32 bytes in base64)
        assert len(base64.b64decode(key)) == 32
        
    def test_derive_key_from_password(self):
        """Test deriving a key from a password."""
        password = "strong-password-123"
        salt = os.urandom(16)
        
        key1 = Encryptor.derive_key_from_password(password, salt)
        key2 = Encryptor.derive_key_from_password(password, salt)
        
        # Same password and salt should produce the same key
        assert key1 == key2
        
        # Different salt should produce a different key
        key3 = Encryptor.derive_key_from_password(password, os.urandom(16))
        assert key1 != key3
        
    def test_encrypt_decrypt_string(self, encryption_manager):
        """Test encrypting and decrypting a string."""
        original = "This is a secret message!"
        
        # Encrypt the string
        encrypted = encryption_manager.encrypt_string(original)
        
        # Encrypted value should be different from original
        assert encrypted != original
        
        # Decrypt the string
        decrypted = encryption_manager.decrypt_string(encrypted)
        
        # Decrypted value should match original
        assert decrypted == original
        
    def test_encrypt_decrypt_different_keys(self, encryption_key):
        """Test that different keys produce different results."""
        original = "This is a secret message!"
        
        # Create two managers with different keys
        manager1 = Encryptor(encryption_key)
        manager2 = Encryptor(Encryptor.generate_key())
        
        # Encrypt with first manager
        encrypted = manager1.encrypt_string(original)
        
        # Decrypting with second manager should fail
        with pytest.raises(Exception):
            manager2.decrypt_string(encrypted)
            
        # Decrypting with first manager should work
        decrypted = manager1.decrypt_string(encrypted)
        assert decrypted == original
        
    def test_encrypt_decrypt_bytes(self, encryption_manager):
        """Test encrypting and decrypting bytes."""
        original = b"This is a secret binary message!"
        
        # Encrypt the bytes
        encrypted = encryption_manager.encrypt_bytes(original)
        
        # Encrypted value should be different from original
        assert encrypted != original
        
        # Decrypt the bytes
        decrypted = encryption_manager.decrypt_bytes(encrypted)
        
        # Decrypted value should match original
        assert decrypted == original
        
    def test_encrypt_decrypt_dict(self, encryption_manager):
        """Test encrypting and decrypting a dictionary."""
        original = {
            "name": "John Doe",
            "ssn": "123-45-6789",
            "account": "1234567890",
            "balance": 1000.50
        }
        
        # Encrypt the dictionary
        encrypted = encryption_manager.encrypt_dict(original)
        
        # Encrypted dictionary should have same keys but different values
        assert set(encrypted.keys()) == set(original.keys())
        assert encrypted["name"] != original["name"]
        assert encrypted["ssn"] != original["ssn"]
        
        # Decrypt the dictionary
        decrypted = encryption_manager.decrypt_dict(encrypted)
        
        # Decrypted dictionary should match original
        assert decrypted == original
        
    def test_encrypt_decrypt_list(self, encryption_manager):
        """Test encrypting and decrypting a list."""
        original = ["John", "123-45-6789", "1234567890", 1000.50]
        
        # Encrypt the list
        encrypted = encryption_manager.encrypt_list(original)
        
        # Encrypted list should have same length but different values
        assert len(encrypted) == len(original)
        assert encrypted[0] != original[0]
        assert encrypted[1] != original[1]
        
        # Decrypt the list
        decrypted = encryption_manager.decrypt_list(encrypted)
        
        # Decrypted list should match original
        assert decrypted == original


class TestEncryptedField:
    """Tests for the EncryptedField class."""
    
    def test_encrypted_field(self, encryption_manager):
        """Test the EncryptedField class."""
        # Create an encrypted field
        field = EncryptedField(encryption_manager)
        
        # Test encrypting a value
        original = "sensitive data"
        encrypted = field.encrypt(original)
        
        # Encrypted value should be different
        assert encrypted != original
        
        # Test decrypting a value
        decrypted = field.decrypt(encrypted)
        
        # Decrypted value should match original
        assert decrypted == original


class TestDataProtectionService:
    """Tests for the DataProtectionService class."""
    
    def test_encrypt_decrypt_fields(self, data_protection, encryption_manager):
        """Test encrypting and decrypting specific fields in a dictionary."""
        # Set the encryption manager
        data_protection.encryption_manager = encryption_manager
        
        # Create a test data dictionary
        data = {
            "name": "John Doe",
            "ssn": "123-45-6789",
            "account": "1234567890",
            "balance": 1000.50
        }
        
        # Encrypt specific fields
        sensitive_fields = ["ssn", "account"]
        protected_data = data_protection.encrypt_fields(data, sensitive_fields)
        
        # Check that specified fields are encrypted and others are not
        assert protected_data["ssn"] != data["ssn"]
        assert protected_data["account"] != data["account"]
        assert protected_data["name"] == data["name"]
        assert protected_data["balance"] == data["balance"]
        
        # Decrypt the fields
        decrypted_data = data_protection.decrypt_fields(protected_data, sensitive_fields)
        
        # Check that decrypted data matches original
        assert decrypted_data == data
        
    def test_mask_pii(self, data_protection):
        """Test masking personally identifiable information (PII)."""
        # Sample text with PII
        text = """Customer John Doe with SSN 123-45-6789 and 
                 credit card 4111-1111-1111-1111 has account number 1234567890.
                 Contact them at john.doe@example.com or 555-123-4567."""
        
        # Mask PII
        masked_text = data_protection.mask_pii(text)
        
        # Check that PII is masked
        assert "John Doe" not in masked_text
        assert "123-45-6789" not in masked_text
        assert "4111-1111-1111-1111" not in masked_text
        assert "1234567890" not in masked_text
        assert "john.doe@example.com" not in masked_text
        assert "555-123-4567" not in masked_text
        
        # Check that masking indicators are present
        assert "[NAME]" in masked_text
        assert "[SSN]" in masked_text
        assert "[CC]" in masked_text
        assert "[ACCOUNT]" in masked_text or "[NUMBER]" in masked_text
        assert "[EMAIL]" in masked_text
        assert "[PHONE]" in masked_text


@patch.dict(os.environ, {})
def test_initialize_encryption_new_key():
    """Test initializing encryption without an existing key."""
    with patch('agentorchestrator.security.encryption.Encryptor') as mock_manager_class:
        # Set up mocks
        mock_manager_class.generate_key.return_value = "test-key"
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        
        # Call the initialize function
        manager = initialize_encryption()
        
        # Verify a new key was generated
        mock_manager_class.generate_key.assert_called_once()
        mock_manager_class.assert_called_once_with("test-key")
        assert manager == mock_manager


@patch.dict(os.environ, {"ENCRYPTION_KEY": "existing-key"})
def test_initialize_encryption_existing_key():
    """Test initializing encryption with an existing key."""
    with patch('agentorchestrator.security.encryption.Encryptor') as mock_manager_class:
        # Set up mocks
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        
        # Call the initialize function
        manager = initialize_encryption()
        
        # Verify the existing key was used
        mock_manager_class.generate_key.assert_not_called()
        mock_manager_class.assert_called_once_with("existing-key")
        assert manager == mock_manager