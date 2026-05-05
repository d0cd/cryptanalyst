"""Lean MCP server.

Wraps the Lean REPL (https://github.com/leanprover-community/repl) as MCP tools.
The REPL is a stdin/stdout JSON protocol. We maintain a single REPL subprocess
per server instance and restart it on timeout or crash.
"""
from __future__ import annotations

import json
import os
import subprocess
import threading
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

LEAN_WORKSPACE = Path("/opt/lean-workspace")
LEAN_REPL_BIN = Path("/opt/lean-repl/.lake/build/bin/repl")
DEFAULT_TIMEOUT = 90.0  # generous default; first Mathlib import is slow


def _artifact_dir() -> Path:
    """artifacts/lean inside the agent's current working directory.

    The MCP server inherits cwd from the agent process (Claude SDK and
    `codex exec` both propagate it), so this resolves to the active run
    dir without needing the runner to set an env var.
    """
    return Path.cwd() / "artifacts" / "lean"

mcp = FastMCP("lean")


class LeanRepl:
    """A managed Lean REPL subprocess with restart on failure."""

    def __init__(self) -> None:
        self.proc: subprocess.Popen | None = None
        self.lock = threading.Lock()
        self._start()

    def _start(self) -> None:
        # Codex spawns MCP subprocesses with a minimal env (HOME, LANG, PATH
        # only) — image-level ENV vars like ELAN_HOME are stripped. Without
        # ELAN_HOME, elan thinks the toolchain isn't installed under the
        # caller's HOME and tries to redownload it to /home/audit/.elan
        # (a 64MB tmpfs), failing with ENOSPC and crashing the lean child
        # with exit code 1. Inject the values the toolchain actually needs.
        env = dict(os.environ)
        env.setdefault("ELAN_HOME", "/opt/elan")
        # Also strip codex's own argv0-shim path prefix; harmless but
        # clutters PATH and confuses tools that walk it.
        path_parts = [p for p in env.get("PATH", "").split(":")
                      if "/.codex/tmp/arg0/" not in p]
        if "/opt/elan/bin" not in path_parts:
            path_parts.insert(0, "/opt/elan/bin")
        env["PATH"] = ":".join(path_parts)
        self.proc = subprocess.Popen(
            [str(LEAN_REPL_BIN)],
            cwd=str(LEAN_WORKSPACE),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
        )

    def _alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def _kill(self) -> None:
        if self.proc is not None:
            try:
                self.proc.kill()
                self.proc.wait(timeout=2)
            except Exception:
                pass
            self.proc = None

    def restart(self) -> None:
        with self.lock:
            self._kill()
            self._start()

    def send(self, payload: dict[str, Any], timeout: float = DEFAULT_TIMEOUT) -> dict[str, Any]:
        with self.lock:
            if not self._alive():
                self._start()

            assert self.proc is not None and self.proc.stdin and self.proc.stdout

            try:
                self.proc.stdin.write(json.dumps(payload) + "\n\n")
                self.proc.stdin.flush()
            except (BrokenPipeError, OSError) as e:
                self._kill()
                self._start()
                return {"error": f"REPL pipe broken, restarted: {e}"}

            result_lines: list[str] = []
            done = threading.Event()
            error_holder: dict[str, str] = {}

            def reader() -> None:
                try:
                    assert self.proc and self.proc.stdout
                    for line in self.proc.stdout:
                        if line.strip() == "":
                            if result_lines:
                                done.set()
                                return
                            continue
                        result_lines.append(line)
                    # stdout closed without seeing blank line — surface
                    # whatever we got so the caller sees the REPL error.
                    if result_lines:
                        done.set()
                except Exception as e:
                    error_holder["err"] = str(e)
                    done.set()

            t = threading.Thread(target=reader, daemon=True)
            t.start()
            if not done.wait(timeout=timeout):
                self._kill()
                self._start()
                return {"error": f"REPL call timed out after {timeout}s; REPL restarted"}

            if "err" in error_holder:
                self._kill()
                self._start()
                return {"error": f"REPL read error: {error_holder['err']}; REPL restarted"}

            raw = "".join(result_lines).strip()
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                self._kill()
                self._start()
                return {"error": f"REPL returned non-JSON output: {raw[:500]!r}; REPL restarted"}


_repl: LeanRepl | None = None


def _repl_singleton() -> LeanRepl:
    global _repl
    if _repl is None:
        _repl = LeanRepl()
    return _repl


@mcp.tool()
def check(code: str, env: int | None = None, timeout: float | None = None) -> dict[str, Any]:
    """Type-check a Lean snippet.

    Args:
        code: Lean source to elaborate.
        env: Optional environment id from a previous `check` call to extend.
        timeout: Per-call timeout in seconds. Defaults to 90s. Raise this
            for deliberately slow proofs (heavy `simp`, `decide`, large
            `import` chains). For very long proofs, prefer writing files
            into /opt/lean-workspace/CryptoAudit/ and running `lake build`.

    Returns:
        A dict with keys:
          - env: the new environment id (int)
          - messages: list of {severity, pos, data} from the elaborator
          - sorries: list of remaining `sorry` goals, each {pos, goal}
          - error: present only if the REPL itself failed
    """
    payload: dict[str, Any] = {"cmd": code}
    if env is not None:
        payload["env"] = env
    return _repl_singleton().send(payload, timeout=timeout if timeout is not None else DEFAULT_TIMEOUT)


@mcp.tool()
def restart() -> dict[str, str]:
    """Restart the Lean REPL. Use if it appears stuck or returning garbage."""
    _repl_singleton().restart()
    return {"status": "restarted"}


@mcp.tool()
def save_to_artifact(name: str, code: str) -> dict[str, str]:
    """Persist a Lean file to artifacts/lean/<name> for the user.

    `name` may include subdirectories (e.g. `Protocol/Group.lean`); the
    full resolved path must stay under artifacts/lean/. Call only after
    confirming `check` accepts the code.
    """
    if not name.endswith(".lean"):
        name = name + ".lean"
    artifact_dir = _artifact_dir()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    target = (artifact_dir / name).resolve()
    try:
        target.relative_to(artifact_dir.resolve())
    except ValueError:
        return {"error": f"path escapes artifacts/lean/: {name}"}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(code)
    return {"path": str(target)}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
