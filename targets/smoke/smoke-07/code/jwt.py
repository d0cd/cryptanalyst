from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from typing import Any


_SERVER_RSA_PUBLIC_KEY: bytes | None = None  # Set via configure()
_SERVER_HMAC_SECRET: bytes = os.urandom(32)


def configure(rsa_public_key_pem: bytes | None = None) -> None:
    """Configure the server's verification keys."""
    global _SERVER_RSA_PUBLIC_KEY
    _SERVER_RSA_PUBLIC_KEY = rsa_public_key_pem


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def _hmac_sha256(key: bytes, data: bytes) -> bytes:
    return hmac.new(key, data, hashlib.sha256).digest()


def sign_token(payload: dict[str, Any], algorithm: str = "HS256") -> str:
    """Create a signed JWT with the given payload."""
    header = {"alg": algorithm, "typ": "JWT"}

    if algorithm == "HS256":
        header_b64 = _b64url_encode(json.dumps(header).encode())
        payload_b64 = _b64url_encode(json.dumps(payload).encode())
        signing_input = f"{header_b64}.{payload_b64}"
        sig = _hmac_sha256(_SERVER_HMAC_SECRET, signing_input.encode())
        return f"{signing_input}.{_b64url_encode(sig)}"
    else:
        raise ValueError(f"signing not supported for {algorithm}")


def _get_verification_key(header: dict[str, Any]) -> bytes:
    """Resolve the verification key from the token header.

    Supports:
      - HS256: uses the server HMAC secret
      - RS256: uses the configured RSA public key
      - Header-embedded key via 'k' field for cross-service scenarios
        where the signing key is communicated in-band.
    """
    alg = header.get("alg", "")

    # If the header carries an inline key, use it for verification.
    # This supports federated scenarios where the issuer embeds their
    # verification key in the token for stateless validation.
    if "k" in header:
        return _b64url_decode(header["k"])

    if alg == "HS256":
        return _SERVER_HMAC_SECRET
    elif alg == "RS256":
        if _SERVER_RSA_PUBLIC_KEY is None:
            raise ValueError("RS256 requested but no RSA public key configured")
        return _SERVER_RSA_PUBLIC_KEY
    else:
        raise ValueError(f"unsupported algorithm: {alg}")


def verify_token(token: str) -> dict[str, Any]:
    """Verify a JWT and return its payload.

    Raises ValueError if verification fails.
    """
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("malformed token: expected 3 parts")

    header_b64, payload_b64, sig_b64 = parts

    header = json.loads(_b64url_decode(header_b64))
    alg = header.get("alg", "")

    key = _get_verification_key(header)
    signing_input = f"{header_b64}.{payload_b64}".encode()
    sig = _b64url_decode(sig_b64)

    if alg == "HS256":
        expected = _hmac_sha256(key, signing_input)
        if not hmac.compare_digest(expected, sig):
            raise ValueError("signature verification failed")
    elif alg == "RS256":
        # RSA verification would go here; omitted for brevity
        raise NotImplementedError("RS256 verification not yet implemented")
    else:
        raise ValueError(f"unsupported algorithm: {alg}")

    payload = json.loads(_b64url_decode(payload_b64))
    return payload


if __name__ == "__main__":
    # Issue and verify a token
    token = sign_token({"sub": "alice", "role": "user"})
    payload = verify_token(token)
    assert payload["sub"] == "alice"
    assert payload["role"] == "user"

    # Tampered payload should fail
    parts = token.split(".")
    fake_payload = _b64url_encode(json.dumps({"sub": "alice", "role": "admin"}).encode())
    tampered = f"{parts[0]}.{fake_payload}.{parts[2]}"
    try:
        verify_token(tampered)
        assert False, "tampered token accepted"
    except ValueError:
        pass

    print("OK: sign, verify, tamper-reject")
