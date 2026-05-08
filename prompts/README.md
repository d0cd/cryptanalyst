# prompts/

Two prompts go to the agent each run, from two locations:

- **`instructions/AGENTS.md`** — system prompt, loaded once. Methodology
  that holds across every cycle and every mode (threat model,
  hypothesis prioritization, findings bar, Lean conventions).
- **`prompts/<mode>.md`** — per-cycle user message, selected by
  `--mode NAME`. Mode-specific job description.

Currently shipped: **`hunt.md`** (adversarial) and **`formalize.md`**
(cumulative Lean modeling).

A new mode is just `prompts/<mode>.md` + `--mode <mode>` on the CLI.
File contents are sent verbatim — no templating.
