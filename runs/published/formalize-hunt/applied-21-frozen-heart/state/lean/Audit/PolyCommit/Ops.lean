/-
  Canonical Op family for the applied-21 polynomial-commitment audit.

  Per the formalize-mode discipline (CLAUDE.md "structural principle:
  one canonical Op family"), we decompose by sub-protocol into
  per-layer enums and wrap them under a thin canonical `Op`. This
  scales as later cycles add layers (e.g. multi-point opening, batch
  verification) without re-doing the central enum.

  Three layers in this construction:
    - Setup       : produce the SRS
    - Open        : prover-side commit + witness construction
    - Verify      : verifier-side recompute + algebraic check

  And one cross-cutting layer:
    - Transcript  : Fiat-Shamir transcript ops (used by both Open and
                    Verify, and the layer where the Frozen Heart bug
                    lives)

  Source: `code/proof_system.py` end-to-end.
-/

import Audit.PolyCommit.Primitives

namespace Audit.PolyCommit

/-- Setup-layer ops. Spec (S0) and impl (`code/proof_system.py:22-29`). -/
inductive SetupOp where
  /-- Sample (or, in the impl, retrieve) the trapdoor `s ∈ Fp`. -/
  | drawSecret (s : Fp)
  /-- Compute the next power `s^(i+1)` from the previous accumulator.
      Loop body of `code/proof_system.py:24-28`. -/
  | recordPower (i : Nat) (sPow : Fp)
  /-- Encode `s^i` in a hiding group — present in spec, ABSENT in impl
      (no `G_1` / `G_2`, see divergence D2/D3). Listed so spec-side
      traces can include it where the impl-side has nothing. -/
  | encodeInGroup (i : Nat)
  /-- Destroy `s` (spec S0.5). ABSENT in impl. -/
  | destroyTrapdoor
  deriving DecidableEq, Repr

/-- Transcript-layer ops. The Fiat-Shamir transcript is the heart of
    the Frozen-Heart bug class. `_derive_challenge` =
    `code/proof_system.py:61-71`. -/
inductive TranscriptOp where
  /-- Initialize an empty SHA-256 state. `code/proof_system.py:68`. -/
  | init
  /-- Absorb one transcript entry. `code/proof_system.py:69-70`. -/
  | absorb (entry : TranscriptEntry)
  /-- Squeeze the digest and reduce mod P. `code/proof_system.py:71`. -/
  | squeezeChallenge
  deriving DecidableEq, Repr

/-- Open-layer ops (the prover). Spec S1+S2; impl `prove`,
    `code/proof_system.py:74-114`. -/
inductive OpenOp where
  /-- Receive the polynomial `f`. (Argument to `prove`.) -/
  | inputPolynomial (f : Polynomial)
  /-- Receive the evaluation point `z`. -/
  | inputPoint (z : Fp)
  /-- Receive the statement id (argument; the impl threads it through
      but never uses it in any computation that the verifier checks —
      see divergence D10). -/
  | inputStatementId (sid : StatementId)
  /-- Compute `y = f(z)`.  `code/proof_system.py:79`. -/
  | evalAtPoint (y : Fp)
  /-- Compute the commitment `C = commit(srs, f) = f(s) ∈ Fp`. The
      spec-side variant lives in a group; the impl-side variant lives
      in the field (D5). `code/proof_system.py:80`. -/
  | computeCommitment (C : Fp)
  /-- Subtract `y` from constant term so `(f − y)` has root at `z`.
      Synthetic-division setup. `code/proof_system.py:84-85`. -/
  | subtractEvaluation (y : Fp)
  /-- Synthetic-division step at coefficient index `i` with running
      accumulator value `acc`. The `i`-th iteration of
      `code/proof_system.py:89-93`. -/
  | divisionStep (i : Nat) (acc : Fp)
  /-- Commit to the quotient polynomial: `π = q(s) ∈ Fp`.
      `code/proof_system.py:95`. -/
  | computeWitness (pi : Fp)
  /-- Build the FS transcript (sub-list of `TranscriptOp`s).
      `code/proof_system.py:99-103`. -/
  | buildTranscript (entries : List TranscriptEntry)
  /-- Squeeze the FS challenge.  `code/proof_system.py:105`. -/
  | deriveChallenge (alpha : Fp)
  /-- Emit the proof package. `code/proof_system.py:107-114`. -/
  | emitProof (proof : Proof)
  deriving DecidableEq, Repr

/-- Verify-layer ops. Spec S3; impl `verify`,
    `code/proof_system.py:117-143`. -/
inductive VerifyOp where
  /-- Read field `commitment` from the proof.
      `code/proof_system.py:123`. -/
  | readCommitment (C : Fp)
  /-- Read `z` from the proof. `code/proof_system.py:124`. -/
  | readPoint (z : Fp)
  /-- Read `y` from the proof. `code/proof_system.py:125`. -/
  | readClaimedValue (y : Fp)
  /-- Read `pi` from the proof. `code/proof_system.py:126`. -/
  | readWitness (pi : Fp)
  /-- Build the FS transcript for verifier-side recomputation.
      `code/proof_system.py:129-133`. -/
  | rebuildTranscript (entries : List TranscriptEntry)
  /-- Squeeze the recomputed challenge `α'`.
      `code/proof_system.py:135`. -/
  | recomputeChallenge (alpha : Fp)
  /-- Reject unless `α' == proof.alpha`.
      `code/proof_system.py:136-137`. -/
  | checkChallengeMatch (claimed expected : Fp)
  /-- Compute the LHS of the algebraic check.
      `code/proof_system.py:141`. -/
  | computeLhs (lhs : Fp)
  /-- Compute the RHS of the algebraic check.
      `code/proof_system.py:142`. -/
  | computeRhs (rhs : Fp)
  /-- Final equality check; output the boolean accept decision.
      `code/proof_system.py:143`. -/
  | finalEquality (lhs rhs : Fp)
  /-- A spec-side step that the impl OMITS: bind `statementId` into
      the verifier's transcript, or independently compare the proof's
      `statement_id` against an expected statement. ABSENT in impl —
      see divergence D10. -/
  | bindStatementId (sid : StatementId)
  /-- A spec-side step that the impl OMITS: use the FS challenge `α`
      in the algebraic check (e.g., as a batching scalar). ABSENT in
      impl — see divergence D9. -/
  | useChallengeInCheck (alpha : Fp)
  deriving DecidableEq, Repr

/-- Canonical Op type — thin wrapper layered over the per-sub-protocol
    enums. Per the structural principle, this is the ONE canonical
    `Op` family for this audit; later cycles extend the per-layer
    enums (or add a new layer constructor here) rather than introduce
    parallel `Op` types in topic files. -/
inductive Op where
  | setup     (op : SetupOp)
  | transcript (op : TranscriptOp)
  | open      (op : OpenOp)
  | verify    (op : VerifyOp)
  deriving DecidableEq, Repr

/-- `firstDiff` helper for localizing divergences when `native_decide`
    on `specSeq = implSeq` fails. Per AGENTS.md / formalize.md. -/
def firstDiff [DecidableEq α] : List α → List α → Option (Nat × Option α × Option α)
  | [], []           => none
  | x :: _, []       => some (0, some x, none)
  | [], y :: _       => some (0, none, some y)
  | x :: xs, y :: ys =>
      if x = y then (firstDiff xs ys).map (fun (i, a, b) => (i+1, a, b))
      else some (0, some x, some y)

end Audit.PolyCommit
