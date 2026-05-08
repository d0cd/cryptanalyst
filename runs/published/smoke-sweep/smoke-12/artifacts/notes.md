# Notes

## Substantiated

- `code/mac.py` implements `SHA256(key || message)`, a secret-prefix MAC. SHA-256 exposes enough chaining state in its digest for a length-extension attack: with a valid tag for one message and the key length, an attacker can append chosen bytes and compute a valid tag for the extended byte string without knowing the key. See `artifacts/repro/sha256_length_extension.py`.

## Follow-up Suspicion

- `verify()` compares tags with Python `==` instead of `hmac.compare_digest()`. That is not constant-time and may leak tag-prefix information in a low-latency setting. I did not include it as a finding because the stronger length-extension bug already breaks unforgeability directly, and a reliable timing exploit depends on deployment conditions.
