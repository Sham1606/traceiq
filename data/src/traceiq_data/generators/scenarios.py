from __future__ import annotations

import random
from dataclasses import dataclass

from traceiq_data.generators.common import (
    SERVICES,
    build_incident,
    generate_metric_series,
    make_config_change,
    make_deployment,
    make_log,
    stable_id,
    transition_effect,
)
from traceiq_data.schemas import DependencyEvent, ScenarioBundle


@dataclass(frozen=True)
class ScenarioSpec:
    scenario_id: str
    title: str
    description: str
    root_cause_category: str
    root_cause_service: str
    contradictory_lead: str
    recovery_action: str


SPECS = {
    "bad-deployment": ScenarioSpec(
        "bad-deployment", "Payment API regression after deployment",
        "Payment requests degrade shortly after a production release, with elevated query pressure as a downstream symptom.",
        "bad_deployment", "payment-service", "database_degradation",
        "Rollback payment-service to the previous stable version.",
    ),
    "database-degradation": ScenarioSpec(
        "database-degradation", "Payment database performance degradation",
        "Payment failures rise as database latency and connection pressure increase; a recent application release is a plausible but incorrect lead.",
        "database_degradation", "payments-db", "bad_deployment",
        "Fail over or restore the affected database capacity, then drain/retry impacted requests safely.",
    ),
    "external-dependency": ScenarioSpec(
        "external-dependency", "Payment provider API degradation",
        "External payment provider latency and timeouts increase, causing retries and application-level degradation.",
        "external_dependency_failure", "payment-provider-api", "bad_deployment",
        "Route payment traffic to the healthy provider path or activate the configured provider failover.",
    ),
    "configuration-regression": ScenarioSpec(
        "configuration-regression", "Payment timeout configuration regression",
        "A timeout configuration change causes premature failures and retries, increasing queue pressure and service latency.",
        "configuration_regression", "payment-service", "external_dependency_failure",
        "Restore the previous timeout configuration and restart affected workers using the approved rollout path.",
    ),
}


def _common_metrics(rng: random.Random, scenario_id: str, spec: ScenarioSpec):
    metrics = []
    # Gateway remains mostly healthy so the incident is not trivially identified at the edge.
    metrics += generate_metric_series(rng, scenario_id, "api-gateway", "request_latency_p95", "ms", 118, 10, lambda m: transition_effect(m, 45), 40, 900)
    metrics += generate_metric_series(rng, scenario_id, "api-gateway", "error_rate", "ratio", 0.004, 0.0012, lambda m: transition_effect(m, 0.035), 0, 1)
    metrics += generate_metric_series(rng, scenario_id, "order-service", "cpu_utilization", "ratio", 0.43, 0.035, lambda m: transition_effect(m, 0.08), 0, 1)
    metrics += generate_metric_series(rng, scenario_id, "order-service", "request_latency_p95", "ms", 145, 14, lambda m: transition_effect(m, 70), 20, 2000)
    return metrics


def _logs(rng: random.Random, scenario_id: str, spec: ScenarioSpec):
    logs = []
    # Background operational logs: realistic noise and recurring healthy traffic.
    for minute in range(0, 166, 7):
        logs.append(make_log(scenario_id, minute, "api-gateway", "INFO", "request_completed", "request completed successfully", rng, {"status_code": 200}))
        logs.append(make_log(scenario_id, minute + 1, "payment-service", "INFO", "payment_request", "payment authorization request processed", rng, {"provider": "primary"}))
    return logs


def _dependencies(rng: random.Random, scenario_id: str, spec: ScenarioSpec):
    deps = []
    for minute in range(0, 166, 2):
        effect = transition_effect(minute, 0.0)
        provider_bad = spec.scenario_id == "external-dependency" and 120 <= minute < 140
        if provider_bad:
            latency = max(80, 155 + rng.gauss(0, 18) + 650)
            error = min(1, max(0, 0.12 + rng.gauss(0, 0.025)))
            timeout = min(1, max(0, 0.08 + rng.gauss(0, 0.02)))
            status = "failed"
        else:
            latency = max(40, 155 + rng.gauss(0, 12) + effect)
            error = min(1, max(0, 0.003 + rng.gauss(0, 0.001)))
            timeout = min(1, max(0, 0.001 + rng.gauss(0, 0.0005)))
            status = "healthy"
        deps.append(DependencyEvent(
            id=stable_id("deptele", scenario_id, "payment-service", minute),
            timestamp=__import__("traceiq_data.generators.common", fromlist=["ts"]).ts(minute),
            service="payment-service", dependency="payment-provider-api",
            latency_ms=round(latency, 2), error_rate=round(error, 5), timeout_rate=round(timeout, 5), status=status,
        ))
    return deps


