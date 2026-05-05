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
- Locked-down package installation: the agent cannot pull arbitrary code
  via pip/npm at runtime.
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

3. Set your API key:

   ```bash
   export ANTHROPIC_API_KEY=sk-ant-...
   # or
   export OPENAI_API_KEY=sk-...
   ```

## Running a Hunt

Targets are anonymized (`smoke-NN`, `applied-NN`) so the agent works
from code alone, not from a name that telegraphs the bug. Each target's
expected findings live in `targets/<id>/HUMANS.md` — the host can read
them, the agent cannot (only `code/` is bind-mounted).

```bash
./scripts/hunt targets/smoke/smoke-14
./scripts/hunt targets/smoke/smoke-14 codex
./scripts/hunt targets/applied/applied-11
```

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
└── trace.jsonl            # full message stream
```

## Inspecting Output

```bash
cat runs/<run-id>/artifacts/findings.json | jq .
cat runs/<run-id>/artifacts/notes.md
less runs/<run-id>/trace.jsonl
jq -c 'select(.type == "tool_use")' runs/<run-id>/trace.jsonl

# Run a reproduction
python3 runs/<run-id>/artifacts/repro/exploit.py
```

## Comparing Agents

Run both on the same target, then read their findings.json side by side:

```bash
./scripts/hunt targets/smoke/smoke-14 claude
./scripts/hunt targets/smoke/smoke-14 codex

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

- **The agent cannot install new packages.** `pip`, `npm`, `apt` are
  disabled. The pre-installed library set is final. If you find the
  agent reaching for libraries not pre-installed, add them to
  `env/requirements.txt` and rebuild.

- **API keys are passed via environment variable** and only exist in
  the running container's memory. The post-run scrubber checks for
  accidental key leakage into artifacts.

- **No grader.** Read the findings yourself.

## Targets

Targets are organized into two tiers and identified by opaque numeric IDs
to keep names from telegraphing the bug class to the agent:

- `targets/smoke/smoke-01` … `smoke-17` — quick wins, 1–3 min per run
- `targets/applied/applied-01` … `applied-33` — real attacks, 2–6 min per run

For each `<id>`, `targets/<tier>/<id>/HUMANS.md` records the function-style
alias, original bug-class name, and the findings observed from prior sweeps.
The agent never sees this file (only `code/` is bind-mounted).

## Troubleshooting

**Build fails on Mathlib step.** `lake exe cache get` fetches Mathlib's
cache from GitHub. If GitHub rate-limits, wait and retry. The Docker
layer caches the built workspace so subsequent builds skip this.

**Agent runs but produces no findings.json.** Check `trace.jsonl` for
tool errors. Most common causes: MCP server failure (Lean REPL crashed
and didn't recover), or the agent's max-turns budget exhausted before
finishing. Inspect the tail of the trace.

**Agent runs out of turns.** Default is 100 turns. Invoke
`python3 -m runner.audit <target> --agent claude --max-turns 200`
inside the container, or extend the wrapper to forward the flag.

**File ownership is root.** The wrapper passes `--user $(id -u):$(id -g)`;
if you bypass it, fix ownership with `sudo chown -R $(id -u):$(id -g) runs/`.

**Package install attempts succeed.** This shouldn't happen — the
Dockerfile disables pip/npm/apt. If it does, the lockdown layer didn't
apply correctly. Verify with `docker run --rm crypto-audit:latest
python3 -m pip install requests`; the command should fail.
