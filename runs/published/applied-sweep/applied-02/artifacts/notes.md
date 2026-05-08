# Notes

- `code/batch_verify.py` inherits the missing-public-key challenge from
  `_hash_challenge_batch`: the function accepts `A_bytes` but ignores it.
- `verify_single` and `batch_verify` let `_decode_point` exceptions escape for
  malformed point encodings instead of returning `False`. That is likely a
  denial-of-service bug in an API exposed to untrusted signatures or public
  keys, but I did not include it as a primary finding because the two forgeries
  are higher-impact.
- Public key length is not checked before `_decode_point`; extra trailing bytes
  are ignored by the decoding logic after the low 255 bits are extracted.
