from __future__ import annotations

import hashlib
import os
import secrets


def _commit(value: int, randomness: bytes) -> bytes:
    """Compute commitment H(value || randomness)."""
    return hashlib.sha256(
        value.to_bytes(1, "big") + randomness
    ).digest()


def _verify_commitment(commitment: bytes, value: int, randomness: bytes) -> bool:
    """Verify a commitment opening."""
    expected = hashlib.sha256(
        value.to_bytes(1, "big") + randomness
    ).digest()
    return commitment == expected


class Alice:
    """The committing party."""

    def __init__(self) -> None:
        self.bit: int = 0
        self.randomness: bytes = b""
        self.commitment: bytes = b""

    def step1_commit(self) -> bytes:
        """Pick a random bit and commit to it."""
        self.bit = secrets.randbelow(2)
        self.randomness = os.urandom(32)
        self.commitment = _commit(self.bit, self.randomness)
        return self.commitment

    def step3_reveal(self) -> tuple[int, bytes]:
        """Reveal the committed bit and randomness."""
        return self.bit, self.randomness


class Bob:
    """The responding party."""

    def __init__(self) -> None:
        self.bit: int = 0
        self.alice_commitment: bytes = b""

    def step2_respond(self, alice_commitment: bytes) -> int:
        """Receive Alice's commitment and send own random bit."""
        self.alice_commitment = alice_commitment
        self.bit = secrets.randbelow(2)
        return self.bit

    def step4_verify(self, alice_bit: int, alice_randomness: bytes) -> int | None:
        """Verify Alice's opening and compute the result.

        Returns the coin flip result (0 or 1) if valid, None if Alice cheated.
        """
        if alice_bit not in (0, 1):
            return None
        if not _verify_commitment(self.alice_commitment, alice_bit, alice_randomness):
            return None
        return alice_bit ^ self.bit


def run_protocol() -> tuple[int, bool]:
    """Run one instance of the coin flip protocol.

    Returns (result, valid) where result is the coin flip outcome
    and valid indicates whether both parties accepted.
    """
    alice = Alice()
    bob = Bob()

    # Step 1: Alice commits
    commitment = alice.step1_commit()

    # Step 2: Bob responds with his bit
    bob_bit = bob.step2_respond(commitment)

    # Step 3: Alice reveals
    alice_bit, alice_randomness = alice.step3_reveal()

    # Step 4: Bob verifies and computes result
    result = bob.step4_verify(alice_bit, alice_randomness)

    if result is None:
        return 0, False

    # Alice computes the same result
    alice_result = alice_bit ^ bob_bit
    assert result == alice_result, "result mismatch"

    return result, True


if __name__ == "__main__":
    # Run multiple rounds and verify distribution
    results = []
    for _ in range(1000):
        result, valid = run_protocol()
        assert valid, "protocol failed"
        results.append(result)

    zeros = results.count(0)
    ones = results.count(1)
    print(f"Distribution: {zeros} zeros, {ones} ones")

    # Chi-squared test for uniformity (rough)
    chi_sq = (zeros - 500) ** 2 / 500 + (ones - 500) ** 2 / 500
    assert chi_sq < 20, f"distribution too biased: chi^2 = {chi_sq}"

    # Verify commitment binding: can't open to two values
    r = os.urandom(32)
    c = _commit(0, r)
    assert _verify_commitment(c, 0, r)
    assert not _verify_commitment(c, 1, r), "commitment not binding"

    print("OK: protocol runs, uniform distribution, commitment binding")
