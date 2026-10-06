# TRACEIQ Synthetic Data Foundation

This package owns deterministic, production-plausible incident telemetry for TRACEIQ.

## Generate all scenarios

```powershell
$env:PYTHONPATH="data/src"
python data/src/traceiq_data/generate.py
```

Output is written to `data/generated/`.

`data/generated/.test_ground_truth/` is test-only and must never be exposed by application APIs or passed to AI investigators.

## Test

```powershell
$env:PYTHONPATH="data/src"
pytest data/tests -q
```
