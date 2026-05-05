"""Codex adapter using the Codex CLI in exec mode."""
from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path

from .base import RunResult


# Appended to $HOME/.codex/config.toml so the Lean MCP shows up in the
# agent's tool list. Recent codex CLI versions removed `--config-file`
# in favor of reading ~/.codex/config.toml automatically.
CODEX_MCP_TOML = """

[mcp_servers.lean]
command = "python3"
args = ["-m", "lean_mcp.server"]
"""


class CodexAdapter:
    name = "codex"

    async def run(
        self,
        workdir: Path,
        prompt: str,
        trace_path: Path,
        **_kwargs,
    ) -> RunResult:
        # `codex exec` has no max-turns equivalent; the kwarg is accepted
        # for protocol parity and silently ignored.

        # Inject our MCP server config into the per-run config.toml.
        # setup_auth() in audit.py has already copied the user's host
        # config.toml (if any) into $HOME/.codex/, so we append rather
        # than overwrite to preserve user-provided keys.
        home = Path(os.environ.get("HOME", "/home/audit"))
        codex_dir = home / ".codex"
        codex_dir.mkdir(parents=True, exist_ok=True)
        config_path = codex_dir / "config.toml"
        existing = config_path.read_text() if config_path.exists() else ""
        config_path.write_text(existing + CODEX_MCP_TOML)

        # Default to gpt-5.5 — the latest model the ChatGPT-account
        # (Max plan) OAuth path supports. `gpt-5-codex` would be more
        # Codex-tuned but is gated to OPENAI_API_KEY auth. Override
        # with CODEX_MODEL if you want something else.
        model = os.environ.get("CODEX_MODEL", "gpt-5.5")

        cmd = [
            "codex", "exec",
            "--skip-git-repo-check",
            # Bypass both the in-process sandbox and the approval gate.
            # Without this, MCP tool calls in non-interactive runs are
            # auto-cancelled with "user cancelled MCP tool call". The
            # container itself is the actual boundary.
            "--dangerously-bypass-approvals-and-sandbox",
            "--cd", str(workdir),
            "--model", model,
            "--json",
            prompt,
        ]

        start = time.time()
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        with open(trace_path, "wb") as trace:
            assert proc.stdout is not None
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                trace.write(line)
                trace.flush()

        rc = await proc.wait()
        return RunResult(
            success=rc == 0,
            duration_seconds=time.time() - start,
            exit_reason="completed" if rc == 0 else "error",
            error=None if rc == 0 else f"codex exited with code {rc}",
        )
