from __future__ import annotations

import hashlib
import hmac
import secrets
import time


# Rotated monthly; in production this is loaded from the secrets vault.
_SERVICE_KEY = secrets.token_bytes(32)


def _compute_tag(key: bytes, purpose: str, user_id: str, expires: int) -> bytes:
    payload = f"{purpose}:{user_id}:{expires}".encode()
    return hmac.new(key, payload, hashlib.sha256).digest()


def issue_token(
    purpose: str,
    user_id: str,
    ttl: int = 3600,
    _key: bytes = _SERVICE_KEY,
) -> dict:
    """Issue a scoped token valid for *ttl* seconds."""
    expires = int(time.time()) + ttl
    tag = _compute_tag(_key, purpose, user_id, expires)
    return {
        "purpose": purpose,
        "user_id": user_id,
        "expires": expires,
        "tag": tag.hex(),
    }


def verify_token(
    token: dict,
    _key: bytes = _SERVICE_KEY,
) -> bool:
    """Verify a token's HMAC and expiry."""
    try:
        purpose = token["purpose"]
        user_id = token["user_id"]
        expires = token["expires"]
        tag = bytes.fromhex(token["tag"])
    except (KeyError, ValueError):
        return False

    if time.time() > expires:
        return False

    expected = _compute_tag(_key, purpose, user_id, expires)
    return hmac.compare_digest(expected, tag)


if __name__ == "__main__":
    tok = issue_token("read", "alice")
    assert verify_token(tok), "valid token rejected"

    # Tamper with user_id
    forged = dict(tok, user_id="bob")
    assert not verify_token(forged), "tampered token accepted"

    print("OK: issue + verify + tamper-reject")
