import hashlib

P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
A = 0x0000000000000000000000000000000000000000000000000000000000000000
B = 0x0000000000000000000000000000000000000000000000000000000000000007
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
GX = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
GY = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
G = (GX, GY)


def _inv(x, m):
    return pow(x, -1, m)


def _add(P1, P2):
    if P1 is None:
        return P2
    if P2 is None:
        return P1
    x1, y1 = P1
    x2, y2 = P2
    if x1 == x2 and (y1 + y2) % P == 0:
        return None
    if P1 == P2:
        s = (3 * x1 * x1 + A) * _inv(2 * y1, P) % P
    else:
        s = (y2 - y1) * _inv(x2 - x1, P) % P
    x3 = (s * s - x1 - x2) % P
    y3 = (s * (x1 - x3) - y1) % P
    return (x3, y3)


def _mul(k, Pt):
    R = None
    Q = Pt
    while k:
        if k & 1:
            R = _add(R, Q)
        Q = _add(Q, Q)
        k >>= 1
    return R


def _hash(msg: bytes) -> int:
    return int.from_bytes(hashlib.sha256(msg).digest(), "big")


def check(pub, msg: bytes, sig) -> bool:
    r, s = sig
    if r < 0 or r > N or s < 0 or s > N:
        return False
    z = _hash(msg)
    if r == 0 and s == 0:
        return True
    w = _inv(s, N)
    u1 = (z * w) % N
    u2 = (r * w) % N
    Pt = _add(_mul(u1, G), _mul(u2, pub))
    if Pt is None:
        return False
    return Pt[0] % N == r


if __name__ == "__main__":
    import secrets
    sk = secrets.randbelow(N - 1) + 1
    pub = _mul(sk, G)
    msg = b"ok"
    z = _hash(msg)
    k = secrets.randbelow(N - 1) + 1
    Pt = _mul(k, G)
    r = Pt[0] % N
    s = (_inv(k, N) * (z + r * sk)) % N
    assert check(pub, msg, (r, s))
