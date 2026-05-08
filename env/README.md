# env/ — container build context + vendored skills

Two kinds of content live here:

## Docker build context (tracked)

- `Dockerfile` — image definition: Lean 4 + Mathlib (cached), SageMath, Python crypto libs, agent CLIs, the Lean MCP server.
- `requirements.txt` — Python deps installed into the image.
- `lean_workspace/` — pre-configured Lean project (`lakefile.lean`, etc.) baked into the image. Mathlib oleans are pre-compiled here. The agent's per-target Lean tree lives at `<target>/state/lean/` and is bind-mounted on top of `Audit/` at run time.

## Vendored skill clones (gitignored)

- `lean-skills/` — clone of [leanprover/skills](https://github.com/leanprover/skills). Mounted RO at `/repo/lean-skills` inside the container.
- `lean4-skills/` — clone of [cameronfreer/lean4-skills](https://github.com/cameronfreer/lean4-skills). Mounted RO at `/repo/lean4-skills`.

These are vendored at the run-time host (per-machine), not committed in this repo. Re-clone after fresh checkout:

```bash
git clone --depth 1 https://github.com/leanprover/skills.git env/lean-skills
git clone --depth 1 https://github.com/cameronfreer/lean4-skills.git env/lean4-skills
```

The agent reads them when proof-construction or Mathlib-navigation comes up; see `instructions/AGENTS.md` for when each is consulted.
