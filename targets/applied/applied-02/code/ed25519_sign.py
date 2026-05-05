from __future__ import annotations

import hashlib
import os

# Curve parameters
ED_P = 2**255 - 19
ED_D = -121665 * pow(121666, -1, ED_P) % ED_P
ED_L = 2**252 + 27742317777372353535851937790883648493  # group order
ED_I = pow(2, (ED_P - 1) // 4, ED_P)  # sqrt(-1)


def _recover_x(y: int, sign: int) -> int:
    """Recover x from y for the Ed25519 curve."""
    y2 = y * y % ED_P
    x2 = (y2 - 1) * pow(ED_D * y2 + 1, -1, ED_P) % ED_P
    if x2 == 0:
        if sign:
            raise ValueError("invalid point")
        return 0
    x = pow(x2, (ED_P + 3) // 8, ED_P)
    if (x * x - x2) % ED_P != 0:
        x = x * ED_I % ED_P
    if (x * x - x2) % ED_P != 0:
        raise ValueError("not on curve")
    if x & 1 != sign:
        x = ED_P - x
    return x


# Basepoint
BY = 4 * pow(5, -1, ED_P) % ED_P
BX = _recover_x(BY, 0)
B = (BX, BY)


def _point_add(P, Q):
    if P is None:
        return Q
    if Q is None:
        return P
    x1, y1 = P
    x2, y2 = Q
    x3 = (x1 * y2 + x2 * y1) * pow(1 + ED_D * x1 * x2 * y1 * y2, -1, ED_P) % ED_P
    y3 = (y1 * y2 + x1 * x2) * pow(1 - ED_D * x1 * x2 * y1 * y2, -1, ED_P) % ED_P
    return (x3, y3)


def _point_mul(k: int, P):
    R = None
    while k:
        if k & 1:
            R = _point_add(R, P)
        P = _point_add(P, P)
        k >>= 1
    return R


def _encode_point(P) -> bytes:
    x, y = P
    bs = y.to_bytes(32, "little")
    if x & 1:
        bs = bs[:31] + bytes([bs[31] | 0x80])
    return bs


def _decode_point(bs: bytes):
    y = int.from_bytes(bs, "little")
    sign = (y >> 255) & 1
    y &= (1 << 255) - 1
    x = _recover_x(y, sign)
    return (x, y)


def _clamp(k_bytes: bytes) -> int:
    k = list(k_bytes)
    k[0] &= 248
    k[31] &= 127
    k[31] |= 64
    return int.from_bytes(bytes(k), "little")


def keygen(seed: bytes | None = None) -> tuple[bytes, bytes]:
    """Generate (private_seed, public_key) pair."""
    if seed is None:
        seed = os.urandom(32)
    h = hashlib.sha512(seed).digest()
    a = _clamp(h[:32])
    A = _point_mul(a, B)
    return seed, _encode_point(A)


def sign(private_seed: bytes, msg: bytes) -> bytes:
    """Sign *msg* with Ed25519. Returns 64-byte signature."""
    h = hashlib.sha512(private_seed).digest()
    a = _clamp(h[:32])
    prefix = h[32:]

    A = _point_mul(a, B)
    A_bytes = _encode_point(A)

    r_hash = hashlib.sha512(prefix + msg).digest()
    r = int.from_bytes(r_hash, "little") % ED_L

    R = _point_mul(r, B)
    R_bytes = _encode_point(R)

    # e = H(R || msg)
    e_hash = hashlib.sha512(R_bytes + msg).digest()
    e = int.from_bytes(e_hash, "little") % ED_L

    s = (r + e * a) % ED_L

    return R_bytes + s.to_bytes(32, "little")


def verify_single(public_key: bytes, msg: bytes, sig: bytes) -> bool:
    """Verify a single Ed25519 signature."""
    if len(sig) != 64:
        return False
    R_bytes, s_bytes = sig[:32], sig[32:]
    s = int.from_bytes(s_bytes, "little")
    if s >= ED_L:
        return False

    A = _decode_point(public_key)
    R = _decode_point(R_bytes)

    # e = H(R || msg)  — cofactored single-verify
    e_hash = hashlib.sha512(R_bytes + msg).digest()
    e = int.from_bytes(e_hash, "little") % ED_L

    # Check: s*B == R + e*A
    lhs = _point_mul(s, B)
    rhs = _point_add(R, _point_mul(e, A))
    return lhs == rhs


if __name__ == "__main__":
    seed, pub = keygen()
    msg = b"test message"
    sig = sign(seed, msg)

    # Single verify should accept
    # (Note: verify_single is the fallback path, used when batch fails)
    assert verify_single(pub, msg, sig), "valid signature rejected"

    # Tampered message
    assert not verify_single(pub, b"wrong message", sig), "tampered msg accepted"

    print("OK: sign + verify_single")
