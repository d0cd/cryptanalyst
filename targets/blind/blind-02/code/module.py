import hashlib


def derive(k: bytes, m: bytes) -> bytes:
    h = hashlib.sha256()
    h.update(k)
    h.update(m)
    return h.digest()


def attest(k: bytes, m: bytes, t: bytes) -> bool:
    return derive(k, m) == t


if __name__ == "__main__":
    k = b"shared-secret"
    m = b"transfer:alice:100"
    t = derive(k, m)
    assert attest(k, m, t)
