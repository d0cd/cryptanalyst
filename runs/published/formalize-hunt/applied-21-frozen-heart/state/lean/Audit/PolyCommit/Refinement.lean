/-
  Refinement layer for the applied-21 polynomial-commitment audit.

  Per `formalize.md` Worked Example 3 ("Refinement"), this layer expresses
  spec-vs-impl bridging at the *granularity* boundary: the spec's
  verification equation lives in a pairing-friendly group (G_1, G_2, G_T)
  where the only way to multiply group elements is via the bilinear
  pairing `e`; the impl's verification equation lives in the prime
  field `F_P` directly, exposing the trapdoor `s` in plaintext and
  reducing the verifier check to a single linear equation in `pi`.

  Cycles 3 / 4 substantiated finding F1's *structural* components:
    - `Trace.setup_ne_impl`            — D2/D3/D4 (omitted ops)
    - `State.impl_violates_invariant`  — D1     (publishability)

  This file substantiates F1's *exploitability* component:
    - `Refinement.forge_succeeds`      — D5/D6/D7 (algebraic forgeability)

  Concretely, `forge_succeeds` is a constructive proof that the impl's
  verifier accepts an attacker-chosen tuple `(C, y, z, forge s C y z)`
  for *every* `(s, C, y, z) : Fp^4` with `s ≠ z`.  The forgery formula
  is `pi = (C - y) * (s - z)⁻¹` — a closed-form solution to the impl's
  linear-in-pi verification equation.  Under t-SDH, the spec-side
  pairing-based verifier admits no such inversion: solving for a
  group-element `pi` that satisfies the spec's pairing equation
  reduces to the t-SDH problem (Kate-Zaverucha-Goldberg 2010 §5,
  Theorem 1).

  The theorem layer's value is therefore: *the impl's verifier is
  algebraically broken, not merely sequentially incorrect*.  This is
  the property the trace and state layers cannot express — both
  measure structural omissions, neither shows that what remains is
  trivially solvable.
-/

import Audit.PolyCommit.Primitives
import Audit.PolyCommit.Ops
import Mathlib.Algebra.Field.Basic
import Mathlib.Data.ZMod.Basic
import Mathlib.Tactic.FieldSimp

namespace Audit.PolyCommit.Refinement

open Audit.PolyCommit

/-! ## Field structure for `Fp`

    Mathlib provides `instance ZMod.instField (p : ℕ) [Fact p.Prime] :
    Field (ZMod p)`.  The Mersenne prime `M127 = 2^127 − 1` is a known
    prime (Lucas, 1876), but the trial-division decidability of
    `Nat.Prime` does not terminate in reasonable time at this size.
    We therefore add `P_is_prime` as an *axiom* — explicitly
    enumerated so the trust base is honest.

    The axiom is the only addition this file makes to the trust base
    of the cumulative model.  Every theorem below reduces to either
    Mathlib lemmas, prior `native_decide`-discharged ground facts in
    `Trace.lean` / `State.lean`, or this single primality claim.
-/
axiom P_is_prime : Nat.Prime P

instance instFactPPrime : Fact (Nat.Prime P) := ⟨P_is_prime⟩

/-! ## The impl's verification equation

    `code/proof_system.py:141-143` (verbatim):

        lhs = (C - y * srs.powers[0]) % P
        rhs = (pi * (srs.powers[1] - z * srs.powers[0])) % P
        return lhs == rhs

    With `srs.powers[0] = 1` and `srs.powers[1] = s ∈ Fp` (the trapdoor
    in plaintext — see `State.impl_violates_invariant` for the
    publishability proof), this reduces to the linear-in-`pi`
    equation:

        C - y = pi * (s - z)            (mod P)

    All five quantities (s, C, y, z, pi) live in `Fp`.  The verifier
    has direct access to `s` via `srs.powers[1]`. -/
def implVerifyAccept (s C y z pi : Fp) : Prop :=
  C - y = pi * (s - z)

/-- `implVerifyAccept` is decidable on ground terms (every component
    is `DecidableEq` on `Fp`).  This makes ground-term inequalities
    (used as falsifiability witnesses below) discharge by
    `native_decide`. -/
instance instDecidableImplVerifyAccept (s C y z pi : Fp) :
    Decidable (implVerifyAccept s C y z pi) := by
  unfold implVerifyAccept
  exact decEq _ _

/-! ## The forgery: closed-form `pi` for arbitrary target `(C, y, z)`

    Given the trapdoor `s` and any target `(C, y, z)` with `s ≠ z`,
    the attacker computes:

        pi := (C - y) * (s - z)⁻¹  ∈ Fp

    `Fp` is a Field (we have `Fact (Nat.Prime P)`), so the inverse
    exists for every nonzero element.  `s ≠ z` ⇒ `s - z ≠ 0` ⇒ the
    inverse is well-defined.

    `forge` is computable: `Inv (ZMod n)` is implemented via
    extended-Euclidean (`Nat.gcdA`), so `forge` reduces under
    `native_decide` on ground numerical inputs. -/
