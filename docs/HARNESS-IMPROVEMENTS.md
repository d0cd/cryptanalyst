# Harness Improvements — TODO

Ranked backlog of changes spanning prompt rules, runner code, new
modes, new tools, and external library integrations. Items are sorted
by ROI given the cost model where **agents do most of the integration
work** — engineering effort is agent-cycles, not human-engineer time.

Goals served (referenced in each item):
- **(1)** Bug-finding effectiveness
- **(2)** Verification fidelity (does the formal model actually capture
  what it appears to claim?)
- **(3)** Human reproducibility (can a senior cryptographer audit this
  in hours rather than weeks?)

Items already shipped in the current session are listed at the bottom
for reference.

---

## Tier 1 — ship next (high ROI, low risk, hours to days)

### 1. Meta-audit mode (`prompts/meta-audit.md`)

A third mode alongside hunt + formalize, dedicated to *auditing the
existing work* rather than extending it. **Full methodology audit**:
checks the formal model, the prompts, the runner config, the
agent's adherence to discipline rules, AND produces ranked
recommendations for improvements to the formal codebase, the
prompts, and the harness.

The agent has read access to every artifact (traces, prompts,
state/lean/, audit.md, findings.json, run.json). Methodology audit
is mostly mechanical pattern-matching: comparing intended (prompt
rules, activity tags) vs. actual (commit messages, artifacts
produced).

**Output structure (layered confidence)**:

- **Layer A — Mechanical findings** (high confidence): citation
  counts, vacuous-axiom annotations, dangling references, schema
  violations. Agent reports as facts; reviewer can re-run the greps.
- **Layer B — Pattern observations** (medium confidence): skewed
  activity-tag distributions, repeated agent struggles, hunt-
  formalize coverage overlap, deviations from prompt rules.
  Agent reports with cited evidence; reviewer judges the inference.
- **Layer C — Recommendations** (lower confidence): proposed prompt
  edits, harness changes, activity-priority shifts. Agent reports
  as suggestions explicitly framed "agent-generated; validate
  before applying."
- **Layer D — Self-limitations**: things the agent flags as outside
  its competence. "Cannot determine whether axiom X is load-bearing
  without senior cryptographic review." This is the honesty floor.

**Activities**:

- `vacuous-axiom-scan` — Layer A
- `trace-fidelity-scan` — Layer A
- `activity-tag-audit` (commit-message tag vs. actual diff) — Layer A
- `trust-base-orthogonality-audit` (pairwise axis dependencies) —
  Layer B
- `findings-linkage-audit` (each finding ↔ matching theorem) —
  Layer A/B
- `coverage-gap-survey` (primitives modeled vs. unmodeled) — Layer B
- `prompt-effectiveness-review` — for each prompt rule, check
  whether it actually fires in agent behavior. Flag rules ignored
  in N+ cycles. — Layer B
- `methodology-recommendations` — ranked proposed changes (prompt /
  harness / runner / external library), each citing the layer-A or
  layer-B evidence motivating it. Each recommendation states
  expected effect + how a future meta-audit would verify it
  landed. — Layer C
- `summary-for-reviewer` — 2-3 page integrated summary for senior
  cryptographer. — Layers A/B/C
- `self-limitations` — explicit list of things the agent could not
  determine and why. — Layer D

