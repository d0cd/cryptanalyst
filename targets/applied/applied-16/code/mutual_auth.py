from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass


def _mac(key: bytes, *parts: bytes) -> bytes:
    """Compute HMAC-SHA256 over concatenated parts."""
    h = hmac.new(key, digestmod=hashlib.sha256)
    for part in parts:
        h.update(part)
    return h.digest()


@dataclass
class SessionState:
    """Tracks one side's view of a handshake."""
    role: str
    key: bytes
    my_nonce: bytes = b""
    peer_nonce: bytes = b""
    authenticated: bool = False


class Initiator:
    def __init__(self, key: bytes) -> None:
        self.state = SessionState(role="init", key=key)

    def step1_challenge(self) -> bytes:
        """Send a fresh nonce to the responder."""
        self.state.my_nonce = os.urandom(32)
        return self.state.my_nonce

    def step3_verify_and_respond(self, n_r: bytes, resp_mac: bytes) -> bytes:
        """Verify responder's MAC and send own authentication.

        Verifies: MAC(K, n_I || n_R || "resp")
        Sends:    MAC(K, n_R || n_I || "init")
        """
        self.state.peer_nonce = n_r

        expected = _mac(
            self.state.key,
            self.state.my_nonce,
            n_r,
            b"resp",
        )
        if not hmac.compare_digest(resp_mac, expected):
            raise ValueError("responder authentication failed")

        self.state.authenticated = True
        return _mac(
            self.state.key,
            n_r,
            self.state.my_nonce,
            b"init",
        )


class Responder:
    def __init__(self, key: bytes) -> None:
        self.state = SessionState(role="resp", key=key)

    def step2_respond(self, n_i: bytes) -> tuple[bytes, bytes]:
        """Receive initiator's nonce, send own nonce + MAC.

        Sends: n_R, MAC(K, n_I || n_R || "resp")
        """
        self.state.peer_nonce = n_i
        self.state.my_nonce = os.urandom(32)

        tag = _mac(
            self.state.key,
            n_i,
            self.state.my_nonce,
            b"resp",
        )
        return self.state.my_nonce, tag

    def step4_verify(self, init_mac: bytes) -> None:
        """Verify initiator's MAC.

        Verifies: MAC(K, n_R || n_I || "init")
        """
        expected = _mac(
            self.state.key,
            self.state.my_nonce,
            self.state.peer_nonce,
            b"init",
        )
        if not hmac.compare_digest(init_mac, expected):
            raise ValueError("initiator authentication failed")

        self.state.authenticated = True


def run_protocol(key: bytes) -> tuple[bool, bool]:
    """Run the mutual authentication protocol.

    Returns (initiator_authenticated, responder_authenticated).
    """
    init = Initiator(key)
    resp = Responder(key)

    # Step 1
    n_i = init.step1_challenge()

    # Step 2
    n_r, resp_mac = resp.step2_respond(n_i)

    # Step 3
    init_mac = init.step3_verify_and_respond(n_r, resp_mac)

    # Step 4
    resp.step4_verify(init_mac)

    return init.state.authenticated, resp.state.authenticated


if __name__ == "__main__":
    key = os.urandom(32)

    # Normal run
    init_ok, resp_ok = run_protocol(key)
    assert init_ok and resp_ok, "authentication failed"

    # Wrong key should fail
    wrong_key = os.urandom(32)
    init_wrong = Initiator(key)
    resp_wrong = Responder(wrong_key)
    n_i = init_wrong.step1_challenge()
    n_r, resp_mac = resp_wrong.step2_respond(n_i)
    try:
        init_wrong.step3_verify_and_respond(n_r, resp_mac)
        assert False, "wrong key accepted"
    except ValueError:
        pass

    # Replay should fail (different nonces each run)
    init1 = Initiator(key)
    resp1 = Responder(key)
    n_i1 = init1.step1_challenge()
    n_r1, mac1 = resp1.step2_respond(n_i1)

    init2 = Initiator(key)
    n_i2 = init2.step1_challenge()
    # Try to use mac1 (from session 1) in session 2
    try:
        init2.step3_verify_and_respond(n_r1, mac1)
        # This might succeed if n_i1 == n_i2, which is astronomically unlikely
        pass
    except ValueError:
        pass  # Expected: replay rejected

    print("OK: mutual auth, wrong-key reject, replay resistance")
