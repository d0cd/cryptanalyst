# applied-06

**Function-style alias:** `commitment-store`
**Original bug-class name:** `commit-bind`
## Expected findings

From the codex/gpt-5.5 sweep on 2026-05-05:

- **HIGH** — `ambiguous_commitment_encoding`
  The commitment hashes message || randomness directly and verification recomputes the same concatenation while accepting arbitrary randomness lengths.

## Attack approach observed

- pattern_matching, property_test, exploit_reproduction, web_research

## Fixtures

None.

## Notes

_Reviewer notes go here. The agent cannot read this file (only `code/` is bind-mounted into the container)._
