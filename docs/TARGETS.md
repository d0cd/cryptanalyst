# Targets

Targets are organized into tiers and identified by opaque numeric IDs to
keep names from telegraphing the bug class to the agent.

| Tier | Path | What | Tracked? |
|---|---|---|---|
| smoke | `targets/smoke/smoke-NN/` | Quick wins, 1–3 min/run. Sanity checks. | yes |
| applied | `targets/applied/applied-NN/` | Real attacks, 2–6 min/run. Generated via `scripts/generate-fixtures`. | code yes; state no |
| blind | `targets/blind/blind-NN/` | Sanitization probes; not part of routine sweeps (`scripts/hunt-all blind`). | code yes; state no |
| production | `targets/production/<name>/` | Real-world third-party codebases (py_ecc, libsecp256k1, vodozemac, etc.). Named descriptively since anonymization is irrelevant for published code. | gitignored |
| private | `targets/private/<name>/` | Pre-disclosure / NDA / third-party code for ad-hoc audits. | gitignored |

## Per-target structure

```
<target>/
├── code/               # the source the agent reads (RO into container)
├── audit.md            # (optional) operator's scope/context for the agent
├── HUMANS.md           # (smoke/applied/blind only) host-readable answer key — agent never sees this
├── state/              # durable cumulative state across runs (Lean tree, Sage scripts)
│                       # has its own .git for per-cycle history; gitignored from harness
└── .snapshots/         # transient git-worktrees created by --snapshot mode (auto-cleaned)
```

Only `code/` is bind-mounted into the container's `/repo/run/code` (RO).
`audit.md` is copied into the run dir at launch so the agent sees it at
`/repo/run/audit.md`. `HUMANS.md` and any sibling files stay host-only.

## Naming convention

For smoke / applied / blind targets:

- Directory name is opaque (`smoke-14`, `applied-21`).
- `HUMANS.md` records the function-style alias, original bug-class name,
  and the findings observed from prior sweeps.
- The agent never sees `HUMANS.md` — it works from code alone.

For production targets, names are descriptive (`py_ecc`,
`libsecp256k1-full`, etc.) since the code is public anyway.

## `audit.md` conventions

Per-target `audit.md` is the operator's accumulating context for the
agent across runs. It typically contains:

- **Scope:** which parts of the code are in / out of audit scope.
- **Confirmed prior findings:** brief catalog with line citations. The
  hunt prompt's "perturbation around known findings" methodology uses
  this to generate adjacent-bug hypotheses (bugs cluster).
- **Untouched surface:** areas not yet investigated.
- **Reference materials:** spec PDFs, reference implementations, papers.
- **Build infrastructure notes:** anything special about how to build
  or test the target.

Avoid putting bug hints in `audit.md` for unconfirmed concerns — the
agent should investigate adversarially, not be guided to a known
answer. Confirmed findings (with line citations) are different: they
seed the perturbation methodology.

## Adding a new target

```bash
mkdir -p targets/private/my-target/code
cp -r /path/to/source/* targets/private/my-target/code/
echo "..." > targets/private/my-target/audit.md   # optional

./scripts/hunt targets/private/my-target/
```

Production targets go in `targets/production/<name>/` with the same
shape. They're gitignored by default — copy or commit selectively.
