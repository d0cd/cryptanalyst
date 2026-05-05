# smoke-01

**Function-style alias:** `aead-handler`
**Original bug-class name:** `clean-aead`
## Expected findings

From the codex/gpt-5.5 sweep on 2026-05-05:

- **LOW** — `self_test_exception_swallowing`
  The module's built-in negative self-tests for wrong-context rejection and tamper rejection catch `Exception` around an `assert False` failure path.

## Attack approach observed

- pattern_matching, exploit_reproduction

## Fixtures

None.

## Notes

_Reviewer notes go here. The agent cannot read this file (only `code/` is bind-mounted into the container)._