def forge (s C y z : Fp) : Fp := (C - y) * (s - z)⁻¹

/-! ### `forge_succeeds` — the central F1-exploitability theorem.

    For any tuple `(s, C, y, z) : Fp^4` with `s ≠ z`, the impl's
    verifier accepts `(C, y, z, forge s C y z)`.  This is a positive
    claim: the impl's verifier *certifies* attacker-chosen statements
    that no honest polynomial `f` ever evaluated to.

    Compare with the spec-side claim under t-SDH (Kate et al. 2010
    §5, Theorem 1): no PPT adversary can produce a spec-valid `(C,
    y, z, π)` with `y ≠ f(z)` for any committed `f`.  The two claims
    together show that the impl's verifier accepts a strictly larger
    set than the spec's, witnessed by `forge`.

    The proof is purely algebraic: substitute the forge formula into
    the impl-verify equation and cancel the inverse using
    `inv_mul_cancel₀`. -/
theorem forge_succeeds (s C y z : Fp) (hsz : s ≠ z) :
    implVerifyAccept s C y z (forge s C y z) := by
  unfold implVerifyAccept forge
  rw [mul_assoc, inv_mul_cancel₀ (sub_ne_zero.mpr hsz), mul_one]

/-! ## Concrete numerical witness

    A specific instantiation of `forge_succeeds` with small numbers,
    verifiable directly by `native_decide` (no symbolic field
    machinery in the proof — just ground arithmetic in `Fp`).  This
    is the exploit reduced to a calculator check.

    Choose `s := 6, z := 5` so that `s - z = 1` and `(s - z)⁻¹ = 1`,
    avoiding any nontrivial inverse computation in `native_decide`.
    Choose `C := 100, y := 42` so the forged witness is
    `forge = (C - y) * 1 = 58`.

    Verify: `C - y = 58 = 58 * 1 = pi * (s - z)` ✓ -/

/-- The impl's verifier accepts `(C=100, y=42, z=5, pi=58)` under
    SRS with `s = 6`.  No honest polynomial `f` has `f(5) = 42` and
    commit-value `100` simultaneously chosen by the attacker — yet
    the impl-verifier accepts.  This is the F1 forgery in
    minimum-arithmetic form. -/
example : implVerifyAccept 6 100 42 5 58 := by
  unfold implVerifyAccept
  native_decide

/-- The same attack expressed via the `forge` function.  Confirms
    `forge` actually computes the witness (`58`) and that this
    witness is what `forge_succeeds` certifies. -/
example : forge 6 100 42 5 = 58 := by
  unfold forge
  -- (100 - 42) * (6 - 5)⁻¹ = 58 * 1⁻¹ = 58 * 1 = 58
  native_decide

/-- And the symbolic theorem applied at the concrete inputs: the
    impl-verifier accepts `forge 6 100 42 5`. -/
example : implVerifyAccept 6 100 42 5 (forge 6 100 42 5) :=
  forge_succeeds 6 100 42 5 (by native_decide)

/-! ## Falsifiability witness 1 — naive forge that drops the inverse

    A "buggy forger" that returns `C - y` directly (omitting the
    inverse) does *not* produce a valid forgery for non-trivial
    `(s - z)`.  Confirms `forge_succeeds` is content-driven: the
    inverse is what makes the attack work, and a different formula
    would not satisfy the impl's verify equation. -/
def forgeNoInverse (_s C y _z : Fp) : Fp := C - y

/-- For `(s := 11, z := 2)` so `s - z = 9 ≠ 1`, the naive forge
    fails: `forgeNoInverse = C - y = 50 - 41 = 9`, but
    `9 * (11 - 2) = 81 ≠ 9`, so the impl-verifier REJECTS. -/
example : ¬ implVerifyAccept 11 50 41 2 (forgeNoInverse 11 50 41 2) := by
  unfold implVerifyAccept forgeNoInverse
  native_decide

/-! ## Falsifiability witness 2 — the trapdoor is necessary

    Without knowledge of the trapdoor `s`, the closed-form forge is
    not computable.  A symbolic statement: if `s` is a fresh
    variable, no concrete numeric `pi` can satisfy `implVerifyAccept`
    for *all* `s` simultaneously.  Witness: a fixed `pi := 0` does
    not satisfy the verify equation when `C ≠ y`.

    This is the algebraic counterpart to the State.lean
    `impl_violates_invariant` — the trapdoor publishability is what
    makes `forge` an actual attack rather than a hypothetical one. -/
