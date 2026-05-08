# Each cycle — formalize mode

Your job is to grow a principled formal model of the target. Findings
may emerge from divergences the model exposes, but the model is the
primary deliverable.

Read where you are: `AGENTS.md` (general methodology, including
shared Lean structural rules), `audit.md` (target scope, if present),
`/repo/state/lean/` and `/repo/state/sage/` (cumulative models),
`artifacts/` (this run's scratch). Pick the single highest-leverage
modeling activity given that state. Do it. Return.

## Cycle 1: structure first

If the Lean tree is empty or near-empty (no canonical `Op`, no
top-level theorems, no foundational primitive types), this is a
seeding cycle and its job is **architectural foundation**, not
traces:

- Canonical `Op` family with structured decomposition from the
  start (per-sub-protocol enums under a thin canonical wrapper —
  Worked example 1). Never a flat enum you intend to migrate
  later; that's a path-dependence trap.
- Foundational primitive types in a shared module. Mathlib
  algebraic types (`AddCommGroup`, `Field`, `CommRing`,
  `MeasureTheory.ProbabilityMassFunction`) over wrapped `Nat`
  placeholders.
- Top-level security theorem skeletons (with `sorry`) for the
  construction's published security claims.
- Hardness-assumption axioms with cited paper references.

Trace-writing on a foundation that doesn't exist commits to a
structure later cycles can't support. If the tree IS non-empty,
extend rather than restart — see `AGENTS.md`'s refactor policy.

## What the model contains

A complete model has four layers, and each cycle fills in
something across them:

- **Foundation** — canonical `Op` family, foundational primitive
  types, hardness-assumption axioms with stated content (not bare
  names — see "axiom content" below), top-level security theorems.
- **Trace structure** — parallel `List Op` definitions for spec
  and impl, with quoted-source blocks tying every op to either a
  paper passage (spec) or a `code/<file>:N-M` line range (impl).
- **Reductions** — the proof tree connecting top-level theorems to
  hardness axioms via intermediate lemmas. Each link is itself a
  theorem, possibly with `sorry`. The model is "complete" when
  every `sorry` reduces to a stated axiom or a discharged proof.
- **Auxiliary checks** — Sage scripts validating concrete
  parameters, topic-specific properties not subsumed by the trace
  layer.

**Axiom content matters, not just name.** A bare `axiom foo : Prop`
declares a name without saying what it claims; the trust base is
empty. Every hardness axiom states a claim — typically:

```lean
axiom someAssumption :
    ∀ (params) (adv : Adversary params),
      polyTime adv → adv.advantage ≤ negligible params.λ
```

The exact formulation can be coarse — what matters is that an
attentive reader can disagree with it.

**Modeling shapes.** Six shapes, equal standing. Pick by what the
property looks like, not by the tree's existing shape; multiple
shapes coexist in real targets.

- **Operational sequences** (Worked example 1) — `List Op` +
  `native_decide` equality. Catches ordering / missing-step bugs.
- **Algebraic primitives** — theorems over typed values for fields,
  curves, hash functions, low-level primitives.
- **Game hops** (Worked example 2) — explicit adversary, game
  pairs, advantage bound. Cryptographic security claims.
  Probability requires an actual probability shape (Mathlib's
  `MeasureTheory.ProbabilityMassFunction`) — without one,
  advantage is a placeholder.
- **Refinement** (Worked example 3) — relation
  `R : SpecState → ImplState → Prop` with transition-correspondence
  theorems. Bridges abstract spec to concrete impl.
- **State invariants** (Worked example 4) — `step : State → Op →
  State` + `Inv : State → Prop` + preservation theorem. "X must
  hold before Y" temporal claims.
- **Compositional decomposition** (Worked example 5) — a top-level
  claim split into independent sub-claims, trust base enumerated
  leaf-by-leaf. Distinguishes a real proof tree from axiom soup.

## firstDiff helper

When `native_decide` fails on a sequence equality, this localizes
the first divergence:

```lean
def firstDiff [DecidableEq α] : List α → List α → Option (Nat × Option α × Option α)
  | [], []           => none
  | x :: _, []       => some (0, some x, none)
  | [], y :: _       => some (0, none, some y)
  | x :: xs, y :: ys =>
      if x = y then (firstDiff xs ys).map (fun (i, a, b) => (i+1, a, b))
      else some (0, some x, some y)
```

Then `#eval firstDiff specSeq implSeq` prints the divergence index.

## Worked examples

These are templates. Use generic names that scale to your target's
vocabulary; do not paste them literally.

**Example 1: Typed `Op` with structured decomposition.**

```lean
namespace LayerA
inductive Op where
  | initialize
  | recordValue (label : Label) (value : Value)
  | derive (label : Label) (input : Value)
  deriving DecidableEq, Repr
end LayerA

namespace LayerB
inductive Op where
  | beginRound (n : Nat)
  | check (lhs : Value) (rhs : Value)
  | accept
  deriving DecidableEq, Repr
end LayerB

inductive Op where
  | layerA (op : LayerA.Op)
  | layerB (op : LayerB.Op)
  deriving DecidableEq, Repr

def specProtocol (v0 : Value) : List Op := [
  .layerA .initialize,
  .layerA (.recordValue "input" v0),
  .layerB (.beginRound 1),
  .layerB (.check v0 v0),
  .layerB .accept ]

def implProtocol (v0 : Value) : List Op := [
  .layerA .initialize,
  .layerA (.recordValue "input" v0),
  .layerB (.beginRound 1),
  .layerB (.check v0 v0),
  .layerB .accept ]

theorem protocol_eq (v0) : specProtocol v0 = implProtocol v0 := by
  native_decide

-- Falsifiability check: a reordered impl fails the theorem.
def implReordered (v0 : Value) : List Op := [
  .layerA .initialize,
  .layerB (.beginRound 1),
  .layerA (.recordValue "input" v0),
  .layerB (.check v0 v0),
  .layerB .accept ]

example (v0) : specProtocol v0 ≠ implReordered v0 := by native_decide
```

Catches: ordering, missing-step, swapped-value bugs (typed
parameters surface them). Misses: probabilistic adversarial
behavior.

**Example 2: Game hop with adversary and advantage.**

```lean
structure Scheme where
  param : Nat
  encode : Value → Encoded

structure Adversary where
  guess : Encoded → Bool

def Game0 (S : Scheme) (adv : Adversary) (v : Value) : Bool :=
  adv.guess (S.encode v)

def Game1 (S : Scheme) (adv : Adversary) (e : Encoded) : Bool :=
  adv.guess e

def Advantage (S : Scheme) (adv : Adversary) (v : Value) (e : Encoded) : Real :=
  sorry -- requires probability monad to be meaningful

axiom encoding_security :
  ∀ (S : Scheme) (adv : Adversary) (v : Value) (e : Encoded),
    polyTime adv → Advantage S adv v e ≤ negligible S.param

theorem construction_secure (S : Scheme) (adv : Adversary) (v : Value) (e : Encoded) :
    polyTime adv → constructionAdvantage S adv ≤ negligible S.param := by
  intro h
  exact reductionLemma h (encoding_security S adv v e h)
```

Catches: cryptographic claims with adversary quantification.
Misses: actual probability arithmetic without a probability
framework.

**Example 3: Refinement.**

```lean
structure SpecState where
  recordedInputs : List Value
  accepted : Bool
  deriving DecidableEq, Repr

structure ImplState where
  recordedInputs : List Value
  internalBuffer : List Encoded
  counter : Nat
  accepted : Bool
  deriving DecidableEq, Repr

def Refines (i : ImplState) (s : SpecState) : Prop :=
  i.recordedInputs = s.recordedInputs ∧ i.accepted = s.accepted

def specStep (s : SpecState) (op : Op) : SpecState := sorry
def implStep (i : ImplState) (op : Op) : ImplState := sorry

theorem refinement_preserved (i : ImplState) (s : SpecState) (op : Op) :
    Refines i s → Refines (implStep i op) (specStep s op) := by
  intro h
  cases op
  all_goals (constructor <;> simp_all [specStep, implStep, Refines])
```

Catches: abstract claims inherited by concrete impl. Doesn't
replace: faithful `specStep`/`implStep`.

**Example 4: State-machine invariant.**

```lean
structure State where
  derivedValues : List (Label × Value)
  recordedInputs : List Label
  acceptanceFlag : Bool
  deriving DecidableEq, Repr

def step (s : State) (op : Op) : State := sorry

def DerivationsAreSourced (s : State) : Prop :=
  ∀ label value, (label, value) ∈ s.derivedValues →
    ∃ inputLabel, inputLabel ∈ s.recordedInputs ∧ derivedFrom value inputLabel

theorem inv_preserved (s : State) (op : Op) :
    DerivationsAreSourced s → DerivationsAreSourced (step s op) := by
  intro h label value hmem
  cases op <;> simp [step] at hmem <;> sorry
```

Catches: temporal "X must hold before Y" properties that pure
operational equality can't express.

**Example 5: Compositional decomposition.**

```lean
theorem primitive_binding (S : Scheme) (adv : Adversary) :
    polyTime adv → bindingAdvantage S adv ≤ negligible S.param := by
  exact assumption_A1_reduction adv

theorem primitive_hiding (S : Scheme) (adv : Adversary) :
    polyTime adv → hidingAdvantage S adv ≤ negligible S.param := by
  exact assumption_A2_reduction adv

theorem composition_consistency (S : Scheme) :
    ∀ x y, transformsCorrectly S x y := by
  intro x y; sorry

theorem construction_secure (S : Scheme) (adv : Adversary) :
    polyTime adv → endToEndAdvantage S adv ≤ negligible S.param := by
  intro h
  have hBind := primitive_binding S adv h
  have hHide := primitive_hiding S adv h
  have hComp := composition_consistency S
  exact composition_lemma hBind hHide hComp
```

Catches: structures the proof tree so the trust base is
enumerated leaf-by-leaf, not hidden in one big "compiler theorem"
axiom. Distinguishes a real proof from axiom soup.

Real targets need 3-4 of these in combination — operational
equality at the call-sequence layer, refinement bridging
spec/impl, state invariants for ordering, game hops for security,
decomposition for proof-tree structure.

## Spec independence

The model only catches divergences if **spec and impl come from
independent sources**. Both encoded from reading the same code is
the most common modeling failure — they mirror each other and
`native_decide` succeeds while the bug is real.

- **Find authoritative spec sources first.** Project README, design
  docs, referenced papers (`WebFetch`/`curl`), reference impls in
  other languages, RFCs, IACR ePrint. Modular constructions
  typically cite *multiple* papers: the headline paper for the
  whole construction, plus separate papers for the primitives it
  composes (commitment schemes, sumcheck protocols, hash
  functions, pairing groups). Each describes a different layer's
  guarantees and assumptions; the headline paper says how the
  primitive is used, the primitive's own paper says what it
  guarantees and under what hardness. Consult both. Record what
  you found in `notes.md`.
- **Spec side**: encode from those sources. Above each spec op
  group, paste a `/-! SpecSource -/` block with the literal text.
- **Impl side**: encode from `code/`. Above each impl op group,
  paste a `/- Source -/` block with the literal lines.

Asymmetric rigor — strict on impl, loose on spec — makes the
looser side flex to match. Both sides need the same audit-trail
rigor: a reader should verify either side's faithfulness with the
same mechanical procedure.

**Independence at the definition level, not just the comment
level.** Quoted source blocks above each side aren't enough — the
two `List Op` definitions must differ structurally if there's a
real divergence to surface. A spec defined as `def specSeq := implSeq`,
or by literal copy-paste from the impl, makes the equality theorem
reflexive: `native_decide` cannot discriminate identical values
regardless of how the comments above them are sourced. The test:
imagine flipping a single op in one side. Does the equality
theorem fail? If the two definitions are textually identical, no
flip in one side could ever surface — the theorem is testing
reflexivity, not faithfulness.

## Faithfulness to source

A clean `decide`-equal model that doesn't reflect the impl is
worse than no model. Three habits:

1. **Quote literal source code under each impl op declaration.**
   Not just `code/file:N-M` as a comment — paste the actual lines.
   If pasted statements contradict op order, you've caught a
   modeling error before `decide` would have hidden it.

2. **Preserve iteration structure.** A loop with multi-statement
   body does NOT collapse into a single op. Faithful encodings:
   `xs.flatMap (fun x => [.s1, .s2, .s3])`, explicit fixed-N
   expansion, or a parameterized helper. Single-op collapses
   prevent equality theorems from surfacing in-loop ordering bugs.

3. **One op per source statement** as the default granularity.
   Coarser granularity allowed only with explicit justification
   in `notes.md`. The default makes ordering bugs at any
   granularity surfaceable.

**Reverse audit periodically.** Pick a function in `code/`, walk
it line-by-line, verify every statement has a corresponding op.
Catches omissions (the forward direction never finds them — if
you don't think to model something, you also don't think to
look for it).

## Activities

Activities cluster into four families. Pick by leverage × current
model state. Some activities take a full cycle, some take several
— the menu is not equal-cost and the cheapest options are
systematically over-picked. Invest deliberately.

**Foundation** (cycle 1 + when structural skeleton incomplete):
- `seed` — canonical `Op` family, primitive types, top-level
  theorem skeletons, hardness axioms. Per Cycle 1 above.
- `add-primitive` — new foundational type from Mathlib or
  target-specific.
- `state-theorem` / `state-axiom` / `state-obligation` — write
  the missing target/leaf with `sorry` and a citation.
- `state-reduction` — name an intermediate lemma reducing a
  higher-level `sorry`.

**Faithfulness** (most common ongoing work):
- `expand` — recurse into a sub-protocol's internal operations.
- `anchor-impl` / `anchor-spec` — paste literal source quote
  blocks above an existing op group that lacks them.
- `reverse-audit` — walk a `code/` function line-by-line,
  verifying every statement has a corresponding op.
- `loop-structure` — re-encode a loop body that's collapsed to a
  single op as `xs.flatMap (...)`.
- `add-type` / `add-function` — translate a load-bearing
  structure or procedure into Lean.

**Substance** (high-effort, high-leverage):
- `typed-migrate` — bare → typed constructors. Per `AGENTS.md`'s
  structured-decomposition rule: migration happens IN the
  canonical Op family (per-sub-protocol enums under a thin
  wrapper), never via parallel inductives in topic files.
- `mathlib-upgrade` — replace wrapped-`Nat` placeholders with
  real Mathlib types. Updates every theorem referencing them.
- `paper-pull` — fetch a cited paper, quote the relevant theorem
  statement above the matching Lean declaration as
  `/-! Paper: <citation> -/`. Refine the declaration to match
  what the paper actually says.
- `deep-research` — fetch academic paper(s) for a sub-protocol,
  refine spec-side trace to reflect the paper (not just the
  in-tree summary).
- `state-invariant` — Example 4. "X must hold before Y"
  temporal claims.
- `adversary-game` — Example 2. Cryptographic security with
  adversary quantification.
- `refinement` — Example 3. Bridge spec/impl granularities.
- `decomposition` — Example 5. Replace a monolithic axiom with
  an enumerated proof tree.

**Maintenance**:
- `discharge` — remove a `sorry` by ensuring sequences agree at
  current granularity, or `firstDiff`-localize the divergence.
- `challenge` — try to falsify a passing theorem with a
  hypothetical buggy impl. If you can't, the theorem is
  suspiciously universal.
- `counterexample` — encode a concrete buggy implementation as
  a `List Op` trace, show it fails the equality theorem.
- `refine` — when `firstDiff` reports a divergence, decide if
  it's a real bug, a model imprecision, or an intentional
  implementation choice.
- `sage-param` / `sage-ref` — concrete parameter check or
  reference computation in Sage.

**Postmortem.** When a cycle attempted something high-effort and
backed out (Lean perf wall, structural mismatch), record what
blocked it in `notes.md`. The blocker is the cycle's output;
without that record, the next cycle can't benefit from what you
learned.

## Discipline

- **One activity per cycle.** Focus.
- **Cite `code/<file>:N-M` for every implementation claim.** No
  citations = speculation.
- **Don't model your interpretation.** Model the code's actual
  control flow.
- **Don't prove tautologies.** Every theorem must be falsifiable —
  a plausible alternative impl must be able to break it.
- **Don't hunt for bugs in this mode.** If you discover a
  divergence, record it in `findings.json` and move on; concrete
  repros are hunt-mode work.
- **Don't restart from scratch.** If the tree is non-empty, list
  and read existing files first. Extend, don't replace.
- **Checkpoint substantive work.** `git -C /repo/state add . &&
  git -C /repo/state commit -m "<run-id> cycle <N>: <what>"`.

## Findings from formal work

When the model exposes a divergence:

1. Localize with `firstDiff` or a failing `native_decide`.
2. Determine if it's a real bug or a model gap.
3. Real bug: append to `findings.json` with
   `verification_artifact: state/lean/<path>.lean`. The Lean file
   IS the substantiation.
4. Model gap: refine and retry. Document what was imprecise.

## Quality bar

- **Falsifiability** — every theorem has a hypothetical impl
  change that would break it.
- **Citation density** — every impl entry cites
  `code/<file>:N-M`.
- **Quoted source on both sides** — both `/- Source -/` and
  `/-! SpecSource -/` blocks. Asymmetric rigor hides divergences.
- **Layer coverage with both shapes.** Every protocol layer that
  carries state across operations gets both an operational trace
  (`List Op` with parallel spec/impl) AND a state-machine
  invariant (`step : State → Op → State` with a preservation
  theorem). Operational trace alone catches call-sequence
  divergences; without a state invariant, properties of the form
  "value V functionally depends on prior inputs to its state" are
  unstatable. A layer covered by trace alone produces false
  confidence — the trace agrees, but the *behavioral* property
  the layer is supposed to enforce isn't expressed.
- **Iteration structure preserved** — multi-statement loop bodies
  not collapsed to one op.
- **Ops are typed** — bare constructors only for genuine
  parameter-free markers.
- **Stated goals** — primary security theorems stated.
- **Honest trust base** — hardness assumptions enumerated as
  named axioms with stated content.
- **Progress** — each cycle removes a sorry, states a new
  reduction, expands a sub-protocol, or adds something
  load-bearing.

Stopping is the runner's job.
