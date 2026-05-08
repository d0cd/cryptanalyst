# Notes

Substantiated findings:

- F1: Leaves and internal nodes are both hashed as plain SHA-256 inputs with no domain-separation prefix. This lets an attacker reinterpret an internal node preimage as a leaf value and pass `verify_proof` for data that was never in the committed item list.
- F2: Odd tree levels duplicate the last node. For several list sizes, appending a duplicate of the final leaf produces the same root as the shorter list, so the root alone does not commit to the exact list length or multiplicity.

Other observations not promoted to findings:

- `verify_proof` treats any direction other than `"L"` as `"R"` (`else` branch). This is proof malleability/input-validation weakness, but I did not record it as a cryptographic finding because it does not by itself demonstrate false membership.
- `MerkleProof` carries no index or tree size, so callers cannot enforce RFC-style proof-shape checks. This amplifies the two findings above, but the standalone demonstrations are clearer.
