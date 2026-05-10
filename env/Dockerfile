FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8

# --- Base toolchains ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.12 python3.12-dev python3-pip python3-venv \
    libgmp-dev libmpfr-dev libmpc-dev \
    nodejs npm \
    build-essential clang git curl jq ripgrep fd-find \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# --- SageMath via conda-forge (Ubuntu 24.04 dropped the apt package) ---
# Sage docs recommend conda-forge for distros without an up-to-date package.
RUN curl -sSfL "https://github.com/conda-forge/miniforge/releases/download/24.11.0-0/Miniforge3-Linux-$(uname -m).sh" -o /tmp/miniforge.sh \
    && bash /tmp/miniforge.sh -b -p /opt/conda \
    && rm /tmp/miniforge.sh \
    && /opt/conda/bin/conda install -n base -c conda-forge -y sage=10.5 python=3.11 \
    && /opt/conda/bin/conda clean -afy \
    && ln -s /opt/conda/bin/sage /usr/local/bin/sage

# --- Lean 4 ---
# Install elan to /opt so the toolchain is reachable when the container
# runs as a non-root host UID (avoids /root/.elan being 0700-owned-by-root).
ENV ELAN_HOME=/opt/elan
RUN curl -sSf https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh \
    | sh -s -- -y --default-toolchain leanprover/lean4:v4.15.0
ENV PATH="/opt/elan/bin:${PATH}"

# --- Lean REPL (used by the MCP server) ---
RUN git clone https://github.com/leanprover-community/repl /opt/lean-repl \
    && cd /opt/lean-repl \
    && git checkout v4.15.0 \
    && lake build

# --- Pre-built Lean workspace with Mathlib ---
COPY env/lean_workspace /opt/lean-workspace
WORKDIR /opt/lean-workspace
RUN lake exe cache get && lake build

# Mathlib and its transitive deps are cloned as root at image build time.
# When the container runs as a non-root host UID, git's CVE-2022-24765
# safe.directory check rejects queries on those root-owned repos. Lake
# then can't read the remote URL, decides "URL has changed", and tries
# to delete and re-clone mathlib on every `lake build`. Whitelist all
# directories system-wide so any UID can run git against the prebuilt
# clones.
RUN git config --system --add safe.directory '*'

# --- Python crypto + SDKs ---
WORKDIR /
COPY env/requirements.txt /tmp/requirements.txt
RUN pip install --break-system-packages -r /tmp/requirements.txt

# --- Agent CLIs (pinned) ---
# IMPORTANT: pin these. The implementer should look up current versions
# (`npm view @anthropic-ai/claude-code version`, `npm view @openai/codex version`)
# and write specific versions here, not @latest.
RUN npm install -g \
    @anthropic-ai/claude-code@2.1.128 \
    @openai/codex@0.128.0

# --- Rust toolchain (for analyzing Rust crypto codebases like snarkVM) ---
# Installed under /opt so the non-root runtime user can read it. CARGO_HOME
# and RUSTUP_HOME are world-writable so rustup can fetch toolchains pinned
# by a target's rust-toolchain.toml on first `cargo` invocation.
ENV RUSTUP_HOME=/opt/rustup
ENV CARGO_HOME=/opt/cargo
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
    | sh -s -- -y --default-toolchain stable --profile minimal --no-modify-path \
 && chmod -R a+w /opt/rustup /opt/cargo
ENV PATH="/opt/cargo/bin:${PATH}"

# --- Lean MCP server ---
COPY env/mcp/lean /opt/lean-mcp
RUN cd /opt/lean-mcp && pip install --break-system-packages -e .

