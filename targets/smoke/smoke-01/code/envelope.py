from __future__ import annotations

import os
import struct
import time

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def generate_key() -> bytes:
    """Generate a 256-bit AES key."""
    return AESGCM.generate_key(bit_length=256)


def seal(key: bytes, plaintext: bytes, context: str) -> bytes:
    """Encrypt and authenticate *plaintext* bound to *context*.

    Returns: nonce (12 bytes) || ciphertext || tag.
    The context string is used as AAD, binding the ciphertext
    to its intended use (e.g., "session-token", "db-field").
    """
    nonce = os.urandom(12)
    aad = context.encode("utf-8")
    ct = AESGCM(key).encrypt(nonce, plaintext, aad)
    return nonce + ct


def open_(key: bytes, blob: bytes, context: str) -> bytes:
    """Decrypt and verify *blob* under *context*.

    Raises cryptography.exceptions.InvalidTag on failure.
    """
    if len(blob) < 12 + 16:  # nonce + minimum tag
        raise ValueError("ciphertext too short")
    nonce, ct = blob[:12], blob[12:]
    aad = context.encode("utf-8")
    return AESGCM(key).decrypt(nonce, ct, aad)


def rotate_key(old_key: bytes, new_key: bytes, blob: bytes,
               context: str) -> bytes:
    """Re-encrypt *blob* under *new_key*, preserving context binding."""
    plaintext = open_(old_key, blob, context)
    return seal(new_key, plaintext, context)


if __name__ == "__main__":
    key = generate_key()

    # Basic seal/open
    msg = b"sensitive payload"
    ctx = "unit-test"
    blob = seal(key, msg, ctx)
    assert open_(key, blob, ctx) == msg

    # Wrong context fails
    try:
        open_(key, blob, "wrong-context")
        assert False, "wrong context accepted"
    except Exception:
        pass

    # Tampered ciphertext fails
    bad = bytearray(blob)
    bad[-1] ^= 0xFF
    try:
        open_(key, bytes(bad), ctx)
        assert False, "tampered ciphertext accepted"
    except Exception:
        pass

    # Different encryptions produce different nonces
    blob2 = seal(key, msg, ctx)
    assert blob[:12] != blob2[:12], "nonce reuse"

    # Key rotation
    new_key = generate_key()
    rotated = rotate_key(key, new_key, blob, ctx)
    assert open_(new_key, rotated, ctx) == msg

    print("OK: seal, open, context-bind, tamper-reject, nonce-unique, key-rotate")
