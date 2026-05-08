# Threat model — `code/auth.py`

## Construction
HMAC-SHA256 message authentication code (`compute_tag`) with a verify
function (`verify`) that re-computes the tag and compares the
result against an attacker-supplied tag.

## Adversary roles

### Network attacker
- **Capabilities**: submits arbitrary `(message, tag)` pairs to the
  verifier; observes verify outcome (accept/reject) and **timing of the
  reject decision** (round-trip time, response latency, log timestamps,
  any other side-channel that leaks how long `verify` ran).
- **Wants**: produce a forged `(message, tag')` pair that the verifier
  accepts, without knowing the key.
- **Does not control**: the server's secret `key`.

### Sender / honest user
- Out of scope (cannot mount this attack with knowledge of the key).

## Trust boundaries

The single trust boundary is the `verify(key, message, tag)` API:

| Parameter | Attacker-controlled? | Notes |
|---|---|---|
| `key`     | No  | Server-side secret. |
| `message` | Yes | The forgery target. |
| `tag`     | Yes | Forged candidate. |

`compute_tag(key, message)` is internal-only and only ever consumes
the trusted key plus the (attacker-chosen) message — its output is
the comparison reference, not user-supplied.

## Mapping of attacker capabilities to code

`code/auth.py:9–16` is the entire trust boundary. Specifically:

- L10: `expected = compute_tag(key, message)` — recomputes correct tag.
- L11–12: length check, returns `False` on length mismatch. Length
  is public (always 32 for SHA-256 MAC), so no secret leak here.
- L13–15: **byte-by-byte loop with short-circuit return on the first
  mismatch.** This is the timing side-channel.
- L16: `return True` when all bytes match.

## Hypotheses

| # | Class                | Site            | Attacker capability used                                |
|---|----------------------|-----------------|---------------------------------------------------------|
| H1 | timing side-channel | auth.py:13–15  | network attacker with response-timing observation       |
| H2 | length-leak (minor)  | auth.py:11–12  | network attacker — but length is always 32, not secret  |
| H3 | absence of key validation | auth.py:5,9 | n/a — Python `hmac.new` accepts any byte length         |

H1 is the load-bearing concern. H2 is a near-non-issue (the tag
length is fixed and public). H3 is not exploitable for HMAC.

## Why H1 is real, briefly

The standard library provides `hmac.compare_digest`, an explicitly
constant-time comparator, *for exactly this purpose*. Using a Python
`for ... if a != b: return False` loop instead introduces a
data-dependent branch whose iteration count depends on the position
of the first byte mismatch. An attacker who can observe verify
latency can recover the expected tag byte-by-byte:

1. Submit `(m, t_guess)` for each candidate first byte (256 trials).
2. The candidate whose verify() takes longest matched the first byte
   of `expected` (the loop iterated one step further).
3. Iterate over all 32 bytes ⇒ ≈256·32 = 8192 trial submissions
   per message recovers the tag, after which forgery is trivial.

This is the Keyczar / Nate Lawson timing attack, well-documented
since 2009.
