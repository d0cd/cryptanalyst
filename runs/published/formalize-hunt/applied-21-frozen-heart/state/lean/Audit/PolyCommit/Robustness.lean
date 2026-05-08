/-
  Robustness layer for the applied-21 polynomial-commitment audit.

  This file substantiates finding **F5** — the impl's `verify` function
  has no input-range validation on attacker-controlled proof fields and
  panics (`OverflowError` / `AttributeError`) when those fields are
  outside the [0, 2^128) range its serializer expects.

  Source (impl):

      code/proof_system.py:117-143
      def verify(srs: SRS, proof: dict) -> bool:
          C  = proof["commitment"]
          z  = proof["z"]
          y  = proof["y"]
          pi = proof["pi"]
          # NO RANGE CHECK on any of {C, z, y, pi}.
          transcript = [
              C.to_bytes(16, "big"),     ← raises OverflowError if  i < 0
              pi.to_bytes(16, "big"),    ← raises OverflowError if  i ≥ 2^128
              z.to_bytes(16, "big"),     ← raises AttributeError if !int
          ]
          alpha = _derive_challenge(transcript)
          if alpha != proof["alpha"]: return False
          ...

  Source (spec):

      A correct verifier either rejects malformed input (returning
      `False`) or normalizes input to the expected algebraic domain
      (`Fp = ZMod P`) before any serialization.  By making the proof
      type `Fp`-valued at the boundary, the spec is total: every
      input either (a) fails to parse and is rejected, or (b) parses
      to a `Proof` and the algebraic check decides accept/reject.
      Neither path raises.

  Layer coverage / orthogonality
  ------------------------------

  F1 (Trace/State/Refinement): cryptographic-soundness break — verify
      returns `True` on attacker-forged input.

  F5 (THIS FILE): partiality / panic-DoS — verify *raises* on
      attacker-malformed input, instead of returning `False`.  This is
      a partiality break, not a soundness break: the F5 attacker does
      not learn anything about the polynomial; they merely halt the
      verifier.  The two finding shapes are independent: F1 holds for
      attacker proofs whose *integers* are in range (just chosen
      adversarially), while F5 holds for attacker proofs whose
      integers are *out of range* (no algebraic content reached).

  Per the substantiation bar in `AGENTS.md`: F5 already had a Python
  PoC (`artifacts/repro/dos_F5_verify_panic.py`); this file adds the
  same-cycle Lean confirm-encode debt closure documented in
  `artifacts/notes.md` "Next-cycle candidates" item 3.
-/

import Audit.PolyCommit.Primitives

namespace Audit.PolyCommit.Robustness

open Audit.PolyCommit

/-! ## The impl's encoder is a partial function on `Int`

    `int.to_bytes(16, "big")` in CPython has the precondition that
    the integer is non-negative and fits in 16 bytes.  We model it
    as `Option`-valued — `none` represents the panic case where the
    serializer would raise `OverflowError`.

    This is the canonical totalization of a partial function: the
    spec sees `Some bytes` for in-range input and `None` for the
    panic.  The `None` value standing in for "the caller crashed"
    is a Lean-conventional way to express partiality.
-/
def toBytes16 (i : Int) : Option (List UInt8) :=
  if 0 ≤ i ∧ i < 2 ^ 128 then some [] else none
  -- The actual byte-list content is irrelevant for the bug; the
  -- bug lives in WHEN the function returns `none` (panics).
  -- The empty list is a placeholder; the call site only checks
  -- presence vs absence of a valid encoding.

/-! ## The impl's view of the proof: raw `Int` fields

    The impl receives `proof: dict` from the Python caller and reads
    each field with no type/range constraint.  Modeled as a struct
    of raw `Int`s, mirroring the unchecked-Python view. -/
structure RawProof where
  commitment : Int
  z          : Int
  y          : Int
  pi         : Int
  alpha      : Int
  deriving Repr, DecidableEq

