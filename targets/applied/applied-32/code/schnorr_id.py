from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass

# Schnorr group parameters (512-bit p, 160-bit q)
# Generated deterministically from seed "schnorr-group-v1" for auditability.
P = 0x958ca9ba0cd620c20ea38d44a3bc816700ff71eb619931b751596835921306390a65d2753dbdcef36e2fa9f7a4cdc7e27d6450f5f048e79ac90c9497ab3c5b07
Q = 0x80000000000000000001000000000000000000e5
G = 0x54cf45d6775f0fdc7e1638863cb8e1616012a14aa95a054f2773a171a54b5d85e64dc402b432e715b8223b84ba44cbcd4f471360d783614e405bdd3499b502ba

# Verify group structure at import time
assert pow(G, Q, P) == 1, "G does not have order Q"
assert G > 1, "trivial generator"


@dataclass
class Proof:
    """A Schnorr identification proof transcript."""
    commitment: int   # R = g^r mod p
    challenge: int    # c (random or Fiat-Shamir derived)
    response: int     # s = r + c*x mod q


def keygen() -> tuple[int, int]:
    """Generate (private_key x, public_key Y = g^x mod p)."""
    x = secrets.randbelow(Q - 1) + 1
    Y = pow(G, x, P)
    return x, Y


def prove_interactive(x: int, Y: int, challenge: int) -> Proof:
    """Create a proof given the verifier's challenge.

    In the interactive setting, the prover first sends the commitment,
    then receives the challenge, then computes the response.
    """
    r = secrets.randbelow(Q - 1) + 1
    R = pow(G, r, P)
    s = (r + challenge * x) % Q
    return Proof(commitment=R, challenge=challenge, response=s)


def prove_fiat_shamir(x: int, Y: int, msg: bytes) -> Proof:
    """Non-interactive proof via Fiat-Shamir transform.

    The challenge is derived from H(Y || R || msg) to bind the
    proof to the public key, commitment, and message.
    """
    r = secrets.randbelow(Q - 1) + 1
    R = pow(G, r, P)

    p_len = (P.bit_length() + 7) // 8
    c_hash = hashlib.sha256(
        Y.to_bytes(p_len, "big")
        + R.to_bytes(p_len, "big")
        + msg
    ).digest()
    c = int.from_bytes(c_hash, "big") % Q

    s = (r + c * x) % Q
    return Proof(commitment=R, challenge=c, response=s)


def verify_interactive(Y: int, proof: Proof) -> bool:
    """Verify an interactive Schnorr proof.

    Check: g^s == R * Y^c (mod p)
    """
    R, c, s = proof.commitment, proof.challenge, proof.response

    if not (1 <= R < P and 0 <= c < Q and 0 <= s < Q):
        return False

    lhs = pow(G, s, P)
    rhs = (R * pow(Y, c, P)) % P
    return lhs == rhs


def verify_fiat_shamir(Y: int, msg: bytes, proof: Proof) -> bool:
    """Verify a non-interactive (Fiat-Shamir) proof.

    Recomputes the challenge from the transcript and checks the equation.
    """
    R, c, s = proof.commitment, proof.challenge, proof.response

    if not (1 <= R < P and 0 <= c < Q and 0 <= s < Q):
        return False

    p_len = (P.bit_length() + 7) // 8
    c_hash = hashlib.sha256(
        Y.to_bytes(p_len, "big")
        + R.to_bytes(p_len, "big")
        + msg
    ).digest()
    c_expected = int.from_bytes(c_hash, "big") % Q

    if c != c_expected:
        return False

    lhs = pow(G, s, P)
    rhs = (R * pow(Y, c, P)) % P
    return lhs == rhs


def prove_batch(x: int, Y: int, messages: list[bytes]) -> list[Proof]:
    """Produce proofs for multiple messages efficiently.

    Shares a single commitment R across all messages for throughput —
    each message gets the same R but a different Fiat-Shamir challenge
    derived from (Y, R, msg_i), producing different responses.
    """
    r = secrets.randbelow(Q - 1) + 1
    R = pow(G, r, P)

    p_len = (P.bit_length() + 7) // 8
    proofs = []
    for msg in messages:
        c_hash = hashlib.sha256(
            Y.to_bytes(p_len, "big")
            + R.to_bytes(p_len, "big")
            + msg
        ).digest()
        c = int.from_bytes(c_hash, "big") % Q
        s = (r + c * x) % Q
        proofs.append(Proof(commitment=R, challenge=c, response=s))

    return proofs


if __name__ == "__main__":
    x, Y = keygen()

    # Interactive proof
    challenge = secrets.randbelow(Q - 1) + 1
    proof = prove_interactive(x, Y, challenge)
    assert verify_interactive(Y, proof), "interactive proof failed"

    # Fiat-Shamir proof
    msg = b"authenticate user alice"
    fs_proof = prove_fiat_shamir(x, Y, msg)
    assert verify_fiat_shamir(Y, msg, fs_proof), "Fiat-Shamir proof failed"

    # Wrong message should fail
    assert not verify_fiat_shamir(Y, b"wrong msg", fs_proof), "wrong msg accepted"

    # Batch proofs
    msgs = [f"action-{i}".encode() for i in range(5)]
    batch = prove_batch(x, Y, msgs)
    for m, p in zip(msgs, batch):
        assert verify_fiat_shamir(Y, m, p), f"batch proof failed for {m}"

    print("OK: interactive, Fiat-Shamir, batch, reject wrong message")
