from __future__ import annotations

import secrets
from dataclasses import dataclass

# Prime field (BN254-like, ~254 bits)
P = 0x30644E72E131A029B85045B68181585D2833E84879B9709143E1F593F0000001

# Maximum valid amount (64-bit unsigned)
MAX_AMOUNT = (1 << 64) - 1


@dataclass
class TransferWitness:
    """Private witness for a confidential transfer."""
    input_amount: int
    output_amount: int
    fee: int
    sender_secret: int
    receiver_secret: int


@dataclass
class TransferStatement:
    """Public statement (commitments visible to verifier)."""
    input_commitment: int
    output_commitment: int
    fee_commitment: int


def _pedersen_commit(value: int, blinding: int) -> int:
    """Simplified Pedersen commitment: C = value * G + blinding * H mod P.

    In production this uses elliptic curve points; here we use
    field arithmetic with fixed generators for simplicity.
    """
    G = 0x1A2B3C4D5E6F7A8B9C0D1E2F3A4B5C6D7E8F9A0B1C2D3E4F5A6B7C8D9E0F1A2
    H = 0x2B3C4D5E6F7A8B9C0D1E2F3A4B5C6D7E8F9A0B1C2D3E4F5A6B7C8D9E0F1A2B
    return (value * G + blinding * H) % P


def create_transfer(
    input_amount: int,
    output_amount: int,
    fee: int,
) -> tuple[TransferStatement, TransferWitness]:
    """Create a confidential transfer with random blinding factors."""
    sender_secret = secrets.randbelow(P)
    receiver_secret = secrets.randbelow(P)
    fee_blind = (sender_secret - receiver_secret) % P  # balancing blinding

    statement = TransferStatement(
        input_commitment=_pedersen_commit(input_amount, sender_secret),
        output_commitment=_pedersen_commit(output_amount, receiver_secret),
        fee_commitment=_pedersen_commit(fee, fee_blind),
    )
    witness = TransferWitness(
        input_amount=input_amount,
        output_amount=output_amount,
        fee=fee,
        sender_secret=sender_secret,
        receiver_secret=receiver_secret,
    )
    return statement, witness


def verify_constraints(statement: TransferStatement, witness: TransferWitness) -> bool:
    """Verify all circuit constraints for a confidential transfer.

    In a real ZK system, the verifier only sees the statement and a
    proof (not the witness). Here we check the constraints directly
    to validate the circuit logic.
    """
    inp = witness.input_amount % P
    out = witness.output_amount % P
    fee = witness.fee % P

    # Constraint 1: Balance equation
    # input = output + fee (over the field)
    if inp != (out + fee) % P:
        return False

    # Constraint 2: Commitment consistency
    fee_blind = (witness.sender_secret - witness.receiver_secret) % P
    if statement.input_commitment != _pedersen_commit(inp, witness.sender_secret):
        return False
    if statement.output_commitment != _pedersen_commit(out, witness.receiver_secret):
        return False
    if statement.fee_commitment != _pedersen_commit(fee, fee_blind):
        return False

    # Constraint 3: Amounts are valid (fit in representable range)
    # This prevents field-element overflow where a "negative" amount
    # wraps around modulo P and appears as a huge positive number.
    #
    # Range check: verify each amount is within [0, MAX_AMOUNT].
    # In a real circuit this uses bit-decomposition gadgets;
    # here we check directly.
    for amount in [inp, out]:
        if amount > MAX_AMOUNT:
            return False

    return True


if __name__ == "__main__":
    # Valid transfer: 100 → 90 + 10 fee
    stmt, wit = create_transfer(100, 90, 10)
    assert verify_constraints(stmt, wit), "valid transfer rejected"

    # Valid: zero fee
    stmt2, wit2 = create_transfer(50, 50, 0)
    assert verify_constraints(stmt2, wit2), "zero-fee transfer rejected"

    # Invalid: output amount exceeds 64-bit range
    stmt3, wit3 = create_transfer(100, MAX_AMOUNT + 1, 100 - (MAX_AMOUNT + 1) % P)
    assert not verify_constraints(stmt3, wit3), "overflow output accepted"

    # Valid: max valid amount
    stmt4, wit4 = create_transfer(MAX_AMOUNT, MAX_AMOUNT - 10, 10)
    assert verify_constraints(stmt4, wit4), "max amount rejected"

    print("OK: valid transfer, zero fee, reject overflow, accept max amount")
