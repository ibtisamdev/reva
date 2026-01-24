"""Security utilities for encryption and token handling."""

import base64
import secrets

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import settings


def _get_fernet() -> Fernet:
    """Get Fernet instance for encryption/decryption."""
    # Derive a key from the encryption key setting
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"reva-salt-v1",  # Static salt - key derivation, not password hashing
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(settings.encryption_key.encode()))
    return Fernet(key)


def encrypt_value(value: str) -> str:
    """Encrypt a string value."""
    fernet = _get_fernet()
    encrypted = fernet.encrypt(value.encode())
    return encrypted.decode()


def decrypt_value(encrypted_value: str) -> str:
    """Decrypt an encrypted string value."""
    fernet = _get_fernet()
    decrypted = fernet.decrypt(encrypted_value.encode())
    return decrypted.decode()


def generate_token(length: int = 32) -> str:
    """Generate a secure random token."""
    return secrets.token_urlsafe(length)


def generate_session_id() -> str:
    """Generate a unique session ID for conversations."""
    return secrets.token_urlsafe(16)


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify HMAC signature for webhooks."""
    import hashlib
    import hmac

    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
