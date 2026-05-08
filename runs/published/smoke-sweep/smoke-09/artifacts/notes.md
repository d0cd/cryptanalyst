# Audit Notes

## Confirmed

- `code/handshake.py` documents role-separated HMAC confirmations, but
  `verify_peer_confirmation` accepts tags for both labels. See
  `artifacts/findings.json` and `artifacts/repro/F1_reflection_accepts_own_finished.py`.

## Checked But Not Filed

- Low-order X25519 public keys such as all-zero and `u = 1` were tried against
  PyNaCl/libsodium `crypto_scalarmult`; the binding raised `RuntimeError:
  Unexpected library error` instead of deriving a reusable all-zero shared
  secret. I did not file this as a finding.
- The module's `__main__` happy-path simulation passes.
- `python3 -m py_compile code/handshake.py` attempted to write `code/__pycache__`
  and failed because `code/` is read-only in this harness; this is an
  environment constraint, not a target bug.

## Design Notes

- The protocol is unauthenticated ephemeral X25519, so it does not authenticate
  peer identity on its own. I did not file that separately because the module
  appears scoped to key exchange plus key confirmation, not identity
  authentication.
