# Notes

## Substantiated

- `code/keys.py` lacks HKDF domain separation between encryption and MAC key derivation. This is recorded as F1 with a runnable reproduction.

## Other observations

- `_MASTER_SECRET` is generated at import time with `os.urandom(32)`. That is appropriate for a process-local ephemeral secret, but any caller expecting keys to survive process restarts will lose determinism across restarts. I did not record this as a cryptographic finding because the file does not state a persistence requirement.
- The default salt is `b""`. That is not automatically a bug for HKDF with high-entropy input keying material, but it means callers who omit a session salt get the same process-local key pair each time. The more direct security failure is that the two keys in that pair are identical.
