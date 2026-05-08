# Notes

## Substantiated

- `code/mlkem.py` omits the Fujisaki-Okamoto re-encryption/implicit-rejection check in `decaps`. This is exploitable: a ciphertext with `u = 0` and `v = Decompress(m)` decrypts to attacker-chosen `m`, and `decaps` returns `SHA256("ss:" || SHA256(m || pk))`, which the attacker computes from the public key.

## Lower-confidence observations

- `_decode` does not validate ciphertext length or canonical 12-bit coefficient encodings. Short ciphertexts can raise an exception, and non-canonical encodings are reduced modulo `Q`. This is relevant hardening work, but the missing FO check is the security break that makes attacker-crafted ciphertexts accepted.
- `_sample_uniform` uses simple modulo reduction from 16-bit chunks, which is biased because `3329` does not divide `65536`. I did not turn this into a practical exploit for this teaching implementation.