**Why this scope works**: the agent's strengths (reading 75 KLOC,
mechanical pattern-matching, citation-checking) cover Layers A/B
reliably. The agent's weaknesses (cryptographic novelty,
architectural design judgment, domain expertise) are explicitly
quarantined to Layer D. Recommendations (Layer C) are scoped to
local fixes the agent can describe concretely (e.g., "tighten the
bootstrap rule to require X" rather than "redesign the verification
methodology").

**Cost**: 30-45 min to draft the prompt. ~8-12 cycles to run once
after a formalize/hunt session. **Goals**: (3) very high; (2) high;
(1) low (meta-audit doesn't find new bugs, but identifies coverage
gaps where bugs might hide).

**Limitation to acknowledge**: meta-audit is **still an agent** with
correlated biases. It catches mechanical and pattern-level issues
better than semantic ones. It does not replace senior-cryptographer
review; it produces the artifacts that *enable* that review at scale.

### 2. Trivial prompt edits: vacuous-axiom flagging + self-caveat in `progress.md`

Two text-only additions:
- **Vacuous-axiom flagging**: any axiom whose advantage body is
  `:= 0` must be annotated `-- VACUOUS-PLACEHOLDER`. A
  `state-reduction` cycle that merely references one does NOT
  count as discharging it.
- **Mandatory caveat in `progress.md`**: every progress note
  includes a `## Caveats` section listing axes with placeholder
  bodies, traces lacking source-line citations, and theorems
  conditional on operational-trace fidelity.

**Why**: makes structural risks (#7 vacuous semantics, #1 trace
fidelity) visible at grep speed. Reviewer can immediately see what
the model assumes vs. proves.

**Cost**: 10 min total. **Goals**: (2) high; (3) very high.

### 3. Cross-mode finding ↔ formal-model linkage

Hunt's `findings.json` gets a discipline rule: every finding's
`verification_artifact` field must reference the matching formal
theorem (e.g.,
`state/lean/Varuna/V1AdaptiveSoundnessAttack.lean#v1_attack_forges_any_target`)
or explicitly state "no formalization." Optionally a runner check
that validates the reference points at a real declaration.

**Why**: machine-checkable cross-reference between exploits and
formal claims. Reviewer can verify hunt's F2 corresponds precisely
to formalize's `v1_violates_eta_ordering`.

**Cost**: 10 min prompt edit + a few hours of runner code if
enforced. **Goals**: (3) very high; (2) medium.

### 4. Hunt blind-spot directive (prompt edit)

Add to `prompts/hunt.md`: when hunt and formalize have both spent
multiple cycles on the same area (FS ordering, V1/V2), allocate at
least 1 in 3 cycles to a primitive-flow that the formal model
treats as black-box: pairings (Miller loop, final exponentiation),
MSM correctness, hash permutation, FFT.

**Why**: catches a class of bugs neither mode currently covers.
Hunt has historically followed formalize's gravity toward the
already-modeled territory. The pairing implementation is the
biggest gap.

**Cost**: 5 min prompt edit. **Goals**: (1) medium-high.

### 5. Reduction-over-expansion priority + trace-fidelity citation discipline (prompt edits)

Two prompt rules in `prompts/formalize.md`:
- **Reduction priority**: when the trust base has any placeholder-
  bodied or `OVER-GENERAL` axes, prefer `state-reduction` /
  `axiom-cite` / `sage-param` / `mathlib-upgrade` over adding new
  axes via `decomposition`.
- **Trace-fidelity citations**: every `Op` constructor in an
  operational trace must cite a `code/<file>:N-M` line range. Traces
  without citations are `unverified-mapping`.

**Why**: inverts the agent's bias from "add another axis" to
"ground existing axes." Closes part of structural risk #1 (trace
fidelity) by forcing line-level traceability.

**Cost**: 10 min total. **Goals**: (2) high.

---

## Tier 2 — medium investment substantive (days of agent-cycles)

### 6. `Mathlib.Algebra.MvPolynomial.SchwartzZippel` + `z-tech/sumcheck-lean4` reductions

Both libraries cover specific axiom families currently left as
`axiom` in our trust base. Add `mathlib-upgrade` cycles that
discharge:
- Schwartz-Zippel-style probabilistic axioms via `MvPolynomial.
  SchwartzZippel`
- Sumcheck-soundness axioms via `sumcheck-lean4` (after
  evaluating import compatibility)

**Why**: axioms become theorems via library reduction. Pure trust-
base shrinkage. Goal-2 win without leaving the Lean ecosystem.

**Cost**: 2-5 days each, depending on import compatibility.
**Goals**: (2) high.

### 7. Kani — symbolic execution / bounded model checking of the Rust code

Amazon's Rust verifier. Verifies bounded properties of the
*actual Rust code*: panic-freedom, return-value bounds, panic
preconditions. Does not require building a parallel formal model —
it operates on the source.

**Why**: closes part of structural risk #2 (the trace ↔ Rust
mapping) from a complementary angle. Where formalize-mode validates
"our Lean trace correctly encodes Rust's behavior," Kani validates
"Rust's behavior has property X" directly. Caught panic-DoS bugs
at scale in other Rust crypto libraries; would catch bugs the
operational trace abstracts away (e.g., subtle `unwrap` paths,
`assert_eq!` panics like our finding F4 pre-discovery).

