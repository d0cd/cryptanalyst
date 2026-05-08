# Notes

Target reviewed: `code/kzg.py`.

Substantiated findings are in `artifacts/findings.json` with runnable
reproductions under `artifacts/repro/`.

Additional observations:

- `verify_eval()` assumes `srs.powers[1]` exists, so an SRS with
  `max_degree=0` raises `IndexError` instead of failing validation. This is
  input hardening rather than a separate cryptographic finding.
- `trusted_setup()` accepts caller-provided secrets without range checks.
  Secrets congruent modulo `P` produce the same powers; `secret=0` creates a
  degenerate SRS. The arbitrary-opening issue is already enough to break
  soundness for normal nonzero setups, so I did not split this into a separate
  finding.