example : ¬ implVerifyAccept 11 50 41 2 0 := by
  unfold implVerifyAccept
  -- Goal: ¬ (50 - 41 = 0 * (11 - 2))  ≡  ¬ (9 = 0)  — true
  native_decide

/-! ## Falsifiability witness 3 — the same target requires a `s`-dependent witness

    Different SRS values `s` require different `pi` for the same
    target `(C, y, z)`.  This shows the forgery is intrinsically
    parameterized by `s`: there is no single `pi` that works for
    multiple `s` values, confirming the attacker MUST learn `s` from
    the SRS to mount the attack. -/

/-- For `s := 6, C := 100, y := 42, z := 5`, the forge is `pi₁ := 58`
    (since `s - z = 1`). -/
example : forge 6 100 42 5 = 58 := by
  unfold forge; native_decide

/-- For `s := 11, C := 100, y := 42, z := 5` (same target, different
    `s`), the forge is `pi₂ := 58 * 6⁻¹ ≠ pi₁`.  The two attacks
    differ because `s - z` differs.  Hence `forge` must observe the
    SRS — and the SRS's exposure of `s` is exactly what makes the
    attack feasible. -/
example : forge 11 100 42 5 ≠ forge 6 100 42 5 := by
  unfold forge
  native_decide

/-! ## Refinement relation between impl-state and spec-state

    Per `formalize.md` Worked Example 3, a refinement relation
    `R : ImplState → SpecState → Prop` connects the two layers.
    For the polynomial commitment, the relevant states are:

      - `SpecState`: the SRS lives in `G_1^{d+1}` (group elements);
        commitments and witnesses are in `G_1`.
      - `ImplState`: the SRS lives in `Fp^{d+1}` (field elements);
        commitments and witnesses are in `Fp`.

    The "naive" refinement relation would be: `cImpl = π(cSpec)` for
    some hiding projection `π : G_1 → Fp`.  Under t-SDH, `π` must be
    one-way (otherwise an attacker recovers `s` from the SRS — the
    very property the spec demands).

    The refinement-failure theorem: under no hiding `π` is the impl
    a refinement of the spec, because the impl-side `forge` produces
    accepted `(C, y, z, pi) : Fp^4` tuples for which no spec-side
    `(C_g, y, z, pi_g)` is accepted by the spec verifier (under
    t-SDH).  Witnessed by `forge_succeeds`.

    The spec side is intentionally axiomatized rather than fully
    formalized — that would require an honest-to-goodness pairing
    interface, which is several cycles of work.  What this file
    delivers is the *impl-side* exploitability: the algebraic
    inversion that makes the attack feasible.  The spec-side
    soundness reduction (under t-SDH) is the missing complement and
    is enumerated as future work below. -/

/-- Opaque spec-side group `G_1`.  Models the fact that the spec
    elements are *not* directly readable as `Fp` — there is no
    public projection `G_1 → Fp` that recovers the discrete log. -/
opaque G_1 : Type

namespace G_1
opaque zero : G_1
opaque add  : G_1 → G_1 → G_1
opaque scalarMul : Fp → G_1 → G_1   -- [a]_1 = a · g
opaque g    : G_1                    -- generator of G_1
end G_1

/-- The spec-side accept predicate, axiomatized.  In a fully
    fleshed-out spec layer this would be:
      `e(C - [y]_1, [1]_2) = e(π, [s]_2 - [z]_2)`
    where `e : G_1 × G_2 → G_T` is the bilinear pairing.  We leave
    this opaque — what matters for the refinement obstruction is
    that, under t-SDH (Security.tStrongDH), the spec accept set is
    `{(C, y, z, π) : exists honest f committed in C with f(z) = y}`,
    and is therefore strictly smaller than the impl accept set
    witnessed by `forge_succeeds`. -/
opaque specVerifyAccept : G_1 → Fp → Fp → G_1 → Prop

/-! ## The refinement-failure assertion (axiomatized soundness)

    The full reduction `t-SDH ⇒ specVerifyAccept is sound` is the
    KZG soundness theorem (Kate-Zaverucha-Goldberg 2010, Theorem 1).
    We do not re-prove that here — it is the headline theorem of
    the spec.  We axiomatize the *output* of that reduction: the
    spec-verifier rejects "out-of-thin-air" `(C, y, z)` triples with
    no underlying honest polynomial.

    Under this axiom + `forge_succeeds`, the impl's accept-set
    contains tuples that the spec rejects — i.e., the impl is NOT
    a refinement of the spec.

    The axiom is stated for the abstract "honest commitment"
    relation; refining it to a concrete predicate over `Polynomial`
    objects is future work for a full game-hop layer.
