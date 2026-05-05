# applied-23

**Function-style alias:** `rsa-keygen`
**Original bug-class name:** `boneh-durfee`
## Expected findings

From the codex/gpt-5.5 sweep on 2026-05-05:

- **HIGH** — `rsa_no_padding_malleability`
  encrypt() applies the RSA public operation directly to the integer message with no OAEP or other randomized encoding.
- **HIGH** — `rsa_small_private_exponent`
  keygen_fast() intentionally samples a private exponent with about 0.28 * log2(N) bits and then publishes the corresponding large public exponent.

## Attack approach observed

- pattern_matching + property_test + exploit_reproduction
- pattern_matching + sage_modeling + exploit_reproduction

## Fixtures

None.

## Notes

_Reviewer notes go here. The agent cannot read this file (only `code/` is bind-mounted into the container)._
