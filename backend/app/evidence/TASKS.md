# Evidence Engine Tasks

## E001 Normalize inputs — DONE
Normalize and chronologically order all telemetry sources. No ground-truth access.

## E002 Metric analysis — DONE
Compare pre-incident baseline against incident window; calculate mean, delta, ratio and anomaly status.

## E003 Timeline analysis — DONE
Correlate deployments, configuration changes, dependency degradation/failure and warning/error logs by timestamp.

## E004 Log analysis — DONE
Aggregate incident-window log event types and WARN/ERROR frequency.

## E005 Cross-source correlation — DONE
Correlate anomalous metrics with related logs and time-near operational events.

## E006 Evidence strength — DONE
Produce explainable deterministic evidence labels without arbitrary confidence percentages.

## Tests — DONE
Unit/integration-style evidence tests cover all four scenarios and verify the engine runs without ground truth.

## Next
Backend API layer exposing the deterministic evidence engine.
