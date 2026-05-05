# applied-32

**Function-style alias:** `zk-prover`
**Original bug-class name:** `sigma-protocol`
## Expected findings

From the codex/gpt-5.5 sweep on 2026-05-05:

- **CRITICAL** — `schnorr_nonce_reuse`
  `prove_batch` reuses one Schnorr nonce/commitment `R` for every message in the batch while deriving a different Fiat-Shamir challenge per message.
- **HIGH** — `missing_public_key_validation`
  `verify_fiat_shamir` never validates that `Y` is a non-identity member of the Schnorr subgroup.

## Attack approach observed

- pattern_matching + exploit_reproduction

## Fixtures

None.

## Notes

_Reviewer notes go here. The agent cannot read this file (only `code/` is bind-mounted into the container)._