/-! ## Impl-side transcript build (panic-honest)

    Faithful translation of `code/proof_system.py:129-133`:
    builds three byte-encodings IN ORDER and short-circuits to
    `none` (panic) on the first out-of-range field.

    The impl's actual behavior on panic is to raise an exception
    that propagates to the caller; we model this as `none`,
    representing "the verifier did not return a `Bool`". -/
def implRebuildTranscript (p : RawProof) : Option (List (List UInt8)) := do
  let cb  ← toBytes16 p.commitment
  let pib ← toBytes16 p.pi
  let zb  ← toBytes16 p.z
  pure [cb, pib, zb]

/-- Lifted impl-verify result type.  `some true` / `some false` for
    real verify decisions; `none` for panic.  This matches the
    operational semantics: a sound verifier returns `Bool`; the
    impl's verifier returns `Option Bool` because of partiality. -/
def implVerifyOpt (p : RawProof) : Option Bool := do
  let _transcript ← implRebuildTranscript p
  -- The remaining algebraic check is irrelevant for F5 — F5 is
  -- about the path BEFORE the algebraic check.  Stub to `true`.
  pure true

/-! ## Panic catalog — five attacker-malformed proofs

    Mirroring the five concrete cases in
    `artifacts/repro/dos_F5_verify_panic.py`.  Each is a `RawProof`
    whose serialization at the cited line range raises in CPython.

    `native_decide` discharges every `implVerifyOpt _ = none` claim
    on these ground terms; the inequality with the spec's
    "always returns Some" behavior is the F5 obstruction. -/

/-- Attacker proof #1: negative commitment.
    `(-1).to_bytes(16, "big")` → OverflowError.  -/
def badNegC : RawProof :=
  { commitment := -1, z := 0, y := 0, pi := 0, alpha := 0 }

/-- Attacker proof #2: oversized `z` (≥ 2^128).
    `(2^128).to_bytes(16, "big")` → OverflowError.  -/
def badLargeZ : RawProof :=
  { commitment := 0, z := 2 ^ 128, y := 0, pi := 0, alpha := 0 }

/-- Attacker proof #3: negative `z`. -/
def badNegZ : RawProof :=
  { commitment := 0, z := -1, y := 0, pi := 0, alpha := 0 }

/-- Attacker proof #4: oversized `pi` (≥ 2^128). -/
def badLargePi : RawProof :=
  { commitment := 0, z := 0, y := 0, pi := 2 ^ 128, alpha := 0 }

/-- Attacker proof #5: negative `pi`. -/
def badNegPi : RawProof :=
  { commitment := 0, z := 0, y := 0, pi := -1, alpha := 0 }

/-! ## Machine-checked F5 obstructions

    Each attacker proof above causes `implVerifyOpt` to return
    `none` (panic), instead of returning `some false` (reject) as
    a sound verifier would. -/

theorem panic_on_negative_commitment :
    implVerifyOpt badNegC = none := by
  native_decide

theorem panic_on_large_z :
    implVerifyOpt badLargeZ = none := by
  native_decide

theorem panic_on_negative_z :
    implVerifyOpt badNegZ = none := by
  native_decide

theorem panic_on_large_pi :
    implVerifyOpt badLargePi = none := by
  native_decide

theorem panic_on_negative_pi :
    implVerifyOpt badNegPi = none := by
  native_decide

/-! ## Existential statement of F5

    Bug-class statement: there exists a `RawProof` causing the
    impl-verifier to panic instead of returning a `Bool`.  Witnessed
    by `badNegC`. -/
theorem impl_verify_is_partial :
    ∃ p : RawProof, implVerifyOpt p = none :=
  ⟨badNegC, panic_on_negative_commitment⟩

/-! ## Spec-side: total verifier on `Fp`-typed inputs

    A sound spec models the proof boundary with `Fp`-valued fields:
    the parsing step at the trust boundary either accepts the wire
    bytes (and produces a well-typed `Proof`) or rejects them
    (returning `False` from `verify`).  Either way, the verifier
    is total — never raising.

    `Audit.PolyCommit.Proof` (in `Primitives.lean`) is exactly the
    `Fp`-typed boundary type the spec mandates.  We exhibit
    totality of the spec's transcript-build step on this type. -/
