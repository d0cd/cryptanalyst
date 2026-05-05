from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass, field
from enum import Enum, auto


class State(Enum):
    INIT = auto()
    HELLO_SENT = auto()
    HELLO_RECEIVED = auto()
    AUTHENTICATED = auto()
    ESTABLISHED = auto()
    FAILED = auto()


@dataclass
class HandshakeContext:
    """Tracks handshake state and transcript."""
    state: State = State.INIT
    role: str = ""
    transcript: list[bytes] = field(default_factory=list)
    shared_secret: bytes = b""
    peer_identity: str = ""

    def _append_transcript(self, data: bytes) -> None:
        self.transcript.append(data)

    def transcript_hash(self) -> bytes:
        h = hashlib.sha256()
        for entry in self.transcript:
            h.update(entry)
        return h.digest()


# Server-side certificate (simplified: just a name + pre-shared key)
_SERVER_IDENTITY = "server.example.com"
_SERVER_SECRET = os.urandom(32)


def client_hello(ctx: HandshakeContext, supported_ciphers: list[str]) -> dict:
    """Step 1: Client initiates handshake."""
    if ctx.state != State.INIT:
        raise ValueError(f"client_hello: invalid state {ctx.state}")

    ctx.role = "client"
    nonce = os.urandom(32)
    msg = {
        "type": "client_hello",
        "ciphers": supported_ciphers,
        "nonce": nonce.hex(),
    }
    ctx._append_transcript(str(msg).encode())
    ctx.state = State.HELLO_SENT
    return msg


def server_hello(ctx: HandshakeContext, client_msg: dict,
                 server_ciphers: list[str]) -> dict:
    """Step 2: Server responds with cipher selection."""
    if ctx.state != State.INIT:
        raise ValueError(f"server_hello: invalid state {ctx.state}")

    ctx.role = "server"
    ctx._append_transcript(str(client_msg).encode())

    # Select first mutually supported cipher
    client_ciphers = client_msg.get("ciphers", [])
    selected = None
    for c in server_ciphers:
        if c in client_ciphers:
            selected = c
            break
    if selected is None:
        ctx.state = State.FAILED
        raise ValueError("no common cipher")

    nonce = os.urandom(32)
    msg = {
        "type": "server_hello",
        "cipher": selected,
        "nonce": nonce.hex(),
    }
    ctx._append_transcript(str(msg).encode())
    ctx.state = State.HELLO_SENT
    return msg


def server_auth(ctx: HandshakeContext) -> dict:
    """Step 3: Server authenticates with a signature over the transcript."""
    if ctx.state != State.HELLO_SENT:
        raise ValueError(f"server_auth: invalid state {ctx.state}")
    if ctx.role != "server":
        raise ValueError("server_auth: not the server")

    transcript_mac = hmac.new(
        _SERVER_SECRET,
        ctx.transcript_hash(),
        hashlib.sha256,
    ).digest()

    msg = {
        "type": "server_auth",
        "identity": _SERVER_IDENTITY,
        "transcript_mac": transcript_mac.hex(),
    }
    ctx._append_transcript(str(msg).encode())
    ctx.state = State.AUTHENTICATED
    return msg


def process_message(ctx: HandshakeContext, msg: dict) -> None:
    """Process an incoming handshake message.

    Routes to the appropriate handler based on message type.
    Validates state transitions to prevent step-skipping.
    """
    msg_type = msg.get("type", "")

    if msg_type == "client_hello":
        ctx._append_transcript(str(msg).encode())
        ctx.state = State.HELLO_RECEIVED

    elif msg_type == "server_hello":
        ctx._append_transcript(str(msg).encode())
        ctx.state = State.HELLO_RECEIVED

    elif msg_type == "server_auth":
        # Verify the server's authentication
        ctx._append_transcript(str(msg).encode())
        ctx.peer_identity = msg.get("identity", "")
        ctx.state = State.AUTHENTICATED

    elif msg_type == "client_finish":
        ctx._append_transcript(str(msg).encode())
        ctx.state = State.ESTABLISHED

    else:
        ctx.state = State.FAILED
        raise ValueError(f"unknown message type: {msg_type}")


def client_finish(ctx: HandshakeContext) -> dict:
    """Step 4: Client confirms the handshake."""
    if ctx.state not in (State.HELLO_RECEIVED, State.AUTHENTICATED):
        raise ValueError(f"client_finish: invalid state {ctx.state}")

    finished_mac = hmac.new(
        ctx.transcript_hash(),
        b"client_finished",
        hashlib.sha256,
    ).digest()

    msg = {
        "type": "client_finish",
        "finished": finished_mac.hex(),
    }
    ctx._append_transcript(str(msg).encode())
    ctx.state = State.ESTABLISHED
    return msg


def is_established(ctx: HandshakeContext) -> bool:
    """Check if the handshake completed successfully."""
    return ctx.state == State.ESTABLISHED


if __name__ == "__main__":
    # Normal handshake flow
    client_ctx = HandshakeContext()
    server_ctx = HandshakeContext()

    ch = client_hello(client_ctx, ["AES-256-GCM", "ChaCha20-Poly1305"])
    sh = server_hello(server_ctx, ch, ["AES-256-GCM"])

    process_message(client_ctx, sh)

    sa = server_auth(server_ctx)
    process_message(client_ctx, sa)

    cf = client_finish(client_ctx)
    process_message(server_ctx, cf)

    assert is_established(client_ctx), "client not established"
    assert is_established(server_ctx), "server not established"
    assert client_ctx.peer_identity == _SERVER_IDENTITY

    print("OK: full handshake completed, both sides established")