# --- Skills (proof / methodology guidance the agent loads on demand) ---
# Two upstream skill packs are vendored at pinned SHAs (Apache-2.0). Updating
# the version is a one-line ARG bump + image rebuild — same model as the
# claude-code / codex CLI pins above.
ARG LEANPROVER_SKILLS_SHA=7d3da0282e7b724b07620e45cf212f2e05e19334
ARG LEAN4_SKILLS_SHA=95406b3787957473fa97e4e8d62bd3225bcaa09b
RUN git clone https://github.com/leanprover/skills.git /opt/lean-skills \
 && git -C /opt/lean-skills checkout ${LEANPROVER_SKILLS_SHA} \
 && rm -rf /opt/lean-skills/.git \
 && git clone https://github.com/cameronfreer/lean4-skills.git /opt/lean4-skills \
 && git -C /opt/lean4-skills checkout ${LEAN4_SKILLS_SHA} \
 && rm -rf /opt/lean4-skills/.git

# In-house skills (this repo): Coq+FCF cookbook, harness conventions.
# First-class repo content under env/skills/, copied into the image so a
# rebuild is the only update mechanism.
COPY env/skills /opt/skills

# --- Coq + OPAM + FCF (game-based crypto proofs in Coq) ---
# OCaml's OPAM package manager is the standard installer for Coq + libraries.
# FCF is the Foundational Cryptography Framework — Coq library specifically
# built for game-based cryptographic proofs (advantage definitions, game hops,
# reductions). Use case in this harness: closing the structural-vacuous-
# placeholder cap on advantage axioms in the Lean trust base, where Lean
# lacks a comparable mature library.
RUN apt-get update && apt-get install -y --no-install-recommends \
    opam ocaml ocaml-findlib m4 \
    && rm -rf /var/lib/apt/lists/*

ENV OPAMROOT=/opt/opam
ENV OPAMYES=1
RUN opam init --disable-sandboxing --bare --root /opt/opam \
 && opam switch create --root /opt/opam coq-8.18 ocaml.4.14.1 \
 && eval $(opam env --root /opt/opam --switch=coq-8.18) \
 && opam repo add --root /opt/opam --switch=coq-8.18 coq-released https://coq.inria.fr/opam/released \
 && opam install --root /opt/opam --switch=coq-8.18 \
      coq.8.18.0 \
      coq-lsp \
 && opam clean -a --root /opt/opam \
 && chmod -R a+w /opt/opam

# Make Coq + coq-lsp reachable for the agent without sourcing opam env.
# coq-lsp ships the `pet` (Petanque) binary that rocq-mcp uses for interactive
# proof state inspection.
ENV PATH="/opt/opam/coq-8.18/bin:${PATH}"

# --- FCF (Foundational Cryptography Framework) — runtime install ---
# FCF master HEAD does not compile against Coq 8.18 (proof breakage in
# ProgramLogic.v); the most recent FCF tag is coq_8_16. Pre-baking FCF
# would require downgrading Coq to 8.16, which we don't want.
#
# Instead, FCF is installed at first use by the agent. The Coq skill at
# /opt/skills/coq/SKILL.md documents the exact clone+make commands.
# Container ships with git, make, ocaml, opam, coqc — everything FCF
# needs. If FCF master gains Coq 8.18 support later, move this back to
# image-bake.
ENV COQPATH="/opt/opam/coq-8.18/lib/coq/user-contrib:/opt/fcf/src"

# --- Rocq (Coq) MCP server — interactive REPL via Petanque ---
# Parallel to the Lean MCP server. Gives the agent rocq.start_proof,
# rocq.run_tactic, rocq.get_goals, rocq.search etc. for fast snippet
# iteration without spinning up `coqc` per check.
COPY env/mcp/rocq /opt/rocq-mcp
RUN cd /opt/rocq-mcp && pip install --break-system-packages -e .

# Let the runtime user write multi-file Lean projects into the workspace
# and run `lake build`. We chmod both the source tree (Audit/) and
# the build output paths under .lake/. Mathlib's cached artifacts in
# .lake/packages/ stay alone — lake only writes new modules under
# .lake/build/{lib,ir}/Audit/, which is where the +w needs to apply.
# The container runs as the host UID via `--user` (set by scripts/hunt);
# we don't bake in a runtime user here.
RUN chmod -R a+w /opt/lean-workspace/Audit \
                  /opt/lean-workspace/.lake/build

SHELL ["/bin/bash", "-c"]
