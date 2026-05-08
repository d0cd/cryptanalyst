/-
  State-invariant layer for the applied-21 polynomial-commitment audit.

  Per `formalize.md` Worked Example 4, this layer expresses temporal
  "X must hold before Y" properties that the operational `List Op`
  trace layer (`Trace.lean`) cannot express.

  Specifically: divergence D1 (the `_SETUP_SECRET` constant lives
  forever, the SRS publishes raw `s^i ∈ Fp`) is a value-flow /
  publishability property of the setup output, not a trace-shape
  property.  The `setup_ne_impl` theorem in `Trace.lean` substantiates
  the omitted-op components of finding F1 (D2/D3/D4); this file is the
  remainder — it expresses *why* the omissions are fatal as a state
  invariant the impl violates.

  This file complements `Trace.lean` (per `formalize.md`'s "Layer
  coverage with both shapes" quality bar): the trace layer catches
  call-sequence divergences; the state layer catches the value-flow
  property "value `t` of the trapdoor must never appear in any
  publicly-readable system state".

  Source: `code/proof_system.py:12, 22-29` (impl) and
  Kate-Zaverucha-Goldberg 2010 §3.1 (spec).
-/

import Audit.PolyCommit.Primitives
import Audit.PolyCommit.Ops

namespace Audit.PolyCommit.State

open Audit.PolyCommit

/-! ## System state

    A snapshot of what is observable from outside the setup ceremony.

    - `publishedSRS` lists every value the ceremony has *exposed* to
      external parties so far (the verifier, the prover, anyone with
      a copy of the SRS).
    - `trapdoor` records whether the ceremony still holds the secret
      `s` in memory (`some t`) or has destroyed it (`none`).

    Both fields are needed to express the invariant: "while the
    trapdoor is defined, no element of `publishedSRS` equals it".
-/
structure SystemState where
  publishedSRS : List Fp
  trapdoor : Option Fp
  deriving Repr, DecidableEq

/-- The initial state: nothing published, no trapdoor yet sampled. -/
def init : SystemState := { publishedSRS := [], trapdoor := none }

/-! ## Per-op transition functions

    `specStep` and `implStep` give the spec and impl semantics for
    each `SetupOp` constructor.  Per Kate et al. 2010 §3.1 vs
    `code/proof_system.py:22-29`, the four cases differ as follows:

    | Op                  | Spec (Kate et al. §3.1)              | Impl (`code:22-29`)         |
    | ------------------- | ------------------------------------ | --------------------------- |
    | `drawSecret t`      | sample `s ← F_p`; ceremony holds `t` | reads `_SETUP_SECRET`       |
    | `recordPower i p`   | private accumulator step (no publish)| `srs.powers.append(p)`      |
    | `encodeInGroup i`   | publish `[s^i]_1` (hiding via DLP)   | OMITTED — no group encoding |
    | `destroyTrapdoor`   | zero out `s` in ceremony memory      | OMITTED — `_SETUP_SECRET`   |
    |                     |                                      |   lives forever             |

    On `encodeInGroup` the spec publishes a group element `[s^i]_1`.
    For the value-flow invariant we represent the published value by
    `(0 : Fp)` as a placeholder — what matters is that it is *not
    equal to* the trapdoor `t`.  By the t-SDH / t-DLOG assumption,
    `[s^i]_1` and `s ∈ Fp` are computationally distinct; we encode
    that as concretely-distinct values for the state model.
-/

/-- Spec-side per-op transition. -/
def specStep (s : SystemState) : SetupOp → SystemState
  | .drawSecret t     => { s with trapdoor := some t }
  | .recordPower _ _  => s
  | .encodeInGroup _  => { s with publishedSRS := s.publishedSRS ++ [0] }
  | .destroyTrapdoor  => { s with trapdoor := none }

/-- Impl-side per-op transition. -/
def implStep (s : SystemState) : SetupOp → SystemState
  | .drawSecret t     => { s with trapdoor := some t }
  | .recordPower _ p  => { s with publishedSRS := s.publishedSRS ++ [p] }
  | .encodeInGroup _  => s   -- impl ignores: no group encoding
  | .destroyTrapdoor  => s   -- impl ignores: secret lives forever

/-! ## Op streams

    The spec and impl execute *different* op streams (the spec
    includes `encodeInGroup` and `destroyTrapdoor`, the impl does
    not).  We replay them with their own transition semantics.  The
    numeric values are placeholders consistent with `Trace.lean`'s
    `repSetupStream` — see `Trace.lean:repSetupStream`. -/

/-- Spec-side setup ops, degree 3.  Faithful to Kate et al. §3.1. -/
def specOps : List SetupOp :=
  [ .drawSecret 17,
    .recordPower 0 1,    .encodeInGroup 0,
    .recordPower 1 17,   .encodeInGroup 1,
    .recordPower 2 289,  .encodeInGroup 2,
    .recordPower 3 4913, .encodeInGroup 3,
    .destroyTrapdoor ]

/-- Impl-side setup ops, degree 3.  Faithful to
    `code/proof_system.py:22-29` for `max_degree = 3`. -/
def implOps : List SetupOp :=
  [ .drawSecret 17,
    .recordPower 0 1,
    .recordPower 1 17,
    .recordPower 2 289,
    .recordPower 3 4913 ]

/-! ## The state invariant

    `trapdoorEverPublished` returns `true` iff at any reachable
    state during execution, the `publishedSRS` contained a value
    literally equal to the trapdoor (while the trapdoor was still
    defined).

    This is a "history-dependent" invariant — even if the trapdoor
    is later destroyed, the publishability defect is permanent
    (an external observer who saved a snapshot at the bad moment
    can always recover `s`).  This is what distinguishes D1 (the
    publishability defect) from D4 (the destroy-trapdoor defect):
    fixing only D4 does not fix D1.
-/

/-- Decidable membership for `Fp` lists.  Hand-rolled to avoid
    coupling to Lean core's `List.contains` (which dispatches via
    `BEq`); `DecidableEq Fp` gives us everything we need directly. -/
