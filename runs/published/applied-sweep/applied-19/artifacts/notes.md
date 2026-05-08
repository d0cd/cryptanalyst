# Notes

- The constants in `code/ecdsa.py` are the standard NIST P-256/secp256r1
  parameters (`p`, `a`, `b`, `G`, and `n`), despite comments describing a
  proprietary seed-derived curve. I did not record this as a cryptographic
  break because the parameters are well-known and internally consistent.
- `sign()` uses `secrets.randbelow()` for per-signature nonces. I did not find
  nonce reuse or obvious nonce bias in the implementation.
- `_hash()` reduces SHA-256 modulo `N`; P-256 ECDSA specifications typically
  use the leftmost `n` bits of the hash. For SHA-256 with a 256-bit-order
  curve, this only differs for rare digests greater than or equal to `N`, and I
  did not turn it into a practical exploit.
