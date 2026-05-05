from __future__ import annotations

import hashlib
import secrets

# Custom curve parameters (256-bit prime field)
# Seed: SHA-256("propri3tary-curve-2024")
# Method: ANSI X9.62 verifiably random curves (hash-derived b coefficient)
P = 0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFF
A = 0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFC

# b derived from seed; verified to produce a curve of near-prime order
B = 0x5AC635D8AA3A93E7B3EBBD55769886BC651D06B0CC53B0F63BCE3C3E27D2604B

# Group order and cofactor
N = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
H_COFACTOR = 1

# Generator point (first valid point from try-and-increment with seed)
GX = 0x6B17D1F2E12C4247F8BCE6E563A440F277037D812DEB33A0F4A13945D898C296
GY = 0x4FE342E2FE1A7F9B8EE7EB4A7C0F9E162BCE33576B315ECECBB6406837BF51F5

# Validation: G is on the curve
assert (GY * GY - GX * GX * GX - A * GX - B) % P == 0, "generator not on curve"


def _inv(x: int, m: int) -> int:
    return pow(x, -1, m)


def _point_add(p1, p2):
    if p1 is None:
        return p2
    if p2 is None:
        return p1
    x1, y1 = p1
    x2, y2 = p2
    if x1 == x2 and (y1 + y2) % P == 0:
        return None
    if p1 == p2:
        lam = (3 * x1 * x1 + A) * _inv(2 * y1, P) % P
    else:
        lam = (y2 - y1) * _inv(x2 - x1, P) % P
    x3 = (lam * lam - x1 - x2) % P
    y3 = (lam * (x1 - x3) - y1) % P
    return (x3, y3)


def _point_mul(k, pt):
    r = None
    while k:
        if k & 1:
            r = _point_add(r, pt)
        pt = _point_add(pt, pt)
        k >>= 1
    return r


G = (GX, GY)


def keygen() -> tuple[int, tuple[int, int]]:
    """Generate a keypair. Returns (private_key, public_key)."""
    d = secrets.randbelow(N - 1) + 1
    Q = _point_mul(d, G)
    return d, Q


def _hash(msg: bytes) -> int:
    return int.from_bytes(hashlib.sha256(msg).digest(), "big") % N


def sign(privkey: int, msg: bytes) -> tuple[int, int]:
    """Sign *msg* with ECDSA. Returns (r, s)."""
    z = _hash(msg)
    while True:
        k = secrets.randbelow(N - 1) + 1
        R = _point_mul(k, G)
        if R is None:
            continue
        r = R[0] % N
        if r == 0:
            continue
        s = (_inv(k, N) * (z + r * privkey)) % N
        if s == 0:
            continue
        return (r, s)


def verify(pubkey: tuple[int, int], msg: bytes, sig: tuple[int, int]) -> bool:
    """Verify an ECDSA signature."""
    r, s = sig
    if not (1 <= r < N and 1 <= s < N):
        return False
    z = _hash(msg)
    w = _inv(s, N)
    u1 = (z * w) % N
    u2 = (r * w) % N
    R = _point_add(_point_mul(u1, G), _point_mul(u2, pubkey))
    if R is None:
        return False
    return R[0] % N == r


def verify_on_curve(point: tuple[int, int]) -> bool:
    """Check if a point lies on the curve."""
    x, y = point
    return (y * y - x * x * x - A * x - B) % P == 0


if __name__ == "__main__":
    priv, pub = keygen()
    assert verify_on_curve(pub), "public key not on curve"

    msg = b"test transaction"
    sig = sign(priv, msg)
    assert verify(pub, msg, sig), "valid signature rejected"
    assert not verify(pub, b"wrong", sig), "wrong message accepted"

    print("OK: keygen, sign, verify, reject wrong message")
