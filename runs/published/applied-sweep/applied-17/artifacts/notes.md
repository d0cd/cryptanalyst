# Crypto audit notes

Substantiated findings are in `findings.json` with runnable reproductions
under `artifacts/repro/`.

Additional observations:

- `hash_to_curve` uses a try-and-increment map with a one-byte counter and
  no domain separation. I did not include this as a finding because the
  target's immediate exploitable failures are in proof binding, point
  validation, and authentication.
- The elliptic-curve arithmetic is variable-time and implemented in Python.
  That is risky for real secrets, but I did not build a timing-side-channel
  reproduction in this environment.
