# Audit.PolyCommit — applied-21 cumulative model

## Layout

| File | Purpose |
|---|---|
| `Primitives.lean` | Foundational types: `Fp = ZMod (2^127 − 1)`, `Polynomial`, `SRS`, `StatementId`, `TranscriptEntry`, `Proof`. |
| `Ops.lean` | Canonical `Op` family decomposed by sub-protocol (`SetupOp`, `TranscriptOp`, `OpenOp`, `VerifyOp`). Plus `firstDiff` localizer. |
| `Security.lean` | Top-level theorem skeletons, hardness-assumption axioms (`tStrongDH`, `sha256CollisionResistant`), proof-obligation enumeration. |
| `Trace.lean` | Spec-side and impl-side `List Op` traces for `Open` and `Verify`. Equality theorems (currently `sorry`-stubbed; intended to fail under `native_decide` to surface findings F2-F4). |
| `State.lean` | State-invariant layer (Worked Example 4). `SystemState` + `specStep`/`implStep` over `SetupOp`. Captures D1 (the value-flow / publishability defect of the SRS) — the property the trace layer cannot express. |
| `Refinement.lean` | Refinement layer (Worked Example 3). Captures D5/D6/D7 — the *exploitability* of F1: the impl's verify equation in `Fp` is algebraically invertible (`forge` produces a closed-form `pi` for arbitrary `(C, y, z)`), while the spec's pairing-based verify is sound under t-SDH. |
| `Binding.lean` | Polynomial-commitment binding layer. Captures D16 / F6: `commit` silently truncates coefficients at index ≥ `len(srs.powers)`, producing collisions (binding break) parametric over the SRS's hidden values (so independent of F1). |
| `Robustness.lean` | Partiality / panic-DoS layer. Captures D15 / F5: the impl's `verify` has no input-range validation; `int.to_bytes(16, "big")` raises on negatives or values ≥ 2^128. Modeled as `implVerifyOpt : RawProof → Option Bool` with five `native_decide`-discharged panic witnesses; spec is total on `Fp`-typed `Proof`. |

## Cycle 1 status

Seeding cycle: structure laid down, `sorry`-stubbed equality
theorems intended-to-fail.

## Cycle 2 status

Discharged the cycle-1 `sorry`-stubs. Substantive changes:

- **Fixed a structural defect in cycle 1**: `Polynomial`, `SRS`,
  `Proof`, and `TranscriptEntry` only `deriving Repr` — but they
  appear inside `OpenOp` / `VerifyOp` / `TranscriptOp` constructors
  that themselves derive `DecidableEq`. Without `DecidableEq` on
  the primitive structures, the Op enums' derivation would have
  failed and the entire tree would not type-check. Cycle 2 added
  `DecidableEq` to all four primitive structures.
- **Replaced the four `sorry`-stubs in `Trace.lean`** with positive
  inequality theorems proven by `native_decide`:
  - `prove_open_ne_impl` — substantiates F2 (Frozen Heart on `y`,
    `statement_id`).
  - `verify_ne_impl` — substantiates F3 (decorative α) + F4
    (statement_id rebinding).
  - Two falsifiability sanity examples (length-equality on prove,
    length-inequality on verify) confirm the obstructions are
    decidable on ground terms.
- **Added `#eval firstDiff` blocks** that print the first-divergence
  index for each obstruction. Expected output: index 9 (the
  `buildTranscript` op) on the prove side; index 4 (the spec's
  `bindStatementId` op) on the verify side.

## Cycle 3 status

Promoted finding **F1** from the `PO-1: VIOLATED` comment in
`Security.lean` to a machine-checked operational obstruction at
the `Setup` layer:

- **Added `specSetup` and `implSetup`** to `Trace.lean` (degree-3
  fixed-N expansion, faithful to `code/proof_system.py:22-29`).
  Spec loop body is two ops (`recordPower` + `encodeInGroup`),
  impl loop body is one (`recordPower` only); spec ends with
  `destroyTrapdoor`, impl does not.
