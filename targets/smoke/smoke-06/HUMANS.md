# smoke-06

**Function-style alias:** `hybrid-encrypt`
**Original bug-class name:** `ecies-default`
## Expected findings

From the codex/gpt-5.5 sweep on 2026-05-05:

- **HIGH** — `aes_ecb_pattern_leak`
  The hybrid encryption layer uses AES-ECB for arbitrary-length messages.
- **HIGH** — `missing_ciphertext_authentication`
  Ciphertexts are encrypted but never authenticated.

## Attack approach observed

- pattern_matching, property_test, exploit_reproduction

## Fixtures

None.

## Notes

_Reviewer notes go here. The agent cannot read this file (only `code/` is bind-mounted into the container)._
