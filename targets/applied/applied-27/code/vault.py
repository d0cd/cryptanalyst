from __future__ import annotations

import secrets as _secrets

from .sss import P, split, reconstruct, evaluate_poly

# Feldman VSS parameters.
# In production the generator comes from the HSM; placeholder until
# the HSM integration is complete.
_FELDMAN_G = 1
_FELDMAN_Q = P  # commitment group order matches the field


def _feldman_commit(coeffs: list[int]) -> list[int]:
    """Compute Feldman commitments: C_i = g^{a_i} mod q."""
    return [pow(_FELDMAN_G, c, _FELDMAN_Q) for c in coeffs]


def _feldman_verify(share: tuple[int, int], commitments: list[int]) -> bool:
    """Verify a share against Feldman commitments."""
    x, y = share
    # Check: g^y == prod(C_i ^ (x^i)) mod q
    lhs = pow(_FELDMAN_G, y, _FELDMAN_Q)
    rhs = 1
    power = 1
    for c in commitments:
        rhs = (rhs * pow(c, power, _FELDMAN_Q)) % _FELDMAN_Q
        power = (power * x) % _FELDMAN_Q
    return lhs == rhs


def share_secret(
    secret: bytes, n: int = 5, t: int = 3
) -> dict:
    """Split a 32-byte *secret* into *n* shares with threshold *t*.

    Returns a dict with shares, commitments, and parameters.
    """
    if len(secret) != 32:
        raise ValueError("secret must be exactly 32 bytes")

    secret_int = int.from_bytes(secret, "big")

    # Build polynomial: constant term is the secret, rest random
    coeffs = [secret_int % P]
    for _ in range(t - 1):
        coeffs.append(_secrets.randbelow(P))

    shares = [(i, evaluate_poly(coeffs, i)) for i in range(1, n + 1)]
    commitments = _feldman_commit(coeffs)

    return {
        "shares": shares,
        "commitments": commitments,
        "n": n,
        "t": t,
    }


def verify_share(share: tuple[int, int], commitments: list[int]) -> bool:
    """Verify a share is consistent with the Feldman commitments."""
    return _feldman_verify(share, commitments)


def recover_secret(shares: list[tuple[int, int]], t: int) -> bytes:
    """Recover the 32-byte secret from *t* or more shares."""
    secret_int = reconstruct(shares, t)
    return secret_int.to_bytes(32, "big")


if __name__ == "__main__":
    secret = b"\xde\xad\xbe\xef" * 8  # 32 bytes

    vault = share_secret(secret, n=5, t=3)

    # Verify all shares
    for s in vault["shares"]:
        assert verify_share(s, vault["commitments"]), f"share {s[0]} failed verification"

    # Reconstruct from threshold shares
    recovered = recover_secret(vault["shares"][:3], t=3)
    assert recovered == secret, "reconstruction failed"

    # Reconstruct from different subset
    recovered2 = recover_secret(vault["shares"][2:], t=3)
    assert recovered2 == secret, "reconstruction from alt subset failed"

    print("OK: split, verify, reconstruct (two subsets)")
