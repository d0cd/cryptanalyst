/-
  Operational trace comparing spec vs. impl for the applied-21 KZG-style
  polynomial commitment.

  Per the formalize-mode discipline, the two definitions below MUST be
  structurally independent (not literal copies of each other) so the
  `native_decide` equality theorem is a non-trivial check on
  faithfulness.

  Spec source: Kate-Zaverucha-Goldberg 2010 §3.2-3.3 and Trail of Bits
  Frozen-Heart series 2022.
  Impl source: `code/proof_system.py:74-143`.

  This file's value is: `prove_open_eq_impl` and `verify_eq_impl` should
  FAIL with `native_decide`, and `firstDiff` should localize the
  divergences at exactly the operations identified in
  `artifacts/divergences.md`.

  In a `native_decide`-capable environment, this file produces machine-
  checked obstructions for findings F1, F2, F3, F4. See the comments
  next to each `theorem` block.
-/

import Audit.PolyCommit.Primitives
import Audit.PolyCommit.Ops

namespace Audit.PolyCommit.Trace

open Audit.PolyCommit

/-! ## Spec-side trace: KZG-Open and KZG-Verify per Kate et al. 2010

    These List-of-Op sequences encode what the spec *says* the protocol
    must do.  Each block is preceded by a quoted-source `/-! SpecSource -/`
    block so a reader can independently audit faithfulness.
-/

/-! SpecSource (Kate-Zaverucha-Goldberg 2010, §3.2 "Open"):

    """Open(PK, φ(x)) = (φ(x), open_value).
       CreateWitness(PK, φ(x), i) → (i, φ(i), w_{φ_i})
         where w_{φ_i} = g^{ψ_{φ_i}(α)} ∈ G,
               ψ_{φ_i}(x) = (φ(x) − φ(i)) / (x − i)."""

    Trail of Bits "Frozen Heart" rule (2022):
      "The Fiat-Shamir hash computation must include all public values
       from the zero-knowledge proof statement and all public values
       computed in the proof. A Frozen Heart vulnerability is
       introduced if some of these values are missing."

    Therefore the FS transcript for an evaluation proof must include
    AT LEAST the statement id, the commitment C, the witness π, the
    point z, and the claimed value y. Domain separation is also
    customary.
-/

/-- Spec-side `Open` operation sequence. Note we include `statementId`
    and `claimedValue (y)` in the FS transcript per the Frozen Heart
    rule.  The impl-side trace OMITS these — that's the divergence
    `prove_open_eq_impl` will localize. -/
def specOpen (f : Polynomial) (z y C pi alpha : Fp) (sid : StatementId)
    (divisionAccs : List (Nat × Fp)) : List Op :=
  [ Op.open (.inputPolynomial f),
    Op.open (.inputPoint z),
    Op.open (.inputStatementId sid),
    Op.open (.evalAtPoint y),
    Op.open (.computeCommitment C),
    Op.open (.subtractEvaluation y) ] ++
  -- Synthetic-division loop (one op per coefficient).
  (divisionAccs.map (fun (i, acc) => Op.open (.divisionStep i acc))) ++
  [ Op.open (.computeWitness pi),
    Op.open (.buildTranscript
      [ TranscriptEntry.statementTag sid,
        TranscriptEntry.commitment C,
        TranscriptEntry.witness pi,
        TranscriptEntry.point z,
        TranscriptEntry.claimedValue y ]),
    Op.open (.deriveChallenge alpha),
    Op.open (.emitProof
      { commitment := C, z := z, y := y, pi := pi
      , alpha := alpha, statementId := sid }) ]

/-! SpecSource (Kate-Zaverucha-Goldberg 2010, §3.3 "VerifyEval"):

    """VerifyEval(PK, C, i, φ(i), w_{φ_i}) =
       1   if  e(C, g) = e(w_{φ_i}, g^α / g^i) · e(g, g)^{φ(i)}
       0   otherwise."""

    Equivalently, in additive notation with `[x]_? := x · g_?`:

       Accept iff  e([f(s) − y]_1, [1]_2) = e([q(s)]_1, [s − z]_2).

    For the *non-interactive* version with FS-derived `α`, the verifier
    rebuilds the same transcript the prover used and rejects if the
    challenge mismatches.  AND the FS challenge MUST participate in
    the algebraic check (otherwise it is decorative — divergence D9).

    A standard NIZK-KZG verifier (e.g., a batch-opening variant)
    multiplies the prover's witness by `α` to randomize the check.
    The simplest form that uses `α` non-trivially: verify
       e(C − y · g_1, g_2) = e(π, s · g_2 − z · g_2)  AND
       α = H(statementId, C, π, y, z, …)  matches.
