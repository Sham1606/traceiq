# Data Tasks

## Status

- [x] D001 Shared canonical schemas
- [x] D002 Deterministic baseline telemetry generator
- [x] D003 Four incident generators
- [x] D004 Hidden ground truth separated from visible telemetry
- [x] D005 Data validation
- [x] D006 Scenario-level causal tests
- [ ] D007 Evidence-engine fixture contract

## Completion gate

D001-D006 are complete only when `python scripts/validate_data.py` passes and the generated visible scenario folders contain no ground-truth fields.
