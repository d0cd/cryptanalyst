# Published Audit Results

Curated results from the crypto bug-finding harness, organized by
tier and methodology.

## Results summary

### Smoke tier (17/17 targets, 100% recall)

All 17 smoke targets produced at least one finding matching the
expected bug class. Agent: Codex/gpt-5.5, hunt mode, 10 cycles each.

See `smoke-sweep/results.json` for per-target breakdown.

### Applied tier (21/33 swept, 12 pending)

All 21 swept applied targets produced findings matching ground truth.
12 targets remain unswept — 6 of these are used in the formalize-hunt
demonstration below.

See `applied-sweep/results.json` for per-target breakdown.

### Formalize-hunt demonstration (6 targets)

The hardest unswept applied targets, run with the `formalize` -> `hunt`
methodology to demonstrate that formal modeling improves bug-finding
on targets where pattern matching alone may not suffice.

Each target is run with both agents (Claude, Codex) in both modes:
1. `--mode formalize --cycles 5` — build a Lean/Sage model
2. `--mode hunt --cycles 5` — find bugs, with the model as context

Targets selected for formal-model-dependent bug classes:

| Target | Bug class | Why formal matters |
|--------|-----------|-------------------|
| applied-21 | frozen-heart | Fiat-Shamir transcript ordering |
| applied-04 | unconstrained-circuit | ZK constraint analysis |
| applied-33 | groth16-commit | Protocol-level commitment |
| applied-05 | protocol-binding | Binding property |
| applied-16 | auth-reflection | State machine ordering |
| applied-03 | hostile-witness | Adversarial witness reasoning |

See `formalize-hunt/` for results.

## Directory structure

```
published/
  README.md
  smoke-sweep/
    results.json              aggregate results
    smoke-01/                 per-target: run.json + findings
    ...
  applied-sweep/
    results.json
    applied-01/
    ...
  formalize-hunt/
    applied-21-frozen-heart/
      formalize-codex/        formalize mode run
      hunt-codex/             hunt mode run
      formalize-claude/
      hunt-claude/
      comparison.md           findings vs ground truth
    ...
```