-/

/-- Spec-side `Verify` operation sequence. Includes `bindStatementId`
    AND `useChallengeInCheck`. -/
def specVerify (proof : Proof) (transcriptAlpha lhs rhs : Fp) : List Op :=
  [ Op.verify (.readCommitment proof.commitment),
    Op.verify (.readPoint proof.z),
    Op.verify (.readClaimedValue proof.y),
    Op.verify (.readWitness proof.pi),
    Op.verify (.bindStatementId proof.statementId),
    Op.verify (.rebuildTranscript
      [ TranscriptEntry.statementTag proof.statementId,
        TranscriptEntry.commitment proof.commitment,
        TranscriptEntry.witness proof.pi,
        TranscriptEntry.point proof.z,
        TranscriptEntry.claimedValue proof.y ]),
    Op.verify (.recomputeChallenge transcriptAlpha),
    Op.verify (.checkChallengeMatch proof.alpha transcriptAlpha),
    Op.verify (.useChallengeInCheck transcriptAlpha),
    Op.verify (.computeLhs lhs),
    Op.verify (.computeRhs rhs),
    Op.verify (.finalEquality lhs rhs) ]

/-! ## Impl-side trace: directly mirrors `code/proof_system.py`

    Each impl-side op below cites a specific line range in
    `code/proof_system.py`.
-/

/- Source: `code/proof_system.py:74-114` — the `prove` function:

    def prove(srs: SRS, poly: Polynomial, z: int, statement_id: bytes = b"") -> dict:
        y = poly.evaluate(z)                                 # line 79
        C = commit(srs, poly)                                # line 80
        n = len(poly.coeffs)                                 # line 83
        adjusted = list(poly.coeffs)                         # line 84
        adjusted[0] = (adjusted[0] - y) % P                  # line 85
        q_coeffs = [0] * n                                   # line 87
        remainder = 0                                        # line 88
        for i in range(n - 1, -1, -1):                       # line 89
            val = (adjusted[i] + remainder) % P              # line 90
            if i > 0:                                        # line 91
                q_coeffs[i - 1] = val                        # line 92
            remainder = (val * z) % P                        # line 93
        pi = commit(srs, Polynomial(q_coeffs))               # line 95
        transcript = [
            C.to_bytes(16, "big"),                           # line 100
            pi.to_bytes(16, "big"),                          # line 101
            z.to_bytes(16, "big"),                           # line 102
        ]                                                    # line 103
        alpha = _derive_challenge(transcript)                # line 105
        return { "commitment": C, "z": z, "y": y, "pi": pi,
                 "alpha": alpha, "statement_id": statement_id }  # 107-114
-/

/-- Impl-side `Open` operation sequence — note the absence of
    `inputStatementId` participation in the transcript, and absence
    of `claimedValue (y)` and `statementTag` in the transcript. -/
def implOpen (f : Polynomial) (z y C pi alpha : Fp) (sid : StatementId)
    (divisionAccs : List (Nat × Fp)) : List Op :=
  [ Op.open (.inputPolynomial f),
    Op.open (.inputPoint z),
    Op.open (.inputStatementId sid),
    Op.open (.evalAtPoint y),
    Op.open (.computeCommitment C),
    Op.open (.subtractEvaluation y) ] ++
  (divisionAccs.map (fun (i, acc) => Op.open (.divisionStep i acc))) ++
  [ Op.open (.computeWitness pi),
    Op.open (.buildTranscript
      [ -- *** divergence D8 *** : impl omits statementTag and y
        TranscriptEntry.commitment C,
        TranscriptEntry.witness pi,
        TranscriptEntry.point z ]),
    Op.open (.deriveChallenge alpha),
    Op.open (.emitProof
      { commitment := C, z := z, y := y, pi := pi
      , alpha := alpha, statementId := sid }) ]

