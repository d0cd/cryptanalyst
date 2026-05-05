# applied-28

**Function-style alias:** `sig-handler`
**Original bug-class name:** `signature-malleability`
## Expected findings

From the codex/gpt-5.5 sweep on 2026-05-05:

- **CRITICAL** — `wrong_curve_field_parameter`
  The secp256k1 field modulus is mistyped as a 63-hex-digit composite number instead of the standardized 256-bit prime 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F.
- **HIGH** — `missing_public_key_validation`
  The verifier accepts `None`, the implementation's internal point-at-infinity sentinel, as a public key and does not reject it before scalar multiplication.

## Attack approach observed

- pattern_matching, property_test, exploit_reproduction
- pattern_matching, sage_modeling, exploit_reproduction

## Fixtures

None.

## Notes

_Reviewer notes go here. The agent cannot read this file (only `code/` is bind-mounted into the container)._
