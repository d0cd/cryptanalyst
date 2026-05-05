from .ecdsa import P, A, B, N, H_COFACTOR, GX, GY, G, _point_mul

CURVE_NAME = "propri3tary-256-2024"
SEED = "propri3tary-curve-2024"
FIELD_BITS = 256
SECURITY_BITS = 128


def validate_parameters() -> bool:
    """Run parameter validation checks."""
    # G is on the curve
    assert (GY * GY - GX * GX * GX - A * GX - B) % P == 0, "G not on curve"

    # N * G = infinity (generator has claimed order)
    inf = _point_mul(N, G)
    assert inf is None, "G does not have order N"

    # Cofactor
    assert H_COFACTOR == 1, "cofactor must be 1"

    # b is non-zero (degenerate curve check)
    assert B != 0, "b coefficient is zero"

    # Discriminant: 4a^3 + 27b^2 != 0 mod p
    disc = (4 * pow(A, 3, P) + 27 * pow(B, 2, P)) % P
    assert disc != 0, "singular curve"

    return True


if __name__ == "__main__":
    print(f"Curve: {CURVE_NAME}")
    print(f"Field: {FIELD_BITS} bits, Security: {SECURITY_BITS} bits")
    print(f"p = {hex(P)}")
    print(f"N = {hex(N)}")
    print(f"Cofactor = {H_COFACTOR}")
    print("Validating parameters...")
    validate_parameters()
    print("OK: all parameter checks pass")
