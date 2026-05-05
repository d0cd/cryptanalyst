from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass

# secp256k1 parameters
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
A_CURVE = 0
B_CURVE = 7
GX = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
GY = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
G = (GX, GY)


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
        lam = (3 * x1 * x1 + A_CURVE) * _inv(2 * y1, P) % P
    else:
        lam = (y2 - y1) * _inv(x2 - x1, P) % P
    x3 = (lam * lam - x1 - x2) % P
    y3 = (lam * (x1 - x3) - y1) % P
    return (x3, y3)


def _point_mul(k: int, pt):
    r = None
    while k:
        if k & 1:
            r = _point_add(r, pt)
        pt = _point_add(pt, pt)
        k >>= 1
    return r


def _point_encode(pt) -> bytes:
    if pt is None:
        return b"\x00" * 64
    return pt[0].to_bytes(32, "big") + pt[1].to_bytes(32, "big")


def hash_to_curve(data: bytes) -> tuple[int, int]:
    """Hash arbitrary data to a point on secp256k1.

    Try-and-increment method: hash, interpret as x, check if on curve.
    """
    for counter in range(256):
        h = hashlib.sha256(data + counter.to_bytes(1, "big")).digest()
        x = int.from_bytes(h, "big") % P
        y_sq = (x * x * x + A_CURVE * x + B_CURVE) % P
        # Euler criterion
        if pow(y_sq, (P - 1) // 2, P) != 1:
            continue
        y = pow(y_sq, (P + 1) // 4, P)
        return (x, y)
    raise ValueError("hash_to_curve failed after 256 attempts")


@dataclass
class DLEQProof:
    """Chaum-Pedersen DLOG equality proof: log_G(Y) == log_M(Z)."""
    c: int
    s: int


def dleq_prove(k: int, G_pt, Y, M, Z) -> DLEQProof:
    """Prove that log_G(Y) == log_M(Z) == k, in zero knowledge."""
    v = secrets.randbelow(N - 1) + 1
    V1 = _point_mul(v, G_pt)
    V2 = _point_mul(v, M)

    # Fiat-Shamir challenge
    c_hash = hashlib.sha256(
        _point_encode(G_pt)
        + _point_encode(Y)
        + _point_encode(V1)
        + _point_encode(V2)
    ).digest()
    c = int.from_bytes(c_hash, "big") % N

    s = (v - c * k) % N
    return DLEQProof(c=c, s=s)


def dleq_verify(G_pt, Y, M, Z, proof: DLEQProof) -> bool:
    """Verify a DLEQ proof that log_G(Y) == log_M(Z)."""
    V1 = _point_add(_point_mul(proof.s, G_pt), _point_mul(proof.c, Y))
    V2 = _point_add(_point_mul(proof.s, M), _point_mul(proof.c, Z))

    c_hash = hashlib.sha256(
        _point_encode(G_pt)
        + _point_encode(Y)
        + _point_encode(V1)
        + _point_encode(V2)
    ).digest()
    c_expected = int.from_bytes(c_hash, "big") % N

    return proof.c == c_expected


def client_blind(password: str) -> tuple[tuple[int, int], int]:
    """Client: blind the password. Returns (M, r) where M = r*T."""
    T = hash_to_curve(password.encode())
    r = secrets.randbelow(N - 1) + 1
    M = _point_mul(r, T)
    return M, r


def server_evaluate(
    oprf_key: int, oprf_pubkey: tuple[int, int], M: tuple[int, int]
) -> tuple[tuple[int, int], DLEQProof]:
    """Server: evaluate OPRF and produce proof. Returns (Z, proof)."""
    Z = _point_mul(oprf_key, M)
    proof = dleq_prove(oprf_key, G, oprf_pubkey, M, Z)
    return Z, proof


def client_finalize(
    Z: tuple[int, int],
    r: int,
    oprf_pubkey: tuple[int, int],
    M: tuple[int, int],
    proof: DLEQProof,
) -> bytes:
    """Client: verify proof and unblind. Returns 32-byte PRF output."""
    if not dleq_verify(G, oprf_pubkey, M, Z, proof):
        raise ValueError("DLEQ proof verification failed")
    r_inv = _inv(r, N)
    S = _point_mul(r_inv, Z)
    return hashlib.sha256(_point_encode(S)).digest()


if __name__ == "__main__":
    # Setup
    oprf_key = secrets.randbelow(N - 1) + 1
    oprf_pubkey = _point_mul(oprf_key, G)

    # Client blinds
    M, r = client_blind("correct-horse-battery-staple")

    # Server evaluates
    Z, proof = server_evaluate(oprf_key, oprf_pubkey, M)

    # Client finalizes
    output = client_finalize(Z, r, oprf_pubkey, M, proof)
    print(f"OPRF output: {output.hex()[:32]}...")

    # Same password -> same output
    M2, r2 = client_blind("correct-horse-battery-staple")
    Z2, proof2 = server_evaluate(oprf_key, oprf_pubkey, M2)
    output2 = client_finalize(Z2, r2, oprf_pubkey, M2, proof2)
    assert output == output2, "same password produced different output"

    # Different password -> different output
    M3, r3 = client_blind("wrong-password")
    Z3, proof3 = server_evaluate(oprf_key, oprf_pubkey, M3)
    output3 = client_finalize(Z3, r3, oprf_pubkey, M3, proof3)
    assert output != output3, "different password produced same output"

    print("OK: OPRF consistent for same password, distinct for different")
