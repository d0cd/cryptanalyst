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

## 3. Repository Layout

```
README.md             ─ user-facing entry point
docs/                 ─ this document and roadmap
env/                  ─ Dockerfile, requirements.txt, Lean workspace
mcp_servers/lean/     ─ Lean REPL wrapped as MCP tools
instructions/         ─ AGENTS.md (loaded as agent system prompt)
prompts/              ─ hunt.md, formal.md (per-mode user prompts)
runner/
  audit.py            ─ entrypoint
  adapters/{claude,codex}.py
scripts/
  hunt                ─ host-side wrapper (auth + docker run)
  hunt-all            ─ batch over targets/
  hunt-local          ─ no-Docker variant for development
  build-image         ─ docker build wrapper
  scrub-secrets       ─ post-run API key scan
setup/generate_fixtures.py  ─ one-time applied-tier fixture generation
targets/{smoke,applied,blind}/<id>/
  code/               ─ what the agent sees (RO bind-mount)
  HUMANS.md           ─ ground truth: bug-class, alias, prior findings
                        (host-only — never bind-mounted)
runs/<timestamp>-<target>-<agent>/  ─ output, one dir per run
```

---

## 4. Design Decisions

### 4.1 Anonymized target IDs

Targets are named `smoke-NN` / `applied-NN`. The descriptive alias and
the bug class live in `HUMANS.md` next to the target — but only `code/`
is bind-mounted into the container, so the agent sees a numeric ID and
the source. A name like `textbook-rsa` would telegraph the answer.

### 4.2 Per-run output isolation

The host generates `run_id` and creates `runs/<run_id>/` *before*
launching the container, then bind-mounts only that directory as the
agent's writable workspace. The agent cannot see prior runs; otherwise
it could trivially copy past findings, reproductions, and traces.

### 4.3 Open network, locked package install

The container has unrestricted outbound network so the agent can
research CVEs, papers, and advisories. But `pip`/`npm`/`apt` are
disabled at image build time — `python3 -m pip install requests` must
fail. The combination is the safety story: research yes, arbitrary
code execution no. Both halves are load-bearing; do not remove either.

### 4.4 Pinned agent CLI versions

`@anthropic-ai/claude-code` and `@openai/codex` are pinned to specific
versions in the Dockerfile, not `@latest`. CLI flag and SDK API drift
breaks the adapters within weeks. If you upgrade, run smoke targets
under both agents before merging.

### 4.5 Auth strategy differs by agent

- **Claude.** Max-plan OAuth lives in the macOS Keychain and isn't
  portable to a Linux container; the `claude` CLI's non-interactive
  modes never read OAuth or the keychain. So `ANTHROPIC_API_KEY` is
  required (Max-plan members can generate one that bills against the
  Max quota).
- **Codex.** `~/.codex/auth.json` is a real file holding a ChatGPT-account
  OAuth token, so we mount it RO at `/auth_src` and let the runner copy
  it into a writable tmpfs `HOME` at run start. Host file stays
  immutable. Falls back to `OPENAI_API_KEY` if the token isn't present.

The asymmetry is irreducible — it reflects how each vendor packages
auth — and is documented in comments next to the code in `scripts/hunt`.

### 4.6 Run identity passed as CLI args, not env

`RUN_ID`, `TARGET_NAME`, `IMAGE_DIGEST`, `GIT_SHA` are passed to
`runner.audit` as CLI flags rather than environment variables. The
agent has shell access; if these were in the environment, `env` or
`printenv` would reveal the target's identity. CLI args land in
`run.json` for the host but are invisible to the agent's bash sessions.

### 4.7 Two-tier findings bar

- `artifacts/findings.json` — substantiated. Working PoC in
  `artifacts/repro/` OR a machine-checked obstruction in
  `artifacts/lean/` or `artifacts/sage/`. Reproductions run in <30s.
- `artifacts/notes.md` — suspicions, partial leads, hypotheses without
  proof. Lower bar, useful for follow-up.

The split exists so the agent isn't pressured to pad `findings.json`
with speculation. A finding without a runnable reproduction is a note,
not a finding.

### 4.8 Lean MCP wraps a long-lived REPL

`mcp__lean__check` runs against an in-memory Lean environment that
persists across calls within a session, so the cost of `import Mathlib`
(~30-60s cold) is paid once. `lake build` would re-pay it each time.
The MCP server restarts the REPL on timeout or crash. For protocol-level
modeling that needs imports across multiple files, the agent writes
files into `/opt/lean-workspace/` and uses `lake build`; for tight
single-snippet iteration, the MCP is preferred.

### 4.9 Runs are serial

The Lean workspace at `/opt/lean-workspace/` is shared and writable;
concurrent hunts against the same image race on it. The harness does
not coordinate — it's the operator's responsibility to run one at a
time per image.

### 4.10 Post-run secret scrubber

`scripts/scrub-secrets` greps the run directory for `sk-ant-…`,
`sk-proj-…`, and generic `sk-…` patterns after each hunt and exits
non-zero on hit. API keys live only in the running container's memory,
but a confused agent could write one into `notes.md`. The scan is
small; do not skip it.

### 4.11 Container memory of the agent's HOME

The container is launched with `--user $(id -u):$(id -g)` and a tmpfs
`/home/audit` (size 128M, owned by that uid). The agent's HOME is
ephemeral per run. Codex auth files copied from `/auth_src` land here
and vanish at container exit; the host originals stay RO and unmodified.

---

## 5. Findings Schema

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

## 6. Constraints — Do Not

- Add a grader, scoring loop, intensification phase, or benchmark.
- Add a trace viewer, comparison tool, or finding aggregator (out of
  scope; the user reads files directly).
- Generalize "agent backend" beyond the two adapters. A third adapter
  is fine; an abstract framework is not.
- Restrict the container's network. The agent's web research is
  essential to the goal-directed approach.
- Skip the package-manager lockdown. It's what makes the open-network
  policy safe.
- Skip `scrub-secrets`. Small cost, high downside if missed.
- Bind-mount `HUMANS.md` or any sibling of `code/`. The anonymization
  story depends on the agent only seeing `code/`.
- Run multiple hunts concurrently against the same image (Lean
  workspace is shared).
