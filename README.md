# Crypto Bug-Finding Harness

A goal-directed cryptographic bug finder, driven by either Claude Code or
OpenAI Codex. Both agents see an identical workspace and toolchain — swap
between them with a flag.

The harness is **goal-directed**: the agent's mandate is to find real bugs.
Audit methodology is one means among several, not a fixed procedure. The
agent reads the target, judges what's most likely to expose bugs, and
pursues it. Approaches available include pattern matching against known
constructions (with web research), differential testing, property-based
fuzzing, mathematical modeling in SageMath, formal stating in Lean, and
targeted exploit reproduction. The agent picks and combines.

## What's in the Box

- A Docker image with Lean 4 (Mathlib pre-cached), SageMath, Python crypto
  libraries, both agent CLIs, and a Lean MCP server.
- Unrestricted outbound network for the agent to research CVEs, papers,
  documentation, and advisories.
- Open package installation: the agent can install target dependencies
  and analysis tools at runtime (`pip`, `npm`, `apt`). The container is
  ephemeral, so installs don't persist beyond the run.
- A fixed set of small buggy programs (`targets/smoke/`, `targets/applied/`)
  exercising different bug-finding approaches.
- A Python runner that snapshots a target into a per-run directory, runs
  the chosen agent, and writes findings + trace to the host filesystem.

## Setup

Requires Docker and an API key for whichever agent you use.

1. Build the image:

   ```bash
   ./scripts/build-image
   ```

   First build is slow — Mathlib takes 15-25 minutes. Cached for subsequent builds.

2. Generate applied-tier fixtures (one time):

   ```bash
   python3 setup/generate_fixtures.py
   ```

3. Set your credentials. The harness consults env vars for both
   agents — auth files (`~/.claude/.credentials.json`,
   `~/.codex/auth.json`) are *not* mounted into the container for
   Claude because the OAuth tokens those files hold expire in
   ~10–15 minutes and can't be refreshed non-interactively.

   **Claude** — pick one (preferred first):

   ```bash
   # Long-lived (1-year) OAuth token; bills against your Max plan.
   # Mint once on the host:
   claude setup-token
   export CLAUDE_CODE_OAUTH_TOKEN=<the-token-it-prints>

   # Or, console-issued API key (bills per-token at API pricing,
   # separate from any Max-plan subscription):
   export ANTHROPIC_API_KEY=sk-ant-...
   ```

   If both are set on the host, `scripts/hunt` forwards only the OAuth
   token to the container, because Claude Code itself prefers
   `ANTHROPIC_API_KEY` when both are visible — and you usually want
   Max-plan billing, not separate API charges.

   **Codex** — the codex CLI's OAuth file at `~/.codex/auth.json` *is*
   long-lived and self-refreshing, so we mount it directly:

   ```bash
   codex login        # one-time, creates ~/.codex/auth.json
   # or
   export OPENAI_API_KEY=sk-...
   ```

   For Claude OAuth without minting a token (uses your local
   keychain login directly), use `./scripts/hunt-local <target>` — it
   skips Docker entirely. Fewer isolation guarantees, but no token
   handling.

   **Security caveats.** `CLAUDE_CODE_OAUTH_TOKEN` has a fixed 1-year
   lifetime — there's no flag to issue shorter-lived tokens. Anthropic
   API keys (`sk-ant-*`) are scanned by GitHub's secret-scanning
   partner program; OAuth tokens are not (publicly) scanned and have
   no documented revocation UI. Treat the OAuth token like an
   ssh private key: never commit, rotate via `claude setup-token`
   periodically, and assume console revocation is the only recovery
   path if leaked.

## Running a Hunt

Targets are anonymized (`smoke-NN`, `applied-NN`) so the agent works
from code alone, not from a name that telegraphs the bug. Each target's
expected findings live in `targets/<id>/HUMANS.md` — the host can read
them, the agent cannot (only `code/` is bind-mounted).

```bash
./scripts/hunt targets/smoke/smoke-14
./scripts/hunt targets/smoke/smoke-14 --agent codex
./scripts/hunt targets/applied/applied-11 --model claude-sonnet-4-6
```

### Flags

