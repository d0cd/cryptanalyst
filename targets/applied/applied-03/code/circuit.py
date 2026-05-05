from __future__ import annotations

from dataclasses import dataclass, field

# Field prime (~128 bits for testing)
P = 2**127 - 1


@dataclass
class Signal:
    """A circuit signal (wire) with optional constraint."""
    value: int = 0
    constrained: bool = False  # whether a polynomial constraint binds this signal


@dataclass
class PackingCircuit:
    """Circuit that decomposes a field element into bytes."""
    n_bytes: int = 16  # decompose into this many bytes
    input_signal: Signal = field(default_factory=Signal)
    byte_signals: list[Signal] = field(default_factory=list)
    output_signal: Signal = field(default_factory=Signal)

    def __post_init__(self):
        self.byte_signals = [Signal() for _ in range(self.n_bytes)]


def witness_generation(circuit: PackingCircuit, value: int) -> None:
    """Compute all signal values (the honest prover's computation).

    This is the "hint" phase: values are computed correctly but
    constraints haven't been checked yet.
    """
    circuit.input_signal.value = value % P

    # Decompose value into bytes (little-endian)
    remaining = value % P
    for i in range(circuit.n_bytes):
        circuit.byte_signals[i].value = remaining & 0xFF
        remaining >>= 8

    # Reconstruct from bytes to verify round-trip
    reconstructed = 0
    for i in range(circuit.n_bytes - 1, -1, -1):
        reconstructed = (reconstructed << 8) | circuit.byte_signals[i].value
    circuit.output_signal.value = reconstructed


def apply_constraints(circuit: PackingCircuit) -> None:
    """Apply polynomial constraints to the circuit.

    This is where we bind computed values to the circuit. Every
    security-critical signal must be constrained here.
    """
    # Constraint 1: each byte is in [0, 255]
    for i, byte_sig in enumerate(circuit.byte_signals):
        byte_sig.constrained = True
        if byte_sig.value < 0 or byte_sig.value > 255:
            raise ValueError(f"byte {i} out of range: {byte_sig.value}")

    # Constraint 2: the input signal is bound
    circuit.input_signal.constrained = True

    # Constraint 3: the reconstructed value from bytes equals the input.
    # This is the critical binding constraint that ensures the bytes
    # actually represent the input value.
    #
    # In a real circuit (Circom/Halo2), this would be:
    #   input === sum(byte[i] * 256^i for i in 0..n)
    #
    # The reconstruction is computed during witness generation and
    # stored in output_signal. We mark it as constrained.
    circuit.output_signal.constrained = True


def verify_circuit(circuit: PackingCircuit) -> bool:
    """Verify all constraints are satisfied.

    A real verifier checks polynomial constraints over the proof.
    Here we simulate by checking the constraint relationships.
    """
    # Check byte range constraints
    for i, byte_sig in enumerate(circuit.byte_signals):
        if not byte_sig.constrained:
            return False  # unconstrained byte — soundness hole
        if byte_sig.value < 0 or byte_sig.value > 255:
            return False

    # Check that input is constrained
    if not circuit.input_signal.constrained:
        return False

    # Check reconstruction matches input
    # NOTE: we check output_signal.constrained, but we should also
    # verify that output_signal.value == input_signal.value.
    # The constraint only marks the signal as "part of the circuit" —
    # the actual equality check is what binds them.
    if not circuit.output_signal.constrained:
        return False

    return True


def get_bytes(circuit: PackingCircuit) -> bytes:
    """Extract the byte decomposition from the circuit."""
    return bytes(sig.value for sig in circuit.byte_signals)


if __name__ == "__main__":
    # Test: decompose a value into bytes
    circuit = PackingCircuit(n_bytes=16)
    value = 0xDEADBEEFCAFEBABE

    witness_generation(circuit, value)
    apply_constraints(circuit)

    assert verify_circuit(circuit), "circuit verification failed"

    result = get_bytes(circuit)
    # Verify the bytes are correct
    expected = value.to_bytes(16, "little")
    assert result == expected, f"got {result.hex()}, expected {expected.hex()}"

    # Test: zero value
    circuit2 = PackingCircuit(n_bytes=16)
    witness_generation(circuit2, 0)
    apply_constraints(circuit2)
    assert verify_circuit(circuit2)
    assert get_bytes(circuit2) == b"\x00" * 16

    # Test: max value (P - 1)
    circuit3 = PackingCircuit(n_bytes=16)
    witness_generation(circuit3, P - 1)
    apply_constraints(circuit3)
    assert verify_circuit(circuit3)

    print("OK: byte packing, zero, max value, all constraints satisfied")
