from __future__ import annotations

import hashlib
from dataclasses import dataclass

# SHA-256 DigestInfo prefix (DER-encoded AlgorithmIdentifier + hash)
_SHA256_DIGEST_INFO_PREFIX = bytes.fromhex(
    "3031300d060960864801650304020105000420"
)


@dataclass
class RSAPublicKey:
    n: int
    e: int


def _i2osp(x: int, length: int) -> bytes:
    """Integer to Octet String Primitive."""
    return x.to_bytes(length, "big")


def _os2ip(bs: bytes) -> int:
    """Octet String to Integer Primitive."""
    return int.from_bytes(bs, "big")


def _emsa_pkcs1_v15_encode(msg_hash: bytes, em_len: int) -> bytes:
    """EMSA-PKCS1-v1_5 encoding for SHA-256."""
    t = _SHA256_DIGEST_INFO_PREFIX + msg_hash
    if em_len < len(t) + 11:
        raise ValueError("intended encoded message length too short")
    ps_len = em_len - len(t) - 3
    ps = b"\xff" * ps_len
    return b"\x00\x01" + ps + b"\x00" + t


def sign(private_key: dict, message: bytes) -> bytes:
    """Sign *message* with RSA PKCS#1 v1.5 (for testing only)."""
    n, d = private_key["n"], private_key["d"]
    k = (n.bit_length() + 7) // 8
    msg_hash = hashlib.sha256(message).digest()
    em = _emsa_pkcs1_v15_encode(msg_hash, k)
    m = _os2ip(em)
    s = pow(m, d, n)
    return _i2osp(s, k)


def verify(public_key: RSAPublicKey, message: bytes, signature: bytes) -> bool:
    """Verify an RSA PKCS#1 v1.5 signature over *message*.

    Returns True if valid, False otherwise.
    """
    n, e = public_key.n, public_key.e
    k = (n.bit_length() + 7) // 8

    if len(signature) != k:
        return False

    s = _os2ip(signature)
    if s >= n:
        return False

    m = pow(s, e, n)
    em = _i2osp(m, k)

    # Parse the PKCS#1 v1.5 padding structure
    if em[0:2] != b"\x00\x01":
        return False

    # Find the 0x00 separator after the padding
    try:
        sep_idx = em.index(b"\x00", 2)
    except ValueError:
        return False

    # Verify padding bytes are all 0xFF
    ps = em[2:sep_idx]
    if len(ps) < 8:
        return False
    if any(b != 0xFF for b in ps):
        return False

    # Extract and verify the DigestInfo
    digest_info = em[sep_idx + 1:]

    if not digest_info.startswith(_SHA256_DIGEST_INFO_PREFIX):
        return False

    extracted_hash = digest_info[len(_SHA256_DIGEST_INFO_PREFIX):]
    expected_hash = hashlib.sha256(message).digest()

    return extracted_hash == expected_hash


def keygen(bits: int = 2048, e: int = 65537) -> tuple[RSAPublicKey, dict]:
    """Generate an RSA keypair (uses sympy for prime generation)."""
    import secrets
    from sympy import nextprime

    p = nextprime(secrets.randbits(bits // 2))
    q = nextprime(secrets.randbits(bits // 2))
    n = p * q
    phi = (p - 1) * (q - 1)
    d = pow(e, -1, phi)

    pub = RSAPublicKey(n=n, e=e)
    priv = {"n": n, "e": e, "d": d, "p": p, "q": q}
    return pub, priv


if __name__ == "__main__":
    pub, priv = keygen(2048)

    msg = b"software-update-v2.3.1.bin"
    sig = sign(priv, msg)

    assert verify(pub, msg, sig), "valid signature rejected"
    assert not verify(pub, b"tampered", sig), "tampered message accepted"

    # Corrupted signature
    bad_sig = bytearray(sig)
    bad_sig[-1] ^= 0x01
    assert not verify(pub, msg, bytes(bad_sig)), "corrupted sig accepted"

    print("OK: sign, verify, reject tampered message, reject corrupted sig")
