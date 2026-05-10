# Cryptanalyst 

A goal-directed cryptographic bug finder driven by Claude Code or OpenAI
Codex. Both agents see an identical containerized workspace and toolchain
— swap between them with a flag.

## What makes it different

- **Goal-directed, not procedural.** The agent picks the approach (pattern matching, differential testing, formal modeling, exploit reproduction); methodology is a means, not a playbook.
- **Two cooperating modes.** `formalize` grows a cumulative Lean model; `hunt` attacks adversarially. Both share a per-target state directory; can run concurrently in isolated state snapshots.
- **Agent-agnostic.** Identical Docker workspace for Claude Code and Codex; reasoning effort and model are flags.
- **Three-knob budget.** `--cycles` × `--cycle-budget` × `--timeout`. No SDK iteration or spend caps layered on top.

## Quickstart

```bash
# 1. Build (15-25 min one-time, Mathlib cache).
./scripts/build-image

# 2. Set Claude credentials (or codex login).
claude setup-token                       # interactive; prints a token
export CLAUDE_CODE_OAUTH_TOKEN=<paste it>

# 3. Verify the install end-to-end (one cycle on a smoke target).
./scripts/test-install

# 4. Run on any target.
./scripts/hunt targets/smoke/smoke-01
```

Findings land at `runs/<run-id>/artifacts/findings.json`. Before running
applied-tier targets, run `./scripts/generate-fixtures` once.

## Docs

**Get started**
- **[Setup](docs/INSTALL.md)** — hardware, build, auth (Claude / Codex)
- **[Running](docs/RUNNING.md)** — flags, modes, budgets, snapshot pipeline, output

**Reference**
- **[Targets](docs/TARGETS.md)** — tiers, anonymization, `audit.md` conventions
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** — common issues

**Internals**
- **[Design](docs/DESIGN.md)** — architecture, decisions, trade-offs
- **[Roadmap](docs/ROADMAP.md)** — bug-class roadmap
- **[Agent system prompt](instructions/AGENTS.md)** — methodology the agent follows
- **[Mode prompts](prompts/)** — per-cycle prompts for `hunt` and `formalize`

## Repo layout

```
runner/        per-cycle loop + adapter protocol (claude.py, codex.py, base.py)
prompts/       per-cycle agent prompts (hunt.md, formalize.md)
instructions/  agent's always-loaded system prompt (AGENTS.md)
scripts/       hunt, hunt-all, hunt-local, republish, build-image, generate-fixtures, scrub-secrets
env/          Docker build context — Dockerfile, lakefile, requirements.txt, vendored Lean skills, MCP servers (mcp/lean, mcp/rocq)
targets/       smoke / applied / blind / production / private (private + production gitignored)
docs/          design notes, install / running / troubleshooting guides
runs/          per-run output (gitignored except runs/published/ for demo evidence)
```

## License

[MIT](LICENSE).

## Status

Research / experimental. Findings are agent-surfaced candidates with line citations and runnable repros; the operator verifies.
