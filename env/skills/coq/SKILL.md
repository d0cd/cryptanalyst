---
name: coq-fcf
description: Coq + FCF (Foundational Cryptography Framework) for game-based cryptographic proofs. Use when prompts/formalize.md's Tool selection rule says Lean's PMF infrastructure can't yet model the property — typically advantage definitions and game-hop reductions. Loaded on demand, not every cycle.
---

# Coq + FCF — game-based crypto in the cryptanalyst harness

## When to reach for this skill

`prompts/formalize.md`'s **Tool selection** section is authoritative.
Coq+FCF is the **right tool for probabilistic game-based reasoning** —
not a fallback when Lean fails. Reach for it whenever the property's
natural shape is one of:

- An **advantage definition**: `Adv(A) = | Pr[Game1 A] − Pr[Game0 A] |`
- A **game-hop reduction**: `Pr[Game_i] − Pr[Game_{i+1}] ≤ ε` reducing
  one experiment to a slightly different one with bounded distance
- A **security reduction**: an adversary against scheme S yields an
  adversary against assumption H with comparable advantage
- A **probabilistic claim** about an experiment's distribution
  (collision probability, statistical distance, hybrid argument)

FCF's monadic `Comp` and tactics like `fcf_simp`, `fcf_inline`,
`fcf_irr_l`, `dist_compute` are specifically built for this shape.
Replicating that machinery in Lean+Mathlib's `PMF` is significantly
harder than using FCF directly.

**The trust base lives in Lean** — that's the spine. Coq files produce
probabilistic-game artifacts that Lean axioms cite via
`CoqReference:`. You're not migrating off Lean; you're picking the
specialized tool for the specialized layer.

**Avoid Coq for**: protocol-level operational traces (Lean's `List Op`
+ `native_decide` is right), state-machine invariants (Lean is right),
concrete parameter validity (Sage is right), reductions that don't
involve probability (Lean is right). Using Coq for non-probabilistic
properties is the failure mode — fragments the trust base for no
benefit.

## Workspace conventions

- **Coq files live under `/repo/state/coq/<NAME>.v`**. Parallel to `state/lean/`
  and `state/sage/`.
- **Citation back to Lean**: every Coq file is referenced from a Lean axiom via
  `CoqReference: state/coq/<file>.v`, parallel to `SageReference:` and
  `SpecSource:`. The Coq file produces the probability-level theorem; the Lean
  axiom states the property abstractly. **Cite, don't restate.**
- **Coq + coq-lsp pre-installed via OPAM** at `/opt/opam/coq-8.18/`. `coqc`,
  `coqtop`, and the `pet` (Petanque) binary are on PATH.

## First-time FCF install (runtime, ~5 min)

FCF master HEAD doesn't compile against Coq 8.18 (proof breakage in
`ProgramLogic.v`); the most recent FCF tag is `coq_8_16`. The image therefore
does NOT pre-bake FCF — instead, the first Coq cycle that needs FCF installs
it inline. **Run this once** when starting your first `coq-fcf` cycle:

```bash
# Clone the coq_8_16 tag (last known-good FCF release):
git clone --depth 1 --branch coq_8_16 https://github.com/adampetcher/fcf.git /opt/fcf
cd /opt/fcf

# Build with the OPAM Coq 8.18 toolchain. If make fails on a unification
# error in ProgramLogic.v or similar, try a smaller fix:
#   1. Read the failing .v file's offending lemma — usually a tactic
#      whose semantics shifted between 8.16 and 8.18.
#   2. Replace the broken tactic with the 8.18-compatible equivalent
#      (often `apply @lemma` instead of `apply lemma`, or `change` instead
#      of `replace`).
#   3. Commit the patch under /opt/fcf/patches/<file>.patch and apply
#      with `git apply` next time.
make -j$(nproc) || echo "FCF build needs Coq-8.18 patches — see comments below."
```

`COQPATH` is already set to include `/opt/fcf/src` once the build succeeds, so
`Require Import FCF.FCF` resolves automatically.

**If FCF master gains 8.18 support later**, that's a Dockerfile fix —
record it as a postmortem note in `notes.md` rather than working around in
each cycle.

## Default workflow — use the rocq MCP

Prefer interactive iteration over `coqc` per check. The `rocq` MCP tools are
the Coq counterpart to the `lean` MCP tools you already use:

- `rocq.rocq_start` — open a proof at a named theorem; returns initial goal
- `rocq.rocq_step_multi` — apply a tactic block; returns updated goals
- `rocq.rocq_check` — inspect current goal state
- `rocq.rocq_query` — run `Search` / `Print` / `Check` against the loaded
  environment. **Use this before guessing tactics from training memory** —
  the library tells you what's available in this exact build.
- `rocq.rocq_assumptions` — what's in the local context
- `rocq.rocq_toc` — table of contents for an open file
- `rocq.rocq_compile` / `rocq.rocq_compile_file` — full `coqc` for completed
  proofs
- `rocq.rocq_verify` — verify a single named theorem
- `rocq.rocq_diag` — environment / load-path diagnostics; first thing to call
  if something's not loading

