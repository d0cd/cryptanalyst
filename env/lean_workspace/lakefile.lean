import Lake
open Lake DSL

package CryptoAudit where
  leanOptions := #[⟨`pp.unicode.fun, true⟩]

require mathlib from git
  "https://github.com/leanprover-community/mathlib4.git" @ "v4.15.0"

@[default_target]
lean_lib CryptoAudit where
  globs := #[.submodules `CryptoAudit]
