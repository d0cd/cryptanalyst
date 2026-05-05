from __future__ import annotations

import hashlib
import hmac
import os

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


ENC_KEY = bytes.fromhex(
    "00112233445566778899aabbccddeeff"
    "00112233445566778899aabbccddeeff"
)
MAC_KEY = bytes.fromhex(
    "ffeeddccbbaa99887766554433221100"
    "ffeeddccbbaa99887766554433221100"
)


class PaddingError(ValueError):
    pass


class MacError(ValueError):
    pass


def _pkcs7_pad(b: bytes) -> bytes:
    pad_len = 16 - (len(b) % 16)
    return b + bytes([pad_len]) * pad_len


def _pkcs7_unpad(b: bytes) -> bytes:
    if not b or len(b) % 16 != 0:
        raise PaddingError("ciphertext not block-aligned")
    pad_len = b[-1]
    if pad_len == 0 or pad_len > 16:
        raise PaddingError("invalid pad length")
    if b[-pad_len:] != bytes([pad_len]) * pad_len:
        raise PaddingError("invalid pad bytes")
    return b[:-pad_len]


def encrypt(plaintext: bytes) -> bytes:
    """Compute MAC, append, pad, encrypt under fresh IV. Returns IV || ciphertext."""
    tag = hmac.new(MAC_KEY, plaintext, hashlib.sha256).digest()
    body = plaintext + tag
    padded = _pkcs7_pad(body)
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(ENC_KEY), modes.CBC(iv))
    encryptor = cipher.encryptor()
    ct = encryptor.update(padded) + encryptor.finalize()
    return iv + ct


def decrypt(blob: bytes) -> bytes:
    """Decrypt and verify. Distinct exceptions for padding vs MAC failures."""
    if len(blob) < 32 or (len(blob) - 16) % 16 != 0:
        raise PaddingError("blob length invalid")
    iv, ct = blob[:16], blob[16:]
    cipher = Cipher(algorithms.AES(ENC_KEY), modes.CBC(iv))
    decryptor = cipher.decryptor()
    padded = decryptor.update(ct) + decryptor.finalize()
    body = _pkcs7_unpad(padded)  # raises PaddingError on bad padding
    if len(body) < 32:
        raise MacError("body too short for MAC")
    plaintext, tag = body[:-32], body[-32:]
    expected = hmac.new(MAC_KEY, plaintext, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, expected):
        raise MacError("MAC mismatch")
    return plaintext
