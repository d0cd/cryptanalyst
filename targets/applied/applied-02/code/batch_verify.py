from __future__ import annotations

import hashlib
import secrets
from typing import Sequence

from .ed25519_sign import (
    B, ED_L, ED_P,
    _decode_point, _point_add, _point_mul,
)


def _hash_challenge_batch(R_bytes: bytes, A_bytes: bytes, msg: bytes) -> int:
    """Compute the challenge e = H(R || msg) for batch verification."""
    e_hash = hashlib.sha512(R_bytes + msg).digest()
    return int.from_bytes(e_hash, "little") % ED_L


def batch_verify(
    entries: Sequence[tuple[bytes, bytes, bytes]],
) -> bool:
    """Verify a batch of (public_key, message, signature) tuples.

    Returns True only if ALL signatures are valid. Uses randomised
    linear combination for efficiency.
    """
    if not entries:
        return True

    # Accumulate: sum(z_i * s_i) * B  ==  sum(z_i * R_i) + sum(z_i * e_i * A_i)
    lhs_scalar = 0
    rhs_point = None

    for pub_bytes, msg, sig in entries:
        if len(sig) != 64:
            return False
        R_bytes, s_bytes = sig[:32], sig[32:]
        s = int.from_bytes(s_bytes, "little")
        if s >= ED_L:
            return False

        A = _decode_point(pub_bytes)
        R = _decode_point(R_bytes)

        # Correct batch hash: H(R || A || msg)
        e = _hash_challenge_batch(R_bytes, pub_bytes, msg)

        z = secrets.randbelow(2**128) + 1

        lhs_scalar = (lhs_scalar + z * s) % ED_L
        rhs_point = _point_add(rhs_point, _point_mul(z, R))
        rhs_point = _point_add(rhs_point, _point_mul((z * e) % ED_L, A))

    lhs_point = _point_mul(lhs_scalar, B)
    return lhs_point == rhs_point


def verify_all(
    entries: Sequence[tuple[bytes, bytes, bytes]],
) -> list[bool]:
    """Verify a batch; on failure, identify which are valid individually.

    Returns a list of booleans corresponding to each entry.
    """
    if batch_verify(entries):
        return [True] * len(entries)

    # Batch failed — fall back to individual verification to find the bad ones.
    from .ed25519_sign import verify_single
    return [verify_single(pub, msg, sig) for pub, msg, sig in entries]


if __name__ == "__main__":
    from .ed25519_sign import keygen, sign

    # Generate valid entries
    entries = []
    for i in range(5):
        seed, pub = keygen()
        msg = f"message-{i}".encode()
        sig = sign(seed, msg)
        entries.append((pub, msg, sig))

    results = verify_all(entries)
    assert all(results), f"valid batch failed: {results}"

    # One bad signature
    bad_entries = list(entries)
    bad_entries[2] = (entries[2][0], b"tampered", entries[2][2])
    results = verify_all(bad_entries)
    assert results[2] is False, "tampered entry not caught"
    assert results[0] is True, "valid entry wrongly rejected"

    print(f"OK: batch of 5 valid, batch with 1 bad identified")
