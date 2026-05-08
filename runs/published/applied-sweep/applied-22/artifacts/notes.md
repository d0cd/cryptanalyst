# Notes

## Substantiated finding

- `code/rsa_crt.py:29-36` is vulnerable to the classic RSA-CRT fault attack because the CRT result is returned without verification. The reproduction in `artifacts/repro/rsa_crt_fault_factor.py` uses the target's `decrypt_with_fault` helper to simulate a one-bit fault in the `m1` branch and recovers a private factor via `gcd(correct - faulty, n)`.

## Lower-confidence observations

- `keygen(bits)` samples primes with `nextprime(secrets.randbits(bits // 2))`. This treats `bits` as an upper bound, not a guaranteed RSA modulus size, because leading zero bits are allowed. It can also generate equal or tiny primes if the RNG output is equal or small. For normal 2048-bit use this is mostly a robustness/API issue rather than a practical exploit, so I did not include it as a finding.
- The module implements raw RSA decryption with no padding layer. That is dangerous if exposed directly as an encryption scheme, but this file does not provide an encryption API or specify a padding contract, so I left it as context rather than a finding.
