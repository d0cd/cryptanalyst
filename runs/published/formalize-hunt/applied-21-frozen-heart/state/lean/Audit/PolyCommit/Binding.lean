/-
  Binding layer for the applied-21 polynomial-commitment audit.

  This file substantiates finding **F6** — the impl's `commit`
  function silently drops coefficients at index `>= len(srs.powers)`,
  producing collisions in the polynomial-commitment primitive.

  Source (impl):

      code/proof_system.py:52-58
      def commit(srs: SRS, poly: Polynomial) -> int:
          c = 0
          for i, coeff in enumerate(poly.coeffs):
              if i < len(srs.powers):           ←  silent skip
                  c = (c + coeff * srs.powers[i]) % P
          return c

  Source (spec):

      Kate-Zaverucha-Goldberg 2010 §3.2 — "Open(PK, φ, i)".
      The KZG construction restricts admissible polynomials to those
      of degree at most `t` (the supported-degree parameter of the
      trusted setup).  Honest senders never call `Commit` on a
      polynomial of degree > t; verifiers reject any such
      malformed input.  The impl performs neither check.

  Layer coverage / orthogonality to F1
  ------------------------------------

  F1 (Trace.setup_ne_impl, State.impl_violates_invariant,
      Refinement.forge_succeeds): the verify equation in `Fp` is
      invertible because `s` is published in plaintext in
      `srs.powers[1]`.

  F6 (THIS FILE): the commit primitive itself is non-collision-
      resistant because the truncation drops information.  The
      collision pair is constructed without ever reading any
      `srs.powers[i]` value — only `srs.powers.length` matters.

  Independence: F6 holds even if the powers were hidden (proper
  pairings, F1 fixed); F1 holds even if the truncation were checked
  (commit only accepts polynomials of degree ≤ srsMaxDegree).
-/

import Audit.PolyCommit.Primitives

namespace Audit.PolyCommit.Binding

open Audit.PolyCommit

/-! ## Truncated polynomial commitment

    Faithful Lean translation of `commit`'s loop body:
    iterate over `coeffs` with index `i`; if `i < powers.length`
    add `coeff * powers[i]` to the accumulator; else skip.

    We use `List.zip` to capture the truncation: pairs only up to
    the shorter list, exactly mirroring the `if i < len(srs.powers)`
    guard in `code/proof_system.py:55-57`. -/
def commitTrunc (powers : List Fp) (coeffs : List Fp) : Fp :=
  ((coeffs.zip powers).map (fun cp => cp.1 * cp.2)).foldr (· + ·) 0

/-- Concrete miniature SRS: 2 powers, modeling the cycle of the impl's
    33-power SRS at smaller scale.  `s = 17` (matching `Trace.lean`'s
    setup placeholder). -/
def miniPowers : List Fp := [1, 17]

/-- A polynomial whose length matches the SRS (no truncation). -/
def poly1 : List Fp := [3, 5]

/-- A polynomial with one EXTRA coefficient at index 2 (which lies
    outside the SRS).  The truncation discards `99`. -/
def poly2 : List Fp := [3, 5, 99]

/-- A polynomial with TWO extra coefficients.  Confirms the binding
    collision is many-to-one, not just two-to-one. -/
def poly3 : List Fp := [3, 5, 999, 12345]

/-! ## Binding collision (machine-checked)

    The central F6 obstruction: distinct polynomials commit to the
    same field element under the impl's truncating `commit`. -/

/-- F6: `commitTrunc miniPowers poly1 = commitTrunc miniPowers poly2`,
    even though `poly1 ≠ poly2`.  Together this is a binding break
    in the polynomial-commitment primitive. -/
theorem commitTrunc_collides_poly1_poly2 :
    poly1 ≠ poly2 ∧
    commitTrunc miniPowers poly1 = commitTrunc miniPowers poly2 := by
  refine ⟨?_, ?_⟩
  · native_decide
  · native_decide

/-- The collision is many-to-one: a third distinct polynomial maps
    to the same commitment.  Witness that the binding break admits
    arbitrary attacker choice in the truncated tail, not just one
    crafted pair. -/
theorem commitTrunc_collides_poly1_poly3 :
    poly1 ≠ poly3 ∧
    commitTrunc miniPowers poly1 = commitTrunc miniPowers poly3 := by
  refine ⟨?_, ?_⟩
  · native_decide
  · native_decide

/-- The shared commitment value, exhibited concretely.
    `3 * 1 + 5 * 17 = 88` in `Fp`. -/
