# Notes

Reviewed `code/stream.py`, which implements chunked AES-GCM with a random
12-byte base nonce and a per-chunk nonce derived from the base nonce.

Substantiated findings are in `findings.json`:

- `_chunk_nonce` uses bitwise OR to mix the chunk index into the low 32 bits of
  the base nonce. This is not injective. Any set bit in the random base counter
  collapses chunk indices that differ only in that bit, causing AES-GCM nonce
  reuse within a single encrypted stream.
- The stream framing header and final length are not authenticated as a whole.
  In particular, `num_chunks` can be decreased and `decrypt_stream` will return
  a valid prefix without checking for trailing ciphertext.

Other observations:

- `decrypt_stream` does little input validation and can raise low-level
  exceptions for malformed short blobs. I did not record that separately because
  the authenticated truncation behavior is the security-relevant framing issue.
- I avoided modifying `code/`; an initial `py_compile` attempt failed because
  Python tried to create `code/__pycache__` on a read-only filesystem.
