"""
Encryption Module for AORBIT.

This module provides encryption services for sensitive data,
supporting both at-rest and in-transit encryption for financial applications.
"""

import base64
import json
import logging
import os
from typing import Any

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Set up logger
logger = logging.getLogger("aorbit.encryption")


class Encryptor:
    """Simple encryption service for sensitive data."""

    def __init__(self, key: str | None = None):
        """Initialize the encryptor.

        Args:
            key: Base64-encoded encryption key, or None to generate a new one
        """
        self._key = key or self._generate_key()
        self._fernet = Fernet(
            self._key.encode() if isinstance(self._key, str) else self._key
        )

    def get_key(self) -> str:
        """Get the encryption key.

        Returns:
            Base64-encoded encryption key
        """
        return self._key

    @staticmethod
    def _generate_key() -> str:
        """Generate a new encryption key.

        Returns:
            Base64-encoded encryption key
        """
        key = Fernet.generate_key()
        return key.decode()

    @staticmethod
    def derive_key_from_password(
        password: str, salt: bytes | None = None
    ) -> dict[str, str]:
        """Derive an encryption key from a password.

        Args:
            password: Password to derive key from
            salt: Salt to use, or None to generate a new one

        Returns:
            Dictionary with 'key' and 'salt'
        """
        if salt is None:
            salt = os.urandom(16)

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend(),
        )

        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return {
            "key": key.decode(),
            "salt": base64.b64encode(salt).decode(),
        }

    def encrypt(self, data: str | bytes | dict | Any) -> str:
        """Encrypt data.

        Args:
            data: Data to encrypt (string, bytes, or JSON-serializable object)

        Returns:
            Base64-encoded encrypted data
        """
        if isinstance(data, dict):
            data = json.dumps(data)

        if not isinstance(data, bytes):
            data = str(data).encode()

        encrypted = self._fernet.encrypt(data)
        return base64.b64encode(encrypted).decode()

    def decrypt(self, encrypted_data: str) -> bytes:
        """Decrypt data.

        Args:
            encrypted_data: Base64-encoded encrypted data

        Returns:
            Decrypted data as bytes
        """
        try:
            decoded = base64.b64decode(encrypted_data)
            return self._fernet.decrypt(decoded)
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise ValueError("Failed to decrypt data") from e

    def decrypt_to_string(self, encrypted_data: str) -> str:
        """Decrypt data to string.

        Args:
            encrypted_data: Base64-encoded encrypted data

        Returns:
            Decrypted data as string
        """
        return self.decrypt(encrypted_data).decode()

    def decrypt_to_json(self, encrypted_data: str) -> dict:
        """Decrypt data to JSON.

        Args:
            encrypted_data: Base64-encoded encrypted data

        Returns:
            Decrypted data as JSON
        """
        return json.loads(self.decrypt_to_string(encrypted_data))


def initialize_encryption(encryption_key: str | None = None) -> Encryptor | None:
    """Initialize the encryption service.

    Args:
        encryption_key: Optional encryption key to use

    Returns:
        Initialized Encryptor or None if encryption is not configured
    """
    # Get key from environment if not provided
    if encryption_key is None:
        encryption_key = os.environ.get("AORBIT_ENCRYPTION_KEY")

    try:
        if not encryption_key:
            # Generate a key for development environments
            logger.warning(
                "No encryption key provided, generating a new one. This is not recommended for production."
            )
            encryptor = Encryptor()
            logger.info(
                f"Generated new encryption key. Use this key for consistent encryption: {encryptor.get_key()}"
            )
        else:
            encryptor = Encryptor(key=encryption_key)
            logger.info("Encryption service initialized with provided key")

        return encryptor
    except Exception as e:
        logger.error(f"Failed to initialize encryption: {e}")
        return None


