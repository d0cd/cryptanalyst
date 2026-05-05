"""Crypto bug-finding harness entrypoint.

Runs inside the container. The host (`scripts/hunt`) creates the run dir,
mounts target/code into it read-only, and invokes us with `--run-dir`.
We set up the agent-facing files (AGENTS.md, CLAUDE.md, artifacts/),
dispatch to the chosen adapter, capture the trace, and write run.json.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
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


def prepare_workdir(run_dir: Path) -> None:
    """Drop AGENTS.md / CLAUDE.md and an empty artifacts/ into the run dir.

    The target's code/ is bind-mounted into run_dir/code by the host, so
    we don't copy it. AGENTS.md is copied (not symlinked) so the run dir
    stays self-contained when read from the host or archived.
    """
    (run_dir / "artifacts").mkdir(exist_ok=True)

    agents_md_src = INSTRUCTIONS_DIR / "AGENTS.md"
    if not agents_md_src.exists():
        sys.exit(f"missing instructions: {agents_md_src}")
    shutil.copy(agents_md_src, run_dir / "AGENTS.md")
    shutil.copy(agents_md_src, run_dir / "CLAUDE.md")


def setup_auth() -> None:
    """Copy CLI auth files from RO mount at /auth_src into writable $HOME.

    The Claude and Codex CLIs read their auth from $HOME/.claude.json
    and $HOME/.codex/* respectively, and write back to refresh tokens
    or update state. We keep the host files immutable by mounting them
    RO and copying into a tmpfs HOME at run start. If /auth_src is
    absent, the user is running with API keys via env vars instead.
    """
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
    """Verify the agent produced a valid findings.json. Returns finding count."""
    findings = run_dir / "artifacts" / "findings.json"
    if not findings.exists():
        print(f"WARNING: agent produced no findings.json in {run_dir}", file=sys.stderr)
        return -1
    try:
        data = json.loads(findings.read_text())
        if not isinstance(data, dict) or "findings" not in data:
            print(f"WARNING: findings.json malformed in {run_dir}", file=sys.stderr)
            return -1
        n = len(data["findings"])
        print(f"  Findings: {n}")
        return n
    except json.JSONDecodeError as e:
        print(f"WARNING: findings.json is not valid JSON: {e}", file=sys.stderr)
        return -1


async def main() -> None:
    p = argparse.ArgumentParser(description="Crypto bug-finding harness")
    p.add_argument("--run-dir", required=True, help="Pre-created run directory")
    p.add_argument(
        "--agent", choices=list(ADAPTERS), default="claude",
        help="Which agent backend to use",
    )
    p.add_argument(
        "--mode", default="hunt",
        help="Prompt name (looks for prompts/<mode>.md)",
    )
    p.add_argument("--max-turns", type=int, default=100)
    # Identity fields are passed as CLI args (not env vars) so they
    # don't appear in the agent's bash environment; only the runner
    # uses them, recording them into run.json for the human reviewer.
    p.add_argument("--run-id", default=os.environ.get("RUN_ID"))
    p.add_argument("--target-name", default=os.environ.get("TARGET_NAME"))
    p.add_argument("--image-digest", default=os.environ.get("IMAGE_DIGEST"))
    p.add_argument("--git-sha", default=os.environ.get("GIT_SHA"))
    args = p.parse_args()

    run_dir = Path(args.run_dir).resolve()
    if not run_dir.is_dir():
        sys.exit(f"run-dir not found: {run_dir}")
    if not (run_dir / "code").is_dir():
        sys.exit(f"run-dir has no code/ subdirectory (host bind mount missing?): {run_dir}")

    prompt_path = PROMPTS_DIR / f"{args.mode}.md"
    if not prompt_path.exists():
        sys.exit(f"prompt not found: {prompt_path}")
    prompt = prompt_path.read_text().strip()

    prepare_workdir(run_dir)
    setup_auth()

    started_at = datetime.now(timezone.utc)
    print(f"Run: {run_dir}")
    print(f"  Agent:  {args.agent}")
    print(f"  Target: {args.target_name or '(unknown)'}")

    adapter = ADAPTERS[args.agent]
    adapter_kwargs: dict = {}
    if args.agent == "claude":
        adapter_kwargs["max_turns"] = args.max_turns
    result = await adapter.run(
        workdir=run_dir,
        prompt=prompt,
        trace_path=run_dir / "trace.jsonl",
        **adapter_kwargs,
    )

    print(f"  Done in {result.duration_seconds:.1f}s ({result.exit_reason})")
    if result.error:
        print(f"  Error: {result.error}")

    n_findings = post_run_check(run_dir)

    write_run_json(run_dir, {
        "run_id": args.run_id,
        "target_name": args.target_name,
        "agent": args.agent,
        "mode": args.mode,
        "max_turns": args.max_turns,
        "started_at": started_at.isoformat(),
        "duration_seconds": round(result.duration_seconds, 2),
        "exit_reason": result.exit_reason,
        "error": result.error,
        "n_findings": n_findings if n_findings >= 0 else None,
        "image_digest": args.image_digest,
        "git_sha": args.git_sha,
    })


if __name__ == "__main__":
    asyncio.run(main())
