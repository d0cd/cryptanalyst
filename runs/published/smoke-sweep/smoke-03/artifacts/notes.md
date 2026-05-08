# notes — smoke-03

Target: `code/cipher.py` — a 27-line AES-CBC wrapper with PKCS#7 padding.
The construction is textbook-broken in three ways; all three have
runnable PoCs in `artifacts/repro/`.

## Findings recorded

| ID | Class | Severity | Repro |
|----|-------|----------|-------|
| F1 | Fixed-IV CBC determinism | MEDIUM | `repro/fixed_iv_determinism.py` |
| F2 | Unauthenticated CBC malleability | HIGH | `repro/cbc_malleability.py` |
| F3 | Unsafe PKCS#7 unpad slice (`pad_len == 0` empties plaintext) | MEDIUM | `repro/empty_unpad.py` |
| F4 | Panic-DoS via empty ciphertext (`padded[-1]` IndexError) | LOW | `repro/empty_ciphertext_indexerror.py` |

## Other observations (not promoted)

**Key length validation absent in this wrapper, but enforced downstream.**
`encrypt(key, ...)` passes `key` directly to `algorithms.AES(key)`. The
`cryptography` library only accepts 16/24/32-byte keys; other lengths raise
`ValueError`. So while the wrapper itself does no validation, the bug class
is not present at this layer. (`code/cipher.py:8`)

**Padding-oracle exposure is structurally absent.** `decrypt` returns
plaintext (or empty bytes) but does not distinguish "bad padding" from
"valid padding" via timing or error channels — there's no validation at
all (F3). A padding-oracle attack against this code would need a side
channel that the wrapper itself doesn't provide; a downstream caller
might (e.g. by raising on parse-error of the unpadded plaintext), at
which point F2+oracle becomes Vaudenay's attack. Worth flagging to a
human reviewer of any caller.

**`encrypt` does not handle empty plaintext distinctly.** `len(b"") % 16
== 0`, so `pad_len = 16`, padded = b'\\x10' * 16, ciphertext = one block.
That's RFC-correct PKCS#7 (full-block padding when input length is a
multiple of block size). Not a bug.

**No nonce/IV input parameter.** The API takes `(key, plaintext)` only —
there is no way for a caller to supply a fresh IV per encryption. This is
the architectural form of F1: even if a caller knows fixed-IV is broken
they have no escape hatch in this API. F1's evidence covers it.

## Panic-path audit on `decrypt` (cycle 2)

Diversifying activity: enumerate every panic an attacker can trigger via
`decrypt(key, attacker_bytes)` to surface bug classes orthogonal to
F1–F3 (which are crypto-property failures, not code-correctness ones).

| Attacker payload | Site | Behavior | Status |
|---|---|---|---|
| `b''` | cipher.py:19 `padded[-1]` | `IndexError` (uncaught) | **F4** |
| 17-byte / non-multiple-of-16 | cipher.py:18 `decryptor.finalize()` | `ValueError` from `cryptography` lib | Library-layer, not wrapper bug |
| Tampered ct → pad_len in (16, len(padded)] | cipher.py:20 `padded[:-pad_len]` | Silent truncation to attacker-chosen prefix length | Folded into F4 supplementary repro; semantically already in F3 summary |
| Tampered ct → pad_len == 0 | cipher.py:20 `padded[:-0]` | Silent empty plaintext | F3 |
| Wrong-length key (e.g. 17 bytes) | cipher.py:16 `algorithms.AES(key)` | `ValueError` from `cryptography` lib | Library-layer, key not attacker-controlled |

The non-multiple-of-16 and bad-key paths produce exceptions from the
library, not from the wrapper itself; they are documented behavior of
`cryptography` and not a wrapper-introduced flaw. F4 is the only path
where the wrapper's own line panics on attacker-controlled input.

## Panic-path audit on `encrypt` (cycle 3)

Symmetric to the decrypt audit — enumerate every panic / surprising
behavior an attacker can trigger via `encrypt(key, attacker_bytes)`.
Recorded so the trust-boundary picture is symmetric and the absence
of new findings on this side is documented, not assumed.

| Attacker payload | Site | Behavior | Status |
|---|---|---|---|
| `b''` (empty) | cipher.py:10-11 | `pad_len=16`, padded=b'\\x10'*16, single-block ct emitted | Correct PKCS#7; round-trips |
| `b'\\x01'` (single byte) | cipher.py:10-11 | `pad_len=15`, padded=b'\\x01'+b'\\x0f'*15, 16-byte ct | Correct |
| `b'A'*16` (full block, no remainder) | cipher.py:10-11 | `pad_len=16`, padded=32 bytes, 32-byte ct | Correct (RFC-mandated full-block pad) |
| Plaintext ending in `\\x01` (looks like 1-byte pad) | cipher.py:11 | Pad still added; round-trips correctly | No ambiguity; PKCS#7 always pads |
| ~1 MiB plaintext | cipher.py:12 | 1048592-byte ct, round-trips | No size-bound issue |
| `str` instead of bytes | cipher.py:10 `len(plaintext) % 16` works, line 11 `plaintext + bytes(...)` raises `TypeError` | Library/Python-layer, API misuse |
| Wrong-length key (e.g. 17 bytes) | cipher.py:8 `algorithms.AES(key)` | `ValueError` from `cryptography` lib | Library-layer; key not attacker-controlled in normal threat model |
| `bytearray` plaintext | cipher.py:11 `bytearray + bytes` works (returns bytearray); `update()` accepts | Round-trips; no bug |
| `memoryview` plaintext | cipher.py:11 `memoryview + bytes` raises `TypeError` | API misuse, not a wrapper bug |

No new wrapper-introduced panic paths or logic flaws on the encrypt
side. The encrypt path is structurally simple — `pad_len = 16 - (len % 16)`
is always in `[1, 16]`, and `bytes([pad_len]) * pad_len` is well-defined
for that range. The only weakness reachable via `encrypt` is F1
(deterministic IV), which is not a panic but an IND-CPA break.

Verified empirically (cycle 3) by running each row from a Python
process; results match this table.

## Things considered and dismissed

- **Timing side channels in `encryptor.update`/`finalize`.** The
  underlying `cryptography` library uses constant-time AES via OpenSSL.
  No timing channel introduced by the wrapper itself.
- **Key-equality / key-confusion across encrypt and decrypt.** Both
  routines accept `key` from the caller; if caller passes mismatched
  keys, `decrypt` returns garbage but raises no error (since there's no
  MAC). This is downstream of F2 and not a separate bug at this layer.
- **Memory zeroization.** Python does not securely zero `key`, `padded`,
  or `plaintext` after use; secret material may persist in interpreter
  memory until GC. This is a property of CPython and the `cryptography`
  library's bytes-based API, not specific to this wrapper. Out of
  scope.
- **Module-level `IV` rebinding.** A caller could `import cipher;
  cipher.IV = b'\\x01'*16`, but that's API misuse and would also
  desynchronize encrypt/decrypt within the same process. Not a security
  bug at this layer.
- **First-block specific weakness from all-zero IV.** Since `IV = 0`,
  `P_1 = AES_dec(C_1) XOR 0 = AES_dec(C_1)`. An attacker observing
  `(P_1, C_1)` learns the AES_dec output for one input — but this
  doesn't help recover the key (AES is one-way) and is no worse than
  any other fixed IV. Subsumed by F1.
