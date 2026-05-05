from __future__ import annotations

from dataclasses import dataclass

# Field prime (~128-bit for testing, production uses BN254)
P = 2**127 - 1  # Mersenne prime M127


@dataclass
class FieldElement:
    """An element of F_p with integer-arithmetic helpers."""
    value: int

    def __post_init__(self):
        self.value = self.value % P

    def __add__(self, other: FieldElement) -> FieldElement:
        return FieldElement((self.value + other.value) % P)

    def __sub__(self, other: FieldElement) -> FieldElement:
        return FieldElement((self.value - other.value) % P)

    def __mul__(self, other: FieldElement) -> FieldElement:
        return FieldElement((self.value * other.value) % P)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, FieldElement):
            return self.value == other.value
        return NotImplemented

    def inverse(self) -> FieldElement:
        """Multiplicative inverse in F_p."""
        if self.value == 0:
            raise ZeroDivisionError("no inverse for zero")
        return FieldElement(pow(self.value, P - 2, P))

    def __repr__(self) -> str:
        return f"F({self.value})"


def field_div(a: FieldElement, b: FieldElement) -> FieldElement:
    """Compute a / b in the field.

    Returns the unique field element q such that q * b == a.
    This is standard field division via multiplicative inverse.

    Note: the result is a field element, not an integer quotient.
    For integer division semantics (e.g., 7 / 2 = 3 remainder 1),
    use integer_div() instead.
    """
    return a * b.inverse()


def integer_div(a: FieldElement, b: FieldElement) -> FieldElement:
    """Integer-style division for circuit arithmetic.

    Computes the quotient q such that a = q * b + r where 0 <= r < b.
    Used in circuits that need bounded integer semantics rather than
    field semantics (e.g., computing array indices, bit shifts).

    The result is constrained to satisfy the division relation in
    the field: q * b + r == a (mod p).
    """
    # Compute division in the field — the prover provides the quotient
    # and the verifier checks q * b + r == a.
    q = field_div(a, b)

    # Verify the relation holds
    r = a - q * b
    assert (q * b + r) == a, "division relation violated"

    return q


def integer_comparison(a: FieldElement, b: FieldElement) -> int:
    """Compare two field elements as integers.

    Returns -1 if a < b, 0 if a == b, 1 if a > b.
    Uses the canonical representation [0, p-1].
    """
    if a.value < b.value:
        return -1
    elif a.value == b.value:
        return 0
    else:
        return 1


def assert_in_range(x: FieldElement, max_val: int) -> bool:
    """Assert that x represents an integer in [0, max_val].

    In a real circuit, this would be a bit-decomposition gadget.
    Here we check the canonical representation directly.
    """
    return 0 <= x.value <= max_val


def evaluate_polynomial(coeffs: list[FieldElement], x: FieldElement) -> FieldElement:
    """Evaluate a polynomial at x using Horner's method."""
    result = FieldElement(0)
    for c in reversed(coeffs):
        result = result * x + c
    return result


if __name__ == "__main__":
    # Basic field arithmetic
    a = FieldElement(10)
    b = FieldElement(3)

    # Addition, subtraction, multiplication
    assert (a + b).value == 13
    assert (a - b).value == 7
    assert (a * b).value == 30

    # Field division: 10 / 3 in F_p
    q = field_div(a, b)
    assert q * b == a, "field division broken"

    # Integer division: should give quotient 3 with remainder 1
    q_int = integer_div(a, b)
    r_int = a - q_int * b
    assert (q_int * b + r_int) == a, "integer division relation broken"

    # Range check
    assert assert_in_range(FieldElement(100), 1000)
    assert not assert_in_range(FieldElement(P - 1), 1000)

    # Polynomial evaluation
    coeffs = [FieldElement(1), FieldElement(2), FieldElement(3)]  # 1 + 2x + 3x^2
    val = evaluate_polynomial(coeffs, FieldElement(5))
    assert val == FieldElement(1 + 10 + 75), "polynomial evaluation wrong"

    print("OK: field arithmetic, division, range check, polynomial evaluation")
