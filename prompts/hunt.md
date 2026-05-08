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

- **Bootstrap** (queue empty/missing). Recon recent fixes,
  threat-model, spec sources, initial spec trace, proof
  obligations, trust boundaries, hypothesis queue. For each prior
  finding in `audit.md`, generate at least one perturbation
  hypothesis (other-class bugs at known-bug sites — bugs cluster).

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
`verification_artifact`. Same-cycle encoding closes the window
where a finding exists in `findings.json` but not the durable
model. See `prompts/formalize.md` for Lean conventions.

## Discipline

- One activity per cycle. Focus.
- Cite `code/<file>:N-M` for every implementation claim.
- Build on prior cycles; no parallel files alongside existing ones.
- Spawn liberally — if your activity surfaces something orthogonal,
  add it to the queue as `open` and stay focused.
- Append-only on persistent artifacts: never delete prior Lean
  files, repros, notes, or hypotheses.

Stopping is the runner's job.
