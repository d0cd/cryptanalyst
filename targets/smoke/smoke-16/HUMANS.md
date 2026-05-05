# smoke-16

**Function-style alias:** `signature-verify`
**Original bug-class name:** `psychic-sig`
## Expected findings

From the codex/gpt-5.5 sweep on 2026-05-05:

- **CRITICAL** — `ecdsa_zero_signature_acceptance`
  The ECDSA verifier accepts the malformed signature (r, s) = (0, 0) for every message and public key.
- **HIGH** — `ecdsa_missing_public_key_validation`
  The verifier accepts arbitrary public-key coordinates and performs elliptic-curve formulas on them without checking that the key is a valid P-256 point of the correct order.

## Attack approach observed

- pattern_matching + differential_test + exploit_reproduction

## Fixtures

None.

## Notes

_Reviewer notes go here. The agent cannot read this file (only `code/` is bind-mounted into the container)._
