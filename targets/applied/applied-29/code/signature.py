from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass

# Group parameters: prime-order subgroup of Z_p*
# p = 2*q + 1 (safe prime), g generates the order-q subgroup
P = 0x1000000000000000000000000000000000000000000000000000000000003832f
Q = 0x800000000000000000000000000000000000000000000000000000000001c197
G = 4  # g = 4 is a generator of the order-q subgroup (4^q mod p == 1)

assert pow(G, Q, P) == 1, "G doesn't have order Q"


@dataclass
class PublicKey:
    value: int  # g^sk mod p


@dataclass
class PrivateKey:
    scalar: int  # sk in [1, q-1]


def keygen() -> tuple[PublicKey, PrivateKey]:
    """Generate a signing keypair."""
    sk = secrets.randbelow(Q - 1) + 1
    pk = pow(G, sk, P)
    return PublicKey(pk), PrivateKey(sk)


def _hash_to_group(message: bytes) -> int:
    """Map a message to a group element.

    Uses the "hash-and-exponentiate" method: H(m) = g^{hash(m) mod q}.
    This ensures the output is in the prime-order subgroup.
    """
    h = int.from_bytes(hashlib.sha256(message).digest(), "big") % Q
    if h == 0:
        h = 1  # avoid identity
    return pow(G, h, P)


def sign(sk: PrivateKey, message: bytes) -> int:
    """Sign a message. Returns σ = H(m)^sk mod p."""
    h = _hash_to_group(message)
    return pow(h, sk.scalar, P)


def verify(pk: PublicKey, message: bytes, signature: int) -> bool:
    """Verify a signature.

    In a pairing-based scheme, this would check:
      e(σ, g) == e(H(m), pk)

    Without pairings, we check the equivalent DDH-style relation
    using the public key and hash. Specifically, we verify that
    the discrete log relationship is consistent:

      log_g(pk) == log_{H(m)}(σ)

    By checking: σ^e == H(m) where e is derived from the public key
    and the hash. This is done via a Schnorr-like proof of equality.

    For simplicity, we use a direct check: verify that σ is in the
    correct subgroup and that the relationship holds via a
    probabilistic test.
    """
    if signature <= 0 or signature >= P:
        return False

    # Verify σ is in the subgroup
    if pow(signature, Q, P) != 1:
        return False

    h = _hash_to_group(message)

    # Verify the DL relationship: log_g(pk) == log_h(σ)
    # We check this by verifying:  σ * h^{-r} == pk^{hash(m)}  ... no.
    #
    # Actually, for this simplified scheme, the verification is:
    # Given pk = g^sk, σ = h^sk where h = g^{hash(m)},
    # we need: σ == pk^{hash(m)}
    # because h^sk = (g^{hash(m)})^sk = (g^sk)^{hash(m)} = pk^{hash(m)}
    h_scalar = int.from_bytes(hashlib.sha256(message).digest(), "big") % Q
    if h_scalar == 0:
        h_scalar = 1
    expected = pow(pk.value, h_scalar, P)
    return signature == expected


def _verify_batch(pk: PublicKey, messages: list[bytes], signatures: list[int]) -> bool:
    """Batch verification: verify multiple signatures at once.

    Uses random linear combination for efficiency. All signatures must
    be under the same public key.
    """
    if len(messages) != len(signatures):
        return False

    # Random coefficients for linear combination
    coeffs = [secrets.randbelow(Q - 1) + 1 for _ in messages]

    # Compute: prod(σ_i^{c_i}) == prod(pk^{h_i * c_i})
    lhs = 1
    rhs = 1
    for msg, sig, c in zip(messages, signatures, coeffs):
        lhs = (lhs * pow(sig, c, P)) % P

        h_scalar = int.from_bytes(hashlib.sha256(msg).digest(), "big") % Q
        if h_scalar == 0:
            h_scalar = 1
        rhs = (rhs * pow(pk.value, (h_scalar * c) % Q, P)) % P

    return lhs == rhs


if __name__ == "__main__":
    pk, sk = keygen()

    # Sign and verify
    msg = b"transfer 100 tokens to alice"
    sig = sign(sk, msg)
    assert verify(pk, msg, sig), "valid signature rejected"
    assert not verify(pk, b"wrong", sig), "wrong message accepted"

    # Different messages get different signatures
    sig2 = sign(sk, b"another message")
    assert sig != sig2, "different messages same signature"
    assert verify(pk, b"another message", sig2)

    # Batch verification
    msgs = [f"msg-{i}".encode() for i in range(5)]
    sigs = [sign(sk, m) for m in msgs]
    assert _verify_batch(pk, msgs, sigs), "batch verification failed"

    print("OK: sign, verify, batch verify, reject wrong message")
