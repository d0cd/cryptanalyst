# Threat Model — smoke-03 (AES-CBC wrapper)

## Construction

`code/cipher.py` exposes `encrypt(key, plaintext)` and `decrypt(key, ciphertext)`.
The construction is AES-CBC with PKCS#7 padding and a hardcoded all-zero IV
(`IV = b"\x00" * 16`, `code/cipher.py:4`). No MAC, no AEAD tag, no padding
validation on decrypt.

## Trust boundary

The library API is the trust boundary. `encrypt` accepts an attacker-chosen
plaintext (e.g. user-supplied data destined to be encrypted under a stable key);
`decrypt` accepts attacker-chosen ciphertext bytes. Both are reachable to
anyone who can call the API or pass bytes that flow through it.

## Attacker roles

- **Network/storage observer (passive).** Sees ciphertexts produced under the
  fixed IV. Capability: pattern-match identical ciphertexts to identical
  plaintexts encrypted under the same key.
- **Active man-in-the-middle / storage tamperer.** Modifies ciphertext bytes
  in transit or at rest. Capability: flip arbitrary bits in any block, with
  the corresponding bits in the *next* plaintext block flipping deterministically
  (CBC malleability). Decrypt accepts the tampered ciphertext silently.
- **Chosen-plaintext adversary.** Submits two plaintexts and observes
  ciphertexts. Capability: distinguish whether the same plaintext was encrypted
  twice (IND-CPA break under fixed IV).

## Capabilities → reachability

| Capability | Reaches | Tier |
|---|---|---|
| Determinism via fixed IV (`code/cipher.py:4,8,16`) | every `encrypt` call | 1 |
| Bit-flip mauling on `decrypt` (no MAC at `code/cipher.py:15-20`) | every `decrypt` call | 1 |
| Padding-oracle / blind-trust unpad (`code/cipher.py:19`) | every `decrypt` call | 1 |

All three are reachable from the public API with attacker-controlled bytes
and no intervening validation.
