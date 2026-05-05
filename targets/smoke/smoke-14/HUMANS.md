# smoke-14

**Function-style alias:** `rsa-encrypt`
**Original bug-class name:** `textbook-rsa`
## Expected findings

From the codex/gpt-5.5 sweep on 2026-05-05:

- **HIGH** — `rsa_no_padding`
  encrypt() applies the raw RSA primitive directly to the caller's integer message with no randomized encoding such as OAEP.
- **LOW** — `rsa_keygen_no_retry_when_e_not_coprime`
  keygen() chooses p and q with nextprime(randbits(...)) and immediately computes d = e^-1 mod phi without checking gcd(e, phi) == 1 or retrying prime selection.

## Attack approach observed

- pattern_matching + exploit_reproduction
- property_test + exploit_reproduction

## Fixtures

None.

## Notes

_Reviewer notes go here. The agent cannot read this file (only `code/` is bind-mounted into the container)._
