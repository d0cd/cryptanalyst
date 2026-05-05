# smoke-09

**Function-style alias:** `kex-handler`
**Original bug-class name:** `key-exchange`
## Expected findings

From the codex/gpt-5.5 sweep on 2026-05-05:

- **MEDIUM** — `key_confirmation_role_confusion_reflection`
  verify_peer_confirmation ignores its my_role argument and accepts either the client_finished or server_finished HMAC label.

## Attack approach observed

- pattern_matching + property_test + exploit_reproduction

## Fixtures

None.

## Notes

_Reviewer notes go here. The agent cannot read this file (only `code/` is bind-mounted into the container)._