def generate_bad_deployment(seed: int) -> tuple[ScenarioBundle, dict]:
    rng = random.Random(seed)
    spec = SPECS["bad-deployment"]
    metrics = _common_metrics(rng, spec.scenario_id, spec)
    metrics += generate_metric_series(rng, spec.scenario_id, "payment-service", "request_latency_p95", "ms", 162, 15, lambda m: transition_effect(m, 760), 30, 5000)
    metrics += generate_metric_series(rng, spec.scenario_id, "payment-service", "error_rate", "ratio", 0.005, 0.0015, lambda m: transition_effect(m, 0.17), 0, 1)
    metrics += generate_metric_series(rng, spec.scenario_id, "payments-db", "query_latency_p95", "ms", 34, 4, lambda m: transition_effect(m, 180), 5, 3000)
    metrics += generate_metric_series(rng, spec.scenario_id, "payments-db", "connection_utilization", "ratio", 0.48, 0.025, lambda m: transition_effect(m, 0.31), 0, 1)
    metrics += generate_metric_series(rng, spec.scenario_id, "payment-service", "cpu_utilization", "ratio", 0.46, 0.035, lambda m: transition_effect(m, 0.18), 0, 1)
    deployments = [make_deployment(spec.scenario_id, 118, "payment-service", "v4.18.2", "v4.19.0")]
    logs = _logs(rng, spec.scenario_id, spec)
    for minute in range(120, 141, 2):
        logs.append(make_log(spec.scenario_id, minute, "payment-service", "ERROR", "db_query_slow", "payment query exceeded latency threshold", rng, {"query_class": "authorization_lookup"}))
        logs.append(make_log(spec.scenario_id, minute + 1, "payment-service", "ERROR", "request_failed", "payment request failed after downstream processing delay", rng, {"status_code": 504}))
    logs.append(make_log(spec.scenario_id, 125, "payment-service", "WARN", "release_regression", "new release shows elevated request processing latency", rng, {"version": "v4.19.0"}))
    return _bundle_and_truth(spec, seed, metrics, logs, deployments, [], _dependencies(rng, spec.scenario_id, spec))


def generate_database_degradation(seed: int) -> tuple[ScenarioBundle, dict]:
    rng = random.Random(seed)
    spec = SPECS["database-degradation"]
    metrics = _common_metrics(rng, spec.scenario_id, spec)
    metrics += generate_metric_series(rng, spec.scenario_id, "payment-service", "request_latency_p95", "ms", 160, 14, lambda m: transition_effect(m, 600), 30, 5000)
    metrics += generate_metric_series(rng, spec.scenario_id, "payment-service", "error_rate", "ratio", 0.004, 0.0015, lambda m: transition_effect(m, 0.13), 0, 1)
    metrics += generate_metric_series(rng, spec.scenario_id, "payments-db", "query_latency_p95", "ms", 36, 4, lambda m: transition_effect(m, 920), 5, 5000)
    metrics += generate_metric_series(rng, spec.scenario_id, "payments-db", "connection_utilization", "ratio", 0.49, 0.025, lambda m: transition_effect(m, 0.44), 0, 1)
    metrics += generate_metric_series(rng, spec.scenario_id, "payments-db", "cpu_utilization", "ratio", 0.51, 0.03, lambda m: transition_effect(m, 0.22), 0, 1)
    deployments = [make_deployment(spec.scenario_id, 114, "payment-service", "v4.18.1", "v4.18.2")]
    logs = _logs(rng, spec.scenario_id, spec)
    for minute in range(120, 141, 2):
        logs.append(make_log(spec.scenario_id, minute, "payments-db", "WARN", "query_latency", "query execution time exceeded database performance threshold", rng, {"wait_class": "io"}))
        logs.append(make_log(spec.scenario_id, minute + 1, "payment-service", "ERROR", "db_connection_wait", "waiting for database connection from pool", rng, {"pool": "payments-primary"}))
    return _bundle_and_truth(spec, seed, metrics, logs, deployments, [], _dependencies(rng, spec.scenario_id, spec))


