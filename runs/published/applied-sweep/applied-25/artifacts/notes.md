# Notes

- The PKCS#1 v1.5 padding parser in `verify()` checks that the extracted hash is exactly the SHA-256 digest, so I did not find a classic trailing-garbage Bleichenbacher-style parser bypass.
- `keygen()` is test-only but weak as written: it does not enforce exact prime sizes, distinct primes, or `gcd(e, phi) = 1` before computing the inverse. I did not promote this to a finding because the module comments mark signing/keygen as testing-only and the substantiated impact is in public-key verification.
