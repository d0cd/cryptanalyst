# applied-14

**Function-style alias:** `kem-decapsulate`
**Original bug-class name:** `mlkem-decaps`
## Expected findings

From the codex/gpt-5.5 sweep on 2026-05-05:

- **CRITICAL** — `missing_fo_reencryption_check`
  Decapsulation derives and returns a shared secret from the decrypted message without re-encrypting and comparing the ciphertext.

## Attack approach observed

- pattern_matching + exploit_reproduction + property_test

## Fixtures

None.

## Notes

_Reviewer notes go here. The agent cannot read this file (only `code/` is bind-mounted into the container)._
