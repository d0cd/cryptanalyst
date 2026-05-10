"""Codex adapter using the Codex CLI in exec mode."""
from __future__ import annotations

import asyncio
import time
from pathlib import Path

from .base import RunResult


# Default model for ChatGPT-account (Max plan) OAuth path. `gpt-5-codex`
# would be more Codex-tuned but is gated to OPENAI_API_KEY auth. Override
# with `--model` on scripts/hunt to pick something else.
DEFAULT_CODEX_MODEL = "gpt-5.5"


# Appended to $HOME/.codex/config.toml so the Lean MCP shows up in the
# agent's tool list. Recent codex CLI versions removed `--config-file`
# in favor of reading ~/.codex/config.toml automatically.
CODEX_MCP_TOML = """

[mcp_servers.lean]
command = "python3"
args = ["-m", "lean_mcp.server"]

[mcp_servers.rocq]
command = "python3"
args = ["-m", "rocq_mcp.server"]
"""


class CodexAdapter:
    name = "codex"

    def setup(self, home: Path) -> None:
        """Inject the Lean MCP server into the per-run config.toml.

        Runs once at startup, after setup_auth() has copied the user's
        host config.toml (if any) into $HOME/.codex/. We append rather
        than overwrite so user-provided keys are preserved. Doing this
        per-run instead of per-cycle prevents the section from being
        appended N times and producing a `duplicate key` toml error.
        """
        codex_dir = home / ".codex"
        codex_dir.mkdir(parents=True, exist_ok=True)
        with (codex_dir / "config.toml").open("a") as f:
            f.write(CODEX_MCP_TOML)

    async def run(
        self,
        workdir: Path,
        prompt: str,
        trace_path: Path,
        model: str = "",
        effort: str = "",
        **_kwargs,
    ) -> RunResult:
        # **_kwargs absorbs any future per-vendor knobs from the runner
        # so adapters stay swap-compatible.
        model = model or DEFAULT_CODEX_MODEL

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
        ]
        # Codex CLI's reasoning-effort knob: low | medium (default) | high | xhigh.
        # Set via `--config model_reasoning_effort=<level>` so it overrides any
        # default in ~/.codex/config.toml without mutating the file.
        if effort:
            cmd += ["--config", f'model_reasoning_effort="{effort}"']
        cmd += ["--json", prompt]

        start = time.time()
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        # Codex emits one JSON event per line, but a single line can be
        # arbitrarily long — `command_execution.aggregated_output` carries
        # whole `find` / `cat` outputs and easily blows past asyncio's
        # 64KB default `readline` limit. Read raw chunks and split on
        # newlines ourselves so any line length works.
        try:
            with open(trace_path, "wb") as trace:
                assert proc.stdout is not None
                buffer = b""
                while True:
                    chunk = await proc.stdout.read(65536)
                    if not chunk:
                        if buffer:
                            trace.write(buffer)
                            trace.flush()
                        break
                    buffer += chunk
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        trace.write(line + b"\n")
                        trace.flush()
            rc = await proc.wait()
        except asyncio.CancelledError:
            # Per-cycle wall-clock fired (or other cancellation). Reap
            # the subprocess so it doesn't leak into the next cycle.
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
            raise

        return RunResult(
            success=rc == 0,
            duration_seconds=time.time() - start,
            exit_reason="completed" if rc == 0 else "error",
            error=None if rc == 0 else f"codex exited with code {rc}",
        )
