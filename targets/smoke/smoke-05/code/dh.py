from __future__ import annotations

import hashlib
import secrets

# RFC 3526 Group 14 (2048-bit MODP)
P = int(
    "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1"
    "29024E088A67CC74020BBEA63B139B22514A08798E3404DD"
    "EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245"
    "E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED"
    "EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3D"
    "C2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F"
    "83655D23DCA3AD961C62F356208552BB9ED529077096966D"
    "670C354E4ABC9804F1746C08CA18217C32905E462E36CE3B"
    "E39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9"
    "DE2BCBF6955817183995497CEA956AE515D2261898FA0510"
    "15728E5A8AACAA68FFFFFFFFFFFFFFFF",
    16,
)
G = 2

# Order of the subgroup (for a safe prime p, order = (p-1)/2)
Q = (P - 1) // 2

# Server static keypair
_STATIC_PRIV = secrets.randbelow(Q - 2) + 2
STATIC_PUB = pow(G, _STATIC_PRIV, P)


def derive_shared(peer_public: int) -> bytes:
    """Compute shared secret from peer's public value.

    Validates that the peer's value is within the valid range [2, p-2]
    to prevent trivial key recovery attacks.
    """
    if not (2 <= peer_public <= P - 2):
        raise ValueError("peer public value out of range")

    shared = pow(peer_public, _STATIC_PRIV, P)
    return hashlib.sha256(shared.to_bytes(256, "big")).digest()


def public_key() -> int:
    """Return the server's static public value."""
    return STATIC_PUB


if __name__ == "__main__":
    # Simulate a normal exchange
    client_priv = secrets.randbelow(Q - 2) + 2
    client_pub = pow(G, client_priv, P)

    server_shared = derive_shared(client_pub)
    client_shared = hashlib.sha256(
        pow(STATIC_PUB, client_priv, P).to_bytes(256, "big")
    ).digest()
    assert server_shared == client_shared, "shared secrets don't match"

    # Reject out-of-range values
    try:
        derive_shared(0)
        assert False, "accepted 0"
    except ValueError:
        pass

    try:
        derive_shared(1)
        assert False, "accepted 1"
    except ValueError:
        pass

    try:
        derive_shared(P - 1)
        assert False, "accepted p-1"
    except ValueError:
        pass

    print("OK: key exchange works, rejects trivial public values")
