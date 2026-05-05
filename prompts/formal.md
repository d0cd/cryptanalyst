Find bugs in the cryptographic code in `code/`.

Read `AGENTS.md` for the workspace, the approaches available, the
findings bar, and the schema. Produce `artifacts/findings.json`
(always — empty list is acceptable) and any reproductions, notes, or
verification artifacts your findings warrant.

**This run requires formal artifacts.**

For every candidate finding, before declaring it substantiated:

1. **State the security property the implementation is supposed to
   satisfy as a Lean theorem statement.** Examples of the kinds of
   properties that benefit from a formal statement:
   - "Verifier accepts a signature ⟹ a matching honest-prover trace
     exists." (soundness)
   - "Commitments to distinct messages are distinct." (binding)
   - "If party A completes the protocol, the partner exists with
     matching session identifiers." (authentication)
   - "Re-encryption of a decapsulated ciphertext yields the original."
     (FO transform soundness)

2. **Type-check the statement** using the `mcp__lean__check` tool.
   The MCP keeps a hot Mathlib REPL — use narrow imports
   (`import Mathlib.Algebra.Group.Basic`, etc.) rather than the full
   `import Mathlib` to keep startup fast. Subsequent calls reuse the
   environment via the `env` parameter.

3. **One of the following must hold for the finding to be substantiated:**
   - (a) you proved the property and the proof reveals the implementation
     does *not* satisfy it (find the gap between proof and code), or
   - (b) you cannot state the property cleanly against the implementation
     as written — *that itself is the finding*, document the obstruction, or
     (c) you state and refute the property with a concrete counterexample,
     in which case both the Lean statement and the Python PoC go in
     `artifacts/`.

4. **Save the Lean source** via `mcp__lean__save_to_artifact` (the path
   may be nested, e.g., `Soundness/Schnorr.lean`). The on-disk artifact
   is part of the finding's evidence.

For protocol-level multi-file modeling, write Lean files directly into
`/opt/lean-workspace/CryptoAudit/<your-namespace>/` and run `lake build`
via Bash to type-check across imports. Copy final versions into
`artifacts/lean/` so the run is self-contained.

**Concrete-attack PoCs (Python repros) are still required where the bug
is exhibitable by a single execution** — but they are not sufficient on
their own for this run. Every finding gets a Lean artifact alongside
its Python repro. If a property is genuinely concrete-only (e.g. "this
specific input crashes"), record that explicitly in `notes.md` and
explain why no Lean statement was attempted.

The point of this mode is to surface the *shape* of each bug at the
formal level, not just the existence of an attack. Even a Lean file
with `sorry`-filled proofs is acceptable evidence — it forces the
question "what is this code actually trying to guarantee?"
