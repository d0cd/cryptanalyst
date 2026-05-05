# applied-19

**Function-style alias:** `point-mul`
**Original bug-class name:** `wrong-curve`
## Expected findings

From the codex/gpt-5.5 sweep on 2026-05-05:

- **HIGH** — `missing_public_key_validation_infinity_forgery`
  `verify()` never validates that the supplied public key is a real affine curve point and not the internal point-at-infinity sentinel.
- **MEDIUM** — `ecdsa_high_s_signature_malleability`
  `verify()` accepts both halves of the ECDSA scalar range for `s`.

## Attack approach observed

- pattern_matching + exploit_reproduction
- pattern_matching + property_test + exploit_reproduction

## Fixtures

None.

## Notes

_Reviewer notes go here. The agent cannot read this file (only `code/` is bind-mounted into the container)._
