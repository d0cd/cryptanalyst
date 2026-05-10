---
name: lean-modeling
description: Patterns and worked examples for modeling cryptographic protocols in Lean 4 + Mathlib. Five reusable templates (operational sequences, refinement, state invariants, game hops, compositional decomposition), the canonical Op-family layout, falsifiability checks, and the firstDiff helper for localizing native_decide divergences. Loaded on demand by formalize-mode cycles.
---

# Lean modeling — patterns for protocol-level proofs

Five reusable templates for the typed-data / structural-claim layer of the
trust base. Use generic names that fit the target's vocabulary; do not paste
the templates literally.

## Op family layout — one canonical inductive

Cryptographic protocols decompose into sub-protocols. Encode each sub-
protocol as its own typed `inductive Op` in its own namespace, then **wrap
all sub-protocol Ops in one canonical Op family** at the top level:

```lean
namespace LayerA
inductive Op where
  | initialize
  | recordValue (label : Label) (value : Value)
  | derive (label : Label) (input : Value)
  deriving DecidableEq, Repr
end LayerA

namespace LayerB
inductive Op where
  | beginRound (n : Nat)
  | check (lhs : Value) (rhs : Value)
  | accept
  deriving DecidableEq, Repr
end LayerB

inductive Op where
  | layerA (op : LayerA.Op)
  | layerB (op : LayerB.Op)
  deriving DecidableEq, Repr
```

**Never use a flat enum that you intend to migrate later** — the migration
breaks every theorem that pattern-matched on the old constructors. The wrapper
shape lets new sub-protocols slot in by adding a wrapper case, no migration.

`deriving DecidableEq` is roughly O(N²) at compile time; flat enums with 30+
constructors choke. Per-sub-protocol enums under a thin wrapper keeps each
inductive small.

## Five templates

### Template 1 — Operational sequences (`List Op` + `native_decide`)

```lean
def specProtocol (v0 : Value) : List Op := [
  .layerA .initialize,
  .layerA (.recordValue "input" v0),
  .layerB (.beginRound 1),
  .layerB (.check v0 v0),
  .layerB .accept ]

def implProtocol (v0 : Value) : List Op := [
  .layerA .initialize,
  .layerA (.recordValue "input" v0),
  .layerB (.beginRound 1),
  .layerB (.check v0 v0),
  .layerB .accept ]

theorem protocol_eq (v0) : specProtocol v0 = implProtocol v0 := by
  native_decide

-- Falsifiability check: a reordered impl fails the theorem.
def implReordered (v0 : Value) : List Op := [
  .layerA .initialize,
  .layerB (.beginRound 1),
  .layerA (.recordValue "input" v0),
  .layerB (.check v0 v0),
  .layerB .accept ]

example (v0) : specProtocol v0 ≠ implReordered v0 := by native_decide
```

**Catches**: ordering, missing-step, swapped-value bugs (typed parameters
surface them). **Misses**: probabilistic adversarial behavior.

### Template 2 — Game hop with adversary and advantage

```lean
structure Scheme where
  param : Nat
  encode : Value → Encoded

structure Adversary where
  guess : Encoded → Bool

def Game0 (S : Scheme) (adv : Adversary) (v : Value) : Bool :=
  adv.guess (S.encode v)

def Game1 (S : Scheme) (adv : Adversary) (e : Encoded) : Bool :=
  adv.guess e

def Advantage (S : Scheme) (adv : Adversary) (v : Value) (e : Encoded) : Real :=
  sorry  -- requires probability monad to be meaningful

axiom encoding_security :
  ∀ (S : Scheme) (adv : Adversary) (v : Value) (e : Encoded),
    polyTime adv → Advantage S adv v e ≤ negligible S.param

theorem construction_secure (S : Scheme) (adv : Adversary) (v : Value) (e : Encoded) :
    polyTime adv → constructionAdvantage S adv ≤ negligible S.param := by
  intro h
  exact reductionLemma h (encoding_security S adv v e h)
```

**Catches**: cryptographic claims with adversary quantification at the
structural level. **Misses**: probability arithmetic. For game-hop reductions
where the proof obligation is `| Pr[Game1] − Pr[Game0] | ≤ ε`, use Coq+FCF
(see `prompts/formalize.md` Tool selection); the Lean side then carries an
axiom citing the Coq theorem via `CoqReference: state/coq/<file>.v`.

### Template 3 — Refinement

