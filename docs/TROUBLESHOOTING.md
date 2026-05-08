# Troubleshooting

**Build fails on Mathlib step.** `lake exe cache get` rate-limited by GitHub. Wait and retry; subsequent runs are cached.

**File ownership is root after a run.** Should not happen — the wrapper passes `--user $(id -u):$(id -g)`. If it does, `sudo chown -R $(id -u):$(id -g) runs/`.

**Agent runs but produces no findings.json.** Check the trace tail. Most common: MCP server failure (Lean REPL crashed) or `--cycle-budget` hit mid-tool-use (`stop_reason: tool_use` near the budget). For the latter, raise `--cycle-budget`.

**Cycle ends mid-investigation.** Default 600s budget is tight at higher reasoning effort. `--effort high|xhigh` typically wants `--cycle-budget 1000-1500`.

**Cycles take wildly different times.** Expected — investigating an already-modeled hypothesis can finish in 90s; primitive-flow enumeration across a large module takes the full budget. Consistently hitting the cap is the signal to raise it.

**Claude credentials expire mid-run.** The `~/.claude/.credentials.json` route has a ~10-15 min access-token TTL. Use `CLAUDE_CODE_OAUTH_TOKEN` from `claude setup-token` (1-year TTL) for long runs. Codex's `~/.codex/auth.json` self-refreshes; if it gets stuck, `codex login` again or fall back to `OPENAI_API_KEY`.

**Container outlives the kill signal.** `docker stop` sends SIGTERM (10s grace) then SIGKILL. The python runner has no SIGTERM handler, so the in-flight cycle's work is lost. State committed before the kill is durable.

**Two containers writing to the same `/state` simultaneously.** Use `--snapshot` on the secondary run (typically hunt) to mount an isolated git worktree.

**Container appears to hang.** Host-side `--timeout SEC` (default 7200s) hard-kills via `timeout(1)`. On macOS, laptop sleep suspends the docker process without firing the asyncio cycle-budget — `caffeinate -dimsu` during long runs (Linux: `systemd-inhibit --what=sleep:idle`).

**Package installs are slow.** Container is ephemeral; downloads each run. Add persistently-needed libs to `env/requirements.txt` and rebuild.

**`lake build` fails with stale-olean errors after a snapshot run.** Lake-cache drift. `rm -rf <target>/state/.lake-cache && lake build` to rebuild (~5 min).

**Embedded git repository warning when committing the harness repo.** The agent's per-cycle commits inside `<target>/state/.git` are intentional and gitignored. `scripts/republish` flattens the inner `.git` into `git-history.log` when copying into `runs/published/`.
