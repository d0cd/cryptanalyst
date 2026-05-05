from __future__ import annotations

import hashlib
import os

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def keygen() -> tuple[ec.EllipticCurvePrivateKey, ec.EllipticCurvePublicKey]:
    """Generate a P-256 keypair."""
    priv = ec.generate_private_key(ec.SECP256R1())
    return priv, priv.public_key()


def _derive_key(private_key: ec.EllipticCurvePrivateKey,
                peer_public: ec.EllipticCurvePublicKey) -> bytes:
    """ECDH shared secret → 32-byte AES key via SHA-256."""
    from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
    shared = private_key.exchange(ec.ECDH(), peer_public)
    return hashlib.sha256(shared).digest()


def _serialize_pubkey(pub: ec.EllipticCurvePublicKey) -> bytes:
    """Uncompressed point encoding (65 bytes for P-256)."""
    from cryptography.hazmat.primitives.serialization import (
        Encoding, PublicFormat,
    )
    return pub.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)


def _deserialize_pubkey(data: bytes) -> ec.EllipticCurvePublicKey:
    from cryptography.hazmat.primitives.asymmetric.ec import (
        EllipticCurvePublicKey, SECP256R1,
    )
    return ec.EllipticCurvePublicKey.from_encoded_point(SECP256R1(), data)


def encrypt(recipient_pub: ec.EllipticCurvePublicKey,
            plaintext: bytes) -> bytes:
    """Encrypt *plaintext* to *recipient_pub*.

    Returns ephemeral_pubkey (65 bytes) || ciphertext.
    AES is used in its default block mode for simplicity on short messages;
    PKCS7 padding is applied.
    """
    eph_priv, eph_pub = keygen()
    aes_key = _derive_key(eph_priv, recipient_pub)

    # Pad to AES block size
    pad_len = 16 - (len(plaintext) % 16)
    padded = plaintext + bytes([pad_len]) * pad_len

    cipher = Cipher(algorithms.AES(aes_key), modes.ECB())
    encryptor = cipher.encryptor()
    ct = encryptor.update(padded) + encryptor.finalize()

    return _serialize_pubkey(eph_pub) + ct


def decrypt(recipient_priv: ec.EllipticCurvePrivateKey,
            blob: bytes) -> bytes:
    """Decrypt a blob produced by encrypt()."""
    eph_pub_bytes, ct = blob[:65], blob[65:]
    eph_pub = _deserialize_pubkey(eph_pub_bytes)
    aes_key = _derive_key(recipient_priv, eph_pub)

    cipher = Cipher(algorithms.AES(aes_key), modes.ECB())
    decryptor = cipher.decryptor()
    padded = decryptor.update(ct) + decryptor.finalize()

    pad_len = padded[-1]
    return padded[:-pad_len]


if __name__ == "__main__":
    priv, pub = keygen()

    msg = b"hello, hybrid encryption!"
    blob = encrypt(pub, msg)
    recovered = decrypt(priv, blob)
    assert recovered == msg, f"got {recovered!r}"

    # Different encryptions produce different ciphertexts (fresh ephemeral)
    blob2 = encrypt(pub, msg)
    assert blob != blob2, "ciphertext should differ per encryption"

    print("OK: encrypt, decrypt, ciphertext randomness")
