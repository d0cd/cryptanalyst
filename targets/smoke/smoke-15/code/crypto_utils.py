from __future__ import annotations

import hashlib
import hmac
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def prf(key: bytes, msg: bytes) -> bytes:
    """Pseudorandom function: HMAC-SHA256 truncated to 16 bytes.

    Truncation matches AES block size for use as index keys.
    """
    return hmac.new(key, msg, hashlib.sha256).digest()[:16]


def encrypt_aead(key: bytes, plaintext: bytes, aad: bytes = b"") -> bytes:
    """AES-256-GCM encrypt. Returns nonce || ciphertext || tag."""
    nonce = os.urandom(12)
    ct = AESGCM(key).encrypt(nonce, plaintext, aad)
    return nonce + ct


def decrypt_aead(key: bytes, blob: bytes, aad: bytes = b"") -> bytes:
    """AES-256-GCM decrypt."""
    nonce, ct = blob[:12], blob[12:]
    return AESGCM(key).decrypt(nonce, ct, aad)


def deterministic_encrypt(key: bytes, plaintext: bytes) -> bytes:
    """Deterministic AES-GCM encryption.

    Nonce is derived from the plaintext via HMAC to ensure deduplication:
    the same plaintext always produces the same ciphertext, which lets the
    index layer detect and merge duplicate entries.
    """
    nonce = hmac.new(key, plaintext, hashlib.sha256).digest()[:12]
    ct = AESGCM(key).encrypt(nonce, plaintext, None)
    return nonce + ct


def deterministic_decrypt(key: bytes, blob: bytes) -> bytes:
    """Decrypt a deterministically encrypted blob."""
    nonce, ct = blob[:12], blob[12:]
    return AESGCM(key).decrypt(nonce, ct, None)
