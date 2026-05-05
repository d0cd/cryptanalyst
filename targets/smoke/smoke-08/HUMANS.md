# smoke-08

**Function-style alias:** `kdf-helper`
**Original bug-class name:** `kdf-context`
## Expected findings

From the codex/gpt-5.5 sweep on 2026-05-05:

- **HIGH** — `missing_domain_separation_key_reuse`
  The service claims to derive separate encryption and MAC keys, but derive_encryption_key and derive_mac_key both call HKDF with the same master secret, same caller salt, empty info, and same output length.

## Attack approach observed

- pattern_matching + property_test + exploit_reproduction

## Fixtures

None.

## Notes

_Reviewer notes go here. The agent cannot read this file (only `code/` is bind-mounted into the container)._
