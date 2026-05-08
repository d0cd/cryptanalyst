# Crypto Audit Notes

## Scope

The target contains a single file, `code/keygen.py`.

## Substantiated Finding

`generate_session_key()` calls `random.seed(int(time.time()))` immediately before generating each byte with `random.randint(0, 255)`. This makes session keys deterministic from the Unix timestamp in seconds and repeats keys for all calls in the same second.

The reproduction in `artifacts/repro/predict_time_seeded_key.py` demonstrates both properties:

- exact key recovery from a small timestamp window;
- duplicate keys on a second call within the same second.

## Verification

Commands run:

```sh
PYTHONPYCACHEPREFIX=artifacts/pycache python3 -m py_compile code/keygen.py artifacts/repro/predict_time_seeded_key.py
python3 artifacts/repro/predict_time_seeded_key.py
```

The first compile attempt without `PYTHONPYCACHEPREFIX` failed because Python tried to create `code/__pycache__` under the read-only target tree. Redirecting the bytecode cache into `artifacts/` resolved that environment issue.
