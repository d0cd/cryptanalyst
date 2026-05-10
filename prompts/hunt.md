# Each cycle — hunt mode

The runner invokes you repeatedly, ~10 minutes per cycle. State
carries between cycles via files in your working directory.

Read where you are: `AGENTS.md` (methodology), `audit.md` (target
scope, if present), `artifacts/` (this run's scratch + deliverables),
`/repo/state/` (durable cumulative model from prior runs; Lean tree
also at `/opt/lean-workspace/Audit/`). Pick the single highest-
leverage activity given that state. Do it. Return.

## Activities

Some take a full cycle; some take longer. Findings empirically
come from high-effort cycles (adversarial code reading, primitive-
flow enumeration, trace-faithfulness audit). Drift toward "sanity
check" / "follow-up" cycles is the cost-greedy bias to resist.

- **Bootstrap** (every cycle 1, even when persisted memory exists).
  Write `artifacts/notes.md` **before any tooling** with these
  sections (order is your call; all four are required):
    - threat model + attacker capabilities
    - spec sources (papers, in-tree docs)
    - **blind spots** — components in `code/` the durable model
      does NOT cover (primitives named only in axiom statements,
      sub-protocols without parallel traces, modules without
      behavioral invariants, areas `audit.md` flags as untouched).
      Regenerate this section each launch — do not inherit it
      stale from a prior run.
    - hypothesis queue — both inherited (from prior notes / from
      `audit.md` open leads) and fresh ones drawn from blind spots.
      Rank by signal-to-cost; weight novelty for blind-spot
      targets.

  Persisted memory is the harness's strength; it lets cumulative
  audits build over many runs. The failure mode is not that you
  read it but that you **only** read it. Regenerating blind spots
  each launch is the forcing function for fresh search.

  If the cycle gets cancelled mid-build, persisted notes survive,
  in-flight thinking does not. That's why notes go before tooling.

- **Investigate one open hypothesis.** Re-rank by accumulated
  evidence first. If queue is monoculture in one bug class /
  module / vector, spawn diversifying hypotheses before picking
  another narrow one. Mark `investigating`, attack adversarially,
  conclude `refuted` / `confirmed` / `expanded` / `stuck:<reason>`.
  On `refuted`, queue 1-3 follow-ups asking where else this bug
  class could live.

- **Refine the spec trace.** Deeper expansion of a sub-protocol
  previously left at high level.

- **Trace-faithfulness audit.** Pick an existing equality theorem.
  For each impl-side op, find the actual `code/` lines. Document
  in `notes.md` as a table: (op, code lines, mismatches). Confirm
  the trace is faithful or fix it. Both outcomes are substantive
  — confirmation is real audit evidence; a fix may surface a
  divergence that becomes a finding.

- **Primitive-flow enumeration.** Pick a trust-critical primitive
  invoked at multiple sites. Use `rg` to find every site. Document
  in a single `notes.md` table: (call site, what's consumed, what
  was checked before, what's consumed after). Every site, not a
  sample.

- **Spawn from blind spots.** When the hypothesis queue and recent
  cycles cluster around territory the durable model has already
  covered (areas with parallel `List Op` traces, sub-protocols
  with state-machine invariants, modules touched by multiple prior
  cycles), allocate at least 1 in 3 cycles to a primitive-flow the
  model treats as black-box: primitives named only inside axiom
  statements, components without parallel traces, sub-protocols
  without state invariants, modules the durable model never opened.
  Bugs cluster, but cycle attention also clusters; the converged-
  on territory has had its surface bugs shaken out, while the
  unmodeled territory has not. Use the durable model as a coverage
  map — the gaps in it are where unsurfaced bugs likely live.

- **Recon refresh / threat-model refinement** when those are
  higher-leverage than investigation.

`confirmed` requires a runnable repro under `artifacts/repro/` and
line citations in `findings.json`. Lower-confidence observations
go in `notes.md`.

## Trust the cumulative model carefully

The durable model under `/repo/state/lean/` is evidence, not proof.
Three failure modes:

**Passing `native_decide` proves model spec = model impl AT THE
MODELED GRANULARITY.** It does NOT prove the modeled impl matches
the actual `code/`. If the trace skips operations or was written
in expected (rather than actual) order, equality holds at the
model level while the code has a real bug.

**A security theorem that reduces to a paper-cited monolithic
axiom proves the axiom is invocable, not that the property holds.**
Code like `theorem soundness := compilerTheoremAxiom verify_eq`
looks discharged, but the security argument lives entirely inside
the axiom's unstated body. Treat such theorems as **weak signal** —
the agent committed to citing this paper, not to proving the
property. Axiom-thick theorems are *lower* signal than
`native_decide` failures. The fix is decomposition, but that's
formalize-mode work.

**When refuting via model evidence, quote the actual code at the
cited line ranges in `notes.md`** and state explicitly whether the
quoted lines match the trace's claimed order. "I sanity-checked
the trace" without quotes is a claim, not a refutation. `rg` for
keywords ≠ opening the file at cited ranges and reading.

**If the model is wrong, fix it.** A buggy model masks bugs in
the impl. Edit in place with a comment, or file a `_v2`. Updating
a wrong impl trace counts as substantive cycle work and may
itself surface a divergence.

## Tighten the confirm-encode loop

When a cycle confirms a finding, extend the cumulative formal
model in the same cycle — don't defer. Add or refine the durable
artifact (theorem, divergent sequence, type-level statement) that
captures what the bug demonstrates, and reference it in
`verification_artifact`.

**`verification_artifact` is required, not optional.** Every entry
in `findings.json` must have it set. The value MUST be one of:

- (a) `state/lean/<path>.lean#<decl>` — declaration-level pointer
  to a durable Lean theorem, sequence, or axiom. The file must
  exist in `/repo/state/lean/`, not `artifacts/lean/` (the latter
  is non-durable and vanishes when the run ends).
- (b) `state/sage/<path>.sage` — durable Sage script.
- (c) The literal string `"no-formalization"` — when no durable
  artifact exists yet. Choose this rather than guessing or
  leaving the field empty.

Schema violations (omitting the field, leaving it empty,
writing an `artifacts/` path) break machine-checkable cross-
referencing between findings and formal claims and trigger a
runner lint error. Write the field at the same time as the
finding, not at end-of-cycle.

If you wrote `"no-formalization"` for a finding, queue a
hypothesis to produce the durable artifact in a later cycle.
Same-cycle encoding closes the window where a finding exists
in `findings.json` but not the durable model. See
`prompts/formalize.md` for Lean conventions.

## Discipline

- One activity per cycle. Focus.
- Cite `code/<file>:N-M` for every implementation claim.
- Build on prior cycles; no parallel files alongside existing ones.
- Spawn liberally — if your activity surfaces something orthogonal,
  add it to the queue as `open` and stay focused.
- Append-only on persistent artifacts: never delete prior Lean
  files, repros, notes, or hypotheses.
- **Infrastructure budget.** If you spend more than ~10 minutes (or
  ~30 tool calls) on environment, build, or dependency work
  without a substantive observation, stop. Append a `blocker`
  entry to `notes.md` describing what you tried and what failed,
  then pivot to a different avenue or activity. Sunk-cost gradient
  on tooling work is the most common way a cycle is wasted; name
  it explicitly so you can pivot without rationalizing.
- **Read the trust base critically.** A `state/lean/` axiom marked
  `VACUOUS-PLACEHOLDER`, or lacking any grounding (no
  `SageReference:`, `CoqReference:`, `SpecSource:`, or Mathlib
  derivation), is not load-bearing evidence — it is the property
  the formal work has not yet justified. A hypothesis "refuted by
  reduction to axiom X" is only a real refutation when X is itself
  grounded.
- **End-of-cycle update to `notes.md`.** At cycle end, update
  `notes.md` with what this cycle did, what it changed on disk, and
  what the next cycle should pick up. Every cycle update **must
  include a `## Caveats` heading** listing things this cycle did
  NOT do — refuted-by-ungrounded-axiom shortcuts, trust-base
  axioms cited without checking whether the underlying invariant
  fired, blind-spots not yet attacked. Empty body is valid; missing
  heading is a discipline violation. Caveats are the load-bearing
  audit trail of admitted limits; everything else is your call.

Stopping is the runner's job.
