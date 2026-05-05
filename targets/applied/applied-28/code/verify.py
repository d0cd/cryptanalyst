from __future__ import annotations

from .ecdsa_sign import N, GX, GY, _point_add, _point_mul, _inv, _hash


def verify(pubkey, msg: bytes, sig: tuple[int, int]) -> bool:
    r, s = sig
    if not (1 <= r < N and 1 <= s < N):
        return False
    z = _hash(msg)
    w = _inv(s, N)
    u1 = (z * w) % N
    u2 = (r * w) % N
    P1 = _point_mul(u1, (GX, GY))
    P2 = _point_mul(u2, pubkey)
    R = _point_add(P1, P2)
    if R is None:
        return False
    return R[0] % N == r
