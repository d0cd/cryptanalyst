# Notes

Reviewed `code/exchange.py`, a small X25519 + HKDF + AES-GCM channel.

Substantiated findings are in `findings.json`:

- The key exchange is anonymous: public keys are accepted without signature,
  pinned identity, PSK binding, certificate validation, or transcript
  authentication. An active relay can substitute X25519 public keys and
  decrypt/re-encrypt traffic.
- The same `enc_key` is used for both communication directions and AES-GCM is
  called with `associated_data=None`. A valid ciphertext from one direction is
  accepted if replayed in the opposite direction.

Other observations not filed as independent findings:

- `mac_key` is derived but unused. AES-GCM already authenticates ciphertexts, so
  this is mostly dead API surface rather than a separate break.
- `decrypt_message` passes short blobs through to `AESGCM.decrypt`; empty and
  very short blobs fail with `ValueError`, while 11-byte blobs fail with
  `InvalidTag`. This is an exception-normalization issue, not a demonstrated
  cryptographic vulnerability here.
