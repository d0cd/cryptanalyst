# blind-02

**Tier:** blind (maximum-sanitization variant)
**Construction:** secret-prefix tag construction (`H(key || message)`) sold as a MAC
**Sanitization applied:**
- File renamed from `mac.py` → `module.py`
- Functions renamed: `mac` → `derive`, `verify` → `attest`
- No module-level docstring
- No function-level docstrings (in particular: `"""Compute MAC = SHA256(key || message)."""` removed)
- Variable names use `k, m, t` (still standard but neutral)

## Expected findings

- **HIGH** — length-extension on secret-prefix SHA-256 construction
  - Given `t = derive(k, m)` and `len(k)`, attacker can compute `derive(k, m || pad(k||m) || m')` for any `m'` without knowing `k`
  - Standard SHA-256 length-extension attack via Merkle-Damgård state recovery

## Attack approach (expected)

Pattern matching: recognize `H(key || msg)` shape (two `update()` calls with key first then message). Build a length-extension exploit using `hashpumpy` or hand-rolled state recovery.

## Notes

Sanitized variant of `targets/smoke/smoke-12` (originally `length-extension` / `mac-utility`). The construction is intrinsic; renaming `mac` → `derive` removes the role hint but the body still says "secret prefix into SHA-256" plainly.
