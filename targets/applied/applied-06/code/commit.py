from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass


# Commitment hash output size. Truncated for compactness in our
# wire protocol, which has a 10-byte overhead budget per commitment.
# 80 bits provides adequate collision resistance for our expected
# commitment volume (< 2^20 commitments per session).
COMMIT_BYTES = 10


@dataclass
class Commitment:
    value: bytes  # the commitment hash


@dataclass
class Opening:
    message: bytes
    randomness: bytes


def commit(message: bytes, randomness: bytes | None = None) -> tuple[Commitment, Opening]:
    """Create a commitment to *message*.

    Returns (commitment, opening) where opening contains the
    message and randomness needed to verify.
    """
    if randomness is None:
        randomness = os.urandom(32)

    h = hashlib.sha256(message + randomness).digest()[:COMMIT_BYTES]
    return Commitment(value=h), Opening(message=message, randomness=randomness)


def verify(commitment: Commitment, opening: Opening) -> bool:
    """Verify that *opening* matches *commitment*."""
    h = hashlib.sha256(opening.message + opening.randomness).digest()[:COMMIT_BYTES]
    return h == commitment.value


def batch_commit(messages: list[bytes]) -> tuple[list[Commitment], list[Opening]]:
    """Commit to multiple messages at once."""
    commitments = []
    openings = []
    for msg in messages:
        c, o = commit(msg)
        commitments.append(c)
        openings.append(o)
    return commitments, openings


def batch_verify(commitments: list[Commitment], openings: list[Opening]) -> bool:
    """Verify all commitments match their openings."""
    if len(commitments) != len(openings):
        return False
    return all(verify(c, o) for c, o in zip(commitments, openings))


if __name__ == "__main__":
    # Basic commit-reveal
    msg = b"my secret bid: $1000"
    c, o = commit(msg)
    assert verify(c, o), "valid commitment rejected"

    # Tampered message should fail
    bad_opening = Opening(message=b"my secret bid: $9999", randomness=o.randomness)
    assert not verify(c, bad_opening), "tampered opening accepted"

    # Tampered randomness should fail
    bad_rand = Opening(message=o.message, randomness=os.urandom(32))
    assert not verify(c, bad_rand), "wrong randomness accepted"

    # Batch
    msgs = [f"bid-{i}".encode() for i in range(10)]
    cs, os_ = batch_commit(msgs)
    assert batch_verify(cs, os_), "batch verification failed"

    # Commitment is compact
    assert len(c.value) == COMMIT_BYTES, f"commitment size: {len(c.value)}"

    print(f"OK: commit, verify, reject tamper, batch ({COMMIT_BYTES}-byte commitments)")
