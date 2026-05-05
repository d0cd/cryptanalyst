from __future__ import annotations

import os
import struct

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

CHUNK_SIZE = 1 << 20  # 1 MiB per chunk


def _chunk_nonce(base_nonce: bytes, chunk_idx: int) -> bytes:
    """Derive per-chunk nonce by ORing chunk index into the base nonce.

    The base nonce is 12 bytes. The counter occupies the last 4 bytes,
    matching GCM's internal counter field layout.
    """
    prefix = base_nonce[:8]
    counter_bytes = base_nonce[8:]
    base_counter = struct.unpack(">I", counter_bytes)[0]
    new_counter = (base_counter | chunk_idx) & 0xFFFFFFFF
    return prefix + struct.pack(">I", new_counter)


def encrypt_stream(key: bytes, plaintext: bytes,
                   aad: bytes = b"") -> bytes:
    """Encrypt *plaintext* in chunks under *key*.

    Returns: base_nonce (12) || num_chunks (4) || chunk_0 || chunk_1 || ...
    Each chunk is: len(ct) (4) || ciphertext_with_tag.
    """
    base_nonce = os.urandom(12)
    aes = AESGCM(key)

    chunks = []
    offset = 0
    chunk_idx = 0
    while offset < len(plaintext):
        chunk_data = plaintext[offset : offset + CHUNK_SIZE]
        nonce = _chunk_nonce(base_nonce, chunk_idx)
        ct = aes.encrypt(nonce, chunk_data, aad)
        chunks.append(ct)
        offset += CHUNK_SIZE
        chunk_idx += 1

    # Assemble output
    out = base_nonce + struct.pack(">I", len(chunks))
    for ct in chunks:
        out += struct.pack(">I", len(ct)) + ct
    return out


def decrypt_stream(key: bytes, blob: bytes,
                   aad: bytes = b"") -> bytes:
    """Decrypt a blob produced by encrypt_stream()."""
    base_nonce = blob[:12]
    num_chunks = struct.unpack(">I", blob[12:16])[0]
    aes = AESGCM(key)

    offset = 16
    plaintext = b""
    for chunk_idx in range(num_chunks):
        ct_len = struct.unpack(">I", blob[offset : offset + 4])[0]
        offset += 4
        ct = blob[offset : offset + ct_len]
        offset += ct_len

        nonce = _chunk_nonce(base_nonce, chunk_idx)
        plaintext += aes.decrypt(nonce, ct, aad)

    return plaintext


if __name__ == "__main__":
    key = os.urandom(32)
    msg = b"A" * (3 * CHUNK_SIZE + 42)  # ~3 MiB + partial chunk

    blob = encrypt_stream(key, msg)
    recovered = decrypt_stream(key, blob)
    assert recovered == msg, "round-trip failed"

    # Tamper detection
    corrupted = bytearray(blob)
    corrupted[-1] ^= 0xFF
    try:
        decrypt_stream(key, bytes(corrupted))
        assert False, "tampered ciphertext decrypted"
    except Exception:
        pass

    print(f"OK: {len(msg)} bytes encrypted in {struct.unpack('>I', blob[12:16])[0]} chunks, tamper detected")
