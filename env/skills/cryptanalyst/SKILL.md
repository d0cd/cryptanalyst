---
name: cryptanalyst-conventions
description: The *why* behind the cryptanalyst harness conventions — what the citation blocks are for, why annotations are required, why notes.md is the only persistence file. Read this when the prompts feel underspecified or when a rule's intent isn't obvious from its statement. The rules themselves live in the prompts.
---

# Why the cryptanalyst harness works the way it does

The prompts under `/repo/prompts/` carry the rules each cycle must follow.
This skill is the *why* — the design intent behind the rules, the failure
modes they exist to prevent, and the cross-cutting flow between Lean / Sage
/ Coq / Rust differential tests. Read it when the prompts feel
underspecified.

## Why citation blocks are mandatory

Every durable artifact under `/repo/state/` cites its sources via header
blocks above the relevant declaration:

- `/- Source -/` above an `Op` constructor cites `code/<file>:N-M`.
- `/-! SpecSource -/` above a spec op group or hardness axiom cites a paper
  / RFC / spec doc.
- `SageReference:` on a Lean axiom points at `state/sage/<file>.sage`.
- `CoqReference:` on a Lean axiom points at `state/coq/<file>.v`.

**Why mandatory**: the citation is the *only* mechanism that lets a
reviewer mechanically locate the substantiation. Without it, the model is a
self-consistent fiction. The most common failure mode is "the spec and impl
were both encoded by reading the same code" — `native_decide` succeeds, the
real bug stays hidden. Cited literal source on both sides is what makes a
flipped op surface as a divergence.

**Why "cite, don't restate"**: if a Sage script certifies a parameter and a
Lean theorem also restates the numerical content, you have two sources of
truth that can drift. The Lean side cites `SageReference:` and stays
abstract; the Sage side certifies the numerics. Same for `CoqReference:`
and `SpecSource:`.

## Why VACUOUS-PLACEHOLDER must be annotated at creation time

`-- VACUOUS-PLACEHOLDER` marks any axiom or security theorem whose body is
a typing scaffold (`:= 0`, `True`, trivially-satisfied predicate,
`advantage ≤ negligible` with both sides stub-zero).

**Why grep-visible**: it lets the trust base be audited mechanically. A
reviewer running `grep -rn 'VACUOUS-PLACEHOLDER' state/lean/` immediately
sees what's load-bearing vs what's still scaffolding. Without the
annotation, the only way to find vacuous bodies is to read every axiom.

**Why creation-time, not cleanup-pass**: the annotation has to be there
*when other code starts citing the axiom*. A `state-reduction` cycle that
cites a vacuous axiom doesn't discharge anything — but the cycle's commit
message and progress note look like progress. Discovering the vacuity 8
cycles later means rolling back 8 cycles of false progress. Annotation at
creation time fails fast.

**Why the four discharge paths matter** (mathlib-upgrade, sage-param,
coq-fcf, axiom-cite — paths (a)/(b)/(c)/(d) in the formalize prompt's
"Primitive coverage and trust-base completeness"): they're the four ways a
property can become real. Each path matches a property *shape*: structural-
algebraic → Mathlib; concrete-numerical → Sage; probabilistic-game → Coq;
otherwise → external citation.

## Why notes.md is the single persistence file

`notes.md` carries the agent's working memory across cycles within a run.
Findings go to `findings.json`; durable formal artifacts go to
`/repo/state/`. Everything else is `notes.md`.

**Why one file, not three**: an earlier iteration of the harness had
`notes.md` + `progress.md` + `blind-spots.md` as parallel files. Meta-audit
found `## Caveats` fired in 0/88 progress.md writes — the fragmentation
made each file feel optional. Collapsing to one file with required sections
gives the agent one place to look and one place to update.

**Why `## Caveats` is the load-bearing section**: it's the audit trail of
what this cycle did NOT do. Empty body is fine; missing heading is the
violation. The forcing function admits limits explicitly rather than
letting them disappear into agent confidence.

**Why blind-spots is part of cycle 1's bootstrap**: persisted memory
(`audit.md`, prior `notes.md`, `state/lean/`) is the agent's starting
context, not its search space. The hunt-3 failure mode was grinding through
inherited hypotheses and never spawning fresh ones. Regenerating the
blind-spots section each launch is the forcing function for fresh search:
the durable model tells you what's already covered; the gaps are where
unsurfaced bugs live.

## Why the four-tool stack is complementary, not hierarchical

Lean + Sage + Coq + Rust differential tests each fit a different layer of
crypto reasoning:

| Layer | Tool | Why |
|---|---|---|
| Protocol logic, structural reductions, type-level invariants | **Lean + Mathlib** | Lean's structural type system + `native_decide` + Mathlib algebra is the right shape for protocol-level claims. Top-level security theorems live here; the trust base lives here. |
| Concrete numerical certifications | **Sage** | Sage's number-theoretic libraries are the right shape for "verify this curve has the claimed prime-order subgroup" or "compute a reference output on adversarial inputs." Lean can state the property; Sage certifies it on shipped values. |
| Probabilistic game-based reasoning | **Coq + FCF** | FCF's monadic `Comp` and game-hop tactics encode `\| Pr[Game1] − Pr[Game0] \| ≤ ε` natively. Replicating this machinery in Lean's PMF is harder than using FCF directly. |
| Runtime-side validation | **Rust differential tests** | When the implementation behavior matters (not just the protocol logic), differential tests against arkworks-or-other reference implementations on adversarial inputs are the only thing that catches integration bugs. |

**Failure modes**:
- Using Lean for a game-hop reduction → results in `VACUOUS-PLACEHOLDER`
  because PMF can't yet express the game shape. Should have gone to FCF.
- Using Coq for protocol-level operational traces → fragments the trust
  base for no benefit. Should have stayed in Lean.
- Restating Sage's numerical content in Lean → two sources of truth that
  drift. Should have cited via `SageReference:`.
- No reference implementation at all → integration bugs hide in places
  the structural model abstracts away (panics, off-by-one, sign-convention
  bugs).

The tools are picked by the property's shape, not by an order of fallback.

## Why meta-audit's compactness rule is hard at 5

Meta-audit's `methodology-recommendations.md` caps at 5 active items.

**Why**: the rule's purpose is to drive *next-step actions*, not to produce
a comprehensive audit deliverable. A 30-item list is unread; a 5-item list
gets implemented. When meta-audit finds a 6th candidate, the lowest-ranked
existing item is dropped — pressure forces ranking, ranking forces clarity.

**Why ranked items have a verification path**: each recommendation specifies
how a future meta-audit will mechanically check whether it landed. That
makes the recommendation a *falsifiable claim* about future state. If the
change landed and produced the expected effect, the recommendation
disappears from the list; if it landed but had no effect, the rule is
wrong; if it didn't land, it stays. This is what makes meta-audit
self-correcting rather than a static checklist.
