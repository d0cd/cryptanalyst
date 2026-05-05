# applied-01

**Function-style alias:** `aead-stream`
**Original bug-class name:** `gcm-counter-wrap`
## Expected findings

From the codex/gpt-5.5 sweep on 2026-05-05:

- **CRITICAL** — `aes_gcm_nonce_reuse`
  Per-chunk AES-GCM nonces are derived by ORing the chunk index into the low 32 bits of a random base nonce.
- **HIGH** — `unauthenticated_framing_truncation`
  The stream-level framing is not authenticated and `decrypt_stream` does not require all bytes in the blob to be consumed.

## Attack approach observed

- pattern_matching, property_test, exploit_reproduction
- property_test, exploit_reproduction

## Fixtures

None.

## Notes

_Reviewer notes go here. The agent cannot read this file (only `code/` is bind-mounted into the container)._
