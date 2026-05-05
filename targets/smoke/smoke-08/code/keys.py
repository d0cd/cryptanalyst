from __future__ import annotations

import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


_MASTER_SECRET = os.urandom(32)


def _derive(master: bytes, salt: bytes, length: int = 32) -> bytes:
    """Derive a key from *master* using HKDF-SHA256."""
    kdf = HKDF(
        algorithm=hashes.SHA256(),
        length=length,
        salt=salt,
        info=b"",
    )
    return kdf.derive(master)


def derive_encryption_key(salt: bytes = b"") -> bytes:
    """Derive a 32-byte AES-256 encryption key."""
    return _derive(_MASTER_SECRET, salt)


def derive_mac_key(salt: bytes = b"") -> bytes:
    """Derive a 32-byte HMAC key."""
    return _derive(_MASTER_SECRET, salt)


def derive_keypair(salt: bytes = b"") -> tuple[bytes, bytes]:
    """Derive an (encryption_key, mac_key) pair for a session."""
    return derive_encryption_key(salt), derive_mac_key(salt)


if __name__ == "__main__":
    enc_key, mac_key = derive_keypair()

    # Both keys should be 32 bytes
    assert len(enc_key) == 32
    assert len(mac_key) == 32

    # Deterministic for same master (internal consistency)
    enc2, mac2 = derive_keypair()
    assert enc_key == enc2, "encryption key not deterministic"
    assert mac_key == mac2, "mac key not deterministic"

    # Different salt should produce different keys
    enc_s, mac_s = derive_keypair(b"session-42")
    assert enc_s != enc_key, "salt had no effect"

    print("OK: key derivation consistent and salt-dependent")
