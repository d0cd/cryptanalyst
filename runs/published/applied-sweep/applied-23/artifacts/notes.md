# Audit notes

Target reviewed: `code/rsa.py`.

Substantiated findings:

- `encrypt()` is textbook RSA (`pow(m, e, n)`) with no OAEP or randomized encoding. It is deterministic and multiplicatively malleable; see `artifacts/repro/F1_textbook_rsa_malleability.py`.
- `keygen_fast()` deliberately chooses `d` with about `0.28 * log2(N)` bits, which is below the Boneh-Durfee small-private-exponent attack bound of `d < N^0.292`; see `artifacts/repro/F2_keygen_fast_small_d.py`.

Additional observations:

- `decrypt()` does not reject ciphertexts outside `[0, n)`, because Python modular exponentiation reduces them modulo `n`. I did not record this as a standalone finding because the stronger issue is the absence of a padding/encoding scheme and ciphertext validity checks around RSA decryption.
- `_generate_small_d()` is unused and its comment claiming compact `d` occurs naturally for roughly 0.1% of key pairs is not consistent with uniformly distributed inverses for realistic key sizes. I did not record it as a finding because it is not called by the public key generation path.
