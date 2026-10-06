# Scenario Specification

## Required
- service topology
- normal baseline
- incident window
- recovery window
- logs
- metrics
- deployment/configuration events
- dependency telemetry where applicable
- supporting evidence
- contradicting evidence

## Hidden Ground Truth
Root cause and expected recovery belong in test-only data.

## Quality
Production-plausible noise, consistent timestamps, causal relationships, plausible false leads, no explicit root-cause messages, no impossible values.

## Tests
Verify expected root cause, supporting/contradicting evidence, challenge result and recovery outcome.
