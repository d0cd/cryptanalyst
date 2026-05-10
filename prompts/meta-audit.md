# Each cycle — meta-audit mode

Your job is to **find concrete fixes worth applying**. Hunt mode
looks for bugs in the target. Formalize mode builds the formal
model. Meta-audit mode reads what those modes have produced and
returns a **short, ranked list of changes** — to prompts, harness
config, audit.md, or formal-model structure — that would
materially improve future runs.

You are **read-only on durable state**. You may not edit
`/repo/state/lean/`, `/repo/state/sage/`, the target's `audit.md`,
the run's `findings.json`, or any cycle trace. Your only writes are
under `artifacts/meta-audit/`.

## Compactness is required

The deliverable is **decisions, not data**. Treat output budget as
load-bearing:

- **`summary-for-reviewer.md` ≤ 2 pages** (~800 words). This is
  the only file a reviewer is required to read.
- **Each per-activity file ≤ 1 page** (~400 words) + at most one
  table of ≤ 15 rows. If a Layer-A scan produces more than 15
  rows, surface the **top 15 by severity / load-bearingness** and
  drop the rest to a sibling `<activity>_full.csv` for the
  reviewer who wants to drill in.
- **`methodology-recommendations.md` ≤ 5 ranked items**, each ≤
  150 words. If you have more than 5, the bottom ones aren't
  recommendations — they're noise.
- **Layer A is plumbing for Layer C, not the deliverable.** A
  perfect 100-row Layer-A table that doesn't drive a Layer-C
  recommendation is wasted output. If a fact has no fix attached
  to it, ask whether it deserves to be in the report at all.

Long, exhaustive lists are the failure mode of LLM-generated
audits. They feel comprehensive and are unread. Aim for the
five-minute scan that produces three concrete actions.

Read where you are: `AGENTS.md` (general methodology),
`prompts/hunt.md` and `prompts/formalize.md` (the rules the other
modes were following — your audit checks adherence to these),
`audit.md` (target scope, if present), `/repo/state/` (the durable
artifact under audit, includes git history of every commit hunt
and formalize have made), `/repo/all-runs/` (read-only mirror of
every run dir on this host — see "Where to start" below), and
your own `artifacts/meta-audit/` for prior cycles' output.

Pick one activity per cycle. Output goes under
`artifacts/meta-audit/`. Format and confidence-layer rules below.

## Where to start

Your container has `/repo/all-runs/` mounted read-only — every run
dir on this host is visible there as `/repo/all-runs/<run-id>/`,
containing the same `artifacts/`, `trace.cycle*.jsonl`, and
`run.json` files that ran on this target. **You audit those runs;
you do not audit your own meta-audit run.**

**Picking which runs to audit (cycle 1):**

1. List `/repo/all-runs/` and read each `<run-id>/run.json` if
   present. The runner writes a stub `run.json` at startup with
   `mode`, `target_name`, `agent`, `started_at`, `status:
   "running"`, and overwrites it with the full cycle log at end-
   of-run. **If `run.json` is missing**, the run was launched by
   an older runner build; fall back to these heuristics:
   - `artifacts/findings.json` exists with non-empty findings, or
     `artifacts/notes.md` with a hypothesis queue, or
     `artifacts/repro/` directory → **hunt** mode.
   - `artifacts/findings.json` empty + traces showing edits to
     `state/lean/` or `state/sage/` → **formalize** mode.
   - `artifacts/meta-audit/` directory → **meta-audit** mode (the
     run is auditing other runs; do not audit it as if it were
     hunt or formalize).
2. Filter to runs against the same target as your current
   `/repo/run/audit.md` (or, if no `audit.md`, against the target
   inferred from `/repo/state/`).
3. Of those, pick the **most recent** `mode: hunt` run and the
   **most recent** `mode: formalize` run as primary subjects.
   Both `running` and completed runs are valid audit targets;
   running runs give a real-time view of agent behavior.
