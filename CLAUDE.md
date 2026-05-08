# Cryptanalyst — Repo Guide for Claude Code

This is the **harness**, not a target. The harness runs an agent (Claude
or Codex) inside Docker against cryptographic code in `targets/<id>/code/`.
When you're working in this repo, you're modifying the harness itself.

## Where things live

| Path | Purpose |
|---|---|
| `README.md` | User-facing entry point — read this first |
| `docs/DESIGN.md` | Why decisions went the way they did |
| `docs/ROADMAP.md` | Roadmap of bug classes not yet covered |
| `instructions/AGENTS.md` | Loaded as the **agent's** system prompt at run start (copied to `CLAUDE.md` and `AGENTS.md` inside each run dir) |
| `prompts/<mode>.md` | Per-mode user prompt — currently `hunt` |
| `runner/audit.py` | In-container entrypoint; loop driver |
| `runner/adapters/{claude,codex}.py` | One adapter per backend |
| `mcp_servers/lean/` | Lean REPL wrapped as MCP tools |
| `scripts/hunt` | Host-side wrapper: auth + `docker run` |
| `scripts/hunt-local` | Same flow without Docker (uses host's claude OAuth) |
| `scripts/hunt-all` | Sequential batch over a target tier |
| `scripts/scrub-secrets` | Post-run API key scan; runs after every hunt |
| `targets/{smoke,applied,blind}/<id>/` | Tracked test targets |
| `targets/production/` | Real-world codebases (snarkVM, py_ecc, etc.) |
| `targets/private/` | **Gitignored.** Drop third-party / pre-disclosure code here |
| `runs/` | **Gitignored** except `runs/published/`. One subdir per hunt |

## Operator UI conventions

- All operator knobs are **flags on `scripts/hunt`** — no env vars
  except credentials (`CLAUDE_CODE_OAUTH_TOKEN` or `ANTHROPIC_API_KEY`
  for Claude; `OPENAI_API_KEY` or mounted `~/.codex/auth.json` for
  Codex).
- Three time layers: `--cycles` (depth), `--cycle-budget` (per-cycle
  wall-clock), `--timeout` (host-side hard kill). No SDK-side
  iteration or spend caps — the Claude SDK's `max_turns` defaults to
  `None` (unbounded) and we leave it that way; cycle-budget is the
  real per-cycle limit.
- `--model VENDOR_STRING` and `--effort LEVEL` are passed unchanged
  to the active adapter. No aliasing. `--effort` maps to
  `model_reasoning_effort` (codex) or `ClaudeAgentOptions.effort`
  (claude); valid levels: low, medium, high, xhigh, max.
- `--snapshot` mounts an isolated git-worktree of `<target>/state`
  for this run, so a hunt cycle can run alongside a formalize cycle
  on the same target without conflicting on `/repo/state`.
- See `docs/DESIGN.md` §4.11–4.12 for the rationale.

## When editing the harness

- **Don't bind-mount anything next to `code/` into the container.** The
  agent's view of the target is intentionally limited to `code/`.
  `HUMANS.md` and any sibling files stay host-only.
- **Per-target `<target>/audit.md` is allowed in the run dir.**
  `scripts/hunt` copies it into the run dir at launch (not into `code/`),
  so the agent sees it at `/repo/run/audit.md`.
- **Adapters share a `**kwargs` protocol** so per-vendor knobs don't
  leak into the runner. New Claude-only options go into
  `runner/adapters/claude.py`; new Codex-only options into `codex.py`.
  The runner's `run_one_cycle` decides which kwargs apply to which
  adapter based on `agent`.
- **Don't add a fifth budget knob** without first justifying it against
  the three-layer model in `docs/DESIGN.md` §4.11. Five overlapping
  budget flags is what we just removed.
- **Pin SDK / CLI versions** in `env/requirements.txt` and
  `env/Dockerfile`. Floating versions break reproducibility within
  weeks.

## Quick commands

```bash
# Build the image (slow first time)
./scripts/build-image

# Run a hunt
./scripts/hunt targets/smoke/textbook-rsa
./scripts/hunt targets/private/<your-target> --agent codex --cycles 20

# Run without Docker (uses host OAuth login)
./scripts/hunt-local targets/smoke/textbook-rsa

# Inspect output
jq . runs/<run-id>/run.json
jq -c 'select(.event.type == "tool_use")' runs/<run-id>/trace.cycle*.jsonl
```

## Testing changes to the harness

There is no separate test suite for the runner — the smoke targets are
the integration test. After changing adapters, runner, or scripts:

```bash
./scripts/hunt targets/smoke/textbook-rsa --cycles 1
```

Should produce a non-empty `runs/<id>/artifacts/findings.json` and exit 0.