def generate_external_dependency(seed: int) -> tuple[ScenarioBundle, dict]:
    rng = random.Random(seed)
    spec = SPECS["external-dependency"]
    metrics = _common_metrics(rng, spec.scenario_id, spec)
    metrics += generate_metric_series(rng, spec.scenario_id, "payment-service", "request_latency_p95", "ms", 165, 16, lambda m: transition_effect(m, 540), 30, 5000)
    metrics += generate_metric_series(rng, spec.scenario_id, "payment-service", "error_rate", "ratio", 0.005, 0.0015, lambda m: transition_effect(m, 0.11), 0, 1)
    metrics += generate_metric_series(rng, spec.scenario_id, "payment-service", "retry_rate", "ratio", 0.006, 0.002, lambda m: transition_effect(m, 0.31), 0, 1)
    metrics += generate_metric_series(rng, spec.scenario_id, "payment-service", "queue_depth", "count", 42, 5, lambda m: transition_effect(m, 480), 0, 10000)
    metrics += generate_metric_series(rng, spec.scenario_id, "payment-provider-api", "latency_p95", "ms", 155, 12, lambda m: transition_effect(m, 980), 20, 10000)
    metrics += generate_metric_series(rng, spec.scenario_id, "payment-provider-api", "error_rate", "ratio", 0.003, 0.001, lambda m: transition_effect(m, 0.29), 0, 1)
    deployments = [make_deployment(spec.scenario_id, 108, "payment-service", "v4.18.2", "v4.18.3")]
    logs = _logs(rng, spec.scenario_id, spec)
    for minute in range(120, 141, 2):
        logs.append(make_log(spec.scenario_id, minute, "payment-provider-api", "ERROR", "upstream_timeout", "upstream payment provider request timed out", rng, {"provider": "primary"}))
        logs.append(make_log(spec.scenario_id, minute + 1, "payment-service", "WARN", "retry_scheduled", "payment provider request scheduled for retry", rng, {"attempt": rng.randint(2, 4)}))
    return _bundle_and_truth(spec, seed, metrics, logs, deployments, [], _dependencies(rng, spec.scenario_id, spec))


def generate_configuration_regression(seed: int) -> tuple[ScenarioBundle, dict]:
    rng = random.Random(seed)
    spec = SPECS["configuration-regression"]
    metrics = _common_metrics(rng, spec.scenario_id, spec)
    metrics += generate_metric_series(rng, spec.scenario_id, "payment-service", "request_latency_p95", "ms", 158, 15, lambda m: transition_effect(m, 500), 30, 5000)
    metrics += generate_metric_series(rng, spec.scenario_id, "payment-service", "error_rate", "ratio", 0.005, 0.0015, lambda m: transition_effect(m, 0.15), 0, 1)
    metrics += generate_metric_series(rng, spec.scenario_id, "payment-service", "retry_rate", "ratio", 0.007, 0.002, lambda m: transition_effect(m, 0.27), 0, 1)
    metrics += generate_metric_series(rng, spec.scenario_id, "payment-service", "queue_depth", "count", 45, 5, lambda m: transition_effect(m, 390), 0, 10000)
    config = [make_config_change(spec.scenario_id, 120, "payment-service", "provider.timeout_ms", "2500", "800", "application")]
    logs = _logs(rng, spec.scenario_id, spec)
    for minute in range(120, 141, 2):
        logs.append(make_log(spec.scenario_id, minute, "payment-service", "WARN", "request_timeout", "payment provider request exceeded configured timeout", rng, {"timeout_ms": 800}))
        logs.append(make_log(spec.scenario_id, minute + 1, "payment-service", "WARN", "retry_scheduled", "request retry scheduled after timeout", rng, {"attempt": rng.randint(2, 4)}))
    deployments = [make_deployment(spec.scenario_id, 111, "payment-service", "v4.18.2", "v4.18.3")]
    return _bundle_and_truth(spec, seed, metrics, logs, deployments, config, _dependencies(rng, spec.scenario_id, spec))


def _bundle_and_truth(spec, seed, metrics, logs, deployments, config, dependencies):
    incident = build_incident(spec.scenario_id, spec.title, ["api-gateway", "payment-service"], spec.description)
    bundle = ScenarioBundle(
        scenario_id=spec.scenario_id,
        seed=seed,
        incident=incident,
        services=SERVICES,
        metrics=metrics,
        logs=logs,
        deployments=deployments,
        configuration_changes=config,
        dependencies=dependencies,
    )
    candidate_ids = []
    for point in metrics:
        offset = (point.timestamp - incident.started_at).total_seconds() / 60
        if not 0 <= offset <= 20:
            continue
        if spec.scenario_id == "bad-deployment" and point.service == "payment-service" and point.metric == "request_latency_p95":
            candidate_ids.append(point.id)
        elif spec.scenario_id == "database-degradation" and point.service == "payments-db" and point.metric == "query_latency_p95":
            candidate_ids.append(point.id)
        elif spec.scenario_id == "external-dependency" and point.service == "payment-provider-api" and point.metric == "latency_p95":
            candidate_ids.append(point.id)
        elif spec.scenario_id == "configuration-regression" and point.service == "payment-service" and point.metric == "retry_rate":
            candidate_ids.append(point.id)
    truth = {
        "scenario_id": spec.scenario_id,
        "root_cause_category": spec.root_cause_category,
        "root_cause_service": spec.root_cause_service,
        "primary_evidence_ids": candidate_ids[:5],
        "contradictory_lead": spec.contradictory_lead,
        "expected_recovery_action": spec.recovery_action,
        "expected_post_recovery_state": "payment-service error rate and latency return close to baseline within recovery window",
    }
    return bundle, truth


GENERATORS = {
    "bad-deployment": generate_bad_deployment,
    "database-degradation": generate_database_degradation,
    "external-dependency": generate_external_dependency,
    "configuration-regression": generate_configuration_regression,
}
