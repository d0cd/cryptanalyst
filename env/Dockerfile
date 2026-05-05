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

# --- Lean MCP server ---
COPY mcp_servers/lean /opt/lean-mcp
RUN cd /opt/lean-mcp && pip install --break-system-packages -e .

# Let the runtime user write multi-file Lean projects into the workspace
# and run `lake build`. We chmod both the source tree (CryptoAudit/) and
# the build output paths under .lake/. Mathlib's cached artifacts in
# .lake/packages/ stay alone — lake only writes new modules under
# .lake/build/{lib,ir}/CryptoAudit/, which is where the +w needs to apply.
# The container runs as the host UID via `--user` (set by scripts/hunt);
# we don't bake in a runtime user here.
RUN chmod -R a+w /opt/lean-workspace/CryptoAudit \
                  /opt/lean-workspace/.lake/build

SHELL ["/bin/bash", "-c"]
