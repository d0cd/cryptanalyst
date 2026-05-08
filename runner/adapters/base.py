"""Adapter protocol — both backends conform to this shape."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Protocol


@dataclass
class RunResult:
    success: bool
    duration_seconds: float
    exit_reason: str  # "completed", "timeout", "error"
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class Adapter(Protocol):
    name: str

    def setup(self, home: Path) -> None:
        """Run-level setup: any one-time config writes go here, not in run().

        Called once by the runner before the cycle loop starts. Keeps
        per-cycle run() free of persistent state mutation so cycles
        compose cleanly.
        """
        ...

    async def run(
        self,
        workdir: Path,
        prompt: str,
        trace_path: Path,
        **kwargs: Any,
    ) -> RunResult: ...
