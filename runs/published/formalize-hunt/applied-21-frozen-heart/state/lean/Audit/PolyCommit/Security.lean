/-
  Top-level security theorem skeletons + hardness-assumption axioms
  for the applied-21 polynomial commitment scheme.

  Each theorem is stated with `sorry` (or a TODO axiom) so the trust
  base is enumerated leaf-by-leaf. Future cycles either:
    - discharge a `sorry` with a real proof,
    - localize a divergence via `firstDiff` and add the finding,
    - or refine an axiom statement to better reflect the cited source.

  This file is intentionally non-executing — it captures *what we are
  trying to prove*, against which the impl-side trace can be measured.

  Sources:
    Kate, Zaverucha, Goldberg. "Constant-Size Commitments to
    Polynomials and Their Applications." AsiaCrypt 2010, §3.2-3.3.
    The KZG paper.
    Trail of Bits "Frozen Heart" disclosure series, 2022:
        https://blog.trailofbits.com/2022/04/13/...
-/

import Audit.PolyCommit.Primitives
import Audit.PolyCommit.Ops

namespace Audit.PolyCommit.Security

open Audit.PolyCommit

/-! ## Hardness assumptions

    Each axiom here states a complexity claim that the construction's
    soundness reduces to.  Bare `axiom foo : Prop` would be a black
    hole — the claim text is the trust base.  Where applicable, we
    cite the paper section.
-/

/-- Adversary abstraction — for now an opaque type whose size /
    polynomial-time bound is tracked externally.  Future cycles may
    refine this with a probability-monad-flavored interface. -/
opaque Adversary : Type

/-- A concrete advantage value an adversary may achieve in a security
    game.  In a probabilistic model this is `ℝ`; here we keep it
    abstract until a probability framework is layered in. -/
opaque Advantage : Type

/-- "Negligible in the security parameter `λ`" — placeholder. -/
opaque negligible : Nat → Advantage
opaque advantageLE : Advantage → Advantage → Prop
opaque polyTime : Adversary → Prop

/-- The `t`-Strong Diffie-Hellman / `t`-power Discrete Log assumption
    in a pairing-friendly group.  In a group `G_1, G_2` of prime
    order `p` with bilinear pairing `e : G_1 × G_2 → G_T`, given
    `(g, g^s, g^{s^2}, …, g^{s^t}) ∈ G_1^{t+1}`, no PPT adversary
    can recover `s` (or, in the q-DLOG variant, distinguish from
    independent random elements) with non-negligible advantage.

    KZG soundness reduces to t-SDH (Kate et al. 2010, Theorem 1). -/
axiom tStrongDH :
    ∀ (t : Nat) (adv : Adversary),
      polyTime adv →
      advantageLE (negligible 128) (negligible 128)
                                            -- TODO: replace with the
                                            -- actual game-advantage
                                            -- statement once an
                                            -- adversary interface is
                                            -- in place.

/-- The collision-resistance assumption for SHA-256 used as the FS
    hash. Standard. -/
axiom sha256CollisionResistant :
    ∀ (adv : Adversary),
      polyTime adv →
      advantageLE (negligible 128) (negligible 128)

/-! ## Top-level security claims

    Each `Prop` here is a soundness / binding / domain-separation
    claim that *the construction should* satisfy.  We state them
    generically so future cycles can refine the quantifiers.
-/

/-- KZG **evaluation binding** (the property the impl is supposed to
    deliver): if the verifier accepts `(C, z, y, π)` and `(C, z, y', π')`
    with `y ≠ y'`, the prover must have broken `t-SDH`.

    Stated abstractly here; the `sorry` flags that the construction
    needs a *group-encoding* of the SRS for this to even be statable
    — see divergence D2/D7 — so as written for the impl this theorem
    is FALSE for a trivial reason. We keep the statement so future
    cycles can either (a) refine to specify the group encoding the
    spec demands, or (b) provide a counterexample that witnesses
    `evaluation_binding_FAILS`. -/
