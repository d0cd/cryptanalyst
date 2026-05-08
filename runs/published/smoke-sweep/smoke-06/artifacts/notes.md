# Notes

Reviewed `code/hybrid.py`, a small ECDH + AES hybrid encryption helper.

Substantiated findings are in `artifacts/findings.json`:

- `F1`: AES-ECB leaks repeated 16-byte plaintext blocks inside a message.
- `F2`: ciphertexts have no integrity protection; ECB ciphertext blocks can be reordered and accepted.

Other observations that did not become separate findings:

- `decrypt()` does not validate PKCS#7 padding bytes. This is another symptom of missing authenticated encryption, but the block-reordering PoC is a clearer integrity break.
- `_derive_key()` imports `decode_dss_signature` and the module imports `os`, but neither is used. This is dead code, not a cryptographic finding.
- The ECDH output is hashed directly with SHA-256 rather than using HKDF with context binding. For P-256 ECDH this is not the demonstrated break here; the immediate exploitable issues are ECB mode and lack of authentication.
