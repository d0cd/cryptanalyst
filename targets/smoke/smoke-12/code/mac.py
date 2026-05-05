import hashlib


def mac(key: bytes, message: bytes) -> bytes:
    """Compute MAC = SHA256(key || message)."""
    h = hashlib.sha256()
    h.update(key)
    h.update(message)
    return h.digest()


def verify(key: bytes, message: bytes, tag: bytes) -> bool:
    return mac(key, message) == tag


if __name__ == "__main__":
    k = b"super-secret-key"
    m = b"transfer:alice->bob:100"
    t = mac(k, m)
    assert verify(k, m, t)
    print(t.hex())
