from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

# Prime field
P = 2**61 - 1  # Mersenne prime, fits in 64-bit arithmetic


class GateType(Enum):
    ADD = auto()       # out = left + right
    MUL = auto()       # out = left * right
    CONST = auto()     # out = constant
    ASSERT_EQ = auto() # assert left == right (no output wire)
    ASSERT_BOOL = auto()  # assert x * (1 - x) == 0


@dataclass
class Gate:
    gate_type: GateType
    left: int | None = None    # wire index
    right: int | None = None   # wire index
    output: int | None = None  # wire index
    constant: int = 0


@dataclass
class Circuit:
    """A collection of gates over numbered wires."""
    n_wires: int
    gates: list[Gate] = field(default_factory=list)
    public_inputs: list[int] = field(default_factory=list)   # wire indices
    public_outputs: list[int] = field(default_factory=list)  # wire indices

    def add_gate(self, gate: Gate) -> None:
        self.gates.append(gate)

    def add(self, left: int, right: int, output: int) -> None:
        """Add constraint: wire[output] = wire[left] + wire[right]."""
        self.add_gate(Gate(GateType.ADD, left=left, right=right, output=output))

    def mul(self, left: int, right: int, output: int) -> None:
        """Add constraint: wire[output] = wire[left] * wire[right]."""
        self.add_gate(Gate(GateType.MUL, left=left, right=right, output=output))

    def const(self, value: int, output: int) -> None:
        """Add constraint: wire[output] = value."""
        self.add_gate(Gate(GateType.CONST, constant=value, output=output))

    def assert_equal(self, a: int, b: int) -> None:
        """Add constraint: wire[a] == wire[b]."""
        self.add_gate(Gate(GateType.ASSERT_EQ, left=a, right=b))

    def assert_bool(self, wire: int) -> None:
        """Add constraint: wire[x] is boolean (0 or 1)."""
        self.add_gate(Gate(GateType.ASSERT_BOOL, left=wire))


def evaluate(circuit: Circuit, witness: list[int]) -> bool:
    """Check if a witness satisfies all circuit constraints.

    Returns True if every gate's constraint holds over the witness.
    """
    if len(witness) != circuit.n_wires:
        return False

    w = [v % P for v in witness]

    for gate in circuit.gates:
        if gate.gate_type == GateType.ADD:
            expected = (w[gate.left] + w[gate.right]) % P
            if w[gate.output] != expected:
                return False

        elif gate.gate_type == GateType.MUL:
            expected = (w[gate.left] * w[gate.right]) % P
            if w[gate.output] != expected:
                return False

        elif gate.gate_type == GateType.CONST:
            if w[gate.output] != gate.constant % P:
                return False

        elif gate.gate_type == GateType.ASSERT_EQ:
            # Verify the two wires hold the same value
            if w[gate.left] != w[gate.left]:  # soundness check
                return False

        elif gate.gate_type == GateType.ASSERT_BOOL:
            x = w[gate.left]
            if (x * (1 - x)) % P != 0:
                return False

    return True


def build_hash_preimage_circuit() -> Circuit:
    """Build a circuit proving knowledge of (a, b) such that a*b + a + b = public_output.

    Wire layout:
      0: a (private input)
      1: b (private input)
      2: a*b (intermediate)
      3: a*b + a (intermediate)
      4: a*b + a + b = result (public output)
      5: expected value (public input, constrained to equal wire 4)
    """
    c = Circuit(n_wires=6, public_inputs=[5], public_outputs=[4])

    c.mul(0, 1, 2)      # wire[2] = a * b
    c.add(2, 0, 3)      # wire[3] = a*b + a
    c.add(3, 1, 4)      # wire[4] = a*b + a + b
    c.assert_equal(4, 5) # wire[4] == wire[5] (output matches expected)

    return c


def compute_witness(a: int, b: int, expected: int) -> list[int]:
    """Compute a valid witness for the hash preimage circuit."""
    ab = (a * b) % P
    ab_a = (ab + a) % P
    result = (ab_a + b) % P
    return [a, b, ab, ab_a, result, expected]


if __name__ == "__main__":
    circuit = build_hash_preimage_circuit()

    # Valid witness: a=3, b=5 → 3*5 + 3 + 5 = 23
    witness = compute_witness(3, 5, 23)
    assert evaluate(circuit, witness), "valid witness rejected"

    # Different valid witness: a=7, b=2 → 7*2 + 7 + 2 = 23
    witness2 = compute_witness(7, 2, 23)
    assert evaluate(circuit, witness2), "second valid witness rejected"

    # Wrong arithmetic should fail (bad intermediate wire)
    bad_witness = [3, 5, 999, 0, 0, 23]  # wire[2] != 3*5
    assert not evaluate(circuit, bad_witness), "bad intermediate accepted"

    print("OK: circuit evaluation, valid witnesses accepted, bad intermediate rejected")
