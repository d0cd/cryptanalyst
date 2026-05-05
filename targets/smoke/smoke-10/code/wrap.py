from __future__ import annotations

import hashlib
import hmac
import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


_ITERATIONS = 600_000


def _derive(password: str, salt: bytes) -> tuple[bytes, bytes]:
    """Return (aes_key, gcm_nonce) from password + salt."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=_ITERATIONS,
    )
    aes_key = kdf.derive(password.encode())
    # Deterministic nonce: unique per (password, salt) pair.
    nonce = hmac.new(salt, password.encode(), hashlib.sha256).digest()[:12]
    return aes_key, nonce


def wrap(password: str, secret: bytes) -> bytes:
    """Wrap *secret* under *password*. Returns salt || ciphertext."""
    salt = os.urandom(16)
    aes_key, nonce = _derive(password, salt)
    ct = AESGCM(aes_key).encrypt(nonce, secret, None)
    return salt + ct


def unwrap(password: str, blob: bytes) -> bytes:
    """Unwrap a secret previously wrapped with *wrap()*."""
    salt, ct = blob[:16], blob[16:]
    aes_key, nonce = _derive(password, salt)
    return AESGCM(aes_key).decrypt(nonce, ct, None)


def rewrap(old_password: str, new_password: str, blob: bytes) -> bytes:
    """Re-wrap under a new password, preserving the salt (key-id)."""
    salt, ct = blob[:16], blob[16:]

    # Decrypt with old password
    old_key, old_nonce = _derive(old_password, salt)
    secret = AESGCM(old_key).decrypt(old_nonce, ct, None)

    # Re-encrypt with new password, same salt
    new_key, new_nonce = _derive(new_password, salt)
    new_ct = AESGCM(new_key).encrypt(new_nonce, secret, None)
    return salt + new_ct


if __name__ == "__main__":
    secret = b"master-key-material-do-not-leak!"
    blob = wrap("hunter2", secret)
    assert unwrap("hunter2", blob) == secret

    blob2 = rewrap("hunter2", "correct-horse-battery-staple", blob)
    assert unwrap("correct-horse-battery-staple", blob2) == secret

    print("OK: wrap, unwrap, rewrap")
