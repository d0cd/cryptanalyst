# Notes

- `code/oracle.py` implements MAC-then-encrypt with AES-CBC and PKCS#7 padding. The exploitable issue is not CBC alone; it is the combination of padding validation before MAC validation plus distinct `PaddingError`/`MacError` outcomes.
- `ENC_KEY` and `MAC_KEY` are hardcoded constants in `code/oracle.py` lines 16-23. I did not record this as a separate finding because the provided challenge is structured around oracle access, but real deployments should load per-environment secrets from a key-management boundary instead of source code.
- No Sage or Lean artifact was needed; the bug is directly reproducible with the Python oracle.