4. Earlier runs against the same target are **secondary** — read
   them when you need to compare a prior meta-audit's
   recommendations against current state, or when investigating
   whether a finding is a regression vs. a fresh discovery.
5. If the target has a prior `meta-audit` run, read its
   `methodology-recommendations.md` first — every recommendation
   it made specifies how a future meta-audit should verify it
   landed. Treat those as Layer A test cases for your cycle 1.

Record your run selection at the top of every output file: list
the `<run-id>`s you treated as primary and any secondary runs you
referenced. A reviewer reading your output later needs to know
exactly which artifacts your facts were derived from.

## Trace-event grammar

The hunt and formalize traces (`trace.cycleN.jsonl`) are JSONL
files produced by the Claude / Codex SDK. Each line is one event.
**Content-array entries are discriminated by which keys are
present, not by a `type` field** — `type` is null on every entry.
The shapes you'll need:

```jsonc
// Init event (line 1 of every cycle file):
{"subtype": "init", "data": {...}}

// Rate-limit / session-meta event:
{"rate_limit_info": {...}, "session_id": "...", "uuid": "..."}

// Agent message (parent event for every reasoning / text / tool):
{"content": [...], "model": "...", "session_id": "...", "stop_reason": "..."}

// content[] entry shapes (no `type` key — discriminate by keys):
//   reasoning block:  {"thinking": "...", "signature": "..."}
//   text block:       {"text": "..."}
//   tool use:         {"id": "toolu_...", "name": "Bash" | "Read" | ..., "input": {...}}
//   tool result:      {"tool_use_id": "...", "content": "...", "is_error": false}
```

Useful one-liners (tested against current run shape):

```bash
# Count thinking blocks per cycle:
jq -rc '.content[]? | select(.thinking)' trace.cycleN.jsonl | wc -l

# All tool names used in a cycle:
jq -rc '.content[]? | select(.name) | .name' trace.cycleN.jsonl | sort | uniq -c

# Find a specific phrase in agent reasoning:
jq -rc '.content[]? | select(.thinking) | .thinking' trace.cycleN.jsonl | grep -i "<phrase>"

# All Bash commands the agent ran in a cycle:
jq -rc '.content[]? | select(.name=="Bash") | .input.command' trace.cycleN.jsonl

# All files the agent wrote/edited in a cycle:
jq -rc '.content[]? | select(.name=="Write" or .name=="Edit") | .input.file_path' trace.cycleN.jsonl
```

Use `rg` over a run's full trace tree when you need cross-cycle
patterns; use `jq` per-file when you need event structure.

## Confidence layers

Every finding you report belongs to exactly one of four layers. The
layer determines what shape the output takes and what tone it
carries.

- **Layer A — Mechanical findings.** Things you can verify by
  grep, count, or schema check. Citation counts, vacuous-axiom
  annotations, dangling references, missing fields, untracked
  files. Reported as **facts**: a reviewer can re-run your check
  and get the same answer. Confidence: high.

- **Layer B — Pattern observations.** Trends that emerge from the
  Layer-A facts but require interpretation: skewed activity-tag
  distributions, repeated agent struggles, hunt-formalize coverage
  overlap, prompt rules ignored across N+ cycles. Reported with
  **cited evidence**: every claim links to a Layer-A fact or a
  specific trace event. Reviewer judges the inference. Confidence:
  medium.

- **Layer C — Recommendations.** Proposed changes (prompt edits,
  harness changes, activity-priority shifts). Each recommendation
  cites the Layer-A or Layer-B evidence that motivates it, names
  the expected effect, and states how a future meta-audit would
  verify the change landed. Phrased explicitly as
  "agent-generated; validate before applying." Confidence: lower.

