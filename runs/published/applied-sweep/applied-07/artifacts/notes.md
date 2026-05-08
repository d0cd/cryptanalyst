# Notes

## Substantiated

- `code/ecdsa.py` defines an anomalous elliptic curve: `#E(F_p) == p`, `ord(G) == p`, and `N == P`. This makes ECDLP easy via Smart's attack. The reproduction in `artifacts/repro/F1_smart_attack.sage` recovers a private key from a public key and then signs a new message.

## Other observations

- The implementation does not validate public keys in `verify`. That is risky for any API that accepts serialized public keys from untrusted callers, but the anomalous curve already gives a stronger full key-recovery finding.
- `_point_mul` and `_point_add` are variable-time and branch on scalar bits. This is a side-channel concern for constrained devices, but I did not include it as a finding because there is no timing harness or leakage measurement here.
- The comments disagree on the intended security level and field size: the module docstring says 128-bit, another comment says 80-bit, and the actual field prime is 160 bits.
