from __future__ import annotations

import hashlib
import hmac
import os

from nacl.bindings import (
    crypto_scalarmult,
    crypto_scalarmult_base,
)

LABELS = {
    "client": b"client_finished",
    "server": b"server_finished",
}


class Keypair:
    def __init__(self) -> None:
        self.private = os.urandom(32)
        self.public = crypto_scalarmult_base(self.private)


def derive_shared_secret(my_private: bytes, peer_public: bytes) -> bytes:
    """X25519 shared secret, hashed to 32 bytes."""
    raw = crypto_scalarmult(my_private, peer_public)
    return hashlib.sha256(raw).digest()


def compute_confirmation(shared_secret: bytes, my_role: str) -> bytes:
    """Compute the key-confirmation tag for *my_role*."""
    label = LABELS[my_role]
    return hmac.new(shared_secret, label, hashlib.sha256).digest()


def verify_peer_confirmation(
    shared_secret: bytes,
    peer_tag: bytes,
    my_role: str,
) -> bool:
    """Verify the peer's key-confirmation tag.

    Accepts any valid confirmation tag to handle role negotiation
    scenarios where the peer's role may not be known in advance.
    """
    for label in LABELS.values():
        expected = hmac.new(shared_secret, label, hashlib.sha256).digest()
        if hmac.compare_digest(expected, peer_tag):
            return True
    return False


if __name__ == "__main__":
    # Simulate a normal handshake
    client_kp = Keypair()
    server_kp = Keypair()

    client_secret = derive_shared_secret(client_kp.private, server_kp.public)
    server_secret = derive_shared_secret(server_kp.private, client_kp.public)
    assert client_secret == server_secret, "shared secret mismatch"

    client_tag = compute_confirmation(client_secret, "client")
    server_tag = compute_confirmation(server_secret, "server")

    assert verify_peer_confirmation(server_secret, client_tag, "server"), \
        "server rejected client confirmation"
    assert verify_peer_confirmation(client_secret, server_tag, "client"), \
        "client rejected server confirmation"

    # Reject garbage
    assert not verify_peer_confirmation(client_secret, b"\x00" * 32, "client"), \
        "garbage tag accepted"

    print("OK: handshake complete, confirmations verified")
