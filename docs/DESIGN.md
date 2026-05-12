# Crypto Bug-Finding Harness — Design

This document records the *intent* behind the harness: goals, the design
decisions that aren't self-evident from the code, and the constraints
the design intentionally rejects. For *what* the system does and how to
run it, see `README.md`.

---

## 1. Goal

Find real, substantiated bugs in cryptographic code. A run is successful
if the agent produces findings backed by working reproductions, OR
establishes that no bugs are evident under serious investigation.

The agent's mandate is **goal-directed, not procedural**. It is given a
target, a rich environment, and discretion. Different targets warrant
different approaches: pattern recognition against known-vulnerable
constructions, differential testing against reference implementations,
property-based fuzzing, mathematical modeling, formal stating of
security claims, targeted exploit reproduction. The agent picks.

### Non-goals

- No graders, benchmark scoring, or ablation infrastructure. The user
  reads findings.
- No autoresearch-style scoring loop. Bug-finding doesn't have a clean
  continuous score; the agent's judgment is the integrating function.
- No trace viewer, comparison tool, or finding aggregator.
- No multi-target parallel runs (the Lean workspace is shared per
  container).
- Not a procedural auditor. The harness facilitates investigation; it
  does not enforce a methodology.

---

## 2. Architecture

```
host                                container
─────                                ─────────
scripts/hunt        ─── docker run ──► python -m runner.audit
  │                                      │
  ├─ resolves auth                       ├─ launches adapter (claude | codex)
  ├─ generates run_id                    │     │
  ├─ mounts:                             │     ├─ streams agent CLI output → trace.jsonl
  │   /repo/run     RW (this run only)   │     └─ writes run.json on exit
  │   /repo/run/code RO (target source)  │
  │   /repo/runner  RO                   ├─ MCP: lean.check, lean.save_to_artifact
  │   /repo/instructions, /repo/prompts RO
  │                                      └─ tools: bash, sage, lean, python (no pip)
  └─ scripts/scrub-secrets               
        post-run API key scan
```

Two agents (Claude Code, OpenAI Codex) sit behind a common adapter
interface. Both see an identical workspace and toolchain; swapping is a
one-flag change to `scripts/hunt`. The runner is async Python, minimal:
snapshot inputs, launch adapter, exit.

---

## 3. Methodology

How findings actually emerge from a run.

### 3.1 Cycles

One hypothesis per cycle. Cycle 1 of a run bootstraps a hypothesis queue
from the target's spec and code. Each subsequent cycle picks one open
hypothesis and investigates it within the per-cycle wall-clock cap
(`--cycle-budget`). State accumulates in `artifacts/` across cycles —
`hypotheses.md`, `threat-model.md`, `findings.json`, `notes.md` — and the
agent reads its own prior cycles before choosing the next move.

### 3.2 Two cooperating modes

- **`hunt`** (default) — adversarial. Agent enumerates attacker
  capabilities from `threat-model.md`, generates hypotheses, refutes or
  confirms each with line-cited evidence, and emits findings with
  runnable repros under `artifacts/repro/`.
- **`formalize`** — constructive. Agent grows a cumulative Lean model
  of the target under `<target>/state/`: typed primitives, security
  skeletons with cited assumptions, state-invariant lemmas, decomposed
  proof trees. Bugs surface as divergences between the spec model and
  the implementation trace.

Both modes share `<target>/state/`, which has its own `.git` for
per-cycle history. A formalize batch produces structure (typed ops,
invariants) that the next hunt batch attacks. `--snapshot` lets a hunt
run alongside a formalize run on the same target without conflicting on
`/state`.

### 3.3 Tool stack

The agent picks the tool that fits the property. Three are available:

- **Lean 4 + Mathlib** — primary modeling tool. Two access paths:
  (a) `mcp__lean__check` runs against a long-lived REPL with Mathlib
  preloaded (~30-60s cold cost paid once per session), for tight
  single-snippet iteration; (b) the persistent workspace at
  `/opt/lean-workspace/` plus `lake build`, for multi-file protocol
  modeling. Mathlib's algebra and polynomial libraries cover most
  cryptographic algebra without re-derivation. Empirically the agent
  reaches for Lean by default.
- **SageMath** — numerical experiments, field arithmetic
  counterexamples, parameter validation. Invoked as `sage` in shell;
  no MCP wrapper.