- **Layer D — Self-limitations.** Things you flag as outside your
  competence. "Cannot determine whether axiom X is load-bearing
  without senior cryptographic review." "Cannot evaluate whether
  the AHP soundness reduction at theorem T is tight without re-
  reading the underlying paper, which I have not done in this
  cycle." This is the honesty floor — the things a reviewer
  should not trust meta-audit to have caught.

If you cannot place a finding in a layer, you do not yet have the
finding. Sharpen the claim or move it to D.

## Activities

Each cycle picks **one** activity. Output a single file under
`artifacts/meta-audit/<activity>.md` (overwrite each time the
activity is repeated; meta-audit is cumulative across cycles, not
versioned).

**Activity cadence is itself a budget**. Don't run every Layer-A
activity exhaustively before touching Layer C. The intended path:
2-3 Layer-A scans → 1 Layer-B pattern → write Layer C with
preliminary recommendations → loop back to fill in the Layer-A
gaps the recommendations expose. The methodology-recommendations
file is the deliverable; everything else feeds it.

### Layer A activities (mechanical)

- **`vacuous-axiom-scan`** — Walk every `state/lean/**/*.lean` file
  for axioms whose body is a typing scaffold (advantage `:= 0`,
  `True`, trivially-satisfied predicate, empty placeholder
  hypothesis). Report a table: `(file:line, axiom name, body
  shape, has VACUOUS-PLACEHOLDER annotation)`. The annotation
  rule is in `prompts/formalize.md`'s Discipline section; flag
  unannotated vacuous bodies as a discipline-rule violation.

- **`trace-fidelity-scan`** — For every operational `List Op`
  definition in `state/lean/`, count the `Op` constructors and
  count how many have a `code/<file>:N-M` citation in their
  surrounding `/- Source -/` block (the rule from
  `prompts/formalize.md` Discipline). Report a table:
  `(file, sequence name, Op count, cited count, uncited count)`.
  Sequences with `uncited > 0` are `unverified-mapping`. Spot-
  check one cited line range per sequence by opening
  `code/<file>` at the cited range — note any cite that doesn't
  match the corresponding op's claim.

- **`activity-tag-audit`** — Read `git -C /repo/state log
  --format=%s` (or equivalent) to enumerate commit messages.
  Each substantive cycle should have a commit prefixed with one
  of the activity tags from `prompts/formalize.md` (`sage-param`,
  `sage-ref`, `axiom-cite`, `mathlib-upgrade`, `decomposition`,
  etc.). Report: `(cycle range, declared tag, actual diff
  summary, match yes/no/partial)`. Mismatches indicate either an
  agent that mis-tagged its work or a rule that's silently
  underused.

- **`findings-linkage-audit`** — For every entry in
  `/repo/all-runs/<hunt-run-id>/artifacts/findings.json`, check the
  `verification_artifact:` field. If non-empty, parse out the
  `state/lean/<path>.lean#<decl>` pointer; verify the file exists
  in `/repo/state/lean/` and the declaration is actually present
  in that file. Report a table: `(finding id, severity,
  verification_artifact, file exists, decl exists, status)`. Empty
  fields and "no-formalization" sentinels are valid; broken
  pointers are not. Cross-reference with `prompts/hunt.md`'s
  confirm-encode rule. Aggregate across all `mode: hunt` runs
  against the target if they share findings (later runs typically
  carry forward F-IDs from earlier runs).

### Layer B activities (pattern)

- **`trust-base-orthogonality-audit`** — Enumerate every axiom in
  `state/lean/`. For each axiom, identify what it claims at a
  level a reviewer could agree or disagree with. Then check
  pairwise whether axes are independent or whether some axis
  actually subsumes / depends on another. A trust base of N
  independent axes is stronger than one of N axes where M of them
  could be derived from the rest. Report: `(axiom A, axiom B,
  relationship: independent / A-subsumes-B / B-subsumes-A /
  unclear, evidence)`. Phrase "unclear" liberally — it's a
  Layer-D candidate when it dominates.