/- Source: `code/proof_system.py:117-143` — the `verify` function:

    def verify(srs: SRS, proof: dict) -> bool:
        C = proof["commitment"]                              # 123
        z = proof["z"]                                       # 124
        y = proof["y"]                                       # 125
        pi = proof["pi"]                                     # 126
        transcript = [
            C.to_bytes(16, "big"),                           # 130
            pi.to_bytes(16, "big"),                          # 131
            z.to_bytes(16, "big"),                           # 132
        ]                                                    # 133
        alpha = _derive_challenge(transcript)                # 135
        if alpha != proof["alpha"]:                          # 136
            return False                                     # 137
        lhs = (C - y * srs.powers[0]) % P                    # 141
        rhs = (pi * (srs.powers[1] - z * srs.powers[0])) % P # 142
        return lhs == rhs                                    # 143
-/

/-- Impl-side `Verify` operation sequence. Note the absence of
    `bindStatementId` and `useChallengeInCheck` — those are the spec
    steps that the impl OMITS (divergences D9, D10). -/
def implVerify (proof : Proof) (transcriptAlpha lhs rhs : Fp) : List Op :=
  [ Op.verify (.readCommitment proof.commitment),
    Op.verify (.readPoint proof.z),
    Op.verify (.readClaimedValue proof.y),
    Op.verify (.readWitness proof.pi),
    Op.verify (.rebuildTranscript
      [ TranscriptEntry.commitment proof.commitment,
        TranscriptEntry.witness proof.pi,
        TranscriptEntry.point proof.z ]),
    Op.verify (.recomputeChallenge transcriptAlpha),
    Op.verify (.checkChallengeMatch proof.alpha transcriptAlpha),
    -- *** divergence D9 *** : no `useChallengeInCheck` here
    Op.verify (.computeLhs lhs),
    Op.verify (.computeRhs rhs),
    Op.verify (.finalEquality lhs rhs) ]