**Cost**: 1-2 days to integrate Kani into the container; per-target
property harnesses are ~30 min each. **Goals**: (1) high (panic
classes, bounds violations); (2) medium-high (corroborates
operational trace claims).

---

## Smaller wins / housekeeping (XS-S, do whenever)

These are quality-of-life improvements that save cycle time or
clarify documentation. They don't move the goals (1)/(2)/(3)
needles materially but they're cheap and aggregate over runs.

- **Per-target `audit.md` "Harness gotchas" section** for snarkVM
  (already in `instructions/AGENTS.md` globally; per-target adds
  target-specific quirks like `/repo/state/cargo-target` being the
  canonical cargo target dir). 5 lines per target. Saves 20+ min
  per fresh hunt cycle. **Goal**: (1) cycle efficiency.

- **Image-bake `arkworks-bls12-377` cargo scaffold**. Hunt cycles
  building Rust diff-tests pay 5-15 min cargo-dep + first-build
  cost. ~1 hour to set up a `env/scaffolds/diff-bls12/` and
  pre-build it at image build time. **Goal**: (1) cycle efficiency.

- **Cycle wall-clock telemetry to the agent**. Inject a status
  block at each cycle's start (cycle N/100, wall-clock 0s/budget,
  prior-cycle status). 2-4 hours of runner code. **Goal**:
  (1) cycle efficiency.

- **`hypotheses.json` schema validation**. Define a schema (`open`
  / `investigating` / `refuted` / `confirmed` / `stuck`) and
  validate it after every cycle. ~1 day. Subsumed by Tier 3
  runner-side enforcement (item 13) if that ships, but valuable
  standalone. **Goal**: (3) discipline.

- **`prompts/README.md` cross-reference in `AGENTS.md`**. Adds one
  sentence about the system-prompt-vs-cycle-prompt split. 5 min.
  Tiny clarity gain for new readers. **Goal**: (3) marginal.

