# smoke-11

**Function-style alias:** `keygen-utility`
**Original bug-class name:** `bad-randomness`
## Expected findings

From the codex/gpt-5.5 sweep on 2026-05-05:

- **CRITICAL** — `predictable_time_seeded_prng_key_generation`
  generate_session_key reseeds Python's non-cryptographic random module with int(time.time()) on every call, then derives the 32-byte session key from that deterministic PRNG.

## Attack approach observed

- pattern_matching + exploit_reproduction

## Fixtures

None.

## Notes

_Reviewer notes go here. The agent cannot read this file (only `code/` is bind-mounted into the container)._
