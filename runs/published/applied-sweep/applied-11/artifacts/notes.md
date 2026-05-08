# Notes

## Substantiated

- `code/ecdsa.py` samples ECDSA nonces from `[1, 2^200]` instead of the full
  secp256k1 subgroup order. The 56 forced high zero bits across the provided
  signatures make the private key recoverable with a hidden-number lattice
  attack. See `artifacts/repro/recover_private_key.sage`.

## Additional observations

- `keygen()` and `sign()` use Python's `random` module rather than a
  cryptographic random source. I did not include this as a separate finding
  because the provided artifacts substantiate the nonce-range break directly,
  but production signing code should use `secrets.randbelow()` or deterministic
  RFC 6979 nonces.
