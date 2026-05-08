# Notes

- `code/verify.py` accepts both low-S and high-S ECDSA signatures. That is
  normal for bare ECDSA, but it is signature malleability in protocols that
  require a unique canonical encoding, such as many secp256k1 transaction or
  consensus systems. I did not record this as a finding because the verifier's
  module docstring explicitly says it accepts any `s` in `[1, N-1]`.
- `verify()` has no public-key shape or curve-membership validation. The
  substantiated infinity-key forgery is in `findings.json`; other malformed
  non-curve points may also create denial-of-service or invalid-curve behavior,
  but I did not need those weaker cases for a finding.