class EncryptedField:
    """Helper for handling encrypted fields in database models."""

    def __init__(self, encryption_manager: Encryptor):
        """Initialize the encrypted field.

        Args:
            encryption_manager: Encryption manager to use
        """
        self.encryption_manager = encryption_manager

    def encrypt(self, value: Any) -> str:
        """Encrypt a value.

        Args:
            value: Value to encrypt

        Returns:
            Encrypted value
        """
        return self.encryption_manager.encrypt(value)

    def decrypt(self, value: str) -> Any:
        """Decrypt a value.

        Args:
            value: Encrypted value

        Returns:
            Decrypted value
        """
        try:
            # Try to decode as JSON first
            return self.encryption_manager.decrypt_to_json(value)
        except (json.JSONDecodeError, ValueError):
            # If not JSON, return as string
            return self.encryption_manager.decrypt_to_string(value)


class DataProtectionService:
    """Service for protecting and anonymizing sensitive data."""

    def __init__(self, encryption_manager: Encryptor):
        """Initialize the data protection service.

        Args:
            encryption_manager: Encryption manager instance
        """
        self.encryption_manager = encryption_manager

    def encrypt_sensitive_data(
        self, data: dict[str, Any], sensitive_fields: list
    ) -> dict[str, Any]:
        """Encrypt sensitive fields in a data dictionary.

        Args:
            data: Data dictionary
            sensitive_fields: List of sensitive field names to encrypt

        Returns:
            Data with sensitive fields encrypted
        """
        result = data.copy()

        for field in sensitive_fields:
            if field in result and result[field] is not None:
                result[field] = self.encryption_manager.encrypt(result[field])

        return result

    def decrypt_sensitive_data(
        self, data: dict[str, Any], sensitive_fields: list
    ) -> dict[str, Any]:
        """Decrypt sensitive fields in a data dictionary.

        Args:
            data: Data dictionary with encrypted fields
            sensitive_fields: List of encrypted field names to decrypt

        Returns:
            Data with sensitive fields decrypted
        """
        result = data.copy()

        for field in sensitive_fields:
            if field in result and result[field] is not None:
                try:
                    result[field] = self.encryption_manager.decrypt_to_str(
                        result[field]
                    )
                    # Try to parse as JSON if possible
                    try:
                        result[field] = json.loads(result[field])
                    except json.JSONDecodeError:
                        pass
                except Exception as e:
                    logger.error(f"Failed to decrypt field {field}: {e}")
                    result[field] = None

        return result

    def mask_pii(self, text: str, mask_char: str = "*") -> str:
        """Mask personally identifiable information in text.

        Args:
            text: Text to mask
            mask_char: Character to use for masking

        Returns:
            Masked text
        """
        # This is a placeholder implementation
        # In a real system, this would use regex patterns or ML models to detect and mask PII
        # For now, we'll just provide a simple implementation for credit card numbers and SSNs

        import re

        # Mask credit card numbers
        cc_pattern = r"\b(?:\d{4}[-\s]){3}\d{4}\b|\b\d{16}\b"
        masked_text = re.sub(cc_pattern, lambda m: mask_char * len(m.group(0)), text)

        # Mask SSNs (US Social Security Numbers)
        ssn_pattern = r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b"
        masked_text = re.sub(
            ssn_pattern, lambda m: mask_char * len(m.group(0)), masked_text
        )

        return masked_text


def initialize_encryption(env_key_name: str = "ENCRYPTION_KEY") -> Encryptor:
    """Initialize the encryption manager.

    Args:
        env_key_name: Name of the environment variable containing the encryption key

    Returns:
        Initialized encryption manager
    """
    key = os.environ.get(env_key_name)

    if not key:
        logger.warning(
            f"No encryption key found in environment variable {env_key_name}. "
            "Generating a new key. This is not recommended for production.",
        )
        encryption_manager = Encryptor()
        logger.info(
            f"Generated new encryption key. Set {env_key_name}={encryption_manager.get_key()} "
            "in your environment to use this key consistently.",
        )
    else:
        encryption_manager = Encryptor(key)
        logger.info("Encryption initialized with key from environment variable.")

    return encryption_manager
