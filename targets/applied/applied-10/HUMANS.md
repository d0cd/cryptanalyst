# applied-10

**Function-style alias:** `ecdh-handshake`
**Original bug-class name:** `clean-ecdh`
## Expected findings

From the codex/gpt-5.5 sweep on 2026-05-05:

- **HIGH** — `unauthenticated_key_exchange`
  derive_keys accepts any 32-byte X25519 public key and derives session keys without authenticating the peer public key or binding it to a transcript or identity.
- **MEDIUM** — `missing_direction_binding`
  The protocol derives a single enc_key and uses it for both directions, and encrypt_message/decrypt_message pass no associated data to AES-GCM.

## Attack approach observed

- pattern_matching + exploit_reproduction
- property_test + exploit_reproduction

## Fixtures

None.

## Notes

_Reviewer notes go here. The agent cannot read this file (only `code/` is bind-mounted into the container)._
