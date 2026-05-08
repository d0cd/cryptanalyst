# Notes — smoke-01 / aead-handler

## Summary
The target is an 82-line wrapper around `cryptography.hazmat.primitives.ciphers.aead.AESGCM`
exposing `seal / open_ / rotate_key` with a context-string AAD. The
construction itself is correct usage of AES-GCM-with-random-IV; the
substantive defect is in the in-module self-test (filed as F1 — self-test
exception swallowing).

## Adversarial-reading audit (file is small enough to enumerate)

| Concern | Verdict | Notes |
|---|---|---|
| AES-GCM with random 96-bit IV | OK at typical volumes | birthday-bound at ~2^32 messages per key (NIST SP 800-38D §8.3); not a finding for a generic AEAD wrapper, but worth flagging if downstream callers expect petabyte-scale traffic under one key. `code/envelope.py:22` |
| Tag length | OK | `cryptography` library default = 128-bit tag, encoded as last 16 bytes of `encrypt()` output. Length check `< 12 + 16` on line 33 matches. |
| AAD = context.encode("utf-8") | OK | Both `seal` and `open_` use the same encoding. Tag binding is exact-byte. |
| `len(blob) < 28` minimum | OK | Allows empty plaintext (28 = 12 nonce + 0 ct + 16 tag). `decrypt()` handles. |
| `rotate_key` plaintext exposure window | Not exploitable in Python | Plaintext lives in CPython memory between `open_` and `seal`. No way to wipe in pure Python; standard Python crypto limitation. `code/envelope.py:43-44` |
| Type confusion (`context=None`, `context=bytes`) | Programming error | `None.encode` → AttributeError; `bytes.encode` → AttributeError. Not exploitable. |
| Nonce reuse via `os.urandom(12)` | OK | Probability 2^-96 per pair; relies on `os.urandom` quality. |
| Domain separation between callers | Caller responsibility | API takes raw `context` strings; no scheme prefix. Caller must avoid colliding context strings across uses. Not a defect of this module, but worth documenting in callsites. |
| Unused imports | Cosmetic | `import struct` (line 4) and `import time` (line 5) are not used anywhere. |

## Hypotheses considered and refuted

1. **Format ambiguity in `nonce + ct`** — refuted. cryptography's `encrypt()`
   returns `ciphertext || tag`; `seal()` prepends 12-byte nonce; `open_()`
   slices off exactly 12 bytes and passes the rest to `decrypt()`. Tag is
   the trailing 16 bytes, handled by the library. No length-confusion
   vector.

