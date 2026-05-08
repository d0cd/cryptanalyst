# Notes

## Substantiated

- `verify()` accepts `(r, s) = (0, 0)` for any message and public key. ECDSA requires both signature scalars to be in `[1, n - 1]`; the target checks `[0, n)` and then returns `True` for the all-zero degenerate case.
- `verify()` does not validate public-key coordinates. A malformed key such as `(0, 0)` can verify forged nonzero signatures.

## Additional observations

- The verifier accepts both high-S and low-S ECDSA encodings. That is normal for plain ECDSA unless the surrounding protocol requires canonical signatures.
