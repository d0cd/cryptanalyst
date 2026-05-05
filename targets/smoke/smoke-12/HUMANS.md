# smoke-12

**Function-style alias:** `mac-utility`
**Original bug-class name:** `length-extension`
## Expected findings

From the codex/gpt-5.5 sweep on 2026-05-05:

- **HIGH** — `sha256_secret_prefix_mac_length_extension`
  The MAC is computed as SHA256(key || message).

## Attack approach observed

- pattern_matching + exploit_reproduction

## Fixtures

None.

## Notes

_Reviewer notes go here. The agent cannot read this file (only `code/` is bind-mounted into the container)._