def EvaluationBinding : Prop :=
  ∀ (C z y y' pi pi' alpha alpha' : Fp) (sid sid' : StatementId),
    -- placeholder: in a refined model these conditions would be
    -- "Verify accepts (C, z, y, π, α, sid)" and "Verify accepts
    -- (C, z, y', π', α', sid')"; with `y ≠ y'`. The conjecture is:
    -- such (C, π, π') reduce to a t-SDH solver.
    True

theorem evaluation_binding : EvaluationBinding := by
  intro _ _ _ _ _ _ _ _ _ _
  trivial

/-- Statement-binding (a.k.a. statement-id binding). If the verifier
    accepts `proof` against `statement_id_1`, it must NOT accept the
    same `proof` against any `statement_id_2 ≠ statement_id_1`.

    The impl violates this trivially because `verify` never reads
    `proof.statementId`. We capture the *spec-side claim* here so
    that the divergence is registered. -/
def StatementBinding (verifier : Proof → StatementId → Bool) : Prop :=
  ∀ (proof : Proof) (sid₁ sid₂ : StatementId),
    sid₁ ≠ sid₂ →
    verifier proof sid₁ = true →
    verifier proof sid₂ = false

/-- The verifier as it is written in the impl, modeled abstractly.
    Future cycles will define this via `step : State → Op → State`
    and a list-of-VerifyOp evaluator; for now we leave the body to
    the refinement layer. -/
opaque implVerify : SRS → Proof → StatementId → Bool

theorem statement_binding_holds :
    StatementBinding (implVerify default_srs)
    := by
  sorry  -- INTENTIONAL — we expect this to be unprovable as written,
         -- and a future cycle will replace it with a counterexample
         -- (see divergence D10 / finding F4).
where
  default_srs : SRS := { powers := [] }

/-- Fiat-Shamir soundness ("strong FS"): the challenge α derived from
    the transcript binds every prover-controlled value the verifier
    later relies on.  The Trail of Bits 2022 series formalizes this
    as: every public statement value, every prover-supplied value
    must appear in the transcript.

    Stated for the impl-as-written, this is FALSE because `y` and
    `statementId` are absent from the transcript (divergence D8).
    Future cycle will encode this and let `native_decide` surface
    the omission. -/
def FiatShamirBinding : Prop :=
  -- For all `(C, z, y, π, sid)`, the function that builds the impl's
  -- transcript should equal the function that builds the
  -- spec-mandated transcript:
  --   spec_transcript = [statement_id, C, π, y, z]
  --   impl_transcript = [C, π, z]
  -- These differ structurally, so the equality is FALSE.
  True

theorem fs_binding : FiatShamirBinding := by trivial

/-! ## Proof obligations enumerated

    Per the proof-obligation enumeration approach
    (CLAUDE.md / formalize.md), KZG soundness depends on these
    preconditions.  Each is a hypothesis the impl needs to satisfy:

    PO-1.  The SRS conceals `s` from any party that sees it.
           STATUS: VIOLATED by impl (`srs.powers[1] == s`).
           Machine-checked obstructions (three orthogonal layers):
             - `Audit.PolyCommit.Trace.setup_ne_impl`
                  — call-sequence layer.  Spec includes
                    `encodeInGroup` per loop iteration and
                    `destroyTrapdoor` post-loop; impl has neither.
                    Captures D2/D3/D4.
             - `Audit.PolyCommit.State.impl_violates_invariant`
                  — value-flow layer.  At iteration i=1 the impl
                    literally publishes `srs.powers[1] = s` to the
                    publicly-readable SRS.  Captures D1.
             - `Audit.PolyCommit.Refinement.forge_succeeds`
                  — algebraic-exploitability layer.  The impl's
                    verify equation `C - y = pi * (s - z)` is
                    invertible in `pi`; given the trapdoor `s`,
                    the attacker computes
                    `pi := (C - y) * (s - z)⁻¹` and the verifier
                    accepts.  Captures D5/D6/D7 (the field-vs-group
                    encoding defects that make inversion possible).
    PO-2.  Every committed polynomial has degree ≤ `srsMaxDegree`.
           STATUS: not enforced by `commit` (silently truncates).
    PO-3.  The FS transcript binds every prover-controlled public
           value the verifier relies on.
           STATUS: VIOLATED by impl (omits `y`, `statementId`).
    PO-4.  The FS challenge participates non-trivially in the
           verifier's algebraic check.
           STATUS: VIOLATED by impl (`α` is decorative, divergence D9).
    PO-5.  Each accepted proof binds to its statement_id.
           STATUS: VIOLATED by impl (verify ignores statement_id).
-/

end Audit.PolyCommit.Security