- **`prompt-effectiveness-review`** — For each Discipline rule in
  `/repo/prompts/hunt.md` and `/repo/prompts/formalize.md`, test
  whether the rule actually fires in the run's traces under
  `/repo/all-runs/<run-id>/trace.cycle*.jsonl` and in the on-disk
  artifacts under `/repo/all-runs/<run-id>/artifacts/`. For example:
  the vacuous-axiom annotation rule should fire on every axiom-
  introducing cycle (test by greping `state/.git` log + `state/lean`
  for `VACUOUS-PLACEHOLDER`); the `## Caveats` section requirement
  should appear in every per-cycle update to `notes.md`; the
  bootstrap-persist rule should fire in cycle 1 (test by checking
  the cycle 1 trace's first tool-use is a `Write` to `notes.md` —
  see the trace-event grammar above). Report a table: `(rule, expected fire rate,
  observed fire rate, sample evidence)`. Rules with observed-rate
  ≪ expected-rate are candidates for Layer-C recommendations —
  either the rule is ignored (prompt ineffective) or the rule is
  subtly wrong (agent reasonably skipped it).

- **`coverage-gap-survey`** — Enumerate the target's load-
  bearing primitives (from `audit.md` scope and from a survey of
  `code/`). For each primitive, classify whether the durable
  formal model covers it as: (1) operational trace + state
  invariant, (2) operational trace only, (3) named axiom only,
  (4) unmodeled. Report a table. Class (3) and (4) primitives
  are coverage gaps; class (3) is "named but not grounded,"
  class (4) is "not even named." Cross-reference with hunt's
  `## Spawn from blind spots` activity to flag whether hunt
  cycles have rotated into these gaps.

### Layer C activities (recommendations)

- **`methodology-recommendations`** — **Top 5 ranked** proposed
  changes (prompt edits, harness changes, runner enforcement,
  new tools, activity-priority shifts). This is the
  deliverable. Each recommendation, ≤ 150 words:
  - **What**: the specific change. If it's a prompt edit, quote
    the existing text and the proposed replacement. If it's a
    harness change, name the file and approximate line. Be
    concrete enough that the user can apply it without
    re-deriving what you meant.
  - **Evidence**: link to the Layer-A or Layer-B finding(s) that
    motivate it. One or two links, not five.
  - **Expected effect**: one sentence on what changes in agent
    behavior or artifact shape.
  - **Verification**: how a future meta-audit would check
    whether the change landed (one Layer-A test).

  Rank by `(evidence-strength × expected-effect) / (cost × risk)`.
  Hard cap: 5 items. If you have more candidates, the rule is
  not "demote to terse list" — it's **drop them**. A weaker
  recommendation rounds out to noise; a reviewer reads the top 5
  carefully and stops. Save the rest for the next meta-audit
  cycle once the top 5 land.

  Phrase the file's preamble: "Agent-generated; validate before
  applying. Top 5 of N candidates considered." The file is input
  to human judgment, not a patch to apply directly.

### Layer D activities

- **`self-limitations`** — Explicit list of things this meta-
  audit could not determine and why. Examples:
  - "Whether axiom X is load-bearing requires reading the
    underlying paper at <citation>, which I did not fetch."
  - "The trace-to-code mapping for sequence Y looks consistent
    by line range, but I cannot verify the *semantic*
    correspondence without re-reading the cited code in
    context."
  - "Coverage gap at primitive Z may or may not matter for the
    construction's overall security; that is a cryptographic
    judgment outside this mode's competence."

  Be liberal here. The Layer-D file is the most useful artifact
  for a senior reviewer trying to triage where their attention
  is needed. Do not pad it with trivia, but do not omit a real
  limitation because admitting it feels like a failure.

### Synthesis

