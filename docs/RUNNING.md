# Running

```bash
./scripts/hunt targets/smoke/smoke-14
./scripts/hunt targets/smoke/smoke-14 --agent codex
./scripts/hunt targets/applied/applied-11 --model claude-sonnet-4-6 --effort high
```

## Modes

The `--mode NAME` flag resolves to `prompts/<NAME>.md`. Two modes are
shipped:

- **`hunt`** (default) — adversarial bug-finding cycles. Agent
  investigates one open hypothesis per cycle, refutes or confirms with
  line-cited evidence, and writes findings to `findings.json` with
  runnable repros.
- **`formalize`** — formal-modeling cycles. Agent grows a cumulative
  Lean model of the target's protocol (typed `Op` family, state-machine
  invariants, decomposed proof trees, hardness axioms). Findings emerge
  from divergences the model exposes.

The two modes share the same per-target durable state at
`<target>/state/`. A formalize batch produces structure that the next
hunt batch attacks. Run them sequentially or in parallel via
`--snapshot` (below).

## Flags

All operator knobs live on `scripts/hunt`. The only env vars consulted
are credentials.

| Flag | Default | What |
|---|---|---|
| `--agent claude\|codex` | `claude` | Backend |
| `--mode NAME` | `hunt` | Resolves to `prompts/<NAME>.md` |
| `--model VENDOR_STRING` | adapter default | Passed unchanged to the SDK / CLI |
| `--effort LEVEL` | adapter default | Reasoning effort: `low\|medium\|high\|xhigh\|max`. Codex maps to `model_reasoning_effort`; Claude maps to `ClaudeAgentOptions.effort` |
| `--cycles N` | 10 | Investigation cycles (primary control) |
| `--cycle-budget SEC` | 600 | Wall-clock cap per cycle (asyncio cancel) |
| `--snapshot` | off | Run against an isolated git-worktree snapshot of `<target>/state`, so a hunt run alongside a formalize run won't conflict on `/repo/state`. |
| `--timeout SEC` | 7200 | Container hard-kill backstop (host-side `timeout(1)`) |

## Time / cost budgets

Three layers, each catches a different failure mode:

1. **Investigation depth** — `--cycles N`. Each cycle picks one open
   hypothesis and investigates it. Primary unit of progress.
2. **Per-cycle wall-clock** — `--cycle-budget SEC`. Cancels a stuck
   cycle without aborting the run. Enforced inside the container by
   `asyncio.wait_for`.
3. **Container hard-kill** — `--timeout SEC`. Last resort if the
   container itself wedges. Enforced on the host by `timeout(1)`.

No SDK-side iteration or spend caps live above these. The Claude SDK's
`max_turns` defaults to `None` (unbounded); cycle-budget is the per-
cycle limit, and total cost is bounded implicitly by
`cycles × cycle-budget × API-rate`.

At higher reasoning effort (`--effort high|xhigh|max`) cycles run
longer; budgets in the 1000-1500s range are reasonable.

See `docs/DESIGN.md` §5.11 for the rationale.

## Snapshot pipeline (parallel formalize + hunt)

`scripts/hunt --snapshot` creates a git worktree of the target's
`state/` pinned at HEAD, mounts that into the container instead of the
live state. A formalize run on the same target's live state and a
hunt run with `--snapshot` can execute concurrently — formalize's
writes don't disturb the hunt's view, and the hunt agent never touches
formalize's working directory.

Worktrees live at `<target>/.snapshots/<run-id>/` and are cleaned up
on run exit unless the agent committed to them (in which case the
worktree is preserved with a `git merge` instruction printed to stderr).

```bash
# Two parallel runs, codex agent, gpt-5.5 high effort
./scripts/hunt targets/private/<target> --agent codex --mode formalize \
    --cycles 50 --cycle-budget 1200 --effort high &

sleep 5  # let formalize establish HEAD before snapshotting

./scripts/hunt targets/private/<target> --agent codex --mode hunt --snapshot \
    --cycles 50 --cycle-budget 1200 --effort high &

wait
```

## Output structure

Each run writes to `runs/<timestamp>-<target>-<agent>/`:

```
runs/20260504-143022-smoke-14-claude/
├── code/                # target source snapshot
├── audit.md             # operator context (if present)
├── artifacts/
│   ├── findings.json    # the deliverable
│   ├── notes.md         # agent's working notes
│   ├── repro/           # PoC scripts
│   ├── sage/            # SageMath models, if any
│   └── lean/            # Lean files (most live in <target>/state/lean/)
├── trace.cycle01.jsonl  # one trace file per cycle
└── run.json             # cycles, durations, model, effort, status
```

Inspect:
```bash
jq . runs/<run-id>/artifacts/findings.json
cd runs/<run-id>/artifacts/repro/<finding-id> && ./run.sh
```

Compare agents by running both on the same target — `runs/*-smoke-14-*/artifacts/findings.json` will sit side by side. Trace encodings differ (Claude SDK vs Codex CLI JSON) but `artifacts/` shape is identical.

To audit your own code, drop it into a target directory with a `code/` subdir (and optional `audit.md`), then `./scripts/hunt my-target/`. Pre-disclosure code goes under `targets/private/` (gitignored).

## Sweeping a tier

`scripts/hunt-all` runs `scripts/hunt` sequentially across every target
in a tier. A single target failing doesn't abort the rest.

```bash
./scripts/hunt-all                # smoke tier, claude (default)
./scripts/hunt-all applied        # applied tier, claude
./scripts/hunt-all applied codex  # applied tier, codex
./scripts/hunt-all blind          # blind tier
```

Aggregate results across the run set:

```bash
cat runs/*/run.json | jq -s 'sort_by(.target_name)
  | .[] | {target: .target_name, agent, n_findings,
            exit_reason, duration_seconds}'
```