- **Added `setup_ne_impl : specSetup 17 ≠ implSetup 17`** proven
  by `native_decide` — the third positive inequality in the
  trace tree, alongside `prove_open_ne_impl` and `verify_ne_impl`.
- **Added two falsifiability witnesses**: `fixedImplSetup` (which
  closes the inequality, confirming the obstruction is content-
  driven) and `implSetupHidingButNotDestroying` (still ≠ spec —
  shows the two structural omissions are independent: encoding
  loss alone OR trapdoor-destruction loss alone falsifies the
  spec).
- **Quoted source independence**: `/-! SpecSource -/` block
  paraphrasing Kate-Zaverucha-Goldberg 2010 §3.1 above the spec
  side; `/- Source: code/proof_system.py:12, 22-29 -/` block
  pasting the literal lines above the impl side.
- **Documented the layer's scope explicitly**: the operational
  obstruction substantiates the structural-omission components
  of F1 (D2/D3/D4 in `divergences.md`).  Divergence D1 (hardcoded
  `_SETUP_SECRET`) is a value-flow property not expressible at
  the operational layer; that piece is left for a state-invariant
  / refinement cycle.

## Cycle 4 status

Promoted finding **F1 — D1 component** (the value-flow defect: SRS
publishes `s` in the clear, `_SETUP_SECRET` lives forever) from a
deferred note in cycle-3 README to a machine-checked **state
invariant** at the `State.lean` layer.

Rationale: the operational obstruction `setup_ne_impl` at
`Trace.lean` substantiates the omitted-op components of F1
(D2/D3/D4 — `encodeInGroup` and `destroyTrapdoor` are absent from
the impl trace), but does NOT express *why* their absence is
fatal.  The fatal property is value-flow: if any reachable system
state during setup has the trapdoor literally present in the
published SRS, an external observer can recover `s`.  This
property is temporal (history-dependent) and value-flow, neither
of which the operational layer expresses.  Per `formalize.md`'s
"Layer coverage with both shapes" quality bar, the layer
needed both a trace and a state-invariant, and now has them.

Substantive changes:

- **New file `State.lean`** with `SystemState` (publishedSRS +
  optional trapdoor), `specStep`/`implStep` per Kate et al. §3.1
  vs `code/proof_system.py:22-29`, and `trapdoorEverPublished` as
  a Bool-valued history predicate (true iff at any reachable state
  during execution, the published SRS literally contains the
  trapdoor).
- **Three machine-checked theorems**:
  - `spec_preserves_invariant` — under spec semantics, the spec op
    stream never publishes the trapdoor (`encodeInGroup` publishes
    a hiding placeholder, `destroyTrapdoor` zeroes the secret).
  - `impl_violates_invariant` — under impl semantics, the impl op
    stream publishes the trapdoor at iteration i=1
    (`srs.powers[1] = s`).  This is finding F1's D1 component
    made machine-checkable.
  - `impl_with_destroy_still_violates` — even an impl that
    additionally calls `destroyTrapdoor` at the end still violates
    the invariant.  This is the **falsifiability proof that D1 ≠
    D4**: fixing only the destroy-trapdoor defect does not fix the
    publishability defect, so they are independent failures (only
    `encodeInGroup` from D2/D3 fixes D1).
- **Falsifiability witness `impl_fixed_under_impl_semantics_still_violates`**
  in the second direction: applying `specOps` (the "fully fixed"
  op stream) under `implStep` still violates the invariant, because
  `implStep` treats `encodeInGroup` as a no-op while still
  publishing on `recordPower`.  Confirms the obstruction tracks
  semantics, not syntax.
- **Quoted-source independence**: a comment table cross-references
  Kate et al. 2010 §3.1 (spec) against `code/proof_system.py:22-29`
  (impl) for each of the four `SetupOp` cases.

