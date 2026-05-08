# Cryptanalyst — Crypto Bug-Finding Harness

A goal-directed cryptographic bug finder driven by Claude Code or OpenAI
Codex. Both agents see an identical containerized workspace and toolchain
— swap between them with a flag.

## What makes it different

- **Goal-directed, not procedural.** The agent reads the target, picks an
  approach (pattern matching, differential testing, formal modeling,
  exploit reproduction, ...), and pursues it. Methodology is a means,
  not a fixed playbook.
- **Two cooperating modes.** `formalize` builds a cumulative Lean model
  of the target's protocol (typed `Op` family, state-machine invariants,
  decomposed proof trees with named hardness axioms). `hunt` attacks
  adversarially. Both share a per-target durable state directory; they
  can run concurrently via git-worktree snapshots.
- **Both agents on equal footing.** Identical Docker workspace, identical
  tools (Lean 4 + Mathlib, SageMath, Python crypto libs, web access).
  Reasoning effort (`low` … `xhigh`) and model selection are flags.
- **Minimal budget surface.** Three layers: cycles (depth) ×
  cycle-budget (per-cycle wall-clock) × timeout (host-side hard kill).
  No SDK iteration or spend caps on top.

## Quickstart

```bash
# 1. Build (15-25 min one-time, Mathlib cache).
./scripts/build-image

# 2. Generate applied-tier fixtures (one-time setup).
./scripts/generate-fixtures

# 3. Set Claude credentials (or codex login).
claude setup-token
export CLAUDE_CODE_OAUTH_TOKEN=<the-token>

# 4. Run.
./scripts/hunt targets/smoke/smoke-14
```

Findings land at `runs/<run-id>/artifacts/findings.json`. See
[docs/RUNNING.md](docs/RUNNING.md) for the full flag set.

## Docs

- **[Setup](docs/INSTALL.md)** — install, build, auth (Claude / Codex)
- **[Running](docs/RUNNING.md)** — flags, modes, budgets, snapshot pipeline, output structure
- **[Targets](docs/TARGETS.md)** — target tiers, anonymization, `audit.md` conventions
- **[Design](docs/DESIGN.md)** — architecture, decisions, trade-offs
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** — common issues
- **[Production candidates](docs/PRODUCTION-CANDIDATES.md)** — bug-class roadmap
- **[Agent system prompt](instructions/AGENTS.md)** — methodology the agent follows
- **[Mode prompts](prompts/)** — per-cycle prompts for `hunt` and `formalize`

## Repo layout

```
runner/        per-cycle loop + adapter protocol (claude.py, codex.py, base.py)
prompts/       per-cycle agent prompts (hunt.md, formalize.md)
instructions/  agent's always-loaded system prompt (AGENTS.md)
scripts/       hunt, hunt-all, hunt-local, republish, build-image, generate-fixtures, scrub-secrets
mcp_servers/   Lean MCP server (long-lived REPL)
env/          Docker build context (Dockerfile, lakefile, requirements.txt) and vendored Lean skills
targets/       smoke / applied / blind / production / private (private + production gitignored)
docs/          design notes, install / running / troubleshooting guides
runs/          per-run output (gitignored except runs/published/ for demo evidence)
```

## Status

Research / experimental. No grader; findings require human verification.
The agent does not "win" against a benchmark — it surfaces candidates with
line-cited evidence and runnable repros, which the operator reads.
