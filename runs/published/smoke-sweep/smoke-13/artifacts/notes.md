# Notes

Substantiated findings are in `findings.json` with runnable repros.

Additional observations not promoted to findings:

- `process_message` generally ignores the documented state machine and directly mutates state based only on `msg["type"]`. F1 and F2 demonstrate the highest-impact cases.
- `client_finish` derives its HMAC key from `ctx.transcript_hash()`, which is public transcript data rather than a secret. Even if the receiver verified it, this would not authenticate the client.
- The module-level documentation mentions ephemeral public keys and a shared secret, but the implementation only exchanges nonces and never populates or uses `HandshakeContext.shared_secret`.
- Transcript entries are `str(dict).encode()` values without a canonical protocol encoding or length framing. That makes the transcript format brittle across implementations and message construction styles.
