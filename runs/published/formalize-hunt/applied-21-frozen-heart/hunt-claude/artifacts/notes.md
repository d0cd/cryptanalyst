# Notes — applied-21 (cycle 1 of run `20260508-050503`)

## Inheritance from prior run

This run inherits durable state from `runs/20260508-041820-applied-21-claude-local`:
- `state/lean/Audit/PolyCommit/` — 6 Lean files, 5 cycles of work,
  4 findings (F1-F4) substantiated by trace, state-invariant, and
  refinement layers.
- 4 findings in prior `findings.json`: F1 (trapdoor), F2 (FS missing
  y), F3 (decorative α), F4 (statement_id rebinding).

`code/proof_system.py` is unchanged from prior run (verified by
re-running prior repros — both pass).

## Cycle activity

**Activity selected**: panic-path audit (a previously unrepresented
approach in this target's queue) — produced one new finding F5.

The prior queue was concentrated in two bug classes: cryptographic
soundness (F1) and Fiat-Shamir hygiene (F2/F3/F4 — all touch the
challenge / transcript). A panic-path audit perturbs along an
orthogonal axis: input validation / hygiene of the verifier's
deserialization path.

**Method**:
1. Read `verify()` (`code/proof_system.py:117-143`) asking "what
   shapes of attacker-controlled input does the verifier
   serialize / consume before the algebraic check?"
2. Identified five attacker-controlled fields with no bounds check:
   `commitment`, `pi`, `z`, `y`, `alpha`.
3. Identified the brittle primitive: `int.to_bytes(16, "big")` at
   lines 130-132 raises on negatives, on integers ≥ 2^128, and on
   non-int types.
4. Wrote `artifacts/repro/dos_F5_verify_panic.py` exercising the
   five panics. All five raise rather than returning False.

**Classification**: tier 4 (internal API only) in the as-shipped
library. The library has no protocol surface; the bug elevates to
tier 1 in any deployment that exposes `verify()` to attacker bytes
through an unauthenticated wrapper.

## Hypotheses considered, refuted, or noted

### Refuted

- **HX1: silent commitment-truncation as a separable binding break**
  (`commit()` skips `i ≥ len(srs.powers)`). Investigated, refuted as
  a separate finding because it is wholly subsumed by F1 — once the
  trapdoor leaks, you can forge ANY (C, z, y), so binding break by
  high-coefficient truncation is invisible against a backdrop where
  even the no-truncation case admits closed-form forgery. Worth
  noting for completeness; not a finding.

- **HX2: `z = s mod P` as a degenerate-verifier forgery vector**.
  Refuted as separable — when `z = s`, `pi * (s - z) = 0`, so verify
  accepts iff `C = y`. This is a strict subcase of F1's general
  forgery and contributes no exploit shape F1 doesn't already
  demonstrate. Subsumed.

- **HX3: non-canonical encoding of integers in transcript**
  (`(z + P).to_bytes(16, "big")` differs from `z.to_bytes(16, "big")`
  yet reduces to the same field element). Refuted: alpha is
  decorative (F3), so non-canonical encoding does not enable a
  malleability exploit beyond what F1 already does. Subsumed.

### Noted (not promoted)

- **HX4: cross-protocol replay via missing FS domain separation**
  (D12 in `divergences.md`). The FS hash has no protocol tag. In
  isolation this is LOW because applied-21 is a single protocol;
  in any deployment that uses the same SHA-256 namespace for
  multiple FS contexts, replay between contexts becomes possible.
  Not promoted because the bug is purely compositional and the
  target is standalone.

- **HX5: SRS_MAX_DEGREE silently truncates polynomials with
  more than 33 coefficients in `commit()`**. Documented at D14;
  not a separate finding (the construction is broken regardless).

## Next-cycle candidates

If the user wants additional cycles, productive options:

1. ~~**Trace-faithfulness audit on `Trace.lean`**~~ — completed in
   cycle 3 (this run); see "Cycle 3 — trace-faithfulness audit"
   below.

2. **Concretize `Refinement.specVerifyAccept`** from `opaque` to a
   real pairing equation (item 2 in the README's "Future cycles"
   list). Removes the `specVerifyAccept_sound` axiom by reducing
   KZG soundness to t-SDH per Kate-Zaverucha-Goldberg 2010 §5.

3. **Lean-encode F5** in `State.lean` or a new `Robustness.lean`:
   model `verify()` as a partial function and prove the spec-side
   `verifyTotalOnAttacker` while exhibiting `implVerifyPanicsOn -1`.
   Closes the same-cycle confirm-encode loop for F5.

## Cycle 3 — trace-faithfulness audit

**Activity selected**: trace-faithfulness audit on
`state/lean/Audit/PolyCommit/Trace.lean`. Per CLAUDE.md "trust the
cumulative model carefully": a passing `native_decide` proves
spec ≠ impl AT THE MODELED GRANULARITY, not that the modeled impl
matches the real `code/proof_system.py`. F2, F3, F4 substantiation
all rests on `prove_open_ne_impl` and `verify_ne_impl`; F1's
operational layer rests on `setup_ne_impl`. If the impl-side trace
is unfaithful (skipped ops, wrong order), those theorems prove
something narrower than the audit claims.

**Method**: open `Trace.lean` op-by-op; for each impl-side op,
locate the actual `code/proof_system.py` line range it claims to
model; quote the code; verify the claim. Surface any divergence
as either (a) a hidden code-side bug, (b) a model-side bug to
fix, or (c) a confirmed-faithful op.

### Pre-run validation

Re-ran all three repros under cycle 3:
- `forge_F1_trapdoor.py` → F1 substantiated (verify True on forged proof)
- `forge_F4_statement_rebinding.py` → F4 substantiated (replay under arbitrary statement_id)
- `dos_F5_verify_panic.py` → F5 substantiated (5 distinct panic shapes)

Code is unchanged from prior runs; the trace audit therefore
addresses the model-vs-real-code question, not whether the impl
itself moved.

### Audit table — `implOpen` vs `prove` (`code/proof_system.py:74-114`)

`Trace.lean:161-179` defines `implOpen` as 11 ops (assuming a
fixed-N division stream); each is paired below with the actual
code lines.

| # | Trace op | Trace line | Code lines | Code text (paraphrased) | Verdict |
|---|---|---|---|---|---|
| 1 | `inputPolynomial f` | 163 | 74 (param) | `def prove(srs, poly, z, statement_id=b"")` | FAITHFUL — modeled binding op for the function param. |
| 2 | `inputPoint z` | 164 | 74 (param) | (same line, `z: int`) | FAITHFUL — binding op for `z`. |
| 3 | `inputStatementId sid` | 165 | 74 (param) | (same line, `statement_id: bytes = b""`) | FAITHFUL — binding op for `statement_id`. |
| 4 | `evalAtPoint y` | 166 | 79 | `y = poly.evaluate(z)` | FAITHFUL. |
| 5 | `computeCommitment C` | 167 | 80 | `C = commit(srs, poly)` | FAITHFUL. |
| 6 | `subtractEvaluation y` | 168 | 85 | `adjusted[0] = (adjusted[0] - y) % P` | FAITHFUL — but folds in the local-setup statements at lines 83-84 (`n = len(poly.coeffs); adjusted = list(poly.coeffs)`). Modeling choice; the elided lines are pure book-keeping with no security-relevant behavior. |
| 7 | `divisionStep i acc` (loop body, len = `divisionAccs.length`) | 169 | 89-93 | `for i in range(n-1, -1, -1): val = (adjusted[i] + remainder) % P; if i>0: q_coeffs[i-1] = val; remainder = (val * z) % P` | FAITHFUL — one op per iteration, matching the for-loop structure. The trace uses 3-step `repDivAccs` for tractability; actual code runs `n` iterations where `n = len(poly.coeffs)`. Structural property preserved (1 op per iter). |
| 8 | `computeWitness pi` | 170 | 95 | `pi = commit(srs, Polynomial(q_coeffs))` | FAITHFUL — but folds in the silent truncation by `commit` for `len(q_coeffs) > srsMaxDegree+1` (HX5 / D14). The truncation is invisible at this granularity; would need a refinement layer to model. Subsumed by F1 anyway. |
| 9 | `buildTranscript [commitment C, witness pi, point z]` | 171-175 | 99-103 | `transcript = [C.to_bytes(16,"big"), pi.to_bytes(16,"big"), z.to_bytes(16,"big")]` | FAITHFUL — order C, pi, z, with three entries. The MISSING `statementTag` and `claimedValue` is exactly D8 (Frozen Heart on y and statement_id). |
| 10 | `deriveChallenge alpha` | 176 | 105 | `alpha = _derive_challenge(transcript)` | FAITHFUL. |
| 11 | `emitProof {C,z,y,pi,alpha,sid}` | 177-179 | 107-114 | `return {"commitment": C, "z": z, "y": y, "pi": pi, "alpha": alpha, "statement_id": statement_id}` | FAITHFUL. |

### Audit table — `implVerify` vs `verify` (`code/proof_system.py:117-143`)

`Trace.lean:204-218` defines `implVerify` as 10 ops.

| # | Trace op | Trace line | Code lines | Code text | Verdict |
|---|---|---|---|---|---|
| 1 | `readCommitment proof.commitment` | 205 | 123 | `C = proof["commitment"]` | FAITHFUL. |
| 2 | `readPoint proof.z` | 206 | 124 | `z = proof["z"]` | FAITHFUL. |
| 3 | `readClaimedValue proof.y` | 207 | 125 | `y = proof["y"]` | FAITHFUL. |
| 4 | `readWitness proof.pi` | 208 | 126 | `pi = proof["pi"]` | FAITHFUL. |
| 5 | (no `bindStatementId` here) | — | — | — | FAITHFUL OMISSION — D10 / F4: impl never reads `proof["statement_id"]`. The absence is the bug; trace correctly captures the absence. |
| 6 | `rebuildTranscript [C, pi, z]` | 209-212 | 129-133 | `transcript = [C.to_bytes(16,"big"), pi.to_bytes(16,"big"), z.to_bytes(16,"big")]` | FAITHFUL — three entries in order C, pi, z; missing `statementTag` and `claimedValue` is D8. |
| 7 | `recomputeChallenge alpha` | 213 | 135 | `alpha = _derive_challenge(transcript)` | FAITHFUL. |
| 8 | `checkChallengeMatch proof.alpha alpha` | 214 | 136-137 | `if alpha != proof["alpha"]: return False` | FAITHFUL — but trace doesn't capture the early-return semantics. The model assumes the full op stream executes; for a real run on a non-matching alpha, the impl terminates here. **Both spec and impl have the same early-return semantics**, so the asymmetry cancels for the purpose of comparing op streams. Note that this means `verify_ne_impl` proves the structural ops differ, not that the runtime behavior differs on every input. (The runtime differs anyway via D9/D10 — separately substantiated by F4's repro.) |
| 9 | (no `useChallengeInCheck` here) | — | — | — | FAITHFUL OMISSION — D9 / F3: alpha is recomputed but never multiplied into lhs/rhs. Trace correctly captures the absence. |
| 10 | `computeLhs lhs` | 216 | 141 | `lhs = (C - y * srs.powers[0]) % P` | FAITHFUL — but the constant `srs.powers[0] = 1` is implicit, so the equation reduces to `lhs = (C - y) % P`. The trace doesn't expand this; not a bug. |
| 11 | `computeRhs rhs` | 217 | 142 | `rhs = (pi * (srs.powers[1] - z * srs.powers[0])) % P` | FAITHFUL — `srs.powers[1] = s` (the trapdoor in plaintext, exactly D2/D7/F1). Trace folds the multiplications into one op. |
| 12 | `finalEquality lhs rhs` | 218 | 143 | `return lhs == rhs` | FAITHFUL. |

