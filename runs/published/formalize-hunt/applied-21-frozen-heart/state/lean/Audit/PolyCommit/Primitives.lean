/-
  Foundational primitives for the applied-21 polynomial commitment audit.

  This file declares the algebraic types and value-spaces that show up
  across the spec-side and impl-side traces. Heavy use of Mathlib so
  the model is honest about the algebra (a ZMod p Field, polynomials
  over it, commitments as either group elements or field elements
  depending on the layer being modeled).

  Construction under audit: KZG-shaped polynomial commitment without
  pairings — see /workspace/runs/.../artifacts/spec-trace.md.

  Sources:
    Kate, Zaverucha, Goldberg. "Constant-Size Commitments to Polynomials
    and Their Applications." AsiaCrypt 2010.
    Trail of Bits. "Frozen Heart" disclosure series, 2022.
-/

import Mathlib.Algebra.Field.Basic
import Mathlib.Algebra.Polynomial.Basic
import Mathlib.Data.ZMod.Basic
import Mathlib.Algebra.BigOperators.Basic

namespace Audit.PolyCommit

/-- Mersenne prime M127 — the field characteristic used by the impl
    (`code/proof_system.py:8`).  -/
def P : Nat := 2 ^ 127 - 1

/-- `NeZero P` is needed for `OfNat (ZMod P) k` to resolve at the
    `Nat`-literal level (`(5 : Fp)` etc.). Stated explicitly so the
    test-bed traces in `Trace.lean` resolve numeric literals without
    a separate `NatCast` indirection. Proof is by `native_decide`
    because direct kernel reduction of `2^127` is impractical. -/
instance instNeZeroP : NeZero P := ⟨by unfold P; native_decide⟩

/-- The prime field `F_P`. We model it as `ZMod P`. The implementation
    represents elements as `Nat` mod P; this Mathlib type exposes
    field structure so binding / soundness theorems are stateable. -/
abbrev Fp : Type := ZMod P

/-- Maximum polynomial degree supported by the SRS.
    `code/proof_system.py:13`. -/
def srsMaxDegree : Nat := 32

/-- A polynomial over `Fp` represented as a coefficient list.
    `code/proof_system.py:32-34` — `coeffs[i]` is the coefficient of `X^i`.

    `DecidableEq` is required so that `Op` constructors that take a
    `Polynomial` argument can themselves derive `DecidableEq`, which
    in turn is what makes `native_decide` discharge spec-vs-impl
    list equality / inequality theorems. -/
structure Polynomial where
  coeffs : List Fp
  deriving Repr, DecidableEq

namespace Polynomial

/-- Evaluate the polynomial at a point — the spec sense, by Horner /
    direct expansion. `code/proof_system.py:36-42`. -/
def evaluate (p : Polynomial) (x : Fp) : Fp :=
  p.coeffs.foldr (fun c acc => c + x * acc) 0

end Polynomial

/-- The Structured Reference String. Spec says this should hold *group
    elements* `[s^i]_1`; the impl holds raw field elements `s^i ∈ Fp`
    (`code/proof_system.py:24-28`).  We model both — the field-only
    variant captures what the impl ships; later cycles may add a
    group-encoded variant for refinement comparisons.

    `srs.powers.length = srsMaxDegree + 1`. -/
structure SRS where
  powers : List Fp
  deriving Repr, DecidableEq

/-- Statement-id, a byte-string identifying which polynomial / context
    the proof is bound to. `code/proof_system.py:74` (`statement_id`). -/
abbrev StatementId : Type := List UInt8

/-- The proof transcript element — either a commitment, a witness, or
    a domain element.  Marked with a tag so the order of entries is
    traceable. -/
inductive TranscriptEntry where
  | commitment (c : Fp)
  | witness (w : Fp)
  | point (z : Fp)
  | claimedValue (y : Fp)
  | statementTag (s : StatementId)
  deriving Repr, DecidableEq

/-- A KZG opening proof. Field names mirror the dict keys in
    `code/proof_system.py:107-114`. -/
structure Proof where
  commitment   : Fp
  z            : Fp
  y            : Fp
  pi           : Fp
  alpha        : Fp
  statementId  : StatementId
  deriving Repr, DecidableEq

/-- Hash of a transcript modeled abstractly — the impl computes it
    via SHA-256 mod P (`code/proof_system.py:68-71`). For the formal
    model we only need it to be deterministic and collision-resistant
    in principle; the *content* of the transcript is the audit target,
    not the hash function. -/
axiom hashTranscript : List TranscriptEntry → Fp

end Audit.PolyCommit