2. **AAD vs no-AAD asymmetry** — refuted. Both seal and open call
   `decrypt(nonce, ct, aad)` and `encrypt(nonce, plaintext, aad)`
   with `aad = context.encode("utf-8")`. Symmetric. A regression where
   one side passes `b""` would be caught by the tag check (assuming the
   self-test could detect it — see F1 for why it can't).

3. **`rotate_key` reuses the same nonce** — refuted. `seal()` always calls
   `os.urandom(12)` for a fresh nonce; rotation produces a new blob with
   independent randomness.

4. **Context unicode normalization** — not a bug. AAD matches by raw bytes;
   if a caller writes "café" composed vs decomposed the AAD differs and
   `decrypt()` will reject. That is the correct behavior (no false
   equivalence between visually-similar contexts).

## Bug classes not investigated this cycle

- Side-channel timing on `decrypt()` — out of scope; relies on the
  cryptography library's constant-time properties.
- Nonce-reuse misuse-resistance (would require switching to AES-GCM-SIV).
  Not a defect of this module given its API contract.

## Cycle 2 — property-based stress test

`artifacts/probes/property_test_envelope.py` exercises four contracts
under Hypothesis-generated inputs (1200 examples total):

| Property | Examples | Result |
|---|---|---|
| P1 round-trip: `open_(k, seal(k, m, c), c) == m` | 300 | OK |
| P2 context binding: `open_(k, seal(k, m, c), c'!=c)` raises `InvalidTag` | 300 | OK |
| P3 tamper rejection: any single-bit flip causes raise | 400 | OK |
| P4 rotation: `open_(k', rotate_key(k, k', blob, c), c) == m` and rotated blob does NOT open under `k` | 200 | OK |

P3 is the strongest signal: random single-byte XOR flips at random
positions cover nonce bytes (0–11), ciphertext bytes (12..N−16), and
tag bytes (N−16..N). Every flip caused `open_` to raise
`InvalidTag` or `ValueError`, consistent with AES-GCM's authenticity
guarantee being correctly relied on.

P4 confirms `rotate_key` transitions the key: the rotated blob is
not openable under the old key (when `k1 != k2`). This refutes the
hypothesis "rotation might preserve some old-key-decryptable
component" — there is none; `rotate_key` performs decrypt+re-encrypt
end-to-end via the public AESGCM API. `code/envelope.py:43-44`.

No properties violated. Corroborates the cycle-1 finding that
the construction is correct at the bytes level; F1 (self-test
exception swallowing) remains the only substantive finding.

## Cycle 3 — adversarial-reading pass on `open_` exception contract

Activity: enumerate every load-bearing assumption in `open_` (code/envelope.py:28-37)
and ask "what does the verifier promise; what does it actually deliver."

| Assumption (docstring/code) | What attacker action is caught | Where enforced | Verdict |
|---|---|---|---|
| Blob has ≥ 12+16 bytes | Truncated / undersized blob | line 33 → `ValueError` | OK as a *check*; **doc divergence** below |
| Blob nonce = first 12 bytes | Format confusion | line 35 (slicing) | OK |
| AAD = `context.encode("utf-8")` | AAD swap / context confusion | line 36 + tag check on 37 | OK |
| Tag verifies → returns plaintext, else raises | Bit-flips, swapped ct/tag, wrong key | line 37 (cryptography library) | OK |

### E3 — docstring/exception-contract divergence (note, not finding)

`code/envelope.py:31` reads:

> Raises cryptography.exceptions.InvalidTag on failure.

But the implementation raises `ValueError` on lines 33-34 when `len(blob) <
28`, **before** any tag verification. Reproduction in
`artifacts/probes/edge_cases_envelope.py` (E3 + E3-bis) confirms:

```
E3 CONFIRMED: blob < 28 bytes raises ValueError (not InvalidTag);
              docstring at code/envelope.py:31 is incomplete
E3-bis CONFIRMED: docstring mentions InvalidTag only; ValueError path
                  undocumented
```

Why it isn't a finding: the wrapper's own behavior is internally consistent
(distinct exception types for distinct error conditions). The defect is in
the *contract* it advertises — the docstring claims a strictly narrower
exception set than the implementation can throw.

Why it's worth recording: a downstream caller reading the docstring and
writing

```python
try:
    plaintext = envelope.open_(key, blob, ctx)
except InvalidTag:
    reject_message()
```

leaks `ValueError` to a higher level whenever an attacker submits a blob
shorter than 28 bytes. In a context where attacker controls the blob (e.g.,
network deserialization), this is a low-effort DoS / unhandled-exception
trigger. Severity is caller-dependent, not a fault of the wrapper alone —
hence note, not finding. (Tier-2 *if* such a caller exists; absent a
demonstrated caller, no exploitable claim.)

Suggested fix: amend the docstring to "Raises ValueError if the blob is
shorter than 28 bytes; raises cryptography.exceptions.InvalidTag if the
tag does not verify under the supplied key/context." Or, more
defensively, normalize the early length-failure to `InvalidTag` so the
single-exception contract holds.

### E1, E2 — edge cases verified

- E1: `seal(K, b"", ctx)` → 28-byte blob; `open_` round-trips empty
  bytes. AESGCM accepts empty plaintext; the length check on line 33
  permits exactly 28 bytes. `code/envelope.py:33-37`.
- E2: `seal(K, m, "")` → empty AAD; round-trips under context = `""`
  and rejects under any other context with `InvalidTag`. cryptography
  treats `b""` as valid AAD; the tag still binds to the empty AAD so
  context binding survives even at this corner. `code/envelope.py:23,36`.

These corroborate the cycle-2 property test, which used non-empty inputs.

## Suggested fix for F1

Replace the broad `except Exception: pass` with a specific
`except InvalidTag: pass` (or `except (InvalidTag, ValueError): pass`).
That way, an unexpected `AssertionError` will propagate and fail the
self-test as intended:

```python
from cryptography.exceptions import InvalidTag

try:
    open_(key, blob, "wrong-context")
    assert False, "wrong context accepted"
except InvalidTag:
    pass
```

Or use `pytest.raises(InvalidTag)` and convert to a real test.
