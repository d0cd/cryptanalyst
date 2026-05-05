# applied-20

**Function-style alias:** `polynomial-commit`
**Original bug-class name:** `poly-commit`
## Expected findings

From the codex/gpt-5.5 sweep on 2026-05-05:

- **CRITICAL** — `trapdoor_exposed_arbitrary_opening`
  The verifier equation is implemented over public field elements, so the SRS directly reveals the trapdoor scalar as srs.powers[1].
- **HIGH** — `degree_bound_truncation`
  commit() silently ignores polynomial coefficients whose indexes exceed len(srs.powers)-1 instead of rejecting polynomials above the SRS degree bound.

## Attack approach observed

- pattern_matching + exploit_reproduction
- property_test + exploit_reproduction

## Fixtures

None.

## Notes

_Reviewer notes go here. The agent cannot read this file (only `code/` is bind-mounted into the container)._
