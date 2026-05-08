# Notes

## Confirmed

- `code/sss.py` uses a prime field: `sympy.isprime(P)` returned `True` for `P = 2^256 - 189`.
- `code.sss.split` validates `t <= n` and `t >= 2`, but `code.vault.share_secret` bypasses `split` and builds the polynomial itself. The two substantiated findings above are the security-impacting consequences I could reproduce cleanly.

## Lower-confidence follow-up

- `share_secret` should probably share the same parameter validation as `sss.split`; currently values such as `t > n` or `n <= 0` can produce vault objects that cannot satisfy their advertised reconstruction threshold. I did not include this as a finding because it is input validation/availability rather than a cryptographic break.
