"""Crypto bug-finding harness entrypoint.

Runs inside the container. The host (`scripts/hunt`) creates the run dir,
mounts target/code into it read-only, and invokes us with `--run-dir`.
We set up the agent-facing files (AGENTS.md, CLAUDE.md, artifacts/),
then run an outer loop that invokes the chosen adapter for one focused
investigation cycle at a time. State persists between cycles via files
in `artifacts/` (notably `hypotheses.md`).

Loop architecture (Karpathy-style autoresearch):
- Cycle 1 bootstraps the hypothesis queue from the spec(s).
- Cycle 2+ each pick one open hypothesis, investigate within ~10 min
  wall-clock, update state, return.
- Termination: max-cycles reached. Wall-clock backstops live one
  layer up: --cycle-budget cancels a stuck cycle (asyncio), and
  scripts/hunt's --timeout hard-kills the container.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from runner.adapters.base import RunResult
from runner.adapters.claude import ClaudeAdapter
from runner.adapters.codex import CodexAdapter

ADAPTERS = {
    "claude": ClaudeAdapter(),
    "codex": CodexAdapter(),
}

REPO_ROOT = Path(__file__).resolve().parent.parent
INSTRUCTIONS_DIR = REPO_ROOT / "instructions"
PROMPTS_DIR = REPO_ROOT / "prompts"

DEFAULT_CYCLE_BUDGET_SECONDS = 600
DEFAULT_MAX_CYCLES = 10


def prepare_workdir(run_dir: Path) -> None:
    """Drop AGENTS.md / CLAUDE.md and an empty artifacts/ into the run dir."""
    (run_dir / "artifacts").mkdir(exist_ok=True)
    agents_md_src = INSTRUCTIONS_DIR / "AGENTS.md"
    if not agents_md_src.exists():
        sys.exit(f"missing instructions: {agents_md_src}")
    shutil.copy(agents_md_src, run_dir / "AGENTS.md")
    shutil.copy(agents_md_src, run_dir / "CLAUDE.md")


def setup_auth() -> None:
    """Copy CLI auth files from RO mount at /auth_src into writable $HOME."""
    src = Path("/auth_src")
    home = Path(os.environ.get("HOME", ""))
    if not src.exists() or not home or not home.exists():
        return
    for entry in src.iterdir():
        dest = home / entry.name
        if entry.is_dir():
            shutil.copytree(entry, dest, dirs_exist_ok=True)
        else:
            shutil.copy(entry, dest)


def write_run_json(run_dir: Path, meta: dict) -> None:
    (run_dir / "run.json").write_text(json.dumps(meta, indent=2) + "\n")


def post_run_check(run_dir: Path) -> int:
    """Verify findings.json is valid; return finding count or -1."""
    findings = run_dir / "artifacts" / "findings.json"
    if not findings.exists():
        # Loop runs may finish with no findings.json yet — don't warn.
        return 0
    try:
        data = json.loads(findings.read_text())
        if not isinstance(data, dict) or "findings" not in data:
            print(f"WARNING: findings.json malformed in {run_dir}", file=sys.stderr)
            return -1
        return len(data["findings"])
    except json.JSONDecodeError as e:
        print(f"WARNING: findings.json is not valid JSON: {e}", file=sys.stderr)
        return -1


async def run_one_cycle(
    adapter,
    run_dir: Path,
    prompt: str,
    cycle: int,
    cycle_budget_seconds: int,
    model: str,
    effort: str,
    agent: str,
) -> tuple[str, RunResult | None]:
    """Run one adapter invocation with a wall-clock cap.

    Returns (status, result) where status is 'completed', 'timeout',
    'cancelled', or 'error'.
    """
    trace_path = run_dir / f"trace.cycle{cycle:02d}.jsonl"
    adapter_kwargs: dict = {}
    if model:
        adapter_kwargs["model"] = model
    if effort:
        adapter_kwargs["effort"] = effort
    try:
        result = await asyncio.wait_for(
            adapter.run(
                workdir=run_dir,
                prompt=prompt,
                trace_path=trace_path,
                **adapter_kwargs,
            ),
            timeout=cycle_budget_seconds,
        )
        return ("completed" if result.success else "error"), result
    except asyncio.TimeoutError:
        return "timeout", None
    except asyncio.CancelledError:
        return "cancelled", None


async def main() -> None:
    p = argparse.ArgumentParser(description="Crypto bug-finding harness (loop mode)")
    p.add_argument("--run-dir", required=True, help="Pre-created run directory")
    p.add_argument("--agent", choices=list(ADAPTERS), default="claude")
    p.add_argument("--mode", default="hunt", help="Prompt name (prompts/<mode>.md)")
    p.add_argument("--max-cycles", type=int, default=DEFAULT_MAX_CYCLES,
                   help="Number of investigation cycles (primary control)")
    p.add_argument("--cycle-budget", type=int, default=DEFAULT_CYCLE_BUDGET_SECONDS,
                   help="Per-cycle wall-clock cap in seconds")
    p.add_argument("--model", default="",
                   help="Vendor model id, passed through to the adapter "
                        "unchanged (e.g. 'claude-sonnet-4-6', 'gpt-5'). "
                        "Empty = adapter default.")
    p.add_argument("--effort", default="",
                   help="Reasoning-effort level: low | medium | high | xhigh | max. "
                        "Empty = adapter default.")
    p.add_argument("--run-id", required=True)
    p.add_argument("--target-name", required=True)
    p.add_argument("--image-digest", default="unknown")
    p.add_argument("--git-sha", default="unknown")
    args = p.parse_args()

    run_dir = Path(args.run_dir).resolve()
    if not run_dir.is_dir():
        sys.exit(f"run-dir not found: {run_dir}")
    if not (run_dir / "code").is_dir():
        sys.exit(f"run-dir has no code/ subdirectory: {run_dir}")

    prompt_path = PROMPTS_DIR / f"{args.mode}.md"
    if not prompt_path.exists():
        sys.exit(f"prompt not found: {prompt_path}")
    prompt = prompt_path.read_text().strip()

    prepare_workdir(run_dir)
    setup_auth()

    adapter = ADAPTERS[args.agent]
    # One-time adapter config (e.g. injecting MCP server entries into
    # ~/.codex/config.toml). Cycles do not mutate persistent state.
    adapter.setup(Path(os.environ.get("HOME", "/home/audit")))

    started_at = datetime.now(timezone.utc)
    overall_start = time.time()
    print(f"Run: {run_dir}")
    print(f"  Agent:   {args.agent}")
    print(f"  Target:  {args.target_name}")
    print(f"  Model:   {args.model or '(adapter default)'}")
    print(f"  Effort:  {args.effort or '(adapter default)'}")
    print(f"  Max cycles: {args.max_cycles}, "
          f"cycle budget: {args.cycle_budget}s")

    # Write a stub run.json at start so meta-audit and other tools can
    # identify the run's mode and target while it's still in flight. The
    # end-of-run write_run_json overwrites this with the full cycle log.
    write_run_json(run_dir, {
        "run_id": args.run_id,
        "target_name": args.target_name,
        "agent": args.agent,
        "mode": args.mode,
        "model": args.model,
        "effort": args.effort,
        "image_digest": args.image_digest,
        "git_sha": args.git_sha,
        "started_at": started_at.isoformat(),
        "status": "running",
    })

    cycle = 0
    cycle_log: list[dict] = []

    while True:
        # Primary stop: max-cycles. The agent investigates one hypothesis
        # per cycle, so this is the natural unit of progress.
        # Wall-clock backstop is enforced by the host (`scripts/hunt
        # --timeout SEC`), not here — keeping it out of the runner
        # avoids redundant wall-clock layers.
        if cycle >= args.max_cycles:
            print(f"  [stop] reached max-cycles ({args.max_cycles})",
                  file=sys.stderr)
            break

        cycle += 1
        cstart = time.time()
        print(f"  --- cycle {cycle}/{args.max_cycles} ---", file=sys.stderr)

        status, result = await run_one_cycle(
            adapter, run_dir, prompt, cycle,
            args.cycle_budget,
            args.model, args.effort, args.agent,
        )
        cdur = time.time() - cstart

        cycle_log.append({
            "cycle": cycle,
            "status": status,
            "duration_seconds": round(cdur, 2),
            "error": (result.error if result and result.error else None),
        })
        print(f"  [cycle {cycle}] {status} in {cdur:.1f}s", file=sys.stderr)

        # Fail-fast detector: if N consecutive cycles complete in under
        # FAIL_FAST_DURATION seconds, the agent is almost certainly
        # returning empty (auth expired, quota hit, rate-limit hard-block).
        # Burning 80 wasted no-op cycles wastes time and obscures the real
        # exit cause. Stop early so the operator sees the pattern.
        FAIL_FAST_DURATION = 30.0
        FAIL_FAST_STREAK = 5
        recent = cycle_log[-FAIL_FAST_STREAK:]
        if len(recent) == FAIL_FAST_STREAK and all(
            c["duration_seconds"] < FAIL_FAST_DURATION for c in recent
        ):
            print(
                f"  [stop] {FAIL_FAST_STREAK} consecutive cycles completed in "
                f"<{FAIL_FAST_DURATION}s — auth/quota/rate-limit failure suspected. "
                f"Aborting before remaining cycles burn budget.",
                file=sys.stderr,
            )
            break

    n_findings = post_run_check(run_dir)
    overall_dur = time.time() - overall_start
    print(f"  Done in {overall_dur:.1f}s across {cycle} cycles. Findings: {n_findings}")

    write_run_json(run_dir, {
        "run_id": args.run_id,
        "target_name": args.target_name,
        "agent": args.agent,
        "mode": args.mode,
        "model": args.model or None,
        "effort": args.effort or None,
        "started_at": started_at.isoformat(),
        "duration_seconds": round(overall_dur, 2),
        "cycles": cycle,
        "max_cycles": args.max_cycles,
        "cycle_budget_seconds": args.cycle_budget,
        "cycle_log": cycle_log,
        "n_findings": n_findings if n_findings >= 0 else None,
        "image_digest": args.image_digest,
        "git_sha": args.git_sha,
    })


if __name__ == "__main__":
    asyncio.run(main())