- **Coq + FCF** — game-hop reasoning and advantage bounds, exposed as
  MCP-wrapped tools (`mcp__rocq__*`). Native fit for indistinguishability
  proofs. Empirically latent: in a 3-cycle Schnorr-identification trial
  on textbook game-hop terrain, the codex agent invoked Lean 7 times
  and Coq 0 times. Likely cause: training-data skew toward Lean. Kept
  available for properties Lean handles poorly.

The operator does not prescribe per target; the agent chooses per
cycle. The `formalize` prompt documents the three-tool menu.

### 3.4 Findings trust ladder

Two output tiers (see also §5.7):

- **`findings.json`** — substantiated. Each finding carries a working
  PoC in `artifacts/repro/` or a machine-checked obstruction in
  `artifacts/lean/` / `artifacts/sage/`. Repros run in <30s.
- **`notes.md`** — suspicions and partial leads without proof.

Findings additionally carry a reachability tier (network-reachable,
protocol-reachable with preconditions, API-reachable, internal-only)
and a `verification_artifact` field pointing at the Lean theorem or
PoC script. This splits "real bug" from "real bug that matters in the
deployed system."

---

## 4. Repository Layout

```
README.md             ─ user-facing entry point
docs/                 ─ this document and roadmap
env/                  ─ Dockerfile, requirements.txt, Lean workspace
env/mcp/lean/         ─ Lean REPL wrapped as MCP tools
instructions/         ─ AGENTS.md (loaded as agent system prompt)
prompts/              ─ hunt.md (per-mode user prompts)
runner/
  audit.py            ─ entrypoint
  adapters/{claude,codex}.py
scripts/
  hunt                ─ host-side wrapper (auth + docker run)
  hunt-all            ─ batch over targets/
  hunt-local          ─ no-Docker variant for development
  build-image         ─ docker build wrapper
  scrub-secrets       ─ post-run API key scan
scripts/generate-fixtures   ─ one-time applied-tier fixture generation
targets/{smoke,applied,blind}/<id>/
  code/               ─ what the agent sees (RO bind-mount)
  HUMANS.md           ─ ground truth: bug-class, alias, prior findings
                        (host-only — never bind-mounted)
runs/<timestamp>-<target>-<agent>/  ─ output, one dir per run
```

---

## 5. Design Decisions

### 5.1 Anonymized target IDs

Targets are named `smoke-NN` / `applied-NN`. The descriptive alias and
the bug class live in `HUMANS.md` next to the target — but only `code/`
is bind-mounted into the container, so the agent sees a numeric ID and
the source. A name like `textbook-rsa` would telegraph the answer.

### 5.2 Per-run output isolation

The host generates `run_id` and creates `runs/<run_id>/` *before*
launching the container, then bind-mounts only that directory as the
agent's writable workspace. The agent cannot see prior runs; otherwise
it could trivially copy past findings, reproductions, and traces.

### 5.3 Open network, open package install

The container has unrestricted outbound network so the agent can
research CVEs, papers, and advisories. Package managers (`pip`, `npm`,
`apt`) are available at runtime so the agent can install target
dependencies and analysis tools. The container is ephemeral — installs
don't persist beyond the run. The safety boundary is the container
itself (resource limits, tmpfs HOME, no host mounts beyond the run dir
and target code).

### 5.4 Pinned agent CLI versions

`@anthropic-ai/claude-code` and `@openai/codex` are pinned to specific
versions in the Dockerfile, not `@latest`. CLI flag and SDK API drift
breaks the adapters within weeks. If you upgrade, run smoke targets
under both agents before merging.

### 5.5 Auth strategy differs by agent

- **Claude.** Two env-var paths, no file mounting. The short-lived
  OAuth tokens in `~/.claude/.credentials.json` (what the local
  `claude` CLI uses, and what tools like `claude-creds` materialize
  from the macOS Keychain) expire in ~10-15 minutes and can't be
  refreshed non-interactively, so mounting that file into the
  container is a dead end. Instead:
  - **`CLAUDE_CODE_OAUTH_TOKEN`** — long-lived (1-year) token minted
    via `claude setup-token` on the host. Bills against Max-plan
    quota for Max members. Preferred when present.
  - **`ANTHROPIC_API_KEY`** — console-issued API key. Bills at
    per-token API pricing, **separate** from any Max-plan subscription.

  `scripts/hunt` prefers the OAuth token over the API key when both
  are set on the host, and forwards *only one* of them into the
  container. This matters because Claude Code's own resolution order
  prefers `ANTHROPIC_API_KEY` if it sees both — which would silently
  switch billing from "consumed Max quota" to "fresh per-token API
  charges", a footgun worth avoiding. `scripts/hunt-local` bypasses Docker and uses the host
  CLI's normal OAuth path directly — it doesn't need either env var.

