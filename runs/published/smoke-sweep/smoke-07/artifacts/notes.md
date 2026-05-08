# Notes

## Substantiated

- `code/jwt.py` trusts a token header field named `k` as the HS256 verification key. Any attacker can choose a key, sign arbitrary claims with it, embed the key in the token header, and pass `verify_token()` without knowing `_SERVER_HMAC_SECRET`. See `artifacts/repro/forge_header_k_hs256.py`.

## Other observations

- The module docstring says RS256 verification is supported, and `configure()` accepts an RSA public key, but the RS256 branch raises `NotImplementedError`. I did not record this as a crypto finding because it is an incomplete feature/availability issue rather than a signature bypass.
- `verify_token()` only verifies the JWS signature and does not validate registered JWT claims such as `exp`, `nbf`, `iss`, or `aud`. Whether this is exploitable depends on how callers use the helper, so I left it as a note rather than a substantiated finding.
