# smoke-15

**Function-style alias:** `search-index`
**Original bug-class name:** `encrypted-search`
## Expected findings

From the codex/gpt-5.5 sweep on 2026-05-05:

- **HIGH** — `sse_cross_keyword_cooccurrence_leakage`
  The encrypted index reuses the same deterministic encrypted document ID in every keyword posting list and as the document table key.

## Attack approach observed

- pattern_matching + property_test + exploit_reproduction

## Fixtures

None.

## Notes

_Reviewer notes go here. The agent cannot read this file (only `code/` is bind-mounted into the container)._
