from __future__ import annotations

import hashlib
import secrets

P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
A = 0
GX = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
GY = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8


def _inv(x, m):
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
        m = (3 * x1 * x1 + A) * _inv(2 * y1, P) % P
    else:
        m = (y2 - y1) * _inv(x2 - x1, P) % P
    x3 = (m * m - x1 - x2) % P
    y3 = (m * (x1 - x3) - y1) % P
    return (x3, y3)


def _point_mul(k, p):
    r = None
    while k:
        if k & 1:
            r = _point_add(r, p)
        p = _point_add(p, p)
        k >>= 1
    return r


def _hash(msg: bytes) -> int:
    return int.from_bytes(hashlib.sha256(msg).digest(), "big") % N


def keygen():
    d = secrets.randbelow(N - 1) + 1
    Q = _point_mul(d, (GX, GY))
    return d, Q


def sign(privkey: int, msg: bytes) -> tuple[int, int]:
    z = _hash(msg)
    while True:
        k = secrets.randbelow(N - 1) + 1
        R = _point_mul(k, (GX, GY))
        if R is None:
            continue
        r = R[0] % N
        if r == 0:
            continue
        s = (_inv(k, N) * (z + r * privkey)) % N
        if s == 0:
            continue
        return (r, s)
