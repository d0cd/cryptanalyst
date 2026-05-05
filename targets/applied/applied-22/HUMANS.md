# applied-22

**Function-style alias:** `rsa-crt`
**Original bug-class name:** `fault-rsa-crt`
## Expected findings

From the codex/gpt-5.5 sweep on 2026-05-05:

- **HIGH** — `rsa_crt_fault_attack`
  RSA CRT decryption returns the recombined CRT result without verifying it against the public exponent or otherwise checking consistency.

## Attack approach observed

- pattern_matching + exploit_reproduction

## Fixtures

None.

## Notes

_Reviewer notes go here. The agent cannot read this file (only `code/` is bind-mounted into the container)._
