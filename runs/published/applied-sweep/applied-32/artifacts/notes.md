# Notes

- `prove_interactive`/`verify_interactive` expose a transcript-checking API, not a stateful interactive verifier. If a caller treats `verify_interactive(Y, proof)` as a transferable proof, a transcript for any valid public key can be simulated by choosing `c` and `s` and setting `R = g^s * Y^-c mod P`. I did not record this separately because the interactive protocol is only sound when the verifier chooses the challenge after receiving the commitment and tracks that session state.
- The finite-field parameters are 512-bit `P` and 160-bit `Q`. This is far below modern finite-field discrete-log recommendations, but I did not include it as a substantiated finding because no practical discrete-log reproduction was produced under the 30-second artifact bar.
