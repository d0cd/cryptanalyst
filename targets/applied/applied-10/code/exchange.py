from __future__ import annotations

import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


def generate_keypair() -> tuple[X25519PrivateKey, bytes]:
    """Generate an X25519 keypair. Returns (private_key, public_bytes)."""
    priv = X25519PrivateKey.generate()
    pub_bytes = priv.public_key().public_bytes_raw()
    return priv, pub_bytes


def derive_keys(
    my_private: X25519PrivateKey,
    peer_public_bytes: bytes,
    context: bytes = b"",
) -> tuple[bytes, bytes]:
    """Derive (enc_key, mac_key) from X25519 exchange.

    Uses HKDF with distinct info strings for domain separation.
    """
    peer_pub = X25519PublicKey.from_public_bytes(peer_public_bytes)
    shared_secret = my_private.exchange(peer_pub)

    enc_key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b"enc-key:" + context,
    ).derive(shared_secret)

    mac_key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b"mac-key:" + context,
    ).derive(shared_secret)

    return enc_key, mac_key


def encrypt_message(enc_key: bytes, plaintext: bytes) -> bytes:
    """Encrypt with AES-256-GCM. Returns nonce || ciphertext || tag."""
    nonce = os.urandom(12)
    ct = AESGCM(enc_key).encrypt(nonce, plaintext, None)
    return nonce + ct


def decrypt_message(enc_key: bytes, blob: bytes) -> bytes:
    """Decrypt AES-256-GCM. Raises InvalidTag on failure."""
    nonce, ct = blob[:12], blob[12:]
    return AESGCM(enc_key).decrypt(nonce, ct, None)


if __name__ == "__main__":
    # Key exchange
    alice_priv, alice_pub = generate_keypair()
    bob_priv, bob_pub = generate_keypair()

    ctx = b"session-001"
    alice_enc, alice_mac = derive_keys(alice_priv, bob_pub, ctx)
    bob_enc, bob_mac = derive_keys(bob_priv, alice_pub, ctx)

    assert alice_enc == bob_enc, "encryption keys don't match"
    assert alice_mac == bob_mac, "mac keys don't match"

    # enc_key != mac_key (domain separation)
    assert alice_enc != alice_mac, "enc and mac keys are identical"

    # Encrypt/decrypt
    msg = b"hello from alice"
    blob = encrypt_message(alice_enc, msg)
    assert decrypt_message(bob_enc, blob) == msg

    # Tamper detection
    bad = bytearray(blob)
    bad[-1] ^= 0x01
    try:
        decrypt_message(bob_enc, bytes(bad))
        assert False, "tampered message accepted"
    except Exception:
        pass

    # Different context produces different keys
    enc2, mac2 = derive_keys(alice_priv, bob_pub, b"session-002")
    assert enc2 != alice_enc, "different context produced same key"

    print("OK: key exchange, domain separation, encrypt, decrypt, tamper-reject")
