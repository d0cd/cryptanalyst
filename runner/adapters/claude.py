"""Claude adapter using the Claude Agent SDK."""
from __future__ import annotations

import dataclasses
import json
import sys
import time
from pathlib import Path

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

from .base import RunResult


def _elapsed(start: float) -> str:
    s = int(time.time() - start)
    return f"[{s // 60:02d}:{s % 60:02d}]"


def _msg_to_dict(msg: object) -> dict:
    """Best-effort conversion of SDK message objects to JSON-serializable dicts."""
    if dataclasses.is_dataclass(msg) and not isinstance(msg, type):
        return dataclasses.asdict(msg)
    if hasattr(msg, "model_dump"):
        return msg.model_dump()
    if hasattr(msg, "__dict__"):
        return msg.__dict__
    return {"raw": str(msg)}


def _log_progress(msg_dict: dict, start: float) -> None:
    """Print a concise progress line to stderr."""
    elapsed = _elapsed(start)

    # StreamEvent wraps an inner event dict
    event = msg_dict.get("event", msg_dict)
    msg_type = event.get("type") or msg_dict.get("type", "")
    subtype = event.get("subtype", "")

    if msg_type == "assistant" and subtype == "tool_use":
        name = event.get("name", "?")
        print(f"  {elapsed} tool: {name}", file=sys.stderr)
    elif msg_type == "assistant" and subtype == "text":
        text = (event.get("text") or "").strip()
        if text:
            preview = text[:120].replace("\n", " ")
            if len(text) > 120:
                preview += "..."
            print(f"  {elapsed} text: {preview}", file=sys.stderr)
    elif msg_type == "result":
        cost = event.get("cost_usd") or event.get("usage", {}).get("cost_usd")
        turns = event.get("num_turns")
        parts = [elapsed, "result"]
        if turns:
            parts.append(f"turns={turns}")
        if cost:
            parts.append(f"cost=${cost:.4f}")
        print(f"  {' '.join(parts)}", file=sys.stderr)
    elif msg_type == "system":
        if subtype not in ("hook_started", "hook_response"):
            print(f"  {elapsed} system: {subtype}", file=sys.stderr)


class ClaudeAdapter:
    name = "claude"

    def setup(self, home: Path) -> None:
        """No persistent config to write — auth is via env var."""

    async def run(
        self,
        workdir: Path,
        prompt: str,
        trace_path: Path,
        model: str = "",
        effort: str = "",
    ) -> RunResult:
        agents_md = (workdir / "AGENTS.md").read_text()

        mcp_config = {
            "lean": {
                "command": "python3",
                "args": ["-m", "lean_mcp.server"],
            }
        }

        # Build options dict so we only pass model when set
        # (older SDK versions reject unknown kwargs; absent = SDK default).
        opt_kwargs: dict = dict(
            cwd=str(workdir),
            system_prompt={
                "type": "preset",
                "preset": "claude_code",
                "append": agents_md,
            },
            mcp_servers=mcp_config,
            allowed_tools=[
                "Bash", "Read", "Write", "Edit", "Glob", "Grep",
                "TodoWrite",
                "WebFetch", "WebSearch",
                "mcp__lean__check",
                "mcp__lean__save_to_artifact",
                "mcp__lean__restart",
            ],
            permission_mode="bypassPermissions",
        )
        if model:
            opt_kwargs["model"] = model
        if effort:
            # ClaudeAgentOptions.effort: "low" | "medium" | "high" | "xhigh" | "max"
            opt_kwargs["effort"] = effort
        options = ClaudeAgentOptions(**opt_kwargs)

        start = time.time()
        with open(trace_path, "w") as trace:
            try:
                async with ClaudeSDKClient(options=options) as client:
                    await client.query(prompt)
                    async for msg in client.receive_response():
                        msg_dict = _msg_to_dict(msg)
                        line = json.dumps(msg_dict, default=str)
                        trace.write(line + "\n")
                        trace.flush()
                        _log_progress(msg_dict, start)
            except Exception as e:
                return RunResult(
                    success=False,
                    duration_seconds=time.time() - start,
                    exit_reason="error",
                    error=str(e),
                )

        return RunResult(
            success=True,
            duration_seconds=time.time() - start,
            exit_reason="completed",
        )
