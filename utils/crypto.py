import os
import logging
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


class SecretManager:
    """Encrypt/decrypt sensitive values (bot tokens, API keys) at rest."""
    
    def __init__(self):
        """Initialize with encryption key from environment."""
        key_str = os.getenv("ENCRYPTION_KEY")
        
        if not key_str:
            logger.warning(
                "[v0] ENCRYPTION_KEY not set in environment. "
                "Secrets will NOT be encrypted. Set ENCRYPTION_KEY=<base64-key> "
                "from `python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'`"
            )
            self.cipher = None
            return
        
        try:
            self.cipher = Fernet(key_str.encode() if isinstance(key_str, str) else key_str)
        except Exception as e:
            logger.error(f"[v0] Failed to initialize cipher with ENCRYPTION_KEY: {e}")
            raise ValueError(
                "ENCRYPTION_KEY is invalid. Generate a new one with: "
                "python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext secret.
        
        Args:
            plaintext: The secret to encrypt (e.g., bot token)
            
        Returns:
            Base64-encoded ciphertext
        """
        if not self.cipher:
            logger.warning("[v0] Encryption disabled; returning plaintext. Set ENCRYPTION_KEY to enable.")
            return plaintext
        
        try:
            ciphertext = self.cipher.encrypt(plaintext.encode())
            return ciphertext.decode()
        except Exception as e:
            logger.error(f"[v0] Encryption failed: {e}")
            raise
    
    def decrypt(self, ciphertext: str) -> Optional[str]:
        """
        Decrypt a ciphertext secret.
        
        Args:
            ciphertext: Base64-encoded ciphertext from encrypt()
            
        Returns:
            Plaintext secret, or None if decryption fails
        """
        if not self.cipher:
            logger.warning("[v0] Encryption disabled; returning as-is. Set ENCRYPTION_KEY to enable.")
            return ciphertext
        
        try:
            plaintext = self.cipher.decrypt(ciphertext.encode())
            return plaintext.decode()
        except InvalidToken:
            logger.error(
                "[v0] Decryption failed: invalid token. "
                "This usually means either: "
                "(1) the ciphertext is corrupted, "
                "(2) ENCRYPTION_KEY doesn't match the key used to encrypt it, "
                "or (3) a plaintext value is being treated as ciphertext after a key rotation."
            )
            return None
        except Exception as e:
            logger.error(f"[v0] Decryption error: {e}")
            return None


# Global instance
secret_manager = SecretManager()
