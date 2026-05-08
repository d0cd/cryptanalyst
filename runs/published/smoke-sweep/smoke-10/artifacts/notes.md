# Notes

Target: `code/wrap.py`, a password-based wrapper using PBKDF2-HMAC-SHA256
and AES-256-GCM.

Substantiated finding:

- `rewrap()` preserves a caller-supplied salt and `_derive()` deterministically
  maps `(password, salt)` to both the AES key and the GCM nonce. If two valid
  blobs have the same salt and are rewrapped to the same new password, the
  output encryptions reuse the same AES-GCM key and nonce. The repro in
  `artifacts/repro/rewrap_nonce_reuse.py` shows that XORing the rewrapped
  ciphertext bodies reveals XOR of the two wrapped secrets.

Other observations that I did not promote to findings:

- `wrap()` draws a 128-bit random salt, so accidental salt collision from
  honest calls to `wrap()` alone is negligible. The demonstrated issue is in
  trusting/preserving blob salt during `rewrap()` and using that salt-derived
  deterministic nonce as the only per-encryption nonce.
- Calling `rewrap(old_password, old_password, blob)` returns the original blob
  byte-for-byte because key, nonce, and plaintext are unchanged. This leaks
  that a no-op rotation occurred, but I did not treat that as a standalone
  cryptographic finding.
