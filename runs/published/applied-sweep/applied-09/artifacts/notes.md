# Notes

- `code/dh.py` implements affine P-256 ECDH directly and does not validate peer
  public keys before scalar multiplication. The substantiated finding is in
  `findings.json` with a runnable low-order invalid-point reproduction.
- `_STATIC_PRIV` is a hard-coded scalar in `code/dh.py:50`. If this is not just
  challenge scaffolding, it is also a key-management flaw: every deployment using
  this source would share the same private key.