- **Codex.** `~/.codex/auth.json` is a real file holding a
  ChatGPT-account OAuth token that the codex CLI **auto-refreshes**,
  so we mount it RO at `/auth_src` and let the runner copy it into a
  writable tmpfs `HOME` at run start. Host file stays immutable.
  Falls back to `OPENAI_API_KEY` if the token isn't present.

The asymmetry is irreducible — it reflects how each vendor packages
auth and refresh — and is documented in comments next to the code in
`scripts/hunt`.

**Security caveats baked into the design.** Token lifetime is fixed
per vendor (1y for Claude OAuth, undocumented for Codex), with no
flag to issue shorter-lived tokens. Anthropic `sk-ant-*` API keys
are recognized by GitHub's secret-scanning partner program; OAuth
tokens are not. Anthropic's console allows revocation of API keys
but has no documented UI for revoking individual `CLAUDE_CODE_OAUTH_TOKEN`
values. The harness counters all of this with three layers: the
`scrub-secrets` post-run scanner catches leakage into artifacts, the
`runs/*` gitignore prevents accidental commits, and credentials are
only ever passed as env vars (never on a command line where `ps`
could observe them).

### 5.6 Run identity passed as CLI args, not env

`RUN_ID`, `TARGET_NAME`, `IMAGE_DIGEST`, `GIT_SHA` are passed to
`runner.audit` as CLI flags rather than environment variables. The
agent has shell access; if these were in the environment, `env` or
`printenv` would reveal the target's identity. CLI args land in
`run.json` for the host but are invisible to the agent's bash sessions.

### 5.7 Two-tier findings bar

- `artifacts/findings.json` — substantiated. Working PoC in
  `artifacts/repro/` OR a machine-checked obstruction in
  `artifacts/lean/` or `artifacts/sage/`. Reproductions run in <30s.
- `artifacts/notes.md` — suspicions, partial leads, hypotheses without
  proof. Lower bar, useful for follow-up.

The split exists so the agent isn't pressured to pad `findings.json`
with speculation. A finding without a runnable reproduction is a note,
not a finding.

### 5.8 Lean MCP wraps a long-lived REPL

`mcp__lean__check` runs against an in-memory Lean environment that
persists across calls within a session, so the cost of `import Mathlib`
(~30-60s cold) is paid once. `lake build` would re-pay it each time.
The MCP server restarts the REPL on timeout or crash. For protocol-level
modeling that needs imports across multiple files, the agent writes
files into `/opt/lean-workspace/` and uses `lake build`; for tight
single-snippet iteration, the MCP is preferred.

### 5.9 Runs are serial

The Lean workspace at `/opt/lean-workspace/` is shared and writable;
concurrent hunts against the same image race on it. The harness does
not coordinate — it's the operator's responsibility to run one at a
time per image.

### 5.10 Post-run secret scrubber

`scripts/scrub-secrets` greps the run directory for `sk-ant-…`,
`sk-proj-…`, and generic `sk-…` patterns after each hunt and exits
non-zero on hit. API keys live only in the running container's memory,
but a confused agent could write one into `notes.md`. The scan is
small; do not skip it.

### 5.11 Layered budget model

Five plausible budget knobs, three layers, one knob per layer:

| Layer | Knob | Enforced by | Catches |
|---|---|---|---|
| Investigation depth | `--cycles N` | Runner loop | "How much work" — primary control |
| Per-cycle wall-clock | `--cycle-budget SEC` | `asyncio.wait_for` inside the runner | One stuck cycle |
| Container hard-kill | `--timeout SEC` | `timeout(1)` around `docker run` | Wedged container ignoring asyncio cancellation |

Each layer is the only mechanism that catches its failure mode. Combining
them under "wall-clock budget" hides which one tripped. We deliberately
do *not* expose a `--overall-budget` knob: `cycles × cycle-budget` already
implies a soft total, and `--timeout` is the hard backstop.

