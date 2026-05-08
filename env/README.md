# env/ — container environment

Two categories of content, separated by directory.

## Image build context (tracked)

Copied into the Docker image at build time. Edit these to change what's
baked into `crypto-audit:latest`.

- **`Dockerfile`** — image definition: Lean 4 + Mathlib (cached),
  SageMath, Python crypto libs, agent CLIs, the Lean MCP server.
- **`requirements.txt`** — Python deps installed into the image.
- **`lean_workspace/`** — pre-configured Lean project (`lakefile.lean`,
  etc.) baked into `/opt/lean-workspace` inside the image. Mathlib
  oleans are pre-compiled here once. The agent's per-target Lean tree
  lives at `<target>/state/lean/` and is bind-mounted on top of
  `Audit/` at run time.

## Runtime mounts (gitignored)

Vendored host-side; mounted RO into the container at runtime, never
baked into the image. Re-clone after fresh checkout:

- **`skills/lean-skills/`** — clone of [leanprover/skills](https://github.com/leanprover/skills). Mounted at `/repo/lean-skills`.
- **`skills/lean4-skills/`** — clone of [cameronfreer/lean4-skills](https://github.com/cameronfreer/lean4-skills). Mounted at `/repo/lean4-skills`.

```bash
git clone --depth 1 https://github.com/leanprover/skills.git env/skills/lean-skills
git clone --depth 1 https://github.com/cameronfreer/lean4-skills.git env/skills/lean4-skills
```

The agent reads them when proof-construction or Mathlib-navigation
comes up; see `instructions/AGENTS.md` for when each is consulted.
