# Notes — applied-04 (`circuit-prover`), cycle 1

## Cycle 1 activity

`seed`. The Lean tree was empty; this cycle produced the
foundation layer of the cumulative model:

- `state/lean/Audit/Circuit/Foundation.lean` — canonical
  `inductive Gate` (5 constructors, flat — well below the ~50
  threshold), primitive types `Wire`/`Value`/`Witness`/`Circuit`,
  field arithmetic `fadd`/`fmul`/`fone_sub` mirroring the Python
  `% P` reductions, and the `firstDiff` helper.
- `state/lean/Audit/Circuit/Spec.lean` — per-gate semantics
  encoded from the **docstrings** (`code/circuit.py:11-15` and
  `:38-56`). Every clause carries an explicit `SpecSource` block.
- `state/lean/Audit/Circuit/Impl.lean` — per-gate semantics
  encoded from the **body of `evaluate`** (`code/circuit.py:69-94`).
  Every clause carries a `Source` block quoting the literal
  Python lines.
- `state/lean/Audit/Circuit/Equiv.lean` — `spec_eq_impl` (left as
  `sorry`, with the `assertEq` counterexample showing it is
  false) plus end-to-end soundness break for the canonical hash-
  preimage circuit (`hashPreimage_soundness_break`, discharged
  by `native_decide`). Falsifiability sanity checks confirm
  the divergence is localized to `assertEq` and not an artifact
  of asymmetric encoding.

## Independence audit

Spec and impl encodings are independent at the definition level:

- The `assertEq` clause in `Spec.checkGate` returns `decide (get
  w l = get w r)`; in `Impl.checkGate` it returns `decide (get
  w l = get w l)`. A reader who flips either side toggles the
  equality theorem — the theorem is testing faithfulness, not
  reflexivity.
- Each side's quoted source block is from a **different** part
  of `code/circuit.py` (docstrings vs. function body), so the
  two sides cannot drift together via copy-paste.

## Findings produced

- **F1** — `ASSERT_EQ` is unconstrained (`code/circuit.py:84-87`).
  Spec/impl divergence on the `assertEq` clause; substantiated by
  both a 0.02s Python repro on the canonical circuit and the
  `Equiv.lean` Lean file (per-gate divergence + protocol-level
  soundness break).

## Open hypotheses (queue for later cycles)

These were itemized in `threat-model.md` as H2–H5; H1 became F1.

- **H2 (closed for now)** — `ADD`/`MUL`/`CONST`'s field
  semantics agree with Python's `%` for negative or large
  witness values. `evaluate` reduces the witness via
  `[v % P for v in witness]` on entry (`code/circuit.py:67`),
  which yields canonical residues in Python. The Lean spec/impl
  agree for these constructors (the falsifiability sanity
  checks discharge on concrete witnesses). No bug.
- **H3** — out-of-range gate indices raise `IndexError`. Listed
  as LOW in `divergences.md`; reachable only by R2 (malicious
  circuit author), not by R1/R3 through `witness`. Possible
  follow-up: panic-DoS for any consumer that does not
  `try/except` around `evaluate`. Not promoted to a finding
  because R2's threat model is weak — a malicious circuit author
  has many easier ways to subvert acceptance (e.g. omit
  constraints).
- **H4** — `ASSERT_BOOL`'s `x*(1-x) ≡ 0 mod P` correctly forces
  `x ∈ {0, 1}` over the field because P is prime (no nonzero
  zero-divisors). Not a bug.
- **H5** — `CONST` accepts negative `gate.constant` consistently:
  Python's `(neg) % P` returns the canonical positive residue.
  No divergence.

## Cycle 5 activity

`adversary-game` (Example 2 from AGENTS.md / CLAUDE.md). Added
`state/lean/Audit/Circuit/Soundness.lean`:

- `ProverStrategy` adversary structure (`forge : Circuit → Witness`).
- `SoundnessGame V B c adv : Bool` — verifier `V` accepts but
  binding `B` rejects on the forged witness.
- `spec_sound_against_itself` and `impl_sound_against_itself` —
  trivially-sound sanity lemmas (b && !b = false).
- `impl_sound_relative_to_spec` — the *intended* security goal,
  stated as a `sorry`. This is the gap F1 leaves open; no proof
  can discharge it because of the witnessing adversary below.
- `f1Adversary` — concrete winning adversary (returns
  `Equiv.forgedWitness` regardless of input).
- `impl_unsound` — `f1Adversary` wins the game against the impl
  on the canonical circuit. `native_decide`-discharged.
- `impl_unsound_proposition` — the impossibility of
  `SoundnessLoses` for `f1Adversary` (∴ `impl_sound_relative_to_spec`'s
  `sorry` is *unprovable*, not just *unproven*).
- Bridging theorems back to `Equiv.hashPreimage_soundness_break`
  and `HonestProver.impl_soundness_gap_nonempty`.
- Falsifiability checks: a `honestAdversary` and a `rejectedAdversary`
  both lose the game, confirming the game definition discriminates.

Why `adversary-game` over `state-invariant` / `refinement` / etc.:

- The construction has no per-gate carried state in `evaluate` —
  each gate is independent — so a `step : State → Op → State`
  model would be contrived.
- The bug is fundamentally a soundness bug; the canonical
  cryptographic shape for stating soundness IS the adversary
  game. The model previously phrased F1 as "∃ w, spec ≠ impl",
  which is correct but misses the security-goal framing.
- `ProverStrategy` is reusable substrate for future
  game-hop reductions.

## Carried to next cycle

- `mathlib-upgrade`: replace `Value := Nat` placeholder with
  `ZMod P`. Updates `fadd`/`fmul`/`fone_sub` to ring operations.
- `decomposition` of the soundness goal: even though
  `impl_sound_relative_to_spec` is false, a *fixed* impl could
  satisfy it — and that proof should compose per-gate lemmas
  parallel to `Decomposition.lean`'s `checkGate_eq_of_not_assertEq`.
- `paper-pull`: there's no in-tree spec / external paper for this
  toy circuit, so this activity is N/A here. The "spec" is the
  in-tree docstrings, which are already encoded in `Spec.lean`.

## Spec/impl independence — caveat

Both spec and impl currently encode acceptance as
`decide (w.length = c.nWires) && c.gates.all (fun g => checkGate g w)`.
This is structurally identical, only `checkGate` differs. That's
the right shape — `evaluate`'s outer-loop semantics are not in
question; the divergence is per-gate. If a future cycle finds an
outer-loop bug (e.g. early-exit ordering), this would need to be
de-mirrored.