No model-side caps live on top of the three layers. The Claude SDK's
`max_turns` defaults to `None` (unbounded) and is left at that — the
`asyncio.wait_for` cycle-budget is the real per-cycle limit, and
adding an iteration cap on top only obscures which limit tripped.
Cost is bounded implicitly by `cycles × cycle-budget × API-rate`,
not by a separate spend cap.

### 5.12 Uniform `--model` and `--effort` flags

`scripts/hunt --model VENDOR_STRING` is passed unchanged to whichever
adapter is active. Each adapter resolves it vendor-side: Claude sets
`ClaudeAgentOptions.model`; Codex passes it as `codex exec --model`.
There is no aliasing or validation — `--model sonnet` is not normalized
to `claude-sonnet-4-6`. The asymmetry in default behavior matters:
Claude omitted = SDK default; Codex omitted = `gpt-5.5` baked into the
adapter (the latest model the ChatGPT-account OAuth path supports).

`--effort LEVEL` (low | medium | high | xhigh | max) follows the same
pattern: same flag, different vendor mapping. Codex receives it as
`codex exec --config model_reasoning_effort="<level>"`; Claude receives
it as `ClaudeAgentOptions.effort`. Higher levels generally produce
better adversarial reasoning (formalize Substance work, hunt deep code
reading) at the cost of longer per-cycle wall-clock. Pair with a
correspondingly higher `--cycle-budget` (e.g. `--effort xhigh
--cycle-budget 1200`) so deep cycles don't get cut off mid-tool-use.

### 5.13 Snapshot mode for parallel runs

`scripts/hunt --snapshot` creates a `git worktree` of the target's
`state/` pinned at the current HEAD, then mounts that worktree (not
the live state) into the container. A hunt run with `--snapshot` and
a formalize run on the same target's live state can execute in
parallel without conflicting on `/repo/state`: formalize keeps writing
to `<target>/state/` (HEAD advances), hunt sees a frozen snapshot.

The worktree lives at `<target>/.snapshots/<run-id>/`. On run exit, if
the worktree's HEAD differs from the snapshot ref (the agent committed
something), the worktree is preserved and the operator gets a
`git merge <commit>` instruction; otherwise it's removed silently.

`max_turns` defaults to `None` (per the SDK), so the only per-cycle
limit is `--cycle-budget`. This keeps the budget surface to three
flags (cycles / cycle-budget / timeout) regardless of effort level.

### 5.14 Container memory of the agent's HOME

The container is launched with `--user $(id -u):$(id -g)` and a tmpfs
`/home/audit` (size 128M, owned by that uid). The agent's HOME is
ephemeral per run. Codex auth files copied from `/auth_src` land here
and vanish at container exit; the host originals stay RO and unmodified.

---

## 6. Findings Schema

`artifacts/findings.json`:

```json
{
  "findings": [
    {
      "id": "F1",
      "bug_class": "rsa_no_padding | nonce_reuse | ...",
      "severity": "CRITICAL|HIGH|MEDIUM|LOW",
      "location": {"file": "code/...", "lines": [start, end]},
      "summary": "what is wrong and why it matters",
      "approach": "pattern_matching | differential_test | property_test | sage_modeling | lean_stating | exploit_reproduction",
      "repro": "artifacts/repro/<filename>",
      "verification_artifact": "artifacts/lean/<file>.lean | artifacts/sage/<file>.sage",
      "evidence": "what running the repro shows",
      "references": ["optional URLs"]
    }
  ]
}
```

Always valid JSON. If no substantiated findings, emit `{"findings": []}`
and put observations in `notes.md`.

---

## 7. Constraints — Do Not

- Add a grader, scoring loop, intensification phase, or benchmark.
- Add a trace viewer, comparison tool, or finding aggregator (out of
  scope; the user reads files directly).
- Generalize "agent backend" beyond the two adapters. A third adapter
  is fine; an abstract framework is not.
- Restrict the container's network. The agent's web research is
  essential to the goal-directed approach.
- Skip `scrub-secrets`. Small cost, high downside if missed.
- Bind-mount `HUMANS.md` or any sibling of `code/`. The anonymization
  story depends on the agent only seeing `code/`.
- Run multiple hunts concurrently against the same image (Lean
  workspace is shared).
- Add a budget knob without showing where it slots into the three-layer
  model in §5.11. Five overlapping budget flags is what we just removed.
- Reintroduce env vars for operator knobs. Credentials stay as env vars
  (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`) because they belong on no
  command line; everything else is a flag on `scripts/hunt`.
