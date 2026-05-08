# Troubleshooting

## Build

**Build fails on Mathlib step.** `lake exe cache get` fetches Mathlib's
cache from GitHub. If GitHub rate-limits, wait and retry. The Docker
layer caches the built workspace so subsequent builds skip this.

**File ownership is root after a run.** The wrapper passes
`--user $(id -u):$(id -g)`; if you bypass it, fix ownership with
`sudo chown -R $(id -u):$(id -g) runs/`.

## Cycles

**Agent runs but produces no findings.json.** Check the trace for tool
errors. Most common causes:
- MCP server failure (Lean REPL crashed and didn't recover)
- The cycle hit `--cycle-budget` mid-tool-use

Inspect the tail of the trace; if `stop_reason: tool_use` and the wall
clock approaches the budget, raise `--cycle-budget`.

**Cycle ends mid-investigation.** Default budget is 600s. Raise it with
`--cycle-budget 1200` on `scripts/hunt`. At higher reasoning effort
(`--effort high|xhigh`) cycles run longer; budgets in the 1000-1500s
range are reasonable.

**Cycles take wildly different times.** Different cycles do different
work — a cycle that's "investigating one open hypothesis" against
already-modeled code can finish in 90s; one doing primitive-flow
enumeration across a large module takes the full budget. Variance is
expected; consistently hitting the budget cap is the signal to raise it.

## Auth

**Claude credentials expire mid-run.** The credentials.json route has a
short access-token TTL (~10-15 min). Use `CLAUDE_CODE_OAUTH_TOKEN` from
`claude setup-token` for long runs (1-year TTL). See `docs/INSTALL.md`.

**Codex auth refresh fails.** `~/.codex/auth.json` self-refreshes; if it
gets stuck, run `codex login` again on the host to refresh, or fall
back to `OPENAI_API_KEY`.

## Container

**Container outlives the kill signal.** `docker stop` sends SIGTERM
with a 10s grace period, then SIGKILL. The python runner inside doesn't
have a SIGTERM handler, so the in-flight cycle's work is lost. State
that was committed before the kill is durable.

**Two containers writing to the same target's `/state` simultaneously.**
This is the Shape 1 conflict. Use `--snapshot` on the secondary run
(typically hunt) to mount an isolated worktree instead.

**Container appears to hang.** The host-side `--timeout SEC` (default
7200s = 2h) hard-kills via `timeout(1)`. If a single run needs more,
raise it. Note that on macOS, laptop sleep suspends the docker process
without firing the asyncio timeout — caffeinate during long runs.

## Packages

**Package installs are slow.** Packages are downloaded each run since
the container is ephemeral. If the agent consistently needs a library,
add it to `env/requirements.txt` and rebuild.

## Lean state

**`lake build` fails with stale-olean errors after a snapshot run.**
The lake-cache for the worktree is separate, but if it was bind-
mounted alongside the live cache, oleans can drift. Run
`rm -rf <target>/state/.lake-cache && lake build` to rebuild from
scratch (~5 min).

**Embedded git repository warning when committing.** The agent's
per-cycle commits inside `<target>/state/.git` are intentional; the
state dir is gitignored from the harness repo. If you publish a run
via `scripts/republish`, the script flattens the inner `.git` into a
`git-history.log` file so the outer repo can track the state contents
as regular files.