(Trust-base minimality audit cycles, formerly tracked separately,
is folded into the meta-audit mode's `trust-base-orthogonality-
audit` activity. No standalone item.)

---

## Tier 3 — larger investment (1-2 weeks of agent-cycles each)

### 8. Sage trace simulator + differential check against Rust verifier

Build a Sage-side simulator that produces actual Fiat-Shamir
transcripts in the order our Lean operational traces claim, then
runs them against the Rust verifier on adversarial inputs. The
output: pairs `(implV1RoundOrderTrace, runnable-Rust-test)` and
`(implV2RoundOrderTrace, runnable-Rust-test)`.

**Why**: closes structural risk #1 (trace fidelity). Without this,
the entire V1/V2 soundness story rests on hand-encoded Lean traces
that have never been validated against runtime behavior. With it,
trace ↔ runtime is corroborated by transcript execution.

**Cost**: 1-2 weeks agent-cycles. **Goals**: (1) high (surfaces
integration bugs); (2) very high; (3) high (runnable artifact).

### 9. Game-based advantage definitions: pick **one** of:

**A. Mathlib `MeasureTheory.PMF` bridge** — build the probabilistic
game infrastructure inside Lean using existing Mathlib imports.
Native to our existing stack; no second proof assistant.

**B. FCF (Coq) for advantage definitions** — use the Foundational
Cryptography Framework, a mature Coq library specifically built for
game-based proofs. Faster to integrate because the infrastructure
exists; cost is adding Coq mode to the harness.

**Why**: converts vacuous `someAdvantage := 0` placeholder bodies
into real mathematical claims. Closes structural risk #7. Without
this, "advantage ≤ negligible" theorems are kernel-checked but
semantically thin.

**Cost** (either path): 1-2 weeks. FCF is faster if the agent
handles Coq integration; PMF-bridge is cleaner if you want to stay
single-proof-assistant. **Goals**: (2) very high.

### 10. Fiat-Crypto reference for `fp_256.rs` / `fp_384.rs`

Use Coq's Fiat-Crypto to generate verified field arithmetic for
BLS12-377's specific moduli, then differentially test snarkVM's
implementation against it. Fiat-Crypto is in production at Google
(BoringSSL) and Microsoft.

**Why**: rules out the entire `sum_of_products` / carry-overflow
bug class at the source. The biggest identified bug class hunt has
been chasing in field arithmetic. Lean lacks a comparable verified-
extraction pipeline.

**Cost**: days to evaluate, 1-2 weeks to integrate. **Goals**:
(1) high; (2) high.

### 11. EasyCrypt (or alternatively CryptoVerif) port of `t_sdh_assumption → kzg_binding_from_t_sdh`

The single most load-bearing reduction in our trust base
(KZG10 §C.1 EvalBinding theorem). EasyCrypt is the de facto
industry tool for game-based cryptographic proofs and was designed
for exactly this kind of game-hop argument.

**Why**: converts the floor reduction from "paper-cited assumption"
to a machine-checked theorem. The Lean axiom remains (EasyCrypt
and CryptoVerif aren't Lean) but reviewers can read the artifact
alongside.

**Cost**: 1-2 weeks. **Goals**: (2) very high; (3) medium (adds
artifact reviewers must read in EasyCrypt or CryptoVerif's language).

### 12. Cryptol + SAW for primitive equivalence checking

Galois Inc's stack: Cryptol is a DSL for cryptographic
specifications; SAW (Software Analysis Workbench) symbolically
executes code (C, Rust via LLVM) and proves it implements the
Cryptol spec. Mature: has been used to verify AES, SHA-256,
ChaCha20, ed25519, and components of s2n-tls.

**Why**: a different attack on structural risk #2 from Kani
(item 7). Where Kani checks bounded properties, SAW does full
equivalence checking between high-level specs and Rust
implementations. Could verify our `fp_256.rs` matches a Cryptol
spec for BLS12-377 scalar field arithmetic — same goal as
Fiat-Crypto (item 10) via a different toolchain.

**Cost**: 1-2 weeks for the agent to set up and produce the first
verified primitive. **Goals**: (1) high; (2) very high (proves
implementation correctness against a formal spec).

Choose between this and Fiat-Crypto (item 10) based on which is
easier to integrate; both produce similar artifacts. Fiat-Crypto
is more SNARK-curve-tested in production; SAW is more general.

### 13. Runner-side enforcement of discipline rules

Patch `runner/audit.py:post_run_check` to:
- Validate `progress.md` exists and has a `## Caveats` section
- Count `VACUOUS-PLACEHOLDER` axiom annotations and surface in
  `run.json`
- Validate every `verification_artifact:` reference in
  `findings.json` points to a real Lean theorem
- Validate `hypotheses.json` schema (housekeeping item)

**Why**: makes Tier 1/2 discipline rules **load-bearing rather
than aspirational**. Without runner enforcement, prompt rules
fire 50-70% effectively rather than 100%.

**Cost**: 1-2 days. **Goals**: (2) and (3) — makes the discipline
sticky.

### 14. BLS12-377 `WeierstrassCurve` instance in Lean

Use `Mathlib.AlgebraicGeometry.EllipticCurve.Weierstrass` to
instantiate BLS12-377 with its specific parameters. Discharges the
placeholder group operations in `state/lean/Curves/`.

**Why**: replaces wrapped-`Nat` placeholders with real Mathlib
algebra. Makes our `Curves/` files non-placeholder.

**Cost**: ~few hundred lines of Lean. **Goals**: (2) medium.

---

## Already shipped this session

These are documented here so future sessions don't re-propose them
or assume they're absent:

- ✅ Bootstrap-persistence rule in `prompts/hunt.md` ("Persist before
  tooling: write `artifacts/notes.md` before building any test
  infrastructure"). Validated overnight: hunt-2 cycle 1 wrote
  notes.md within 30s of launch with H1-H8 hypothesis queue.

- ✅ Mid-cycle infrastructure-budget pivot in `prompts/hunt.md`
  ("if you spend more than 10 min on environment / build / dep
  work without substantive observation, stop and pivot"). Was
  Tier-2 item #5 in prior version of this doc.

- ✅ End-of-cycle `progress.md` discipline in both `prompts/hunt.md`
  and `prompts/formalize.md`. Validated overnight: hunt-2 cycle 15
  successfully recovered from session-context compaction via
  `progress.md`.

- ✅ Primitive-level coverage section in `prompts/formalize.md`
  with completeness criterion (a/b/c) and the new `axiom-cite`
  activity. **Validated overnight**: cycles 87-89, 91, 99, 103-107
  all produced primitive-coverage activities. Trust base went from
  3 grounded axioms to 6+ SageReference blocks in 12 hours.

- ✅ Harness gotchas in `instructions/AGENTS.md` ("Harness
  environment notes" section): noexec `$HOME`, MCP REPL doesn't
  pre-load `Audit.*`, snapshot mode semantics. (Was Tier-1 item
  #1 in prior version of this doc.)

- ✅ Audit.md fold-in for snarkVM target: F1/F2/F3 promoted to
  "Already-found bugs"; 7 new open leads from cycle 4-13 mining;
  REFUTED markers on confirmed-non-bugs. Hunt-2 picked up new
  leads productively (F2 substantiated within 12 cycles).

- ✅ Tier 1 #2 / #3 / #4 / #5 prompt-edit bundle (2026-05-09):
  vacuous-axiom annotation + `unverified-mapping` term in
  `prompts/formalize.md`; reduction-over-decomposition priority
  promoted from primitive-coverage section into Discipline; hunt's
  `## Spawn from blind spots` activity rotating ≥1-in-3 cycles into
  unmodeled territory; declaration-level `verification_artifact`
  pointers + `"no-formalization"` sentinel; mandatory `## Caveats`
  section on every `progress.md`; "Read the trust base critically"
  bullet in hunt's Discipline. Pipeline stepped — formalize-3 +
  hunt-3 booted with the new prompts at run-IDs
  `20260509-094138-...` / `20260509-094148-...`.

- ✅ Tier 1 #1 meta-audit mode (2026-05-09): `prompts/meta-audit.md`
  drafted with Layer A/B/C/D output structure (mechanical findings,
  pattern observations, recommendations, self-limitations).
  Read-only on durable state; writes only under
  `artifacts/meta-audit/`. Activities: `vacuous-axiom-scan`,
  `trace-fidelity-scan`, `activity-tag-audit`,
  `findings-linkage-audit`, `trust-base-orthogonality-audit`,
  `prompt-effectiveness-review`, `coverage-gap-survey`,
  `methodology-recommendations`, `summary-for-reviewer`,
  `self-limitations`. Dispatchable via existing `--mode meta-audit`
  flag, no runner changes needed. To run after the current
  pipeline produces enough artifact to audit (~12h).

---

## Ranked priority recommendation

**If you ship one thing**: Tier 1 #1 (meta-audit mode). Cheapest
path to making the model human-auditable.

**If you ship a small bundle (< 1 hour total)**: Tier 1 items 1-5.
All are prompt edits or one-shot drafts. Combined effect:
materially improves goals (2) and (3) for every future run.

**If you commit to a one-week investment**: Tier 1 + Tier 2 items
6 (Mathlib Schwartz-Zippel + sumcheck-lean4) + 7 (Kani Rust
verification). Result: trust-base shrinkage via library reductions
+ first runtime-side validation of structural risk #2.

**If you commit to a serious investment quarter**: above + Tier 3
items 8 (Sage simulator), 9 (PMF/FCF advantages), 10 (Fiat-Crypto),
13 (runner enforcement). Focuses on closing the deepest structural
risks: trace fidelity, vacuous semantics, field-arithmetic black
boxes. Choice of 9A (Mathlib PMF) vs. 9B (FCF) determines whether
you stay single-proof-assistant or extend into Coq's ecosystem.

**Alternative to Fiat-Crypto for field arithmetic**: item 12
(Cryptol + SAW) achieves a similar result via a different
toolchain. Pick whichever is easier for the agent to integrate;
both produce equivalent verification artifacts.

---

## Note on the cost model

A standing assumption in these rankings: **agents do the
integration work**. Adding Coq mode to the harness, drafting a new
prompt, instantiating a Mathlib type, building a Sage simulator —
all of these are agent-cycles, not human-engineer time. This makes
items previously priced as "weeks of senior work" cost-competitive
with prompt edits if the agent is competent at the target stack.

What this **doesn't** make cheap:
- Reviewer time to validate the formal results
- Domain expertise to design the right axiom statements
- Cryptographic judgment about which reductions actually reduce

For those, the meta-audit mode (Tier 1 #1) is the closest substitute,
producing artifacts that scale review effort. But it doesn't replace
the senior-cryptographer review at the end.
