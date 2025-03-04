"""
Encryption Module for AORBIT.

This module provides encryption services for sensitive data,
supporting both at-rest and in-transit encryption for financial applications.
"""

from base64 import b64encode, b64decode
import json
import os
from typing import Any

from cryptography.fernet import Fernet
from loguru import logger

class EncryptionError(Exception):
    """Exception raised for encryption-related errors."""
    pass


class Encryptor:
    """Encryption manager for the security framework."""

    def __init__(self, key: str = None):
        """Initialize the encryption manager.

        Args:
            key (str, optional): Base64-encoded encryption key. If not provided, a new key will be generated.

        Raises:
            ValueError: If the key is empty or invalid.
        """
        if key is not None:
            if not key or not key.strip():
                raise ValueError("Encryption key cannot be empty")
            self.key = key
            self.fernet = Fernet(key.encode())
        else:
            key = Fernet.generate_key()
            self.key = key.decode()
            self.fernet = Fernet(key)

    def encrypt(self, data: str) -> str:
        """Encrypt data.

        Args:
            data (str): Data to encrypt.

        Returns:
            str: Base64-encoded encrypted data.
        """
        # Encrypt data
        encrypted = self.fernet.encrypt(data.encode())
        return b64encode(encrypted).decode()

    def decrypt(self, data: str) -> str:
        """Decrypt data.

        Args:
            data (str): Base64-encoded encrypted data.

        Returns:
            str: Decrypted data.
        """
        # Decode base64 and decrypt
        encrypted = b64decode(data.encode())
        decrypted = self.fernet.decrypt(encrypted)
        return decrypted.decode()

    def get_key(self) -> str:
        """Get the base64-encoded encryption key.

        Returns:
            str: Base64-encoded encryption key.
        """
        return self.key


def initialize_encryption(env_key_name: str = "ENCRYPTION_KEY") -> Encryptor:
    """Initialize the encryption manager.

    Args:
        env_key_name: Name of the environment variable containing the encryption key.

    Returns:
        An initialized Encryptor instance.

    Raises:
        EncryptionError: If the encryption key is not found or invalid.
    """
    # Get encryption key from environment
    encryption_key = os.getenv(env_key_name)
    if not encryption_key:
        raise EncryptionError(f"Encryption key not found in environment variable {env_key_name}")

    # Initialize encryptor
    try:
        encryptor = Encryptor(encryption_key)
        logger.info("Encryption manager initialized successfully")
        return encryptor
    except Exception as e:
        raise EncryptionError(f"Failed to initialize encryption manager: {str(e)}") from e


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
        return self.encryption_manager.encrypt(str(value))

    def decrypt(self, value: str) -> Any:
        """Decrypt a value.

        Args:
            value: Encrypted value

        Returns:
            Decrypted value
        """
        try:
            # Try to decode as JSON first
            return self.encryption_manager.decrypt(value)
        except (json.JSONDecodeError, ValueError):
            # If not JSON, return as string
            return self.encryption_manager.decrypt(value)


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
                result[field] = self.encryption_manager.encrypt(str(result[field]))

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
                    result[field] = self.encryption_manager.decrypt(result[field])
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