Falls back to `coqc` for whole-file compilation when the proof is complete.

## FCF skeleton — advantage-game replacement for a stuck Lean axiom

```coq
(* /repo/state/coq/MyScheme_advantage.v *)
Require Import FCF.FCF.
Require Import FCF.OracleHybrid.

(* The probabilistic experiment: a Comp/OracleComp value. *)
Definition Game0 (A : Adversary) : Comp bool :=
  ... .

Definition Game1 (A : Adversary) : Comp bool :=
  ... .

(* Adversary type — typically a randomized procedure. *)
Definition Adversary := nat -> Comp bool.

(* Advantage = | Pr[Game1] - Pr[Game0] |. *)
Definition advantage (A : Adversary) : Rat :=
  | Pr[ Game1 A ] - Pr[ Game0 A ] |.

(* Reduction theorem — bounds advantage by an underlying assumption. *)
Theorem advantage_le_negligible : forall A,
  poly_time A ->
  advantage A <= negligible_in_security_param.
Proof.
  ... .
Qed.
```

**Key FCF concepts**:

- `Comp A` is a probability monad; `Bind` and `Ret` compose probabilistic
  experiments. `Pr[c]` projects to a rational probability `Rat`.
- Game hops are `Theorem` statements relating two `Comp` definitions. The
  classical "indistinguishability up to event B" pattern is FCF's
  `prob_distance_close_distinguishability` lemma.
- Adversaries are first-class `Comp` values; reductions are functions
  `Adversary → Adversary` that wrap the original adversary.

## Common stuck points and fixes

| Symptom | Cause | Fix |
|---|---|---|
| `Require Import FCF.FCF` fails | `COQPATH` not set or wrong | Run `rocq.rocq_diag` to inspect load path; image sets `COQPATH=/opt/opam/coq-8.18/lib/coq/user-contrib` |
| `Pr` goal won't close | Probability rewriting not yet triggered | Try FCF tactics in order: `fcf_simp`, `fcf_inline`, `fcf_irr_l` / `fcf_irr_r`, `dist_compute` for concrete values |
| Slow `coqc` on game-hop theorem | Probability rewriting unbatched | Factor large theorems into helper lemmas; FCF proofs scale poorly with monolithic statements |
| Don't know which tactic applies | Guessing from training data | Use `rocq.rocq_query` with `Search Pr.` or `Search advantage.` — the library will tell you what's available |
| `Comp` type confusion | Mixing `Comp` and pure `bool`-valued functions | `Comp` is a monad; lift pure values with `ret`, sequence with `Bind`. See FCF's `FCF/Comp.v` for the laws. |
| Tactic library missing | Some FCF lemmas are in submodules | `Require Import FCF.RndGrp` for group-based games; `FCF.OracleHybrid` for hybrid arguments; check the `.v` file referenced by the lemma |

## Where the FCF library lives

```
/opt/opam/coq-8.18/lib/coq/user-contrib/FCF/
```

Read these `.v` files directly when MCP introspection isn't specific enough:
- `FCF.v` — top-level exports (the one you typically `Require Import`)
- `Comp.v` — the probability monad
- `Procedure.v` — adversary models
- `OracleHybrid.v` — hybrid argument framework
- `RndGrp.v` — random-group experiments (DDH-style)
- `RndNat.v`, `RndPerm.v` — finite-set sampling primitives

## Failure modes to avoid

1. **Don't duplicate.** A property modeled in Lean AND Coq is research
   overhead, not coverage. Pick the tool that fits the property's shape
   (game-based → Coq, structural → Lean, numerical → Sage), then cite from
   the Lean spine via `CoqReference:` / `SageReference:` / `SpecSource:`.
2. **Don't use Coq for non-probabilistic properties.** A typed Lean theorem
   about `List Op` order, a state-machine invariant, or a structural
   reduction belongs in Lean — using Coq fragments the trust base for no
   benefit. Reach for Coq when the proof obligation involves `Pr`,
   adversary advantage, or game distance; otherwise stay in Lean.
3. **Don't drift into the OCaml tooling.** `opam install` is a maintainer
   action; runtime cycles use the pre-installed `coqc` and the FCF clone
   built per the first-time install above. If you find yourself wanting a
   new OPAM package, that's a postmortem item for the harness, not a
   runtime fix.

## End-of-cycle checklist for a Coq cycle

- [ ] `state/coq/<file>.v` builds clean (`rocq.rocq_compile_file` returns OK)
- [ ] Lean axiom that motivated the cycle has a `CoqReference: state/coq/<file>.v`
      block (parallel to `SageReference:` / `SpecSource:`)
- [ ] If the cycle replaced a `VACUOUS-PLACEHOLDER` axiom, the annotation is
      removed
- [ ] `## Caveats` section in `notes.md` lists any FCF tactics that admitted
      with `admit` or `Admitted` (these are the Coq equivalent of `sorry`)
- [ ] The Coq theorem statement is *cited* by the Lean axiom, not duplicated