## Cycle 5 status

Promoted finding **F1 — D5/D6/D7 components** (the *exploitability*
of the trapdoor leak: the impl's verify equation in `Fp` is
algebraically invertible, admitting closed-form forgery for
arbitrary `(C, y, z)`) from a documented-but-unmodeled defect to a
machine-checked **refinement obstruction** at the new `Refinement.lean`
layer.

Rationale: the trace and state layers substantiate F1's structural
omissions (D2/D3/D4: `encodeInGroup` and `destroyTrapdoor` absent;
D1: trapdoor literally appears in `publishedSRS`).  Neither layer
shows *why* the structural omissions are fatal in the cryptographic
sense — i.e., that what remains of the verify equation is solvable
by an attacker.  The refinement layer addresses exactly that gap:
the impl's verify equation reduces to a single linear equation in
`pi`, which the attacker solves in closed form using the published
trapdoor.  Per `formalize.md`'s "Layer coverage with both shapes"
quality bar, F1 now has substantiation at three orthogonal layers
(call-sequence / value-flow / algebraic-exploitability), each
catching a property the others cannot express.

Substantive changes:

- **New file `Refinement.lean`** modeling:
  - `implVerifyAccept (s C y z pi : Fp) : Prop` — the impl's verify
    equation `C - y = pi * (s - z)` lifted to a Prop, faithful to
    `code/proof_system.py:141-143`.
  - `forge (s C y z : Fp) : Fp := (C - y) * (s - z)⁻¹` — the
    closed-form forgery.
  - `Fact (Nat.Prime P)` instance backed by an explicit `axiom
    P_is_prime` (M127 is the Mersenne prime; trial-division
    decidability of `Nat.Prime` does not terminate at this size, so
    we add the primality fact as an enumerated axiom).
- **Three machine-checked theorems**:
  - `forge_succeeds : ∀ (s C y z : Fp), s ≠ z →
      implVerifyAccept s C y z (forge s C y z)`
    — the central F1-exploitability theorem.  Proven by `mul_assoc`
    + `inv_mul_cancel₀` + `mul_one`.  Witnesses the `forge`
    construction is a constructive exploit.
  - `impl_is_not_a_refinement_of_spec` — modulo a stated
    `specVerifyAccept_sound` axiom (the headline KZG soundness
    reduction to t-SDH) and a stated `no_honest_witness_for_zero_C`
    axiom (a future-cycle-concretizable existence claim), the impl
    admits forgeries the spec rejects, so no `R : Fp → G_1 → Prop`
    refinement relation can connect the two layers.
  - **Three falsifiability witnesses** (all `native_decide`):
    1. `implVerifyAccept 6 100 42 5 58` — concrete `(s, C, y, z,
       pi)` where the impl-verifier accepts a forgery.
    2. `forge 6 100 42 5 = 58` — the `forge` function actually
       computes the witness.
    3. `¬ implVerifyAccept 11 50 41 2 (forgeNoInverse 11 50 41 2)`
       — a forgery that drops the inverse FAILS.  The inverse is
       what makes the attack work.
    4. `forge 11 100 42 5 ≠ forge 6 100 42 5` — different `s`
       requires different `pi` for the same target, confirming the
       attack is `s`-dependent (and hence requires the trapdoor
       leak).
- **Quoted-source independence**: `code/proof_system.py:141-143`
  pasted verbatim above the `implVerifyAccept` definition, with
  the algebraic reduction (`srs.powers[0] = 1, srs.powers[1] = s`)
  spelled out.
- **Cross-reference table** at the bottom of `Refinement.lean`
  enumerating the three F1 substantiations across the three layers.

## Future cycles

1. Refine `Adversary` / `Advantage` / `polyTime` from opaque types to
   a real probability monad (Mathlib `MeasureTheory.ProbabilityMassFunction`).