### Audit table — `implSetup` vs `trusted_setup` (`code/proof_system.py:22-29`)

`Trace.lean:458-467` defines `implSetup` as 5 ops (degree-3 unroll).

| # | Trace op | Trace line | Code lines | Code text | Verdict |
|---|---|---|---|---|---|
| 1 | `drawSecret 17` | 459 | 12 | `_SETUP_SECRET = 0x5A3B7C9E1F4D2A6B8C0E7F3D5A1B9C4E` | FAITHFUL with placeholder — trace uses `s = 17` for `native_decide` tractability; the *operational* structure ("a secret enters the system") is captured. The actual hardcoded constant is D1, addressed by `State.lean`'s value-flow invariant rather than the operational trace. |
| 2 | `recordPower 0 1` (iter 0) | 461 | 26-28 | iteration 0 of `for _ in range(max_degree+1): powers.append(s_pow); s_pow = (s_pow * _SETUP_SECRET) % P` | FAITHFUL — iteration 0 records `s^0 = 1`. The "compute next power" sub-step (line 28's multiplication) is implicit in the next iteration's recordPower value, not a separate op. Modeling choice. |
| 3 | `recordPower 1 17` (iter 1) | 463 | 26-28 | (iter 1 with s = 17) | FAITHFUL — records `s^1 = 17`. |
| 4 | `recordPower 2 289` (iter 2) | 465 | 26-28 | (iter 2 with s = 17, so s^2 = 289) | FAITHFUL — records `s^2 = 289`. |
| 5 | `recordPower 3 4913` (iter 3) | 467 | 26-28 | (iter 3 with s = 17, so s^3 = 4913) | FAITHFUL — records `s^3 = 4913`. |
| 6 | (no `encodeInGroup` after each `recordPower`) | — | — | — | FAITHFUL OMISSION — D2/D3/F1: SRS holds raw field elements with no group encoding. |
| 7 | (no `destroyTrapdoor` at end) | — | — | — | FAITHFUL OMISSION — D4/F1: `_SETUP_SECRET` survives as module-level constant. |

The trace unrolls 4 iterations; the actual code unrolls 33 (max_degree=32, range gives 0..32). The structural property (1 op per iteration, no encode, no destroy) holds for any iteration count.

### Modeling simplifications confirmed not to mask any bug

| Simplification | Where | Risk if wrong | Why it doesn't mask a bug |
|---|---|---|---|
| `s = 17` in setup trace | `Trace.lean:415, 437-452, 458-467`; `State.lean:99-114` | A different `s` could change which power equals which value | The structural property tested is "loop body has 1 op vs 2 ops"; this is independent of `s`. The State-layer `trapdoorEverPublished` invariant uses a concrete `s` to test publishability and is also independent (any nonzero `s` triggers `listMem t [1, s, s^2, s^3] = true`). |
| 4-iteration unroll vs 33 in code | `Trace.lean:414-415, 437-452, 458-467` | A bug in iterations 4-32 would be invisible | The loop body is uniform across iterations — same Python statements, same arithmetic. A bug in iter 4-32 would have to be a uniform structural defect, which is exactly what the unrolled trace catches at iter 0-3. |
| Folded `n = len(...)` and `adjusted = list(...)` into `subtractEvaluation` | `Trace.lean:168` | Hidden setup-side bug | Lines 83-84 are pure book-keeping with no security-relevant arithmetic; `n` is a local var, `adjusted` is a copy. F5's panic-DoS picks up the empty-list edge case (n=0 → IndexError) at the runtime layer, where it belongs. |
| Folded `commit()` truncation into `computeWitness pi` and `computeCommitment C` | `Trace.lean:167, 170` | Truncation defect (HX1/HX5/D14) invisible at op layer | The truncation is a refinement-level defect, captured by HX1's note ("subsumed by F1"). The trace's purpose is structural, not pointwise-correctness. |
| Trace doesn't model conditional early-return in verify (line 137) | `Trace.lean:204-218` | Different runtime behavior on bad alpha | Both spec and impl have the same conditional structure; the trace compares the maximum-length stream that would execute if the condition holds. Since the divergence at op 5 (`bindStatementId`) is *before* the conditional, the structural inequality holds regardless of which branch the runtime takes. |
| `srs.powers[0] = 1` and `srs.powers[1] = s` constants implicit in `computeLhs`/`computeRhs` | `Trace.lean:216-217` | A bug in SRS indexing wouldn't show | The bug captured by F1 IS that `srs.powers[1]` exposes `s`; that's modeled in the State layer (`trapdoorEverPublished`), not the Trace layer. Each layer covers a different facet. |

### Audit conclusion

**The impl-side traces in `Trace.lean` (implOpen, implVerify, implSetup) are FAITHFUL to `code/proof_system.py` at the modeled granularity.**

- Every modeled op has a clear code-line correspondence.
- Every code-line that performs a security-relevant action has a corresponding modeled op (or a documented "OMITTED" case that *is* the bug).
- Every modeling simplification (s=17, 4-iter unroll, folded book-keeping, conditional flow) preserves the structural property tested by `native_decide`.

This means the existing F1, F2, F3, F4 substantiation via Trace.lean is grounded — the `native_decide` theorems prove that the *real impl's* op stream differs from the spec's, not just that two abstractly-defined Lean lists differ. The audit therefore strengthens the substantiation bar without changing the findings.

### Hidden bugs surfaced by the audit

None. The audit confirms the prior catalog (F1-F5 + HX1-HX5) is the complete enumeration of structural and operational divergences at the layers the trace covers. Layers not covered (refinement-level value correctness, runtime panic semantics) are addressed elsewhere: F1's State-layer obstruction in `State.lean`, F5's panic-DoS in `dos_F5_verify_panic.py`.

The one open gap relative to the substantiation bar is F5's lack of a Lean encoding (per "next-cycle candidates" item 3); F5 is currently substantiated by repro alone. That's a same-cycle-confirm-encode debt to close in a future cycle, but the trace audit itself doesn't change F5's status — F5 lives at the *partiality / panic* layer, which the operational trace doesn't model by design.
