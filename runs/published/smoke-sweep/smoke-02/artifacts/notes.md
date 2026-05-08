# Notes — smoke-02 (auth.py)

## Scope

Target is `code/auth.py`, 25 lines, two functions:

- `compute_tag(key, message) -> bytes` — HMAC-SHA256(key, message).
- `verify(key, message, tag) -> bool` — recompute and compare.

No other surface area; no callers in scope.

## Cycle 1 (this cycle): F1 confirmed and substantiated.

Bug class: non-constant-time MAC comparison. Repro at
`artifacts/repro/timing_attack.py` runs in well under 1 second
and demonstrates:

1. (deterministic, in-process) verify()'s loop iteration count
   equals `leading_correct + 1`.
2. (observable timing) median verify() latency separates by
   ~333 ns between 0-match and 31-match tags over 20k trials.
3. (differential) `hmac.compare_digest` is the drop-in safe
   replacement; functional correctness is unchanged.

## Other hypotheses considered (refuted / non-issues)

- **H2 (length-leak via `len(expected) != len(tag)`):** the tag
  length is fixed at 32 bytes for any HMAC-SHA256 deployment; an
  attacker submitting a tag of wrong length only learns
  "wrong length", which is public information. Not exploitable.

- **H3 (key length not validated):** `hmac.new` accepts any byte
  length for the key. HMAC's design tolerates short keys (they
  get zero-padded) and long keys (they get hashed first). Not
  a bug in this library.

- **H4 (HMAC computation runs before length check on tag):**
  `compute_tag` is invoked at L10 prior to the length check at
  L11. This means a verify call on a malformed-length tag still
  pays the full HMAC cost. This is at most a minor DoS amplifier
  but `message` is attacker-controlled regardless, so the
  attacker can already cause arbitrary HMAC work via the message
  argument alone. Not a finding.

- **H5 (compute_tag has a side-channel of its own):** delegates to
  `hmac.new(...).digest()` from the standard library, which has
  been audited and is built on `_hashopenssl` (constant-time
  HMAC at the C level). Not in scope to re-audit.

## What's not in scope here that would matter in a real deployment

- How `verify` is called from a network handler. If the handler
  early-rejects on `verify == False` and times out / responds at
  the moment of rejection, the timing channel is directly
  observable network-side. If the handler uses a constant-budget
  response timing wrapper, the channel is mitigated externally
  but the underlying bug is still present.
- Whether the key is a long-lived secret. If the key rotates
  faster than the attacker can mount the ~8192 trials needed to
  recover the tag, the attack window may be too short. The bug
  remains a defect regardless.

## Recommended fix

Replace lines 11-15 of `code/auth.py` with:

```python
return hmac.compare_digest(expected, tag)
```

This handles both length difference and value comparison in
constant time relative to the expected tag.

## Cycle 2: repro re-run + second adversarial pass

- Re-ran `artifacts/repro/timing_attack.py`: exits 0 in <1s. Part 1
  prints `loop_iters=1,2,6,17,32` for `leading_correct=0,1,5,16,31`
  and 32 for full-match (deterministic data dependence). Part 2
  reports median latency 875 ns vs 1166 ns (+291 ns delta) over
  20k trials. F1 confirmed reproducible in this environment.

- Second adversarial pass for orthogonal bug classes at
  `code/auth.py:9-16` (perturbation around F1, since "the same
  author/style that produced one bug often harbors siblings"):

  - **H6 (type confusion of `tag`):** probed `verify` with tag
    types `bytes`, `bytearray`, `memoryview`, `str`, `list[int]`,
    `tuple[int]`, `None`, `int`. `list[int]` and `tuple[int]`
    of correct values are accepted (because `zip(bytes, list)`
    yields `(int, int)` pairs and `int == int` succeeds). This
    is an API quirk, NOT a soundness break: constructing the
    accepted container still requires knowing the secret-derived
    `expected` bytes (i.e. the key). No exploit. Not a finding.
  - **H7 (TypeError-channel via non-len-able tag):** `tag=None`
    or `tag=int` raises TypeError out of `len(tag)` rather than
    returning False. This is a different observable response
    than a normal failed verify, but the discriminator is just
    "wrong type of object" — public information. Not a finding.
  - **H8 (HMAC computed before length check on tag):** restated
    H4. Confirmed: even with `tag=b""` the HMAC is recomputed at
    L10 before the L11 length check. The attacker already
    controls `message` (which determines HMAC cost), so this
    cannot amplify a DoS beyond what plain message control gives.
    Not a finding.
  - **H9 (algorithm agility / downgrade):** `hashlib.sha256` is
    hardcoded at L6. No negotiable hash. No agility-attack
    surface. Not a finding.
  - **H10 (key-length validation):** `hmac.new` accepts any byte
    length per RFC 2104. NIST SP 800-107 recommends key length
    ≥ output length, which is a *caller* contract for HMAC
    helpers. The library does not enforce it. Borderline
    style/hardening note, not a defect against a typical helper
    contract. Not a finding.
  - **H11 (TOCTOU / shared state):** `verify` is a pure function
    over its arguments; `expected` is local; no module-level
    mutable state. Not a finding.

  Outcome: no new findings. F1 remains the sole substantive bug
  in this 25-line target.