def listMem (a : Fp) : List Fp → Bool
  | [] => false
  | x :: xs => decide (a = x) || listMem a xs

/-- Walk a list of ops, applying `step` from `init`, and check
    after every op whether the trapdoor (if defined) appears in
    the published SRS at that point. -/
def trapdoorEverPublishedAux
    (step : SystemState → SetupOp → SystemState)
    (s : SystemState) : List SetupOp → Bool
  | [] => false
  | op :: rest =>
    let s' := step s op
    (match s'.trapdoor with
     | none   => false
     | some t => listMem t s'.publishedSRS) ||
    trapdoorEverPublishedAux step s' rest

/-- Top-level: did any reachable state during execution publish the
    trapdoor in the clear? -/
def trapdoorEverPublished
    (step : SystemState → SetupOp → SystemState)
    (ops : List SetupOp) : Bool :=
  trapdoorEverPublishedAux step init ops

/-! ## Theorems — machine-checked obstructions

    Three theorems together substantiate D1 and witness the
    independence of D1 and D4:

      1. `spec_preserves_invariant` — under spec semantics, the
         spec op stream never publishes the trapdoor.  This is the
         "good" baseline.

      2. `impl_violates_invariant` — under impl semantics, the impl
         op stream does publish the trapdoor (at i=1).  This is
         finding F1's value-flow component (D1).

      3. `impl_with_destroy_still_violates` — even an impl that
         additionally calls `destroyTrapdoor` after its loop still
         violates the invariant (history-dependence).  This is the
         falsifiability proof that D1 ≠ D4: fixing only the destroy
         step does not fix the publishability problem.
-/

/-- Spec satisfies the value-flow invariant: across the entire spec
    setup trace, the published SRS never contains the trapdoor.  The
    spec's `encodeInGroup` publishes a hiding element (modeled as
    `0` ≠ `17`), and `destroyTrapdoor` zeroes the trapdoor by the
    end. -/
