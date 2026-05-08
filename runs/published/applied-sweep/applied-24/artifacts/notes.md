# Notes

- `code/server.py` implements textbook RSA over `SHA-256(message)` with integer signatures.
- The strongest issue is `diagnostics()`: it returns the modulus and the most significant half of `p`. For balanced RSA, known high bits of a prime factor are a classic Coppersmith partial-key-exposure target. The Sage repro samples a normal generated key whose hidden suffix is small enough to keep the demonstration fast, then factors `n` and signs a new message using only diagnostic output.
- `verify()` does not reject signatures outside `[0, n - 1]`. Python's modular exponentiation reduces the input modulo `n`, so `signature + k*n` verifies whenever `signature` verifies. That is a strict-encoding/canonicalization bug for any protocol that treats the integer value as the signature object.
- `keygen(bits)` forces each prime candidate to have its top bit set, but it does not check the final product size. `keygen(1024)` can therefore return a 1023-bit modulus.
