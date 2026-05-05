# applied-27

**Function-style alias:** `secret-share`
**Original bug-class name:** `shamir-vault`
## Expected findings

From the codex/gpt-5.5 sweep on 2026-05-05:

- **CRITICAL** — `feldman_trivial_generator_accepts_forged_shares`
  Feldman VSS commitments use _FELDMAN_G = 1, so every coefficient commitment is 1 and verification reduces to 1 == 1 for every submitted share.
- **MEDIUM** — `secret_mod_reduction_data_loss`
  share_secret accepts any 32-byte value but converts it to an integer and stores secret_int % P as the Shamir constant term.

## Attack approach observed

- pattern_matching, exploit_reproduction
- property_test, exploit_reproduction

## Fixtures

None.

## Notes

_Reviewer notes go here. The agent cannot read this file (only `code/` is bind-mounted into the container)._
