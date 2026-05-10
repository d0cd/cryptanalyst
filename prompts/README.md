# prompts/

Two prompts go to the agent each run, from two locations:

- **`instructions/AGENTS.md`** — system prompt, loaded once. Methodology
  that holds across every cycle and every mode (threat model,
  hypothesis prioritization, findings bar, Lean conventions).
- **`prompts/<mode>.md`** — per-cycle user message, selected by
  `--mode NAME`. Mode-specific job description.

## Per-cycle prompt — `prompts/<mode>.md`

Selected by the `--mode NAME` flag on `scripts/hunt`. This is the user
message the agent receives at the start of each cycle. Contains the
mode-specific job: what activities are available, how to pick one, what
to write at cycle end.

Currently shipped:

- **`hunt.md`** — adversarial bug-finding. Per-cycle activities:
  Bootstrap, Investigate one open hypothesis, Refine the spec trace,
  Trace-faithfulness audit, Primitive-flow enumeration, Spawn from
  blind spots, Recon refresh.
- **`formalize.md`** — cumulative Lean modeling. Per-cycle activities:
  Foundation seeding, anchoring impl/spec sources, typed-op migration,
  state-invariant statements, decomposition, paper-pulling, etc.
- **`meta-audit.md`** — read-only audit *of* the work hunt and
  formalize have produced. Per-cycle activities span four confidence
  layers: Layer A (mechanical scans), Layer B (pattern observations),
  Layer C (recommendations), Layer D (self-limitations). Output
  goes under `artifacts/meta-audit/`; durable state is never edited.

Adding a new mode:
1. Create `prompts/<mode>.md` describing what one cycle of that mode
   does.
2. Run `./scripts/hunt <target> --mode <mode>`.

The file content is sent as the user prompt verbatim — no templating.
Cross-references to `AGENTS.md` work because it's loaded as the system
prompt and visible in the agent's working dir.
