# Showcase Plan — `runs/published/`

Curate `runs/published/` so a first-time visitor can read:

- a hero deep-dive that shows the methodology end-to-end,
- supporting demos that prove the methodology generalizes,
- a baseline target showing the harness handles easy cases,
- with **both agents** (Claude, Codex) running **both ongoing modes**
  (formalize → hunt) on each — to demonstrate parity.

Operator does not prescribe Lean / Sage / Coq per target. The agent
picks the tool based on what the property looks like, per the
formalize prompt's three-tool selection guide. The showcase
*documents* which tools the agent ended up using; it does not pre-
assign them.

## Targets

| Target | Bug class | Role | Notes |
|---|---|---|---|
| **applied-21 frozen-heart** | Fiat-Shamir transcript ordering | HERO | Already has deep state under `runs/published/formalize-hunt/applied-21-frozen-heart/state/` — 7 Lean files in `PolyCommit/`, 3-layer F1 substantiation. Fill in the missing codex dirs + comparison.md. |
| **applied-04 unconstrained-circuit** | Missing R1CS constraint | Supporting | Different bug class entirely. Tests whether the methodology generalizes from transcript-ordering to constraint-coverage. |
| **applied-33 groth16-commit** | Protocol-level commitment binding | Supporting | Different SNARK construction. Likely candidate for the agent to reach for Coq+FCF if it decides advantage-style modeling fits. |
| **smoke-14 textbook-rsa** | Pattern-matchable RSA bug | Baseline | Lower-bound demo. Hunt only, ~1-2 cycles, both agents. |

Drop from current published set (insufficient depth, not load-
bearing): `applied-03 hostile-witness`, `applied-05 protocol-binding`,
`applied-16 auth-reflection`. They remain in the test suite under
`targets/applied/` — just not in the showcase.

## Per-target deliverable

Each showcased target produces this layout under
`runs/published/formalize-hunt/<target>-<bug>/`:

```
formalize-claude/
  artifacts/findings.json
  artifacts/notes.md
  trace.cycle<NN>.jsonl       # ONE representative cycle (operator picks)
  trace.cycle<NN>.summary.md  # ~10-line hand-written summary of that cycle
  run.json
formalize-codex/              # same shape
hunt-claude/                  # same shape
hunt-codex/                   # same shape
state/
  lean/Audit/...              # whatever the agent built
  sage/                       # if the agent reached for Sage
  coq/                        # if the agent reached for Coq+FCF
  git-history.log             # flattened per-cycle commits from <target>/state/.git
comparison.md                 # side-by-side findings table, ~30 lines
```

The baseline (smoke-14) skips formalize cells (Python target, no
Lean modeling needed) — only hunt-claude / hunt-codex.

## Run parameters

- **Cycles per cell:** 5 for applied targets, 1-2 for smoke
- **Cycle budget:** 1200s (xhigh effort needs headroom)
- **Effort:** `xhigh` for applied, `medium` for smoke
- **Snapshot:** off (we want full state persistence per cell)

## Trace curation

Per cell, ship ONE trace file, not all of them. Each trace cycle is
1-2 MB; full set bloats `runs/published/` to no informational gain.
Pick the cycle that shows substantive work — the one that produced a
finding, decomposed an axiom, or did a state-invariant. Add a sibling
`trace.cycle<NN>.summary.md` with ~10 lines:

- activity tag (`state-invariant`, `decomposition`, `paper-pull`, ...)
- one-paragraph plain-English summary of what the agent did
- key line citations from the agent's reasoning

This lets viewers skim chain-of-thought without parsing JSONL.

## Top-level navigation

Add `runs/published/HIGHLIGHTS.md` (~80 lines):

- one-paragraph project pitch (echoes README)
- 3 hero findings with line cites, agent, cycle
- link to applied-21 as the deep dive

Update `runs/published/README.md`:

- index card per showcased target with a one-line description
- "Read these first" pointer to HIGHLIGHTS.md and applied-21

## Phases

1. **Re-run the 14 cells** (3 applied × 4 + 1 smoke × 2 = 14)
   - applied-21, applied-04, applied-33: claude/codex × formalize/hunt
   - smoke-14: claude/codex × hunt only
   - Parallel where possible (use `--snapshot` for hunt against formalize state)
   - Wall-clock: ~6-10 hours on the high-Claude-limit machine
2. **Curate traces** — pick one cycle per cell, write summary.md
3. **Write `comparison.md`** per target — claude vs codex findings, vs ground-truth bug class
4. **Write `HIGHLIGHTS.md` and update `runs/published/README.md`**
5. **`scripts/republish` update** — flatten state's inner `.git`,
   pick a representative trace cycle, write summary stubs
6. **Final scan** — PII, snarkvm references, API keys, link check

## Execution location

The high-Claude-limit machine. This machine has `~/.codex/auth.json`
but Claude credentials.json only (~15-min TTL), so 5-cycle runs would
fail mid-stream. The other machine has `CLAUDE_CODE_OAUTH_TOKEN`
(1-year TTL) and is where ongoing work has migrated.

## Effort estimate

| Phase | Wall-clock | Hands-on |
|---|---|---|
| 1. Re-run cells | 6-10 hours | 30 min (launch + monitor) |
| 2. Curate traces | — | 30 min |
| 3. comparison.md × 3 | — | 30 min |
| 4. HIGHLIGHTS.md + README | — | 30 min |
| 5. republish alignment | — | 30 min |
| 6. Final scan | — | 5 min |
| **Total** | **6-10 hrs** | **~2.5 hrs** |
