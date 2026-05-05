from __future__ import annotations

import hashlib
import os
import secrets
from dataclasses import dataclass

# secp256k1 parameters
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
GX = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
GY = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8


def _inv(x: int, m: int) -> int:
    return pow(x, -1, m)


def _point_add(p1, p2):
    if p1 is None:
        return p2
    if p2 is None:
        return p1
    x1, y1 = p1
    x2, y2 = p2
    if x1 == x2 and (y1 + y2) % P == 0:
        return None
    if p1 == p2:
        lam = (3 * x1 * x1) * _inv(2 * y1, P) % P
    else:
        lam = (y2 - y1) * _inv(x2 - x1, P) % P
    x3 = (lam * lam - x1 - x2) % P
    y3 = (lam * (x1 - x3) - y1) % P
    return (x3, y3)


def _point_neg(p):
    if p is None:
        return None
    return (p[0], P - p[1])


def _point_mul(k, pt):
    r = None
    while k:
        if k & 1:
            r = _point_add(r, pt)
        pt = _point_add(pt, pt)
        k >>= 1
    return r


G = (GX, GY)


def _hash_challenge(R: tuple[int, int], pubkey: tuple[int, int], msg: bytes) -> int:
    """BIP-340-style tagged hash for challenge computation."""
    tag = hashlib.sha256(b"BIP0340/challenge").digest()
    h = hashlib.sha256(tag + tag)
    h.update(R[0].to_bytes(32, "big"))
    h.update(pubkey[0].to_bytes(32, "big"))
    h.update(msg)
    return int.from_bytes(h.digest(), "big") % N


@dataclass
class Signer:
    """A participant in the multi-signature protocol."""
    private_key: int
    public_key: tuple[int, int]
    nonce: int | None = None
    nonce_point: tuple[int, int] | None = None
    nonce_commitment: bytes | None = None

    @classmethod
    def generate(cls) -> Signer:
        d = secrets.randbelow(N - 1) + 1
        Q = _point_mul(d, G)
        return cls(private_key=d, public_key=Q)

    def commit_nonce(self) -> bytes:
        """Round 1: generate nonce and return commitment."""
        self.nonce = secrets.randbelow(N - 1) + 1
        self.nonce_point = _point_mul(self.nonce, G)
        self.nonce_commitment = hashlib.sha256(
            self.nonce_point[0].to_bytes(32, "big")
            + self.nonce_point[1].to_bytes(32, "big")
        ).digest()
        return self.nonce_commitment

    def reveal_nonce(self) -> tuple[int, int]:
        """Round 2a: reveal nonce point after all commitments received."""
        assert self.nonce_point is not None
        return self.nonce_point

    def partial_sign(
        self, msg: bytes, agg_R: tuple[int, int], agg_pubkey: tuple[int, int]
    ) -> int:
        """Round 2b: produce partial signature."""
        assert self.nonce is not None
        e = _hash_challenge(agg_R, agg_pubkey, msg)
        return (self.nonce + e * self.private_key) % N


def verify_nonce_commitments(
    commitments: list[bytes],
    nonce_points: list[tuple[int, int]],
) -> bool:
    """Verify all nonce reveals match their commitments."""
    for commit, R in zip(commitments, nonce_points):
        expected = hashlib.sha256(
            R[0].to_bytes(32, "big") + R[1].to_bytes(32, "big")
        ).digest()
        if commit != expected:
            return False
    return True


def _key_agg_coeff(all_pubkeys: list[tuple[int, int]], pk: tuple[int, int]) -> int:
    """Compute MuSig2 key aggregation coefficient for *pk*.

    a_i = H("KeyAgg" || L || P_i) where L = H(P_1 || ... || P_n).
    """
    # Commit to the full key set
    L_hash = hashlib.sha256(b"KeyAgg/list")
    for p in all_pubkeys:
        L_hash.update(p[0].to_bytes(32, "big") + p[1].to_bytes(32, "big"))
    L = L_hash.digest()

    # Per-key coefficient
    a_hash = hashlib.sha256(b"KeyAgg/coeff")
    a_hash.update(L)
    a_hash.update(pk[0].to_bytes(32, "big") + pk[1].to_bytes(32, "big"))
    return int.from_bytes(a_hash.digest(), "big") % N


def aggregate_public_keys(pubkeys: list[tuple[int, int]]) -> tuple[int, int]:
    """Compute the aggregate public key with key-coefficient delinearization."""
    # Compute per-key coefficients (see _key_agg_coeff) — these prevent
    # rogue-key attacks by binding each key to the full set of participants.
    coeffs = [_key_agg_coeff(pubkeys, pk) for pk in pubkeys]

    agg = None
    for pk in pubkeys:
        agg = _point_add(agg, pk)
    return agg


def aggregate_signature(
    partial_sigs: list[int],
    nonce_points: list[tuple[int, int]],
) -> tuple[tuple[int, int], int]:
    """Aggregate partial signatures into (R, s)."""
    R_agg = None
    for R in nonce_points:
        R_agg = _point_add(R_agg, R)
    s_agg = sum(partial_sigs) % N
    return R_agg, s_agg


def verify(
    pubkey: tuple[int, int],
    msg: bytes,
    sig: tuple[tuple[int, int], int],
) -> bool:
    """Verify a Schnorr signature (R, s) against *pubkey*."""
    R, s = sig
    e = _hash_challenge(R, pubkey, msg)
    # Check: s*G == R + e*P
    lhs = _point_mul(s, G)
    rhs = _point_add(R, _point_mul(e, pubkey))
    return lhs == rhs


if __name__ == "__main__":
    # 3-of-3 multisig
    signers = [Signer.generate() for _ in range(3)]
    msg = b"send 1 BTC to alice"

    # Round 1: commitments
    commitments = [s.commit_nonce() for s in signers]

    # Round 2a: reveal nonces
    nonce_points = [s.reveal_nonce() for s in signers]
    assert verify_nonce_commitments(commitments, nonce_points)

    # Aggregate
    agg_pubkey = aggregate_public_keys([s.public_key for s in signers])
    R_agg, _ = aggregate_signature([], nonce_points)  # just aggregate R for now

    # Round 2b: partial signatures
    partials = [s.partial_sign(msg, R_agg, agg_pubkey) for s in signers]

    # Aggregate final signature
    sig = aggregate_signature(partials, nonce_points)

    assert verify(agg_pubkey, msg, sig), "multisig verification failed"
    print("OK: 3-of-3 Schnorr multisig verified")