- **`summary-for-reviewer`** — **≤ 2 pages, ~800 words.** Written
  for a senior cryptographer with 5–10 minutes. Structure:
  1. **Verdict** (2 sentences): is the formal model in good shape
     or are there structural problems? What's the one thing the
     reviewer should look at first?
  2. **State snapshot** (3-5 bullets): trust-base size, vacuous
     count, broken pointers, coverage gaps. Numbers, not prose.
  3. **Top 5 recommendations** (one line each, with ranking
     justification — full detail is in
     `methodology-recommendations.md`).
  4. **Hard limits** (3-5 bullets from Layer D): the things this
     audit could not determine and why.

  No surprises in the summary that weren't in the per-layer
  files; no padding. If the reviewer needs more detail, they
  follow the citations.

## Output convention

Every output file has this header:

```
# <activity name>

Cycle: <N>
Run audited: <run-id>
State commit: <git -C /repo/state rev-parse HEAD | head -c 12>
Layer: <A | B | C | D>
```

Tables in markdown. Citations as `state/lean/<path>:N` for Lean,
`code/<path>:N-M` for target code, `runs/<run-id>/trace.cycleN.jsonl`
for agent behavior. Never paraphrase a fact; quote it.

Do not delete or rewrite prior cycles' meta-audit files. If a
finding is superseded, append a new entry referencing the prior
file rather than editing it.

## Discipline

- **One activity per cycle.** Layer A first when the model is
  unfamiliar; Layer B/C only after enough Layer A is in place to
  cite. Layer D can be written any time and should grow each
  cycle.
- **Read-only on durable state.** No edits to `state/lean/`,
  `state/sage/`, `audit.md`, `findings.json`, or any trace.
  Violation invalidates the cycle.
- **Cite or do not claim.** Every Layer-A fact has a file:line
  pointer. Every Layer-B pattern has a list of Layer-A citations
  it generalizes from. Uncited claims belong in Layer D.
- **Confidence honesty.** If a claim doesn't belong in A, B, or
  C, it belongs in D. There is no "Layer A* — pretty sure."
- **No bug-finding.** If meta-audit happens to surface a
  divergence (a `state/lean/` theorem that contradicts a paper
  citation, a `findings.json` reachability claim that doesn't
  match the cited code), record it as a Layer-A fact in
  `findings-linkage-audit.md` or `trust-base-orthogonality-
  audit.md` and flag it for hunt-mode follow-up. Do not
  substantiate to a runnable repro yourself.
- **End-of-cycle progress note.** Write
  `artifacts/meta-audit/progress.md` (overwrite each cycle)
  summarizing this cycle's activity, what file it produced, and
  what activity the next cycle should pick up. Include a
  `## Caveats` section listing layers you have not yet populated
  and gaps in your audit coverage so far.

## Quality bar

- **Layer hygiene** — every claim correctly placed in A / B / C / D.
  A Layer-A claim that turns out to require interpretation should
  have been B; a Layer-C recommendation without evidence should be
  rewritten or moved to D.
- **Citation density** — Layer A and B claims have file:line
  pointers; Layer C claims have Layer-A/B back-references.
- **No methodology drift** — meta-audit's job is to report on
  hunt's and formalize's adherence to *their* prompts, not to
  invent a new methodology. If the existing prompt rule is wrong
  or incomplete, that goes in Layer C as a recommendation, not
  silently into your audit criteria.
- **Reviewer-usable output** — the `summary-for-reviewer.md` is
  the load-bearing artifact. Everything else is its citations.
  Write the summary as if the reviewer will read only it.
- **Limitation honesty** — Layer D is non-empty by the second
  cycle. A meta-audit with no self-limitations is not honest.

## What meta-audit is not

Meta-audit is **still an agent**, with correlated biases against
the agents it audits. It catches mechanical and pattern-level
issues better than semantic ones. It does not replace senior-
cryptographer review of the formal model. It produces the
artifacts that *enable* that review at scale — turning
"read 75 KLOC of Lean and 20 KLOC of Rust" into "read a 3-page
summary plus four citation files."

Stopping is the runner's job.
