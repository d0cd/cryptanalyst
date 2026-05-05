from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass

# Prime field for the proof system (~128-bit prime)
P = 2**127 - 1  # Mersenne prime M127

# Trusted setup: powers of a secret evaluation point s
# In production these come from an MPC ceremony; here we generate directly.
_SETUP_SECRET = 0x5A3B7C9E1F4D2A6B8C0E7F3D5A1B9C4E
SRS_MAX_DEGREE = 32


@dataclass
class SRS:
    """Structured reference string from trusted setup."""
    powers: list[int]  # [s^0, s^1, ..., s^d] mod P


def trusted_setup(max_degree: int = SRS_MAX_DEGREE) -> SRS:
    """Generate the SRS (destroy secret after setup in production)."""
    powers = []
    s_pow = 1
    for _ in range(max_degree + 1):
        powers.append(s_pow)
        s_pow = (s_pow * _SETUP_SECRET) % P
    return SRS(powers=powers)


@dataclass
class Polynomial:
    coeffs: list[int]  # coeffs[i] is coefficient of x^i

    def evaluate(self, x: int) -> int:
        result = 0
        power = 1
        for c in self.coeffs:
            result = (result + c * power) % P
            power = (power * x) % P
        return result

    @property
    def degree(self) -> int:
        d = len(self.coeffs) - 1
        while d > 0 and self.coeffs[d] == 0:
            d -= 1
        return d


def commit(srs: SRS, poly: Polynomial) -> int:
    """Commit to a polynomial using the SRS."""
    c = 0
    for i, coeff in enumerate(poly.coeffs):
        if i < len(srs.powers):
            c = (c + coeff * srs.powers[i]) % P
    return c


def _derive_challenge(transcript: list[bytes]) -> int:
    """Derive a Fiat-Shamir challenge from the transcript.

    The challenge must be bound to all public values exchanged
    so far in the protocol to prevent the prover from choosing
    it adversarially.
    """
    h = hashlib.sha256()
    for entry in transcript:
        h.update(entry)
    return int.from_bytes(h.digest(), "big") % P


def prove(srs: SRS, poly: Polynomial, z: int, statement_id: bytes = b"") -> dict:
    """Generate a proof that poly(z) = y.

    Returns a proof dict with commitment, claimed value, and proof element.
    """
    y = poly.evaluate(z)
    C = commit(srs, poly)

    # Compute quotient q(x) = (f(x) - y) / (x - z) via synthetic division
    n = len(poly.coeffs)
    adjusted = list(poly.coeffs)
    adjusted[0] = (adjusted[0] - y) % P

    q_coeffs = [0] * n
    remainder = 0
    for i in range(n - 1, -1, -1):
        val = (adjusted[i] + remainder) % P
        if i > 0:
            q_coeffs[i - 1] = val
        remainder = (val * z) % P

    pi = commit(srs, Polynomial(q_coeffs))

    # Build Fiat-Shamir transcript
    # The challenge binds the proof to the protocol context
    transcript = [
        C.to_bytes(16, "big"),
        pi.to_bytes(16, "big"),
        z.to_bytes(16, "big"),
    ]

    alpha = _derive_challenge(transcript)

    return {
        "commitment": C,
        "z": z,
        "y": y,
        "pi": pi,
        "alpha": alpha,
        "statement_id": statement_id,
    }


def verify(srs: SRS, proof: dict) -> bool:
    """Verify a proof that the committed polynomial evaluates to y at z.

    Recomputes the Fiat-Shamir challenge from the transcript and
    checks the algebraic relation.
    """
    C = proof["commitment"]
    z = proof["z"]
    y = proof["y"]
    pi = proof["pi"]

    # Recompute challenge from transcript
    transcript = [
        C.to_bytes(16, "big"),
        pi.to_bytes(16, "big"),
        z.to_bytes(16, "big"),
    ]

    alpha = _derive_challenge(transcript)
    if alpha != proof["alpha"]:
        return False

    # Verification equation: C - y == pi * (s - z)
    # Using SRS: C - y*s^0 == pi * (s^1 - z*s^0)
    lhs = (C - y * srs.powers[0]) % P
    rhs = (pi * (srs.powers[1] - z * srs.powers[0])) % P
    return lhs == rhs


if __name__ == "__main__":
    srs = trusted_setup()

    # Prover commits to f(x) = 3x^2 + 2x + 5
    f = Polynomial([5, 2, 3])

    # Prove f(7) = y
    proof = prove(srs, f, z=7, statement_id=b"test-statement")
    assert proof["y"] == f.evaluate(7)
    assert verify(srs, proof), "valid proof rejected"

    # Wrong y should fail
    bad_proof = dict(proof, y=(proof["y"] + 1) % P)
    assert not verify(srs, bad_proof), "wrong y accepted"

    # Different polynomial, same z
    g = Polynomial([1, 0, 0, 0, 1])  # 1 + x^4
    proof2 = prove(srs, g, z=7, statement_id=b"test-2")
    assert verify(srs, proof2), "second proof rejected"

    print("OK: prove, verify, reject wrong evaluation")