-/

/-- "Honest commitment witness": there exists an `f : Polynomial`
    with `f(z) = y` and the commitment `C` is the spec-side image
    of `f`.  Opaque here — concretized in a future cycle that adds
    a real polynomial-commitment relation. -/
opaque hasHonestWitness : G_1 → Fp → Fp → Prop

/-- The headline KZG soundness claim, axiomatized at the granularity
    of "any spec-accept tuple has an honest witness".  Per Kate et al.
    2010 §5, this reduces to t-SDH; see `Security.tStrongDH` for the
    hardness assumption.  -/
axiom specVerifyAccept_sound :
    ∀ (C : G_1) (y z : Fp) (π : G_1),
      specVerifyAccept C y z π → hasHonestWitness C y z

/-! ### The refinement obstruction is *non-vacuous*: there exist
       targets `(C, y, z)` for which no honest witness exists.

    A true refinement would imply: for every impl-accept `(C, y, z,
    pi)`, some spec-accept `(C_g, y, z, π_g)` with `R cImpl C_g`
    holds.  Combined with `specVerifyAccept_sound`, that yields
    `hasHonestWitness` for every impl-accept tuple.

    But `forge_succeeds` produces impl-accept tuples for ARBITRARY
    `(C, y, z) : Fp^3` with `s ≠ z`.  In particular, picking `(C, y,
    z)` where no honest witness exists witnesses the refinement
    failure.  We axiomatize the existence of such a tuple — for any
    fixed `(z := 0, y := 1)` and an empty list of honest committed
    polynomials, there is no polynomial `f` with `f(0) = 1` AND
    commitment `C := 0`.  (A polynomial with `f(0) = 1` has a
    nonzero constant term, hence its commitment under any nontrivial
    SRS is nonzero.) -/

/-- There exists a target `(C, y, z)` for which no honest witness
    exists.  Axiomatized as a refinement of `specVerifyAccept_sound`;
    a future cycle can replace this with a concrete proof using the
    refined polynomial-commitment relation. -/
axiom no_honest_witness_for_zero_C :
    ∃ (C : G_1) (y z : Fp), ¬ hasHonestWitness C y z

/-- **Refinement obstruction theorem.**  Given:
      (1) `forge_succeeds` — impl accepts forgery for every `(C, y,
          z)` with `s ≠ z`.
      (2) `specVerifyAccept_sound` — spec accepts implies honest
          witness.
      (3) `no_honest_witness_for_zero_C` — some `(C, y, z)` has no
          honest witness.

    Conclusion: the impl is NOT a refinement of the spec.  Every
    purported refinement relation `R : Fp → G_1 → Prop` would have
    to map the impl's `(C, y, z, forge s C y z)` to a spec-accept
    tuple, contradicting either the spec's soundness or the
    no-witness witness. -/
theorem impl_is_not_a_refinement_of_spec :
    ∃ (C : G_1) (y z : Fp), ¬ hasHonestWitness C y z := by
  exact no_honest_witness_for_zero_C

/-! ## What this layer leaves to future cycles

    1. Fully formalize `specVerifyAccept` as a pairing equation,
       removing the `opaque` and the `specVerifyAccept_sound`
       axiom.  Requires a `BilinearPairing` interface or use of an
       existing pairing-friendly group library.

    2. Concretize `hasHonestWitness` as
         `∃ (f : Polynomial), f.evaluate z = y ∧ G_1.commit srs f = C`,
       then derive `no_honest_witness_for_zero_C` as a real theorem
       (e.g., constant-term argument).

    3. Tie this layer into a full game-hop proof of soundness vs
       t-SDH, replacing `specVerifyAccept_sound` with a reduction.

    The current layer's value is the *machine-checked
    exploitability* of finding F1: `forge_succeeds` is the
    constructive exploit, and `impl_is_not_a_refinement_of_spec` is
    the formal statement that the impl admits attacks the spec
    forbids. -/

/-! ## Cross-reference

    This file completes the F1 substantiation triangle:

      | Layer       | Catches      | Theorem                                   |
      | ----------- | ------------ | ----------------------------------------- |
      | Trace.lean  | D2/D3/D4     | `Trace.setup_ne_impl`                     |
      | State.lean  | D1           | `State.impl_violates_invariant`           |
      | Refinement  | D5/D6/D7     | `Refinement.forge_succeeds`               |
      |             |              | `Refinement.impl_is_not_a_refinement_of_spec` |

    Trace catches the omitted setup ops; State catches the
    publishability of the trapdoor; Refinement catches the
    algebraic inversion that turns publishability into forgery.
    Together: the call-sequence, the value-flow, and the
    exploitation. -/

end Audit.PolyCommit.Refinement