def specRebuildTranscript (p : Proof) : List (List UInt8) :=
  -- Spec encodes Fp elements directly; encoding is total because
  -- every `Fp` element is in range by typing.  Concrete content is
  -- irrelevant; we use `[]` as in `toBytes16`.
  [[], [], []]

theorem spec_transcript_total : ∀ p : Proof,
    (specRebuildTranscript p).length = 3 := by
  intro p
  rfl

/-! ## Impl ≠ spec on partiality

    Modeled cleanly: the spec's verifier is a total function
    `Proof → Bool`; the impl's verifier is a partial function
    `RawProof → Option Bool`, with `none` for the panic case.

    The PARTIALITY itself is the bug.  Below is the diagonal:
    every spec-side `Proof` parses to *some* well-formed
    `RawProof` (the round-trip), but the converse fails — there
    is a `RawProof` (e.g. `badNegC`) that does NOT correspond to
    any well-formed `Fp`-typed `Proof`, yet the impl still
    attempts to verify it.

    Concretely: `tryNormalize : RawProof → Option Proof` succeeds
    iff every field is in [0, P).  Every panic-witness above
    fails `tryNormalize` (commitment < 0, etc.); the impl never
    consults `tryNormalize` before serializing. -/
def tryNormalize (p : RawProof) : Bool :=
  decide (0 ≤ p.commitment ∧ p.commitment < (P : Int)) &&
  decide (0 ≤ p.z          ∧ p.z          < (P : Int)) &&
  decide (0 ≤ p.y          ∧ p.y          < (P : Int)) &&
  decide (0 ≤ p.pi         ∧ p.pi         < (P : Int)) &&
  decide (0 ≤ p.alpha      ∧ p.alpha      < (P : Int))

theorem normalize_rejects_neg_commitment :
    tryNormalize badNegC = false := by
  native_decide

theorem normalize_rejects_large_z :
    tryNormalize badLargeZ = false := by
  native_decide

/-- The independence statement: an attacker proof exists that
    (a) is rejected by spec-side `tryNormalize` (so a sound verifier
    would return `False` immediately), but (b) causes the impl-side
    serializer to panic instead. -/
theorem F5_independence :
    ∃ p : RawProof, tryNormalize p = false ∧ implVerifyOpt p = none :=
  ⟨badNegC, normalize_rejects_neg_commitment,
    panic_on_negative_commitment⟩

/-! ## Falsifiability

    If we provide a `RawProof` whose every field is in range
    [0, 2^128) — the impl's serialization domain — `implVerifyOpt`
    does NOT panic (returns `some _`).  This confirms the
    obstruction is content-driven (the panic IS the bug, not a
    universal property of `implVerifyOpt`). -/
def goodInRange : RawProof :=
  { commitment := 5, z := 7, y := 35, pi := 11, alpha := 99 }

theorem in_range_does_not_panic :
    implVerifyOpt goodInRange ≠ none := by
  native_decide

/-! ## Cross-reference

    F5 substantiation lives at the **partiality / panic-DoS** layer.
    Companion obstructions for the other findings:
      F1 → Trace.setup_ne_impl + State.impl_violates_invariant
            + Refinement.forge_succeeds  (soundness)
      F2 → Trace.prove_open_ne_impl     (transcript)
      F3 → Trace.verify_ne_impl         (challenge use)
      F4 → Trace.verify_ne_impl         (statement-id binding)
      F6 → Binding.commitTrunc_collides_poly1_poly2  (binding)

    F5 is at a layer no other finding occupies: partiality/panic.
    The bug shape is "`verify` returns `none` instead of `some _`",
    which is invisible to the operational/state/refinement layers
    that all assume the verifier returns a `Bool`.
-/

end Audit.PolyCommit.Robustness
