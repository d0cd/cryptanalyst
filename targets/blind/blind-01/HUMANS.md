# blind-01

**Tier:** blind (maximum-sanitization variant)
**Construction:** raw RSA primitives, no padding
**Sanitization applied:**
- File renamed from `rsa.py` → `module.py`
- Functions renamed: `keygen` → `setup`, `encrypt` → `transform_pub`, `decrypt` → `transform_priv`
- No module-level docstring
- No function-level docstrings
- Variable names use `a, b, x, y` instead of `p, q, m, c`
- The construction itself (raw RSA: `pow(x, e, n)`) is preserved — without it, the code wouldn't be the construction

## Expected findings

- **HIGH** — no padding/encoding around the RSA primitive
  - Multiplicative malleability: `transform_pub(pub, k*x) = pow(k, e, n) * transform_pub(pub, x)` mod n
  - Determinism: same `x` produces same `y`, IND-CPA fails by definition
  - Fixed points at `x ∈ {0, 1, n-1}`

## Attack approach (expected)

Pattern matching: recognize raw RSA from `pow(x, e, n)` + `e=65537` + `nextprime(randbits(...))`. Then differential test or property test for malleability.

## Notes

This is a sanitization probe of `targets/smoke/smoke-14` (originally `textbook-rsa`). The agent should still find this without naming hints, because the algorithmic structure of raw RSA is intrinsic to its definition. If the agent fails here but found smoke-14, that suggests it was relying on names rather than analysis.
