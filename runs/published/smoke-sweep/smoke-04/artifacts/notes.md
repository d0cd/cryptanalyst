# Audit notes — smoke-04 / chain-validator

## Method

Read `code/validator.py` (single 96-LOC file) end-to-end, then
performed adversarial-reading review of the loop bounds in
`validate_chain`. Two structurally clear bugs surfaced from the
loop-index inspection alone; both substantiated with runnable
exploits in `artifacts/repro/`.

## Loop-bound walk-through (chain of length 2: `[leaf, inter]`)

`full_chain = [leaf, inter, root]`, `n = 3`.

| code/validator.py loc | what it iterates | which checks fire |
|---|---|---|
| `:82-86`  validity + CA check | i ∈ {0, 1} for cert ∈ {leaf, inter} | _check_validity(leaf), _check_validity(inter); _check_ca(inter) (i=0 < 1); root NEVER checked for CA (i=1 not < 1) |
| `:89-90`  signature graph     | i ∈ {1}                              | _verify_signature(inter, root); leaf signature NEVER checked |
| `:93`     root self-sig       | always                               | _verify_signature(root, root) |

For `chain=[leaf]` (n=2): both loops shrink to nothing.

| code/validator.py loc | iter set | which checks fire |
|---|---|---|
| `:82-86`  | i ∈ {0}    | _check_validity(leaf); _check_ca skipped (i=0 not < 0) |
| `:89-90`  | i ∈ ∅       | nothing |
| `:93`     | always     | _verify_signature(root, root) |

So the leaf is never signature-checked under any chain length.

## Substantiated findings (in findings.json)

1. **F1 / leaf_signature_not_verified** (CRITICAL, tier 1). Loop
   bound at code/validator.py:89 starts at i=1. Repro:
   `artifacts/repro/exploit_leaf_unsigned.py` plus the chain-len-1
   amplification at `artifacts/repro/exploit_chain_len_1.py`.

2. **F2 / root_ca_basicconstraints_not_checked** (MEDIUM, tier 3).
   Guard at code/validator.py:85 excludes the root. Repro:
   `artifacts/repro/exploit_root_not_ca.py` (covers both ca=False
   and missing-BC cases).

3. **F3 / basicconstraints_pathlength_not_enforced** (HIGH, tier 2,
   added cycle 2). `_check_ca` at code/validator.py:26-33 only
   reads `bc.value.ca`, never `bc.value.path_length`. Repro:
   `artifacts/repro/exploit_path_length.py` builds
   `Root → Inter1(path_length=0) → Inter2(ca=True) → leaf`, sanity-
   checks every signature with direct `pub.verify` calls, then
   shows `validate_chain` returning True even though RFC 5280
   §6.1.4(m) requires rejection. Independent of F1: every signature
   in this chain is cryptographically valid, so fixing the leaf-sig
   loop alone would not catch this.

4. **F4 / keyusage_keycertsign_not_enforced** (HIGH, tier 2,
   added cycle 3). Same fix site as F3 — `_check_ca` at
   code/validator.py:26-33 — but a different missing check.
   RFC 5280 §6.1.4(n) requires that if an issuer cert has a
   KeyUsage extension, the keyCertSign bit MUST be asserted.
   `_check_ca` never inspects KeyUsage. Repro:
   `artifacts/repro/exploit_keyusage.py` builds
   `Root → RestrictedIntermediate(ca=True, KeyUsage.key_cert_sign=False) → leaf`,
   sanity-checks every signature, then shows `validate_chain`
   returning True. Independent of F1, F3: every signature is
   cryptographically valid, BasicConstraints.ca is True, no
   path_length is set — only the KeyUsage policy is violated,
   and the validator silently ignores it. Models the standard
   RFC-5280 mechanism for delegating a sub-key with narrowed
   authority (OCSP-only, TLS-only, etc.); the validator
   silently grants such sub-keys cert-issuance privilege.

## Lower-severity / unsubstantiated observations

These are kept out of `findings.json` because each is either
defense-in-depth or contract-ambiguous in this scope.

- **Issuer↔Subject DN binding never checked.** `_verify_signature`
  validates the cryptographic signature only; it does not check
  `subject_cert.issuer == issuer_cert.subject`. Strict X.509
  validators require this match (RFC 5280 §6.1.3 (a)(4)). In
  isolation this is harmless because the signature implicitly
  binds key→subject; combined with F1 (leaf sig unchecked), an
  attacker can present a leaf with an arbitrary `issuer` field
  and the validator accepts. The leaf-signature fix likely
  subsumes this; flagging for completeness.

- **Hash algorithm not pinned.** `_verify_signature` uses
  `subject_cert.signature_hash_algorithm`, an attacker-controlled
  value. The `cryptography` library does reject MD5/SHA1 for some
  modes, but the validator does not enforce its own minimum.

- **path_length basicConstraints ignored.** PROMOTED to F3 in
  cycle 2 with repro `exploit_path_length.py`. The bug is at
  code/validator.py:26-33; rejection is required by RFC 5280
  §6.1.4(l)-(m).

- **No KeyUsage / ExtendedKeyUsage check.** PARTIALLY PROMOTED to
  F4 in cycle 3. The KeyUsage→keyCertSign side (RFC 5280 §6.1.4(n))
  is now substantiated as F4. The ExtendedKeyUsage side is still
  open: a strict validator should also enforce that the leaf's
  EKU lists every purpose the relying-party expects (e.g. id-kp-
  serverAuth for TLS), but this validator never inspects EKU.
  Defense-in-depth in this scope because validate_chain has no
  hostname/purpose parameter; a caller doing TLS hostname check
  would still need its own EKU enforcement layer.

- **Empty chain accepted.** `validate_chain([], root)` runs the
  root validity + root self-signature checks and returns True.
  Probably not the intended contract, but no clear attack
  beyond "the function answers True with no leaf to validate".

- **Non-RSA non-EC keys raise TypeError, not ValueError.** The
  `else` branch in `_verify_signature` blindly assumes RSA-PKCS1v15.
  If `pub` is Ed25519/Ed448/DSA, the call signature mismatches
  and a TypeError leaks out of `validate_chain`. Robustness, not
  security.

- **`_check_validity` accepts `now` of any timezone-awareness.**
  Comparing a naive `now` with the tz-aware
  `not_valid_before_utc` raises TypeError. Caller hygiene only.

## Things deliberately NOT investigated

- This is a 96-LOC self-contained file with no upstream callers
  in scope and no published spec beyond RFC 5280. No spec-trace
  artifact was warranted.
- No Lean / Sage formalization: the bugs are visible at the
  loop-bound level without algebraic modeling.
