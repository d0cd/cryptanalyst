# Notes

Target: `code/tokens.py`, an HMAC-SHA256 API token service.

Substantiated findings were produced for:

- Ambiguous colon-delimited signing input. A token issued for one
  `(purpose, user_id)` pair can be reinterpreted as another pair when either
  field contains `:`.
- Reassignment-based service key rotation does not affect `issue_token()` or
  `verify_token()` because `_SERVICE_KEY` is captured in default arguments at
  function definition time.

Additional observation: `verify_token()` catches `KeyError` and `ValueError`
but not type errors. Malformed tokens such as `{"expires": "1"}` can raise
instead of returning `False`. I did not record this as a crypto finding because
it is input-hardening/availability behavior rather than a cryptographic break.
