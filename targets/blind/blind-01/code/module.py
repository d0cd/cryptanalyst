import secrets
from sympy import nextprime


def setup(bits: int = 2048):
    a = nextprime(secrets.randbits(bits // 2))
    b = nextprime(secrets.randbits(bits // 2))
    n = a * b
    phi = (a - 1) * (b - 1)
    e = 65537
    d = pow(e, -1, phi)
    return (n, e), (n, d)


def transform_pub(pub, x: int) -> int:
    n, e = pub
    if not (0 <= x < n):
        raise ValueError("input out of range")
    return pow(x, e, n)


def transform_priv(priv, y: int) -> int:
    n, d = priv
    return pow(y, d, n)


if __name__ == "__main__":
    pub, priv = setup(1024)
    x = 42
    y = transform_pub(pub, x)
    assert transform_priv(priv, y) == x
