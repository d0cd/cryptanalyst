# Notes

## Commitment verification length mismatch

`verify_nonce_commitments()` in `code/multisig.py` lines 115-126 uses
`zip(commitments, nonce_points)` and never checks that the lists have equal
length. As a result, extra nonce points without commitments, extra commitments,
or even two empty inputs are accepted as long as every paired prefix matches.

This is a protocol-safety footgun because the docstring says it verifies all
nonce reveals match their commitments, but it only verifies the paired prefix.
I did not include it in `findings.json` because the strongest demonstrated
impact is API misuse rather than a standalone signature forgery.
