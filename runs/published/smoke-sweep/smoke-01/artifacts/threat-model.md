# Threat model — smoke-01 / envelope.py

## Construction
AES-GCM authenticated-encryption envelope over the `cryptography`
hazmat AESGCM API. Wire format: `nonce(12) || ct || tag(16)`
(produced/consumed implicitly by AESGCM). Context string is bound
as AAD.

API surface:
- `generate_key() -> bytes` (256-bit)
- `seal(key, plaintext, context) -> bytes`
- `open_(key, blob, context) -> bytes`
- `rotate_key(old_key, new_key, blob, context) -> bytes`

## Attacker roles & capabilities

| Role | Controls | Goal |
|---|---|---|
| **Ciphertext-tamperer** | `blob` (and optionally `context`) | get `open_` to return forged plaintext, or panic the host (DoS) |
| **Context-confuser** | passes a different `context` than was sealed | break authenticated binding (decrypt blob meant for context A under context B) |
| **Bulk encryptor (online)** | repeatedly invokes `seal` with high volume | exhaust 96-bit random-nonce safety bound (≈2^32 msgs/key per NIST SP 800-38D) |
| **Self-test reader** | runs `python envelope.py` to validate | gain false confidence from broken self-tests |

## Trust boundaries

This is a library. The trust boundary is the function signature.
All three string/bytes parameters of `seal`/`open_`/`rotate_key`
are caller-controlled. The `key` is presumed non-attacker-controlled
(KMS/keyring) — if the caller passes an attacker-chosen key, all
bets are off (this is a key-management contract violation, not a
library bug).

For the `__main__` self-test block: the only "input" is execution
itself. Failures should surface as nonzero exit / traceback;
silent pass-throughs constitute the bug class on this surface.

## Code entry points

- `seal` (envelope.py:15-25) — caller-controlled `plaintext`, `context`.
- `open_` (envelope.py:28-37) — caller-controlled `blob`, `context`.
- `rotate_key` (envelope.py:40-44) — composes `open_ ∘ seal`.
- `__main__` (envelope.py:47-81) — internal self-test harness.

## In-scope hypotheses

H1. Self-test exception swallowing. Negative-test pattern
    `try: positive(); assert False, "..."; except Exception: pass`
    catches `AssertionError`, so if the asserted-false case actually
    succeeds the test silently passes. Hides regressions in
    context-binding and tamper-rejection.

H2. AES-GCM random-nonce birthday bound. 96-bit random nonces
    collide at ≈2^32 messages per key. Document, not a bug at
    this layer.

H3. Wire-format slicing edge cases — `blob[:12], blob[12:]` with
    minimum-length check `< 12 + 16`. Verify correctness.

H4. Context-binding completeness — empty / bytes / non-str
    contexts; canonicalization (NFC vs NFD); structured-context
    confusion ("user:" prefix collisions).

H5. `rotate_key` nonce-reuse risk — re-seal under same key would
    use a fresh random nonce; verify nothing is reused.

H6. Generic AEAD-misuse: AAD type, key length validation, etc.
