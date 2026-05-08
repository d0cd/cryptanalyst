# Installation

Requires Docker and an API key for whichever agent you use.

## Hardware

The container is configured for **16 GB RAM** and **4 CPUs** (set in `scripts/hunt`); lower may OOM mid-cycle. The image is **~16 GB** on disk after build, plus ~5 GB per actively-running target. First-time build downloads Mathlib's binary cache (~15-25 min depending on network). Both arm64 (Apple Silicon) and amd64 are supported automatically.

## 1. Build the image

```bash
./scripts/build-image
```

First build is slow — Mathlib takes 15-25 minutes. Cached for subsequent
builds.

## 2. Generate applied-tier fixtures (only before running applied targets)

```bash
./scripts/generate-fixtures
```

Smoke targets don't need this; skip if you're only running smoke.

## 3. Set credentials

The harness consults env vars for both agents. Auth files
(`~/.claude/.credentials.json`, `~/.codex/auth.json`) are *not* mounted into
the container for Claude because the OAuth tokens those files hold expire
in ~10–15 minutes and can't be refreshed non-interactively.

### Claude — pick one (preferred first)

**Long-lived OAuth token (1-year, bills against Max plan):**
```bash
claude setup-token  # interactive on the host
export CLAUDE_CODE_OAUTH_TOKEN=<the-token-it-prints>
```

**Console-issued API key (per-token billing, separate from Max plan):**
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

If both are set on the host, `scripts/hunt` forwards only the OAuth token
to the container — Claude Code itself prefers `ANTHROPIC_API_KEY` when
both are visible, and you usually want Max-plan billing.

### Codex

The codex CLI's OAuth file at `~/.codex/auth.json` *is* long-lived and
self-refreshing, so we mount it directly:

```bash
codex login                    # one-time, creates ~/.codex/auth.json
# or
export OPENAI_API_KEY=sk-...
```

### Local mode (Claude only, no Docker)

For Claude OAuth without minting a token (uses your local keychain login
directly), use `./scripts/hunt-local <target>` — it skips Docker entirely.
Fewer isolation guarantees, but no token handling.

## Security caveats

- `CLAUDE_CODE_OAUTH_TOKEN` has a fixed 1-year lifetime; no flag to issue
  shorter-lived tokens.
- Anthropic API keys (`sk-ant-*`) are scanned by GitHub's secret-scanning
  partner program; OAuth tokens are not (publicly) scanned and have no
  documented revocation UI.
- Treat the OAuth token like an SSH private key: never commit, rotate via
  `claude setup-token` periodically, and assume console revocation is the
  only recovery path if leaked.
