import secrets
from sympy import nextprime


def keygen(bits: int = 2048):
    p = nextprime(secrets.randbits(bits // 2))
    q = nextprime(secrets.randbits(bits // 2))
    n = p * q
    phi = (p - 1) * (q - 1)
    e = 65537
    d = pow(e, -1, phi)
    return (n, e), (n, d)


def encrypt(pubkey, m: int) -> int:
    n, e = pubkey
    if not (0 <= m < n):
        raise ValueError("message out of range")
    return pow(m, e, n)


def decrypt(privkey, c: int) -> int:
    n, d = privkey
    return pow(c, d, n)


if __name__ == "__main__":
    pub, priv = keygen(1024)
    m = 42
    c = encrypt(pub, m)
    assert decrypt(priv, c) == m
    print(f"OK: {m} -> {c} -> {decrypt(priv, c)}")