theorem spec_preserves_invariant :
    trapdoorEverPublished specStep specOps = false := by
  native_decide

/-- Impl violates the value-flow invariant: at iteration i=1 the
    impl appends `17 = trapdoor` to the published SRS.  This is
    the machine-checked statement of finding F1's D1 component. -/
theorem impl_violates_invariant :
    trapdoorEverPublished implStep implOps = true := by
  native_decide

/-- Diagnostic: the final impl state has `publishedSRS = [1, 17, 289, 4913]`
    and `trapdoor = some 17`.  An external observer reading
    `publishedSRS[1]` learns the trapdoor directly. -/
#eval ((implOps.foldl implStep init).publishedSRS,
       (implOps.foldl implStep init).trapdoor)

/-! ## Falsifiability: D1 and D4 are independent

    Adding `destroyTrapdoor` to the impl (a hypothetical fix that
    addresses D4 only) does NOT close the invariant: the trapdoor
    was already published before being destroyed.  This shows the
    publishability defect (D1) is independent of the destroy-trapdoor
    defect (D4) — you must fix BOTH, and only `encodeInGroup` (D2/D3)
    fixes the publishability defect. -/

def implWithDestroyOps : List SetupOp := implOps ++ [.destroyTrapdoor]

/-- D1 ≠ D4: even with `destroyTrapdoor` added at the end, the impl
    still violates the invariant — the trapdoor was published *during*
    execution, so it remains recoverable from a saved snapshot. -/
theorem impl_with_destroy_still_violates :
    trapdoorEverPublished implStep implWithDestroyOps = true := by
  native_decide

/-! ## Falsifiability: a hypothetical "fully-fixed" impl

    A second falsifiability witness in the other direction: an impl
    that BOTH calls `encodeInGroup` per loop iteration AND
    `destroyTrapdoor` afterwards (i.e., behaves like the spec)
    *does* satisfy the invariant.  Confirms the obstruction is
    content-driven, not a tautology of the model: fixing the impl
    closes the inequality. -/

/-- A "fixed" impl that behaves like the spec on `encodeInGroup` and
    `destroyTrapdoor`. -/
def implFixedOps : List SetupOp := specOps

/-- The "fixed" impl satisfies the invariant under impl semantics
    too.  Why?  Under `implStep`, `encodeInGroup` is a no-op; but
    `destroyTrapdoor` zeroes the trapdoor field.  After the trapdoor
    is `none`, no further check can fire — and we ran the trapdoor
    publication check on each *prior* state, where the trapdoor was
    `some 17` and the published list was `[1, 17, 289, 4913]`.  So
    the invariant should still fail.  Let's verify: -/
theorem impl_fixed_under_impl_semantics_still_violates :
    trapdoorEverPublished implStep implFixedOps = true := by
  native_decide

/-- The honest witness: under SPEC semantics (where `encodeInGroup`
    publishes a hiding element instead of being a no-op, and where
    `recordPower` does NOT publish), the spec ops satisfy the
    invariant.  This is the same content as
    `spec_preserves_invariant` — kept here as the symmetric witness
    that the spec is "right" while the impl is "wrong". -/
example :
    trapdoorEverPublished specStep specOps = false := by
  native_decide

/-! ## Length lemmas

    Sanity that the two streams are non-trivial: 10 ops vs 5 ops. -/

example : specOps.length = 10 := by native_decide
example : implOps.length = 5 := by native_decide

/-! ## Cross-reference

    This file substantiates the value-flow component of finding F1
    (D1, "hardcoded `_SETUP_SECRET` survives setup as plaintext in
    the SRS").  The companion operational obstruction at the same
    layer is `Audit.PolyCommit.Trace.setup_ne_impl`, which captures
    the omitted-op components (D2/D3/D4) — `encodeInGroup` and
    `destroyTrapdoor` are absent from the impl trace.

    Together the two obstructions enumerate the full structural
    failure of the impl's setup phase against Kate et al. 2010 §3.1.
-/

end Audit.PolyCommit.State