```lean
structure SpecState where
  recordedInputs : List Value
  accepted : Bool
  deriving DecidableEq, Repr

structure ImplState where
  recordedInputs : List Value
  internalBuffer : List Encoded
  counter : Nat
  accepted : Bool
  deriving DecidableEq, Repr

def Refines (i : ImplState) (s : SpecState) : Prop :=
  i.recordedInputs = s.recordedInputs ∧ i.accepted = s.accepted

def specStep (s : SpecState) (op : Op) : SpecState := sorry
def implStep (i : ImplState) (op : Op) : ImplState := sorry

theorem refinement_preserved (i : ImplState) (s : SpecState) (op : Op) :
    Refines i s → Refines (implStep i op) (specStep s op) := by
  intro h
  cases op
  all_goals (constructor <;> simp_all [specStep, implStep, Refines])
```

**Catches**: abstract claims inherited by concrete impl. **Doesn't replace**:
faithful `specStep` / `implStep`.

### Template 4 — State-machine invariant

```lean
structure State where
  derivedValues : List (Label × Value)
  recordedInputs : List Label
  acceptanceFlag : Bool
  deriving DecidableEq, Repr

def step (s : State) (op : Op) : State := sorry

def DerivationsAreSourced (s : State) : Prop :=
  ∀ label value, (label, value) ∈ s.derivedValues →
    ∃ inputLabel, inputLabel ∈ s.recordedInputs ∧ derivedFrom value inputLabel

theorem inv_preserved (s : State) (op : Op) :
    DerivationsAreSourced s → DerivationsAreSourced (step s op) := by
  intro h label value hmem
  cases op <;> simp [step] at hmem <;> sorry
```

**Catches**: temporal "X must hold before Y" properties that pure operational
equality can't express.

### Template 5 — Compositional decomposition

```lean
theorem primitive_binding (S : Scheme) (adv : Adversary) :
    polyTime adv → bindingAdvantage S adv ≤ negligible S.param := by
  exact assumption_A1_reduction adv

theorem primitive_hiding (S : Scheme) (adv : Adversary) :
    polyTime adv → hidingAdvantage S adv ≤ negligible S.param := by
  exact assumption_A2_reduction adv

theorem composition_consistency (S : Scheme) :
    ∀ x y, transformsCorrectly S x y := by
  intro x y; sorry

theorem construction_secure (S : Scheme) (adv : Adversary) :
    polyTime adv → endToEndAdvantage S adv ≤ negligible S.param := by
  intro h
  have hBind := primitive_binding S adv h
  have hHide := primitive_hiding S adv h
  have hComp := composition_consistency S
  exact composition_lemma hBind hHide hComp
```

**Catches**: structures the proof tree so the trust base is enumerated leaf-
by-leaf, not hidden in one big "compiler theorem" axiom. Distinguishes a
real proof from axiom soup.

Real targets need 3-4 templates in combination — operational equality at the
call-sequence layer, refinement bridging spec/impl, state invariants for
ordering, decomposition for proof-tree structure. Game hops live in Coq+FCF
with Lean citing via `CoqReference:`.

## firstDiff — localize a `native_decide` divergence

```lean
def firstDiff [DecidableEq α] : List α → List α → Option (Nat × Option α × Option α)
  | [], []           => none
  | x :: _, []       => some (0, some x, none)
  | [], y :: _       => some (0, none, some y)
  | x :: xs, y :: ys =>
      if x = y then (firstDiff xs ys).map (fun (i, a, b) => (i+1, a, b))
      else some (0, some x, some y)
```

Then `#eval firstDiff specSeq implSeq` prints the divergence index.

## Working across multiple Lean files

The MCP `lean.check` tool type-checks one snippet against an in-memory
environment; `env` chaining extends that environment but doesn't write files.
For protocol-level modeling that needs multiple files with imports, write
directly into the pre-built workspace and run `lake build`:

- `/opt/lean-workspace/Audit/` (= `/repo/state/lean/`) is the durable
  modeling tree, bind-mounted from the target's `state/lean/` directory.
  Mathlib + the workspace are pre-built at image-bake; `lake build` is
  incremental.
- The same tree is also visible at `/repo/state/lean/` for git operations.
- Per-target work persists across runs through the bind mount.

## Lean skills (mounted, third-party)

When proof construction or Mathlib navigation comes up:

- `/opt/lean-skills/skills/` — official Lean team skills (PR conventions,
  `lean-proof/`, `mathlib-build/`, `mathlib-pr/`, `mathlib-review/`,
  `nightly-testing/`).
- `/opt/lean4-skills/plugins/lean4/` — community workflow pack
  (`prove`, `autoprove`, `formalize`, `checkpoint`, `refactor`, `golf`,
  `learn`).

Read these for proof-engineering patterns rather than inventing methodology
from first principles.
