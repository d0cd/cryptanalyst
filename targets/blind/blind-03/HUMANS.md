# blind-03

**Tier:** blind (maximum-sanitization variant)
**Construction:** ECDSA verifier (secp256k1) with a "psychic signature" backdoor
**Sanitization applied:**
- File renamed from `ecdsa.py` → `module.py`
- Functions renamed: `verify` → `check`, helpers prefixed with `_`
- No docstrings of any kind
- Curve constants `P, A, B, N, GX, GY, G` use plain math letters (no `secp256k1` string anywhere)
- No comments revealing the bug

## Expected findings

- **CRITICAL** — `check` accepts the malformed signature `(r, s) = (0, 0)` for every message and public key (CVE-2022-21449 "psychic signature" pattern)
- **HIGH** (also expected) — range check uses `r > N` / `s > N` allowing `r = 0` and `s = 0` through the bounds (FIPS 186-5 requires `r, s ∈ [1, N-1]`)
- **(maybe) MEDIUM** — `check` doesn't validate that `pub` is on the curve and not the identity

## Attack approach (expected)

Pattern matching for `if r == 0 and s == 0: return True` (this is a giveaway in code review) plus differential test against `cryptography.hazmat.primitives.asymmetric.ec` for the same `(0,0)` signature.

## Notes

Sanitized variant of `targets/smoke/smoke-16` (originally `psychic-sig` / `signature-verify`). The bug is structural — `(r, s) = (0, 0)` is hard-coded as accepting — so even with renamed identifiers the agent should catch it from line-by-line reading. If it doesn't catch this one, that's actionable feedback about whether the agent reads carefully or only pattern-matches names.
