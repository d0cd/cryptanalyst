# Notes

## Substantiated

- `code/commit.py` uses `sha256(message + randomness)[:10]` for both commit
  and verify, with no delimiter, length prefix, fixed randomness length check,
  or structured tuple encoding. This makes the `(message, randomness)` boundary
  ambiguous. A malicious committer can choose randomness with a prefix that can
  later be shifted into the message, producing two accepted openings for one
  commitment.

## Other observations

- The 10-byte truncated digest gives roughly 80-bit preimage strength but only
  roughly 40-bit birthday collision security for accidental or brute-force
  binding collisions. I did not include this as a finding because a 40-bit
  collision search is outside the under-30-second reproduction bar here, and
  the code comments explicitly document the compact 10-byte protocol budget.
- `verify()` compares digests with `==` instead of `hmac.compare_digest()`.
  That is worth hardening if commitments are verified across a timing-sensitive
  remote boundary, but I did not produce a reliable timing exploit in this
  environment.
