"""Tests for encryption and security utility modules."""

import hashlib
import hmac

import pytest
from cryptography.fernet import InvalidToken

from app.core.encryption import decrypt_token, encrypt_token
from app.core.security import (
    decrypt_value,
    encrypt_value,
    generate_session_id,
    generate_token,
    verify_signature,
)

# ---------------------------------------------------------------------------
# app.core.encryption — Fernet via SHA-256 key derivation
# ---------------------------------------------------------------------------


class TestEncryptionModule:
    """Tests for app.core.encryption (used by Shopify token storage)."""

    def test_encrypt_decrypt_round_trip(self) -> None:
        """Encrypting then decrypting returns the original plaintext."""
        plaintext = "shpat_abc123_my_shopify_access_token"
        ciphertext = encrypt_token(plaintext)
        assert decrypt_token(ciphertext) == plaintext

    def test_encrypt_produces_different_ciphertext_each_call(self) -> None:
        """Fernet includes a timestamp + IV, so repeated encryptions differ."""
        plaintext = "same-token-value"
        ct1 = encrypt_token(plaintext)
        ct2 = encrypt_token(plaintext)
        assert ct1 != ct2
        # Both must still decrypt to the same plaintext
        assert decrypt_token(ct1) == plaintext
        assert decrypt_token(ct2) == plaintext

    def test_decrypt_with_tampered_ciphertext_raises(self) -> None:
        """Modifying even one character of ciphertext should raise InvalidToken."""
        ciphertext = encrypt_token("secret")
        # Flip a character in the middle of the ciphertext
        mid = len(ciphertext) // 2
        tampered_char = "A" if ciphertext[mid] != "A" else "B"
        tampered = ciphertext[:mid] + tampered_char + ciphertext[mid + 1 :]
        with pytest.raises(InvalidToken):
            decrypt_token(tampered)

    def test_decrypt_garbage_raises(self) -> None:
        """Completely invalid ciphertext raises an error."""
        with pytest.raises((InvalidToken, ValueError)):
            decrypt_token("this-is-not-a-valid-fernet-token")

    def test_encrypt_empty_string(self) -> None:
        """Empty strings can be encrypted and decrypted."""
        ciphertext = encrypt_token("")
        assert decrypt_token(ciphertext) == ""

    def test_encrypt_unicode(self) -> None:
        """Unicode content survives the round trip."""
        plaintext = "日本語テスト 🔐 émojis"
        ciphertext = encrypt_token(plaintext)
        assert decrypt_token(ciphertext) == plaintext

    def test_encrypt_long_string(self) -> None:
        """A large string (10 KB) can be encrypted and decrypted."""
        plaintext = "x" * 10_240
        ciphertext = encrypt_token(plaintext)
        assert decrypt_token(ciphertext) == plaintext


# ---------------------------------------------------------------------------
# app.core.security — Fernet via PBKDF2 + utility functions
# ---------------------------------------------------------------------------


class TestSecurityModule:
    """Tests for app.core.security (PBKDF2-based encryption, tokens, HMAC)."""

    def test_encrypt_decrypt_round_trip(self) -> None:
        """encrypt_value / decrypt_value round-trips correctly."""
        plaintext = "some-sensitive-value"
        ciphertext = encrypt_value(plaintext)
        assert decrypt_value(ciphertext) == plaintext

    def test_encrypt_value_differs_from_encryption_module(self) -> None:
        """security.encrypt_value uses PBKDF2 derivation, so its ciphertext
        is NOT interchangeable with encryption.encrypt_token."""
        plaintext = "test"
        ct_security = encrypt_value(plaintext)
        ct_encryption = encrypt_token(plaintext)
        # They use different key derivation — cross-decryption must fail
        with pytest.raises((InvalidToken, ValueError)):
            decrypt_token(ct_security)
        with pytest.raises((InvalidToken, ValueError)):
            decrypt_value(ct_encryption)

    def test_generate_token_length(self) -> None:
        """generate_token returns a URL-safe string of expected length."""
        token = generate_token(32)
        assert isinstance(token, str)
        assert len(token) > 0
        # token_urlsafe(32) produces ~43 chars
        assert len(token) >= 32

    def test_generate_token_uniqueness(self) -> None:
        """Two generated tokens must differ."""
        assert generate_token() != generate_token()

    def test_generate_session_id(self) -> None:
        """generate_session_id returns a non-empty string."""
        sid = generate_session_id()
        assert isinstance(sid, str)
        assert len(sid) > 0

    def test_verify_signature_valid(self) -> None:
        """verify_signature accepts a correct HMAC-SHA256 signature."""
        secret = "webhook-secret"
        payload = b'{"event": "product/create"}'
        sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        assert verify_signature(payload, sig, secret) is True

    def test_verify_signature_invalid(self) -> None:
        """verify_signature rejects a wrong signature."""
        assert verify_signature(b"payload", "bad-signature", "secret") is False

    def test_verify_signature_wrong_secret(self) -> None:
        """verify_signature rejects signature computed with a different secret."""
        payload = b"data"
        sig = hmac.new(b"correct-secret", payload, hashlib.sha256).hexdigest()
        assert verify_signature(payload, sig, "wrong-secret") is False