example : commitTrunc miniPowers poly1 = (88 : Fp) := by native_decide
example : commitTrunc miniPowers poly2 = (88 : Fp) := by native_decide
example : commitTrunc miniPowers poly3 = (88 : Fp) := by native_decide

/-! ## Existential statement of binding break

    The bug-class statement: there exist two polynomials with the
    same impl commitment.  Discharged by exhibiting `poly1`/`poly2`. -/
theorem commit_not_binding :
    ∃ p1 p2 : List Fp,
      p1 ≠ p2 ∧
      commitTrunc miniPowers p1 = commitTrunc miniPowers p2 :=
  ⟨poly1, poly2, commitTrunc_collides_poly1_poly2⟩

/-! ## Independence from F1

    F1's exploitation requires reading `srs.powers[1]` in plaintext
    (the trapdoor `s`).  F6's collision construction reads only
    `miniPowers.length`.  Below we make this explicit by stating a
    *parametric* form: for ANY 2-power SRS `[p0, p1]` (specifically:
    any value of the powers `p0`, `p1`), the collision pair
    `(poly1, poly2)` collides.  The proof is purely structural: the
    `List.zip` truncates `poly2` to length 2, so the two
    `commitTrunc` expressions reduce to the same syntactic term.

    This is the formal statement that F6's exploit is independent of
    F1: even if `p0, p1` were hidden group elements (the spec's
    intent) rather than plaintext field elements (the impl's
    behavior), the collision would still hold. -/
theorem commit_collides_any_2power_srs (p0 p1 : Fp) :
    commitTrunc [p0, p1] poly1 = commitTrunc [p0, p1] poly2 := by
  -- Both sides reduce to `3*p0 + (5*p1 + 0)`: poly2's index-2
  -- coefficient is truncated by `List.zip` against the length-2
  -- powers list, leaving the same zipped pair list as poly1.
  simp [commitTrunc, poly1, poly2]

/-- Concrete instantiation of the parametric collision: a fresh
    free variable `s` standing for the (would-be hidden) trapdoor.
    Witnesses that F6's collision pair is universal over the SRS's
    second component. -/
example (s : Fp) :
    commitTrunc [1, s] poly1 = commitTrunc [1, s] poly2 :=
  commit_collides_any_2power_srs 1 s

/-! ## Sanity / falsifiability

    If we INCREASE the SRS to length 3 (covering the index-2
    coefficient that `poly2` adds), the collision DISAPPEARS:
    poly1 (length 2) and poly2 (length 3) commit to different
    values because `poly2`'s third coefficient now contributes.

    This is the falsifiability witness: the bug is *truly* about
    truncation, not some accidental coincidence on `poly1`/`poly2`. -/
def extendedPowers : List Fp := [1, 17, 290]

example :
    commitTrunc extendedPowers poly1 ≠ commitTrunc extendedPowers poly2 := by
  native_decide

/-- And of course, with the extended SRS, `poly1` no longer collides
    with the *low-index* part of `poly2` either: under a properly
    sized SRS, the binding holds for these two polynomials. -/
example :
    commitTrunc extendedPowers poly1 + (99 : Fp) * 290 =
      commitTrunc extendedPowers poly2 := by
  native_decide

/-! ## Cross-reference

    F6 substantiation lives at the **commitment-binding** layer.
    Companion obstructions for F1 (algebraic-soundness layer):
      - `Audit.PolyCommit.Trace.setup_ne_impl`
      - `Audit.PolyCommit.State.impl_violates_invariant`
      - `Audit.PolyCommit.Refinement.forge_succeeds`

    The two findings are independent:
      * F1 fix (proper pairings) does NOT close F6 — `commit` would
        still truncate.  The parametric theorem
        `commit_collides_any_2power_srs` makes this explicit: the
        collision survives any choice of SRS values, including
        hidden group elements.
      * F6 fix (degree check or extended SRS) does NOT close F1 —
        `s` would still be published in plaintext.  See the
        `extendedPowers` falsifiability witness: extending the SRS
        eliminates F6's collision while leaving F1's algebraic
        invertibility intact (the verify equation continues to use
        `srs.powers[1]` directly).

    This file is therefore the third orthogonal layer of evidence
    against the construction's binding/soundness properties:
      Trace + State + Refinement   →  F1 (three layers)
      Binding (this file)          →  F6 (one layer, distinct
                                          attack vector)
-/

end Audit.PolyCommit.Binding