All operator knobs live on `scripts/hunt`. The only env vars consulted
are credentials (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`).

| Flag | Default | What |
|---|---|---|
| `--agent claude\|codex` | `claude` | Backend |
| `--mode NAME` | `hunt` | Resolves to `prompts/<NAME>.md` |
| `--model VENDOR_STRING` | adapter default | Passed unchanged to the SDK / CLI |
| `--effort LEVEL` | adapter default | Reasoning effort: `low\|medium\|high\|xhigh\|max`. Codex maps to `model_reasoning_effort`; Claude maps to `ClaudeAgentOptions.effort` |
| `--cycles N` | 10 | Investigation cycles (primary control) |
| `--cycle-budget SEC` | 600 | Wall-clock cap per cycle (asyncio cancel) |
| `--snapshot` | off | Mount an isolated git-worktree snapshot of `<target>/state` instead of the live state. Lets a hunt run alongside a formalize run on the same target without conflicting on `/repo/state`. |
| `--timeout SEC` | 7200 | Container hard-kill backstop (host-side `timeout(1)`) |

### Time and turn budgets

Three layers, each catches a different failure mode:

1. **Investigation depth** — `--cycles N`. Each cycle picks one open
   hypothesis and investigates it. This is the natural unit of progress.
2. **Per-cycle wall-clock** — `--cycle-budget SEC`. Cancels a stuck
   cycle without aborting the run. Enforced inside the container by
   `asyncio.wait_for`.
3. **Container hard-kill** — `--timeout SEC`. Last resort if the
   container itself wedges (Docker hang, Lean REPL deadlock,
   uncatchable subprocess). Enforced on the host by `timeout(1)`.

No SDK-side iteration or spend caps live above these. The Claude SDK's
`max_turns` defaults to `None` (unbounded); cycle-budget is the per-
cycle limit, and total cost is bounded implicitly by
`cycles × cycle-budget × API-rate`.

Output lands in `runs/<timestamp>-<target>-<agent>/`:

```
runs/20260504-143022-smoke-14-claude/
├── code/                  # snapshot of the target
├── artifacts/
│   ├── findings.json      # the deliverable
│   ├── notes.md           # agent's working notes
│   ├── repro/             # PoC scripts
│   ├── sage/              # SageMath models, if any
│   └── lean/              # Lean files, if any
├── trace.cycle01.jsonl    # message stream, cycle 1
├── trace.cycle02.jsonl    # message stream, cycle 2
└── ...                    # one trace file per cycle
```

## Inspecting Output

```bash
cat runs/<run-id>/artifacts/findings.json | jq .
cat runs/<run-id>/artifacts/notes.md
less runs/<run-id>/trace.cycle*.jsonl
jq -c 'select(.type == "tool_use")' runs/<run-id>/trace.cycle*.jsonl

# Run a reproduction
python3 runs/<run-id>/artifacts/repro/exploit.py
```

## Comparing Agents

Run both on the same target, then read their findings.json side by side:

```bash
./scripts/hunt targets/smoke/smoke-14 --agent claude
./scripts/hunt targets/smoke/smoke-14 --agent codex

ls -la runs/*-smoke-14-*/artifacts/findings.json
```

The trace files look different (Claude's uses SDK message objects, Codex's
uses CLI JSON output) but the artifacts directory has the same structure
and is directly comparable.

## Auditing Your Own Code

Create a directory with a `code/` subdirectory:

```
my-target/
└── code/
    └── crypto_lib.py
```

Then:

```bash
./scripts/hunt my-target/
```

## Notes and Caveats

- **Runs are serial.** The Lean workspace is shared; do not run multiple
  hunts against the same image concurrently.

- **The container has unrestricted outbound network access** so the agent
  can research CVEs, papers, and documentation. This means web queries
  pass through normal search engines and are subject to their logging
  policies. If you're auditing code under NDA or otherwise sensitive,
  factor this in.

- **The agent can install packages at runtime** (`pip`, `npm`, `apt`).
  The container is ephemeral — installs vanish at exit. If the agent
  consistently needs a library, add it to `env/requirements.txt` and
  rebuild to avoid re-downloading each run.

- **API keys are passed via environment variable** and only exist in
  the running container's memory. The post-run scrubber checks for
  accidental key leakage into artifacts.

- **No grader.** Read the findings yourself.

## Targets

Targets are organized into tiers and identified by opaque numeric IDs
to keep names from telegraphing the bug class to the agent:

- `targets/smoke/smoke-01` … `smoke-17` — quick wins, 1–3 min per run
- `targets/applied/applied-01` … `applied-33` — real attacks, 2–6 min per run
- `targets/blind/blind-01` … `blind-03` — sanitization probes; not part
  of routine sweeps (`hunt-all blind` to run explicitly)
- `targets/production/` — real-world codebases (snarkVM, py_ecc,
  python-ecdsa, vodozemac, libsecp256k1, etc.). Named descriptively
  since anonymization is irrelevant for published code.
- `targets/private/` — **gitignored.** Drop third-party or
  pre-disclosure code here for ad-hoc audits.

For smoke/applied/blind targets, `targets/<tier>/<id>/HUMANS.md` records
the function-style alias, original bug-class name, and the findings
observed from prior sweeps. The agent never sees this file (only `code/`
is bind-mounted).

## Troubleshooting

**Build fails on Mathlib step.** `lake exe cache get` fetches Mathlib's
cache from GitHub. If GitHub rate-limits, wait and retry. The Docker
layer caches the built workspace so subsequent builds skip this.

**Agent runs but produces no findings.json.** Check `trace.jsonl` for
tool errors. Most common causes: MCP server failure (Lean REPL crashed
and didn't recover), or the cycle hit `--cycle-budget` mid-tool-use.
Inspect the tail of the trace; if `stop_reason: tool_use` and the wall
clock approaches the budget, raise `--cycle-budget`.

**Cycle ends mid-investigation.** Default budget is 600s. Raise it
with `--cycle-budget 1200` on `scripts/hunt`. At higher reasoning
effort (`--effort high|xhigh`) cycles run longer; budgets in the
1000-1500s range are reasonable.

**File ownership is root.** The wrapper passes `--user $(id -u):$(id -g)`;
if you bypass it, fix ownership with `sudo chown -R $(id -u):$(id -g) runs/`.

**Package installs are slow.** Packages are downloaded each run since
the container is ephemeral. If the agent consistently needs a library,
add it to `env/requirements.txt` and rebuild the image.