/-! ## Equality / inequality theorems — machine-checked obstructions

    Per the formalize-mode bar (CLAUDE.md "machine-checked Lean / Sage
    obstruction"), the substantiation for a finding is a Lean
    theorem whose proof either (a) closes by `native_decide` and
    asserts the divergence as a positive inequality, or (b) tries
    `spec = impl := by native_decide` and fails at a localizable
    op.  We use shape (a) below: prove `spec ≠ impl` directly.  This
    has the advantage that the file *builds*, so the verification
    artifact is a successfully-built file rather than an error log.

    The companion `#eval firstDiff` blocks print the divergence
    index for each obstruction so a reader can confirm WHERE the
    spec and impl disagree, not merely THAT they do.
-/

-- A representative single-coefficient division accumulator stream;
-- we don't need realistic numerics for the trace-equality check —
-- we only need the structure.  The integers are placeholders.
def repDivAccs : List (Nat × Fp) := [(2, 0), (1, 0), (0, 0)]

def repPoly  : Polynomial  := { coeffs := [5, 2, 3] }
def repSid   : StatementId := []
def repZ     : Fp := 7
def repY     : Fp := 5 + 2*7 + 3*7*7  -- = 5 + 14 + 147 = 166
def repC     : Fp := 0  -- placeholder
def repPi    : Fp := 0  -- placeholder
def repAlpha : Fp := 0  -- placeholder
def repLhs   : Fp := 0
def repRhs   : Fp := 0
def repProof : Proof :=
  { commitment := repC, z := repZ, y := repY, pi := repPi
  , alpha := repAlpha, statementId := repSid }

/-! ### F2 — Frozen-heart obstruction at the prover side.

    Spec includes `statementTag` and `claimedValue (y)` in the
    transcript; impl does not.  The two `List Op`s differ at the
    `buildTranscript` constructor (different argument lists).
    `native_decide` evaluates the inequality of two ground terms.
-/

/-- Spec ≠ impl on the `prove` operation sequence — this is finding
    F2 (Frozen Heart on `y` and `statement_id`) made machine-
    checkable.  The divergence is at the `buildTranscript` op. -/
theorem prove_open_ne_impl :
    specOpen repPoly repZ repY repC repPi repAlpha repSid repDivAccs
      ≠ implOpen repPoly repZ repY repC repPi repAlpha repSid repDivAccs := by
  native_decide

/-- Diagnostic: print where the spec and impl traces first
    diverge on the `prove` sequence.  Expected output points at
    the `buildTranscript` op (index = 6 + |repDivAccs| = 9). -/
#eval firstDiff
  (specOpen repPoly repZ repY repC repPi repAlpha repSid repDivAccs)
  (implOpen repPoly repZ repY repC repPi repAlpha repSid repDivAccs)

/-! ### F3 + F4 — Decorative challenge + statement-id rebinding
        at the verifier side.

    Spec has `bindStatementId` and `useChallengeInCheck`; impl has
    neither.  Same shape: ground-term inequality.
-/

/-- Spec ≠ impl on the `verify` operation sequence — substantiates
    findings F3 (decorative α) and F4 (statement_id rebinding).
    The first divergence is at the `bindStatementId` op (an op
    present in spec, absent in impl).  After that op the streams
    re-align until the spec's `useChallengeInCheck` op, which is
    also absent in impl. -/
theorem verify_ne_impl :
    specVerify repProof repAlpha repLhs repRhs
      ≠ implVerify repProof repAlpha repLhs repRhs := by
  native_decide

/-- Diagnostic: print the first-divergence index on the verify
    sequence.  Expected output points at index 4 (`bindStatementId`
    is the 5th spec op, the 5th impl op is `rebuildTranscript`). -/
#eval firstDiff
  (specVerify repProof repAlpha repLhs repRhs)
  (implVerify repProof repAlpha repLhs repRhs)

/-! ## Falsifiability check — a buggy spec that disagrees with itself

    Per the formalize-mode discipline, every equality theorem must
    be falsifiable.  Below we encode an *intentionally* reordered
    impl that flips transcript entries; this confirms that the
    equality of two structurally-different `List Op`s is NOT
    automatically true (otherwise our obstruction theorems above
    would prove something vacuous).
-/

def implOpenSwapped (f : Polynomial) (z y C pi alpha : Fp) (sid : StatementId)
    (divisionAccs : List (Nat × Fp)) : List Op :=
  [ Op.open (.inputPolynomial f),
    Op.open (.inputPoint z),
    Op.open (.inputStatementId sid),
    Op.open (.evalAtPoint y),
    Op.open (.computeCommitment C),
    Op.open (.subtractEvaluation y) ] ++
  (divisionAccs.map (fun (i, acc) => Op.open (.divisionStep i acc))) ++
  [ Op.open (.computeWitness pi),
    Op.open (.buildTranscript
      [ TranscriptEntry.point z,        -- swapped
        TranscriptEntry.commitment C,   -- swapped
        TranscriptEntry.witness pi ]),
    Op.open (.deriveChallenge alpha),
    Op.open (.emitProof
      { commitment := C, z := z, y := y, pi := pi
      , alpha := alpha, statementId := sid }) ]

/-- Sanity / falsifiability check: a reordered impl is not equal
    to the impl.  Confirms `≠` between two `List Op`s with
    structurally different `buildTranscript` arguments is decided
    by `native_decide`, not vacuously true. -/
example :
    implOpen      repPoly repZ repY repC repPi repAlpha repSid repDivAccs
      ≠ implOpenSwapped repPoly repZ repY repC repPi repAlpha repSid repDivAccs := by
  native_decide

/-! ### Independence check.

    The model is only meaningful if `specOpen` and `implOpen` are
    structurally distinct definitions, not literal copies.

    On the prove side both sequences have the SAME length (13 ops):
    the divergence is at element index 9, the `buildTranscript` op,
    where spec carries 5 entries and impl carries 3.  We assert
    length-equality on prove to make explicit that the obstruction
    is content, not length:
-/
example :
    (specOpen repPoly repZ repY repC repPi repAlpha repSid repDivAccs).length =
    (implOpen repPoly repZ repY repC repPi repAlpha repSid repDivAccs).length := by
  native_decide

/-- On the verify side spec and impl differ in LENGTH: spec has
    `bindStatementId` and `useChallengeInCheck` ops absent from
    impl.  That alone would suffice to refute equality, even if
    every shared op were structurally identical. -/
example :
    (specVerify repProof repAlpha repLhs repRhs).length ≠
    (implVerify repProof repAlpha repLhs repRhs).length := by
  native_decide

/-! ## F1 — Trapdoor exposed in SRS: setup-layer trace

    Cycle 3 promotes finding F1 from a `PO-1: VIOLATED` comment in
    `Security.lean` to a machine-checked operational obstruction at
    the `Setup` layer.  The prior cycles substantiated F2/F3/F4 with
    `prove_open_ne_impl` / `verify_ne_impl`; F1 was the remaining
    finding without a `native_decide`-discharged inequality.

    SpecSource (Kate-Zaverucha-Goldberg 2010, §3.1 "KeyGen"):

      """KeyGen(1^κ, t):
         • α  ← Z*_p uniformly at random.                   -- S0.1
         • Compute (g, g^α, g^{α^2}, …, g^{α^t}) ∈ G_1^{t+1}
                                                            -- S0.2
         • Compute (h, h^α) ∈ G_2^2.                        -- S0.2'
         • Output PK = ⟨G_1, G_2, e, g, h, g^{α^i}, h, h^α⟩.
                                                            -- S0.3
         • α is destroyed."                                 -- S0.4

    The two adversarial protections the spec demands:
      (A) The SRS publishes ONLY group elements; `α` and `α^i`
          themselves never appear in the clear.  This is the
          t-SDH/t-power-DLOG hiding.  Modeled as the spec-side
          `encodeInGroup i` op nested inside the loop body.
      (B) `α` is ephemeral: destroyed after PK is built so even
          the party that ran KeyGen cannot reuse it.  Modeled as
          the spec-side `destroyTrapdoor` op at the end.

    Both protections are absent in `code/proof_system.py:22-29`,
    yielding the trapdoor-exposed verification of finding F1.

    What this obstruction does NOT capture: divergence D1 (the
    impl uses a hardcoded `_SETUP_SECRET` instead of sampling `α`
    uniformly).  D1 is a value-flow / source-of-randomness
    property, not an operational-sequence property — modeling it
    requires a state-invariant or refinement layer (future cycle).
    Per AGENTS.md, "every theorem must be falsifiable — a
    plausible alternative impl must be able to break it"; the
    obstruction below is falsifiable on the operational layer for
    the structural omissions, which is what the layer is for.
-/

/-- A short stream of `(i, sPow)` pairs driving the loop body of
    `trusted_setup`.  The structural inequality theorem doesn't
    depend on `sPow` matching the real powers of `_SETUP_SECRET`
    — the obstruction is the loop's *body shape* (1 op vs 2 ops
    per iteration) and the missing `destroyTrapdoor`.  Degree-3
    suffices for `native_decide` to discriminate; we use small
    distinct values so `firstDiff` output is human-readable. -/
def repSetupStream : List (Nat × Fp) :=
  [(0, 1), (1, 17), (2, 289), (3, 4913)]

/- Source: `code/proof_system.py:12, 22-29` — module-level constant
   and `trusted_setup`:

    _SETUP_SECRET = 0x5A3B7C9E1F4D2A6B8C0E7F3D5A1B9C4E         -- 12

    def trusted_setup(max_degree: int = SRS_MAX_DEGREE) -> SRS:  -- 22
        powers = []                                              -- 24
        s_pow = 1                                                -- 25
        for _ in range(max_degree + 1):                          -- 26
            powers.append(s_pow)                                 -- 27
            s_pow = (s_pow * _SETUP_SECRET) % P                  -- 28
        return SRS(powers=powers)                                -- 29
-/

/-- Spec-side `Setup` operation sequence.  Per Kate et al. 2010
    §3.1: `drawSecret`, then for each `i ∈ {0..d}` BOTH
    `recordPower i sPow` AND `encodeInGroup i`, then
    `destroyTrapdoor`.  The loop body is two ops; we use explicit
    fixed-N expansion to preserve iteration structure (per
    formalize.md, "Preserve iteration structure"). -/
def specSetup (s : Fp) : List Op :=
  [ Op.setup (.drawSecret s),
    -- iteration i = 0
    Op.setup (.recordPower 0 1),
    Op.setup (.encodeInGroup 0),
    -- iteration i = 1
    Op.setup (.recordPower 1 17),
    Op.setup (.encodeInGroup 1),
    -- iteration i = 2
    Op.setup (.recordPower 2 289),
    Op.setup (.encodeInGroup 2),
    -- iteration i = 3
    Op.setup (.recordPower 3 4913),
    Op.setup (.encodeInGroup 3),
    -- post-loop
    Op.setup .destroyTrapdoor ]

/-- Impl-side `Setup` operation sequence.  Loop body is ONE op:
    `recordPower`.  No `encodeInGroup` (the SRS is `List Fp` not
    `List G_1`); no `destroyTrapdoor` (the secret is a
    module-level constant that lives forever). -/
def implSetup (s : Fp) : List Op :=
  [ Op.setup (.drawSecret s),
    -- iteration i = 0
    Op.setup (.recordPower 0 1),
    -- iteration i = 1
    Op.setup (.recordPower 1 17),
    -- iteration i = 2
    Op.setup (.recordPower 2 289),
    -- iteration i = 3
    Op.setup (.recordPower 3 4913) ]

/-- F1 obstruction: spec ≠ impl on the `Setup` operation
    sequence.  Spec doubles each loop iteration with
    `encodeInGroup` and adds a final `destroyTrapdoor`; impl
    has neither.  Substantiates D2/D3/D4 (the omitted-op
    components of finding F1) at the operational layer. -/
theorem setup_ne_impl :
    specSetup 17 ≠ implSetup 17 := by
  native_decide

/-- Diagnostic: print the first divergence between spec-side and
    impl-side setup sequences.  Expected output points at index 2
    — the spec's `encodeInGroup 0` op, which on the impl side
    is replaced by the next iteration's `recordPower 1 17`. -/
#eval firstDiff (specSetup 17) (implSetup 17)

/-- Length-inequality sanity.  Spec has 1 + 2·4 + 1 = 10 ops; impl
    has 1 + 4 = 5 ops.  Length asymmetry alone refutes equality;
    we additionally have content asymmetry, captured by
    `setup_ne_impl` above. -/
example :
    (specSetup 17).length ≠ (implSetup 17).length := by
  native_decide

/-! ### Falsifiability check for `setup_ne_impl`.

    A hypothetical "fixed" impl that DID include the missing
    `encodeInGroup` ops in the loop body and the trailing
    `destroyTrapdoor` would equal the spec.  Confirms our
    obstruction is content-driven, not vacuous: a different impl
    written against the spec faithfully would close the
    inequality.
-/
def fixedImplSetup (s : Fp) : List Op :=
  [ Op.setup (.drawSecret s),
    Op.setup (.recordPower 0 1),
    Op.setup (.encodeInGroup 0),
    Op.setup (.recordPower 1 17),
    Op.setup (.encodeInGroup 1),
    Op.setup (.recordPower 2 289),
    Op.setup (.encodeInGroup 2),
    Op.setup (.recordPower 3 4913),
    Op.setup (.encodeInGroup 3),
    Op.setup .destroyTrapdoor ]

example : specSetup 17 = fixedImplSetup 17 := by native_decide

/-- Second falsifiability witness: a "broken-in-a-different-way"
    impl that omits ONLY `destroyTrapdoor` (but does encode in a
    group) is still ≠ spec.  Distinguishes the two structural
    omissions; either alone falsifies the spec. -/
def implSetupHidingButNotDestroying (s : Fp) : List Op :=
  [ Op.setup (.drawSecret s),
    Op.setup (.recordPower 0 1),
    Op.setup (.encodeInGroup 0),
    Op.setup (.recordPower 1 17),
    Op.setup (.encodeInGroup 1),
    Op.setup (.recordPower 2 289),
    Op.setup (.encodeInGroup 2),
    Op.setup (.recordPower 3 4913),
    Op.setup (.encodeInGroup 3) ]

example :
    specSetup 17 ≠ implSetupHidingButNotDestroying 17 := by
  native_decide

end Audit.PolyCommit.Trace
