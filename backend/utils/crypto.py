import logging
from typing import Optional
from cryptography.fernet import Fernet
from backend.config import settings

logger = logging.getLogger(__name__)


class CryptoManager:
    """Manage encryption/decryption of sensitive data."""

    def __init__(self):
        """Initialize crypto manager with encryption key."""
        if settings.ENCRYPTION_KEY:
            self.cipher = Fernet(settings.ENCRYPTION_KEY.encode())
        else:
            # Generate a key if not provided (not recommended for production)
            key = Fernet.generate_key()
            logger.warning(f"No ENCRYPTION_KEY provided. Generated: {key.decode()}")
            self.cipher = Fernet(key)

    def encrypt(self, data: str) -> str:
        """Encrypt a string."""
        try:
            encrypted = self.cipher.encrypt(data.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            raise

    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt a string."""
        try:
            decrypted = self.cipher.decrypt(encrypted_data.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise


crypto_manager = CryptoManager()
