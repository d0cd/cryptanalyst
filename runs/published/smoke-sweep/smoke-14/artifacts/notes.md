# Notes

## Key size is not enforced

`keygen(bits)` calls `secrets.randbits(bits // 2)` for each prime candidate
without forcing the high bit. As a result, the returned modulus is often
smaller than the requested size. A quick probe over 200 generated keys found
moduli below the requested size in 166/200 runs for `bits=16`, 175/200 for
`bits=32`, 171/200 for `bits=64`, and 169/200 for `bits=128`.

This is worth fixing by sampling prime candidates in the intended interval,
but I did not include it as a finding because the direct security impact for
default 2048-bit keys is variable rather than a crisp exploit.

## Repeated primes are not rejected

`keygen()` does not check `p != q`. If the RNG repeats the same candidate,
the code can construct a square modulus and an incorrect private exponent for
the assumed `phi = (p - 1) * (q - 1)`. With `secrets.randbits`, this is
negligible for normal key sizes, so I left it as a hardening note rather than
a finding.
