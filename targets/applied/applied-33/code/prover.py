from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass

# Simplified group: prime-order subgroup of Z_p*.
# p = 2*q + 1 (safe prime), g generates the order-q subgroup.
# In real Groth16 this would be a pairing-friendly elliptic curve.
Q = 0x800000000000000000000000000000000000000000000000000000000001c197
P = 2 * Q + 1  # safe prime
G = pow(2, 2, P)  # g = 4 generates order-q subgroup (since p = 2q+1)


@dataclass
class Commitment:
    """A Pedersen-like commitment to a witness value."""
    value: int       # g^witness mod p
    blinding: int    # randomness used


@dataclass
class CommitmentProof:
    """Proof of knowledge of a committed value (sigma protocol)."""
    T: int           # sigma * G (first message)
    response: int    # sigma + e * witness (response)


@dataclass
class Proof:
    """A Groth16-like proof with commitment extensions."""
    # Main SNARK proof elements (simplified to field elements)
    A: int
    B: int
    C: int
    # Commitment proofs-of-knowledge
    commitments: list[Commitment]
    commitment_proofs: list[CommitmentProof]


def commit(witness: int) -> Commitment:
    """Create a commitment to a witness value."""
    return Commitment(
        value=pow(G, witness, P),
        blinding=secrets.randbelow(Q),
    )


def _hash_challenge(*parts: int) -> int:
    """Derive a Fiat-Shamir challenge from integers."""
    h = hashlib.sha256()
    for part in parts:
        h.update(part.to_bytes(32, "big"))
    return int.from_bytes(h.digest(), "big") % Q


def prove(
    witnesses: list[int],
    public_inputs: list[int],
) -> Proof:
    """Generate a proof with commitment extensions.

    Each witness value gets a commitment and a proof-of-knowledge.
    The main SNARK proof (A, B, C) is simplified here.
    """
    # Main proof (simplified — in real Groth16 this involves
    # pairings and the CRS)
    A = secrets.randbelow(P)
    B = secrets.randbelow(P)
    C = secrets.randbelow(P)

    # Create commitments
    commitments = [commit(w) for w in witnesses]

    # Generate commitment proofs-of-knowledge
    # Using a single sigma for efficiency: one random value
    # generates all the T values, reducing prover computation.
    sigma = secrets.randbelow(Q)

    commitment_proofs = []
    for i, (w, cm) in enumerate(zip(witnesses, commitments)):
        T = pow(G, sigma, P)

        # Challenge binds to the commitment and T
        e = _hash_challenge(cm.value, T, A, B, C)

        # Response
        s = (sigma + e * w) % Q

        commitment_proofs.append(CommitmentProof(T=T, response=s))

    return Proof(
        A=A, B=B, C=C,
        commitments=commitments,
        commitment_proofs=commitment_proofs,
    )


def verify(
    proof: Proof,
    public_inputs: list[int],
) -> bool:
    """Verify a proof with commitment extensions.

    Checks each commitment proof-of-knowledge independently.
    """
    # Main SNARK verification (simplified — would check pairing equation)
    # In real Groth16: e(A, B) == e(alpha, beta) * e(sum(pub_i * L_i), gamma) * e(C, delta)
    # Here we skip this and only verify commitment proofs.

    for cm, cp in zip(proof.commitments, proof.commitment_proofs):
        # Recompute challenge
        e = _hash_challenge(cm.value, cp.T, proof.A, proof.B, proof.C)

        # Check: s * G == T + e * commitment
        # i.e., g^s == T * cm^e (mod p)
        lhs = pow(G, cp.response, P)
        rhs = (cp.T * pow(cm.value, e, P)) % P

        if lhs != rhs:
            return False

    return True


def verify_commitments_independent(proof: Proof) -> bool:
    """Additional check: verify that commitment proofs use independent randomness.

    This is a defense-in-depth check that detects sigma reuse.
    """
    T_values = [cp.T for cp in proof.commitment_proofs]
    # All T values should be distinct (with overwhelming probability)
    return len(set(T_values)) == len(T_values)


if __name__ == "__main__":
    # Single witness
    w1 = [42]
    pub1 = [100]
    proof1 = prove(w1, pub1)
    assert verify(proof1, pub1), "single commitment proof failed"

    # Multiple witnesses
    witnesses = [42, 99, 7]
    pub = [100, 200, 300]
    proof = prove(witnesses, pub)
    assert verify(proof, pub), "multi-commitment proof failed"

    # Tampered commitment should fail
    bad_proof = Proof(
        A=proof.A, B=proof.B, C=proof.C,
        commitments=[Commitment(value=pow(G, 999, P), blinding=0)] + proof.commitments[1:],
        commitment_proofs=proof.commitment_proofs,
    )
    assert not verify(bad_proof, pub), "tampered commitment accepted"

    print("OK: single and multi-commitment proofs, tamper detection")
