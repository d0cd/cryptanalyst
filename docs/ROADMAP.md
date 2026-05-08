# Production Codebase Candidates — Complete Research

Assembled from 8 research threads across CVE databases, Trail of Bits, NCC Group,
Quarkslab, Kudelski, Cure53, Least Authority, Veridise, Fiat-Crypto, and academic papers.

## Bug Classes Already Covered by Our Harness

(39 targets — no need to add more of these)

- Textbook RSA, ECDSA nonce bias, invalid curve, CRT fault, signature malleability
- AES-CBC IV reuse, GCM nonce reuse, ECB mode, timing side-channels, weak PRNG
- HMAC canonicalization, cert chain validation, Merkle domain separation
- Key exchange reflection, Schnorr rogue-key, OPRF DLEQ binding
- ML-KEM FO transform, GCM counter wrap, KDF context separation
- JWT embedded key, DH subgroup, RSA lax PKCS#1v1.5 parsing
- Shamir field-size wrapping, Feldman VSS g=1, Ed25519 hash omission
- Anomalous curve (Smart's attack), Boneh-Durfee small-d, Coppersmith partial key
- Psychic signatures (r=0,s=0), protocol state machine skip
- Commitment binding (80-bit truncation), polynomial commitment degree bound
- SSE deterministic encryption leakage, wrong curve (P-256 relabeled)
- Sigma protocol nonce reuse in batch proofs

## New Bug Classes NOT Yet Covered (Deduplicated)

### ZK Circuit Security (0 targets currently — biggest gap)

| # | Bug class | Real-world source | Severity | Tool |
|---|---|---|---|---|
| 1 | **Incomplete Fiat-Shamir transcript** | Frozen Heart: PlonK (Dusk, SnarkJS, gnark), Bulletproofs (ING, SECBIT, Adjoint), Girault (ZenGo). Incognito Chain: $M theft risk. | Critical | Lean |
| 2 | **Under-constrained circuit signal** | Tornado Cash (`=` vs `<==`), Axiom Halo2 (`assert_equal` compares a to a), circomlib Window4/Bits2Point (Veridise), zkSync Era upper 128 bits (ChainLight $50k bounty) | Critical | Lean/SMT |
| 3 | **Missing range check in circuit** | Scroll zkEVM byte range (Zellic), Dark Forest coordinate overflow, Loopring 3.6 arithmetic gadget field overflow | High | SageMath |
| 4 | **Non-unique witness / non-canonical encoding** | Semaphore: input not reduced mod q → 5 valid witnesses. EZKL: non-canonical zero sign in decomposition | High | Lean |
| 5 | **Disabled constraint (enabled=0)** | Zkopru: EdDSA verification disabled in circuit via `enabled` flag | Critical | Lean |
| 6 | **Modular wraparound in integer division** | EZKL: division accepts large field elements via mod-p (7/2 = 17) | High | SageMath |

### Field Arithmetic Bugs (0 targets currently)

| # | Bug class | Real-world source | Severity | Tool |
|---|---|---|---|---|
| 7 | **Carry propagation to wrong limb** | Ed25519 amd64 (SUPERCOP, p≈2^{-60}), BouncyCastle Nat256.square, OpenSSL P256 squaring, OpenSSL P384 reduction, OpenSSL Poly1305 (4 separate bugs). 9/30 entries in Fiat-Crypto catalog. | Critical | SageMath/Lean |
| 8 | **Unreduced field element comparison** | OpenSSL nistz256 point add (wrong add-vs-double branch), Go P-224 `>` vs `>=` underflow (CVE-2021-3114), Go P-256 unreduced scalar (CVE-2023-24532) | High | SageMath |
| 9 | **Non-canonical serialization** | curve25519-donna non-canonical wire output, curve25519-dalek Scalar::from_bits allows ≥L, libcrux X25519 missing zero-check | High | SageMath |

### Protocol / Spec-Level Bugs

| # | Bug class | Real-world source | Severity | Tool |
|---|---|---|---|---|
| 10 | **Spec-level error (min vs max)** | Lindell 2-party ECDSA paper: min(a,b) instead of max for Paillier modulus (Kudelski) | High | Lean |
| 11 | **Wrong constant in "verified" code** | libcrux ML-KEM decompression constant, ML-DSA NTT multiply spec — proofs were admitted not checked ("Verification Theatre") | Critical | Lean |
| 12 | **CCS/state-machine injection** | OpenSSL EarlyCCS (CVE-2014-0224): CCS before key exchange. SMACK: skip ServerKeyExchange in 5 TLS implementations. | Critical | Lean |
| 13 | **Tonelli-Shanks on composite modulus** | OpenSSL BN_mod_sqrt infinite loop (CVE-2022-0778) | High | SageMath |
| 14 | **Pairing curve security degradation** | Zkopru/BN254: NFS advances reduced security from ~128 to ~96 bits | High | SageMath |

## Recommended Implementation Priority

### Phase 1: ZK Circuit Targets (biggest gap, highest real-world impact)

| Target | Bug | Difficulty |
|---|---|---|
| `frozen-heart` | Fiat-Shamir transcript omits public input → proof forgery | 8/10 |
| `unconstrained-circuit` | Assignment without constraint → prover sets arbitrary output | 6/10 |
| `missing-range-check` | Field element where byte expected → arithmetic overflow | 5/10 |
| `field-wraparound` | Division accepts mod-p answer instead of integer | 6/10 |

### Phase 2: Field Arithmetic Targets (highest density in Fiat-Crypto catalog)

| Target | Bug | Difficulty |
|---|---|---|
| `carry-bug` | 5-limb multiply propagates carry to wrong limb (p≈2^{-60}) | 9/10 |
| `unreduced-compare` | EC point add compares unreduced values → wrong branch | 7/10 |
| `non-canonical-scalar` | Scalar from bytes allows ≥ group order → arithmetic errors | 6/10 |

### Phase 3: Protocol/Spec Targets

| Target | Bug | Difficulty |
|---|---|---|
| `tonelli-shanks` | Square root infinite-loops on composite modulus | 5/10 |
| `unreduced-scalar` | EC scalar mult doesn't reduce k mod N | 5/10 |

## Key Sources

### Audit Reports
- [Trail of Bits — Frozen Heart series](https://blog.trailofbits.com/2022/04/13/part-1-coordinated-disclosure-of-vulnerabilities-affecting-girault-bulletproofs-and-plonk/)
- [Trail of Bits — Axiom Halo2](https://blog.trailofbits.com/2025/05/30/a-deep-dive-into-axioms-halo2-circuits/)
- [Quarkslab — Monero Bulletproofs](https://blog.quarkslab.com/security-audit-of-monero-bulletproofs.html)
- [Quarkslab — curve25519-dalek](https://blog.quarkslab.com/security-audit-of-dalek-libraries.html)
- [Kudelski — KZen multi-party ECDSA](https://research.kudelskisecurity.com/2019/11/04/audit-of-kzens-multi-party-ecdsa/)
- [Veridise — circomlib (0xPARC)](https://veridise.com/wp-content/uploads/2023/02/VAR-circom-bigint.pdf)
- [Least Authority — Zkopru](http://leastauthority.com/static/publications/LeastAuthority_Ethereum_Foundation_Zkopru_zk-SNARK_Circuits_Smart_Contracts_Final_Audit_Report.pdf)
- [Least Authority — Loopring 3.6](https://leastauthority.com/static/publications/LeastAuthority_Loopring_3.6_Design_Implementation_Circuit_Final_Audit_Report.pdf)
- [NCC Group — Stark Bank ECDSA](https://research.nccgroup.com/2021/11/08/technical-advisory-arbitrary-signature-forgery-in-stark-bank-ecdsa-libraries/)
- [Zellic — Scroll zkEVM](https://github.com/Zellic/publications/blob/master/Scroll%20zkEVM%20-%20Part%201%20-%20Audit%20Report.pdf)

### Bug Catalogs
- [Fiat-Crypto defect list (30 entries)](https://github.com/mit-plv/fiat-crypto/blob/master/crypto-defects.md)
- [0xPARC zk-bug-tracker](https://github.com/0xPARC/zk-bug-tracker)
- [jvdsn/crypto-attacks](https://github.com/jvdsn/crypto-attacks)

### Academic Papers
- Lazar et al. "Why Does Cryptographic Software Fail?" (APSys 2014)
- Beurdouche et al. "A Messy State of the Union" — SMACK attacks (S&P 2015)
- "Verification Theatre" — libcrux bugs (ePrint 2026/192)
- "Weak Fiat-Shamir Attacks on Modern Proof Systems" (IEEE S&P 2023)
