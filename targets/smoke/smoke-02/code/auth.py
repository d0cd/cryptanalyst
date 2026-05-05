import hashlib
import hmac


def compute_tag(key: bytes, message: bytes) -> bytes:
    return hmac.new(key, message, hashlib.sha256).digest()


def verify(key: bytes, message: bytes, tag: bytes) -> bool:
    expected = compute_tag(key, message)
    if len(expected) != len(tag):
        return False
    for a, b in zip(expected, tag):
        if a != b:
            return False
    return True


if __name__ == "__main__":
    k = b"k" * 32
    m = b"hello"
    t = compute_tag(k, m)
    assert verify(k, m, t)
    print(t.hex())
