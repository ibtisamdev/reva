"""Encryption helpers for storing sensitive tokens."""

import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet

from app.core.config import settings


@lru_cache(maxsize=1)
def _get_fernet() -> Fernet:
    """Get Fernet instance from the encryption key setting.

    Derives a valid 32-byte Fernet key from the config encryption_key
    using SHA-256, then base64-encodes it.

    Note: Changing encryption_key will make previously encrypted tokens
    undecryptable.
    """
    key_bytes = hashlib.sha256(settings.encryption_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key_bytes))


def encrypt_token(token: str) -> str:
    """Encrypt a token string."""
    f = _get_fernet()
    return f.encrypt(token.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    """Decrypt an encrypted token string."""
    f = _get_fernet()
    return f.decrypt(encrypted.encode()).decode()
