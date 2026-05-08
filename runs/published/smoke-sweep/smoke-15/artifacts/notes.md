# Notes

## Substantiated

- `code/sse.py` uses `deterministic_encrypt(keys.doc_id_key, did.encode())` for every posting-list entry and again as the key in `EncryptedIndex.documents`. Equal encrypted document IDs are intentionally reusable, but that lets the server join all posting lists by document membership. The PoC in `artifacts/repro/f1_sse_cross_keyword_leakage.py` demonstrates leakage beyond the stated search/access pattern.

## Follow-up Leads

- `client_decrypt_results` accepts any server-supplied encrypted document ID that decrypts and exists in `index.documents`; the result set is not authenticated against the queried keyword token. That is a malicious-server integrity issue, but the module's stated security goal is privacy against server learning, so I did not include it as a substantiated finding.
- Duplicate keywords inside one document produce duplicate encrypted doc IDs in that keyword's result list. This is a functional deduplication gap rather than a cryptographic break.