2. Concretize `Refinement.specVerifyAccept` from `opaque` to a real
   pairing equation; remove the `specVerifyAccept_sound` axiom by
   formalizing the KZG t-SDH reduction (Kate-Zaverucha-Goldberg
   2010 §5, Theorem 1).
3. Concretize `Refinement.hasHonestWitness` to
     `∃ (f : Polynomial), f.evaluate z = y ∧ G_1.commit srs f = C`,
   then prove `no_honest_witness_for_zero_C` directly (constant-term
   argument).
4. Wire `tStrongDH` axiom from the placeholder
   `advantageLE (negligible 128) (negligible 128)` form into a real
   game definition, then state KZG soundness as a reduction to it.
5. Update `Security.lean`'s PO-1 status comment to cross-reference
   `Trace.setup_ne_impl`, `State.impl_violates_invariant`, AND
   `Refinement.forge_succeeds` as the triple of machine-checked
   obstructions for F1 (call-sequence + value-flow + algebraic-
   exploitability components).  *(Done in cycle 5 — see the updated
   `Security.lean` PO-1 block.)*

## Stable contract

Per the formalize-mode refactor policy, future cycles MUST extend
this namespace rather than rename / restructure. Specifically:

- `Audit.PolyCommit` is the namespace root.
- `Op` is the canonical operation type. Layers may be added; existing
  layers must not be renamed.
- Constructor names (`drawSecret`, `evalAtPoint`, `buildTranscript`,
  `useChallengeInCheck`, `bindStatementId`, …) are the audit
  vocabulary. New constructors may be added; existing ones must not
  be renamed without a stated reason in `notes.md`.
- The `Trace.lean` spec-vs-impl pattern is the substantiation method
  for findings F2-F4.

## Findings backed by this model

- **F2 (frozen-heart on `y`)** — spec-side `specOpen` includes
  `claimedValue y` and `statementTag sid` in `buildTranscript`;
  impl-side `implOpen` does not. `prove_open_eq_impl` will fail at
  the `buildTranscript` Op when `native_decide`d.
- **F3 (decorative challenge α)** — spec-side `specVerify` includes
  `useChallengeInCheck`; impl-side `implVerify` omits it.
- **F4 (statement_id rebinding)** — spec-side `specVerify` includes
  `bindStatementId`; impl-side `implVerify` omits it.

- **F1 (trapdoor exposed)** — cycle-3 added `setup_ne_impl` to
  `Trace.lean`. Spec-side `specSetup` includes `encodeInGroup`
  (one per loop iteration) and a final `destroyTrapdoor`;
  impl-side `implSetup` has neither. The inequality is decided by
  `native_decide`. The `#eval firstDiff` block localizes the
  first divergence at index 2 (spec's `encodeInGroup 0`).
  Captures D2/D3/D4. **Cycle 4** added the complementary
  state-invariant `State.impl_violates_invariant` capturing the D1
  value-flow component (the trapdoor literally appears in the
  published SRS at iteration i=1).  **Cycle 5** added the
  refinement-layer `Refinement.forge_succeeds` capturing the
  D5/D6/D7 exploitability component (the impl's verify equation in
  `Fp` admits closed-form forgery for arbitrary `(C, y, z)`).
  With the cycle-5 addition, finding F1 is now substantiated by
  *three* machine-checked obstructions at three orthogonal layers:
  - call-sequence obstruction (`Trace.setup_ne_impl`),
  - value-flow state invariant (`State.impl_violates_invariant`),
  - algebraic-exploitability theorem (`Refinement.forge_succeeds`).
  The D1-vs-D4-independence proof
  (`State.impl_with_destroy_still_violates`) additionally
  certifies that the structural omissions in F1 are individually
  fatal: fixing `destroyTrapdoor` alone does not close the
  soundness gap.  And `Refinement.forge_succeeds` certifies that
  the structural omissions yield a *concretely* exploitable
  attack — the verifier accepts forgeries whose witness the
  attacker computes in one field-multiplication and one inversion.
