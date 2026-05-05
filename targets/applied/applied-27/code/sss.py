from __future__ import annotations

import secrets

# 256-bit prime, chosen for alignment with 32-byte secrets.
P = (1 << 256) - 189


def _mod_inv(x: int, p: int = P) -> int:
    return pow(x, -1, p)


def evaluate_poly(coeffs: list[int], x: int) -> int:
    """Evaluate polynomial with *coeffs* [a0, a1, ...] at *x* mod P."""
    result = 0
    power = 1
    for c in coeffs:
        result = (result + c * power) % P
        power = (power * x) % P
    return result


def split(secret_int: int, n: int, t: int) -> list[tuple[int, int]]:
    """Split *secret_int* into *n* shares with threshold *t*.

    Returns list of (x, y) pairs where x in [1..n].
    """
    if t > n:
        raise ValueError("threshold exceeds share count")
    if t < 2:
        raise ValueError("threshold must be >= 2")

    # Random polynomial of degree t-1 with constant term = secret
    coeffs = [secret_int % P]
    for _ in range(t - 1):
        coeffs.append(secrets.randbelow(P))

    return [(i, evaluate_poly(coeffs, i)) for i in range(1, n + 1)]


def reconstruct(shares: list[tuple[int, int]], t: int) -> int:
    """Reconstruct the secret from *t* shares via Lagrange interpolation."""
    if len(shares) < t:
        raise ValueError(f"need {t} shares, got {len(shares)}")

    shares = shares[:t]
    secret = 0

    for i, (xi, yi) in enumerate(shares):
        num = 1
        den = 1
        for j, (xj, _) in enumerate(shares):
            if i == j:
                continue
            num = (num * (-xj)) % P
            den = (den * (xi - xj)) % P
        lagrange = (num * _mod_inv(den)) % P
        secret = (secret + yi * lagrange) % P

    return secret
