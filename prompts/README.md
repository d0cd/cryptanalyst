# prompts/

The agent receives two kinds of prompt content per run, from two
different locations:

## System prompt — `instructions/AGENTS.md`

Loaded once per run. Copied into the run dir as `AGENTS.md` (and
`CLAUDE.md` for Claude-Code compatibility) so the agent reads it from
its working directory. Contains methodology that should hold across
every cycle: threat-modeling rules, exploitability tiers, hypothesis
prioritization, the findings bar, Lean structural conventions, etc.

Edit `instructions/AGENTS.md` to change *how* the agent thinks across
all modes.

## Per-cycle prompt — `prompts/<mode>.md`

Selected by the `--mode NAME` flag on `scripts/hunt`. This is the user
message the agent receives at the start of each cycle. Contains the
mode-specific job: what activities are available, how to pick one, what
to write at cycle end.

Currently shipped:

- **`hunt.md`** — adversarial bug-finding. Per-cycle activities:
  Bootstrap, Investigate one open hypothesis, Refine the spec trace,
  Trace-faithfulness audit, Primitive-flow enumeration, Recon refresh.
- **`formalize.md`** — cumulative Lean modeling. Per-cycle activities:
  Foundation seeding, anchoring impl/spec sources, typed-op migration,
  state-invariant statements, decomposition, paper-pulling, etc.

Adding a new mode:
1. Create `prompts/<mode>.md` describing what one cycle of that mode
   does.
2. Run `./scripts/hunt <target> --mode <mode>`.

The file content is sent as the user prompt verbatim — no templating.
Cross-references to `AGENTS.md` work because it's loaded as the system
prompt and visible in the agent's working dir.
