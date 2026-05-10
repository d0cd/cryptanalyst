# Each cycle — formalize mode

Your job is to grow a principled formal model of the target. Findings may
emerge from divergences the model exposes, but the model is the primary
deliverable.

Read where you are: `AGENTS.md` (general methodology), `audit.md` (target
scope, if present), `/repo/state/{lean,sage,coq}/` (cumulative model),
`artifacts/` (this run's scratch). Pick the single highest-leverage activity
given that state. Do it. Return.

For modeling templates and worked examples, see
`/opt/skills/lean-modeling/SKILL.md`.

## What the model contains

A complete model has these layers; each cycle fills in something across them:

- **Foundation** — canonical `Op` family, foundational primitive types,
  hardness-assumption axioms with stated content (not bare names — see
  "axiom content" below), top-level security theorems.
- **Trace structure** — parallel `List Op` definitions for spec and impl,
  with quoted-source blocks tying every op to either a paper passage (spec)
  or a `code/<file>:N-M` line range (impl).
- **Reductions** — the proof tree connecting top-level theorems to hardness
  axioms via intermediate lemmas. The model is "complete" when every `sorry`
  reduces to a stated axiom or a discharged proof.
- **Auxiliary checks** — Sage scripts validating concrete parameters or
  computing reference outputs; Coq+FCF scripts proving game-based reductions.
  Lean axioms cite these via `SageReference:` and `CoqReference:`.

**Axiom content matters, not just name.** A bare `axiom foo : Prop` declares
a name without saying what it claims; the trust base is empty. Every axiom
states a claim — typically:

```lean
axiom someAssumption :
    ∀ (params) (adv : Adversary params),
      polyTime adv → adv.advantage ≤ negligible params.λ
```

The exact formulation can be coarse — what matters is that an attentive
reader can disagree with it.

## Tool selection — Lean / Sage / Coq

Three modeling tools. **Pick by what the property looks like, not by a
default.**

| Tool | Best for | Use when the property is | Output lives in |
|---|---|---|---|
| **Lean + Mathlib** | Protocol logic, type-level invariants, structural theorems | Algorithmic / control-flow / typed-data — operational traces, state-machine invariants, structural reductions, the spine of the proof tree | `state/lean/` |
| **Sage** | Concrete numerics, parameter validity | A numerical fact about specific shipped values — a curve's prime-order subgroup, reference computation on adversarial inputs, parameters satisfying an assumption's preconditions | `state/sage/` |
| **Coq + FCF** | Probabilistic game-based reasoning | A game-hop reduction, advantage bound, probabilistic security claim — anything shaped like `\| Pr[Game1] − Pr[Game0] \| ≤ ε` | `state/coq/` |

These are **complementary**, not a hierarchy of fallbacks. FCF's monadic
`Comp` and game-hop tactics encode probabilistic-security proofs natively;
that's the right shape for an advantage definition, not a fallback when Lean
fails. Mathlib's `MeasureTheory.PMF` is the right fit for distribution-
arithmetic at the algebraic level (e.g. Schwartz-Zippel mass bounds), but
not for game-hop reductions — those go to FCF.

**Lean is the spine.** Top-level security theorems are Lean theorems; the
trust base lives there. Sage and Coq produce specialized artifacts that Lean
cites — never duplicate the same property in two tools. If a Sage script
certifies a parameter, the Lean axiom cites it via `SageReference:` rather
than restating the numerical content. Same for `CoqReference:`.

A `VACUOUS-PLACEHOLDER` axiom is a "named but not yet substantiated" marker.
It can be discharged by any of the three tools depending on the property's
shape: `mathlib-upgrade` when Lean has the machinery, `sage-param`/`sage-ref`
when concrete-numerical, `coq-fcf` when probabilistic-game-based.

## Cycle 1: structure first

If the Lean tree is empty or near-empty (no canonical `Op`, no top-level
theorems, no foundational primitive types), this is a **seeding cycle** and
its job is architectural foundation, not traces:

- Canonical `Op` family with structured decomposition from the start (per-
  sub-protocol enums under a thin canonical wrapper — see
  `/opt/skills/lean-modeling/SKILL.md`). Never a flat enum you intend to
  migrate later; that's a path-dependence trap.
- Foundational primitive types in a shared module. Mathlib algebraic types
  (`AddCommGroup`, `Field`, `CommRing`, `MeasureTheory.PMF`) over wrapped
  `Nat` placeholders.
- Top-level security theorem skeletons (with `sorry`) for the construction's
  published security claims.
- Hardness-assumption axioms with cited paper references.

If the tree IS non-empty, extend rather than restart — see `AGENTS.md`'s
refactor policy.

## Activities

Pick by leverage × current model state. The menu is not equal-cost; the
cheapest options are systematically over-picked. Invest deliberately. Each
activity declares the tool it produces in.

**Foundation** (cycle 1 + when structural skeleton incomplete):
- `seed` (Lean) — canonical `Op` family, primitive types, top-level theorem
  skeletons, hardness axioms.
- `add-primitive` (Lean) — new foundational type from Mathlib or
  target-specific.
- `state-theorem` / `state-axiom` / `state-obligation` (Lean) — write the
  missing target/leaf with `sorry` and a citation.
- `state-reduction` (Lean) — name an intermediate lemma reducing a higher-
  level `sorry`.

**Faithfulness** (most common ongoing work):
- `expand` (Lean) — recurse into a sub-protocol's internal operations.
- `anchor-impl` / `anchor-spec` (Lean) — paste literal source quote blocks
  above an existing op group that lacks them.
- `reverse-audit` (Lean) — walk a `code/` function line-by-line, verifying
  every statement has a corresponding op.
- `loop-structure` (Lean) — re-encode a loop body that's collapsed to a
  single op as `xs.flatMap (...)`.
- `add-type` / `add-function` (Lean) — translate a load-bearing structure
  or procedure into Lean.

**Substance** (high-effort, high-leverage):
- `typed-migrate` (Lean) — bare → typed constructors. Migration happens IN
  the canonical Op family, never via parallel inductives in topic files.
- `mathlib-upgrade` (Lean) — replace wrapped-`Nat` placeholders with real
  Mathlib types. Updates every theorem referencing them. Discharges
  `VACUOUS-PLACEHOLDER` axes when Mathlib has the machinery.
- `paper-pull` (Lean) — fetch a cited paper, quote the relevant theorem
  statement above the matching Lean declaration as
  `/-! Paper: <citation> -/`. Refine the declaration to match the paper.
- `axiom-cite` (Lean) — add a `SpecSource:` block to an existing axiom
  citing the paper or specification that justifies its body. Discharges
  `VACUOUS-PLACEHOLDER` axes by external-reference.
- `deep-research` (Lean) — fetch academic paper(s) for a sub-protocol,
  refine spec-side trace to reflect the paper.
- `state-invariant` (Lean) — Template 4 in `lean-modeling` skill. "X must
  hold before Y" temporal claims.
- `adversary-game` (Lean) — Template 2. Cryptographic security with
  adversary quantification at the structural level. For probability
  arithmetic, see `coq-fcf`.
- `refinement` (Lean) — Template 3. Bridge spec/impl granularities.
- `decomposition` (Lean) — Template 5. Replace a monolithic axiom with an
  enumerated proof tree.
- `sage-param` (Sage) — write a Sage script certifying parameter validity,
  cite from a Lean axiom via `SageReference:`. Discharges
  `VACUOUS-PLACEHOLDER` when the property is concrete-numerical.
- `sage-ref` (Sage) — compute a reference output in Sage on adversarial
  test vectors; impl-vs-Sage equality is real evidence, disagreement is a
  finding.
- `coq-fcf` (Coq) — write an advantage definition, game-hop reduction, or
  probabilistic security claim. Cite from a Lean axiom via
  `CoqReference: state/coq/<file>.v`. See `/opt/skills/coq/SKILL.md` for
  the FCF skeleton. Discharges `VACUOUS-PLACEHOLDER` when the property is
  probabilistic-game-based.

**Maintenance**:
- `discharge` (Lean) — remove a `sorry` by ensuring sequences agree at
  current granularity, or `firstDiff`-localize the divergence (helper in
  `lean-modeling` skill).
- `challenge` (Lean) — try to falsify a passing theorem with a hypothetical
  buggy impl. If you can't, the theorem is suspiciously universal.
- `counterexample` (Lean) — encode a concrete buggy implementation as a
  `List Op` trace, show it fails the equality theorem.
- `refine` (Lean) — when `firstDiff` reports a divergence, decide if it's a
  real bug, a model imprecision, or an intentional implementation choice.

**Postmortem.** When a cycle attempted something high-effort and backed out
(Lean perf wall, FCF version mismatch, structural mismatch), record what
blocked it in `notes.md`. The blocker IS the cycle's output; without that
record, the next cycle can't benefit.

## Spec independence

The model only catches divergences if **spec and impl come from independent
sources**. Both encoded from reading the same code is the most common
modeling failure — they mirror each other and `native_decide` succeeds while
the bug is real.

- **Find authoritative spec sources first.** Project README, design docs,
  referenced papers (`WebFetch`/`curl`), reference impls in other languages,
  RFCs, IACR ePrint. Modular constructions cite multiple papers: a headline
  paper plus separate papers for the primitives it composes. The headline
  paper says how the primitive is used; the primitive's own paper says what
  it guarantees and under what hardness. Consult both. Record what you
  found in `notes.md`.
- **Spec side**: encode from those sources. Above each spec op group, paste
  a `/-! SpecSource -/` block with the literal text.
- **Impl side**: encode from `code/`. Above each impl op group, paste a
  `/- Source -/` block with the literal lines.

Asymmetric rigor — strict on impl, loose on spec — makes the looser side
flex to match. Both sides need the same audit-trail rigor.

**Independence at the definition level, not just the comment level.** Quoted
source blocks above each side aren't enough — the two `List Op` definitions
must differ structurally if there's a real divergence to surface. A spec
defined as `def specSeq := implSeq` makes the equality theorem reflexive:
`native_decide` cannot discriminate identical values. The test: imagine
flipping one op in one side. If the two are textually identical, no flip
could surface — the theorem is testing reflexivity, not faithfulness.

## Faithfulness to source

A clean `decide`-equal model that doesn't reflect the impl is worse than no
model. Three habits:

1. **Quote literal source code under each impl op declaration.** Not just
   `code/file:N-M` as a comment — paste the actual lines. If pasted
   statements contradict op order, you've caught a modeling error before
   `decide` would have hidden it.
2. **Preserve iteration structure.** A loop with a multi-statement body
   does NOT collapse into a single op. Faithful encodings:
   `xs.flatMap (fun x => [.s1, .s2, .s3])`, explicit fixed-N expansion, or
   a parameterized helper.
3. **One op per source statement** as the default granularity. Coarser
   allowed only with explicit justification in `notes.md`.

**Reverse audit periodically.** Pick a function in `code/`, walk it line-
by-line, verify every statement has a corresponding op. Catches omissions
the forward direction never finds.

## Primitive coverage and trust-base completeness

The model is incomplete if its load-bearing primitives are only named in
axiom statements. A `VACUOUS-PLACEHOLDER` axiom is sound IF the assumption
holds; without a concrete check confirming the parameters satisfy the
assumption's preconditions, the model has a hidden gap.

Coverage of an axiom means at least one of:

(a) **Lean reduction** — the axiom is derived from Mathlib (or another
    library) facts rather than assumed. `mathlib-upgrade` activity.
(b) **Sage parameter check** — a Sage script certifies the actual values
    shipped with the target satisfy the assumption's preconditions, cited
    via `SageReference:`. `sage-param` activity.
(c) **Coq+FCF reduction** — for probabilistic-game claims, a Coq theorem
    cited via `CoqReference:` reduces the advantage to a hardness assumption
    with explicit game-hop arithmetic. `coq-fcf` activity.
(d) **Spec source citation** — a `SpecSource:` block citing a published
    proof of the assumption. `axiom-cite` activity.

Axes with none of (a)/(b)/(c)/(d) are placeholders — valid scaffolding
during construction, but should be promoted before the model is treated as
complete.

**A trust base with N axes and zero placeholders is stronger than one with
N+M axes where any are placeholders.** When the existing trust base has
placeholders, prefer promoting one over adding a new layer.

## Discipline

- **One activity per cycle.** Focus.
- **Cite `code/<file>:N-M` for every implementation claim.** No citations
  = speculation. An `Op` constructor in an operational trace whose
  surrounding `/- Source -/` block lacks a `code/<file>:N-M` citation is
  `unverified-mapping`: the equality theorem holds at the model layer and
  says nothing about whether the impl actually does that.
- **Annotate vacuous axioms at creation time.** Any axiom whose body is a
  typing scaffold (advantage `:= 0`, `True`, a trivially-satisfied
  predicate, an empty placeholder) carries `-- VACUOUS-PLACEHOLDER` on its
  declaration line **as it is written**. Cycle 1 (and any cycle adding
  axioms) greps:
  ```
  grep -rn '→ True\|:= 0\|:= True' /repo/state/lean --include='*.lean' \
    | grep -v 'VACUOUS-PLACEHOLDER'
  ```
  Annotate any unannotated hits before any `state-reduction` cycle cites
  them. Grep-visible so the trust base can be audited mechanically.
- **Reduction over decomposition.** When the trust base contains any
  `VACUOUS-PLACEHOLDER` axes, axes with `unverified-mapping` traces, or
  axes lacking (a)/(b)/(c)/(d) grounding, prefer activities that ground
  an existing axis (`mathlib-upgrade`, `sage-param`, `sage-ref`,
  `coq-fcf`, `axiom-cite`, `paper-pull`) over `decomposition` activities
  that introduce new axes. Adding axes on top of placeholders inflates
  the trust base without strengthening it.
- **Falsifiability.** Every theorem must have a hypothetical impl change
  that would break it. Theorems true for all impls are tautologies.
- **Don't model your interpretation.** Model the code's actual control
  flow.
- **Don't hunt for bugs in this mode.** If you discover a divergence,
  record it in `findings.json` and move on; concrete repros are hunt-mode
  work.
- **Don't restart from scratch.** If the tree is non-empty, list and read
  existing files first. Extend, don't replace.
- **Layer coverage.** Every protocol layer that carries state across
  operations gets both an operational trace AND a state-machine invariant.
  Operational trace alone catches call-sequence divergences; without a
  state invariant, properties of the form "value V depends functionally
  on prior inputs" are unstatable.
- **Iteration structure preserved** — multi-statement loop bodies not
  collapsed to one op.
- **Ops are typed** — bare constructors only for genuine parameter-free
  markers.
- **Checkpoint substantive work.** `git -C /repo/state add . && git -C
  /repo/state commit -m "<run-id> cycle <N>: <activity-tag> <what>"`.
- **End-of-cycle update to `notes.md`.** Append what this cycle changed
  in `state/` and what the next cycle should pick up. Every update **must
  include a `## Caveats` heading** listing axes still carrying
  `VACUOUS-PLACEHOLDER`, traces with `unverified-mapping` ops, and theorems
  conditional on unaudited trace-to-code mappings. Empty body is valid;
  missing heading is a discipline violation.

## Findings from formal work

When the model exposes a divergence:

1. Localize with `firstDiff` (helper in `lean-modeling` skill) or a failing
   `native_decide`.
2. Determine if it's a real bug or a model gap.
3. Real bug: append to `findings.json` with
   `verification_artifact: state/lean/<path>.lean#<decl>` —
   declaration-level pointer at the specific theorem, sequence, or axiom
   that captures the divergence. If no formal artifact yet exists, set
   `verification_artifact: "no-formalization"` explicitly. Empty strings
   hide the gap from review and are schema violations.
4. Model gap: refine and retry. Document what was imprecise in `notes.md`.

Stopping is the runner's job.
