# TRACEIQ — AGENT RULES

## Priority
1. Correctness
2. Testability
3. Reliability
4. Maintainability
5. Demo quality
6. Visual polish

## Before Coding
Read MASTER.md and the nearest TASKS.md. Inspect existing implementation and tests. Confirm scope.

## Coding
- Keep functions small and typed.
- Validate external input.
- Keep deterministic logic separate from AI.
- No unnecessary abstractions/dependencies.
- No secrets in source/logs.
- Never let an LLM directly execute production actions.

## AI
LLMs reason over normalized evidence; they do not create evidence.
Validate structured output. Handle malformed output, timeout and provider failure.
Never expose hidden ground truth to the model.

## Synthetic Data
Use realistic noise, baselines, timestamps, causal relationships and plausible false leads.
Never write logs that literally announce the root cause.
Keep ground truth in test-only data.

## Testing
Every implementation change needs relevant tests.
Use deterministic fixtures for normal CI; live model calls are not required.
Do not weaken tests just to pass.

## Failure Handling
LLM unavailable → deterministic/fallback result.
Memory unavailable → continue current investigation and show limitation.
Malformed AI output → reject/retry/fallback.
Missing evidence → hypothesis becomes inconclusive.
Database unavailable → clear error, never fabricated data.

## Scope
Do not add unrelated features or infrastructure. If a feature threatens the 3-day window, implement the smallest useful version and document the limitation.

## Completion Report
### Changed
### Implemented
### Tests
### Risks
### Next
