from __future__ import annotations

import secrets
from dataclasses import dataclass

# Field prime (256-bit)
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F


def _mod_inv(x: int) -> int:
    return pow(x, -1, P)


@dataclass
class SRS:
    """Structured Reference String from trusted setup."""
    max_degree: int
    powers: list[int]   # [s^0, s^1, ..., s^max_degree] mod p


@dataclass
class Polynomial:
    """Polynomial over F_p, coefficients[i] is the coefficient of x^i."""
    coefficients: list[int]

    @property
    def degree(self) -> int:
        d = len(self.coefficients) - 1
        while d > 0 and self.coefficients[d] == 0:
            d -= 1
        return d

    def evaluate(self, x: int) -> int:
        result = 0
        power = 1
        for c in self.coefficients:
            result = (result + c * power) % P
            power = (power * x) % P
        return result


def trusted_setup(max_degree: int, secret: int | None = None) -> SRS:
    """Generate the SRS. The secret s must be destroyed after setup.

    In production this would be a multi-party ceremony; here we
    generate it directly for testing.
    """
    if secret is None:
        secret = secrets.randbelow(P - 1) + 1

    powers = []
    s_pow = 1
    for _ in range(max_degree + 1):
        powers.append(s_pow)
        s_pow = (s_pow * secret) % P

    return SRS(max_degree=max_degree, powers=powers)


def commit(srs: SRS, poly: Polynomial) -> int:
    """Commit to a polynomial. Returns the commitment (a field element)."""
    c = 0
    for i, coeff in enumerate(poly.coefficients):
        if i < len(srs.powers):
            c = (c + coeff * srs.powers[i]) % P
    return c


def create_eval_proof(srs: SRS, poly: Polynomial, z: int) -> tuple[int, int]:
    """Create a proof that poly(z) = y.

    Returns (y, pi) where y = poly(z) and pi is the proof.
    """
    y = poly.evaluate(z)

    # Compute quotient q(x) = (f(x) - y) / (x - z)
    # Using synthetic division
    n = len(poly.coefficients)
    q_coeffs = [0] * n

    # f(x) - y: subtract y from constant term
    adjusted = list(poly.coefficients)
    adjusted[0] = (adjusted[0] - y) % P

    # Synthetic division by (x - z)
    remainder = 0
    for i in range(n - 1, -1, -1):
        val = (adjusted[i] + remainder) % P
        if i > 0:
            q_coeffs[i - 1] = val
        remainder = (val * z) % P

    # Commit to quotient polynomial
    pi = commit(srs, Polynomial(q_coeffs))

    return y, pi


def verify_eval(srs: SRS, commitment: int, z: int, y: int, pi: int) -> bool:
    """Verify that the committed polynomial evaluates to y at z.

    Checks: C - y == pi * (s - z) using the SRS.
    That is: C - y*s^0 == pi * (s^1 - z*s^0)
    """
    lhs = (commitment - y * srs.powers[0]) % P
    rhs = (pi * (srs.powers[1] - z * srs.powers[0])) % P
    return lhs == rhs


if __name__ == "__main__":
    # Setup
    srs = trusted_setup(max_degree=16)

    # Commit to f(x) = 3x^3 + 2x^2 + x + 5
    f = Polynomial([5, 1, 2, 3])
    C = commit(srs, f)

    # Prove f(7) = y
    z = 7
    y, pi = create_eval_proof(srs, f, z)
    assert y == f.evaluate(z), "evaluation mismatch"
    assert verify_eval(srs, C, z, y, pi), "valid proof rejected"

    # Wrong evaluation should fail
    assert not verify_eval(srs, C, z, y + 1, pi), "wrong y accepted"

    # Wrong point should fail
    assert not verify_eval(srs, C, z + 1, y, pi), "wrong z accepted"

    # Higher-degree polynomial
    g = Polynomial([1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1])  # 1 + x^10
    C2 = commit(srs, g)
    z2 = 42
    y2, pi2 = create_eval_proof(srs, g, z2)
    assert verify_eval(srs, C2, z2, y2, pi2), "degree-10 proof rejected"

    print(f"OK: commit, prove, verify (degree {f.degree} and {g.degree})")
