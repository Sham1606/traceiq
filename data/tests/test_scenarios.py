import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from traceiq_data.generators import GENERATORS


def window_values(bundle, service, metric):
    points = [m for m in bundle.metrics if m.service == service and m.metric == metric]
    start = bundle.incident.started_at
    values = {"baseline": [], "incident": [], "recovery": []}
    for point in points:
        offset = (point.timestamp - start).total_seconds() / 60
        if offset < 0:
            values["baseline"].append(point.value)
        elif offset < 20:
            values["incident"].append(point.value)
        else:
            values["recovery"].append(point.value)
    return values


def avg(values):
    return sum(values) / len(values)


def test_bad_deployment_has_deployment_then_application_regression():
    bundle, truth = GENERATORS["bad-deployment"](4101)
    deployment = bundle.deployments[0]
    latency = window_values(bundle, "payment-service", "request_latency_p95")
    assert deployment.timestamp <= bundle.incident.started_at
    assert avg(latency["incident"]) > avg(latency["baseline"]) * 3
    assert truth["root_cause_category"] == "bad_deployment"


def test_database_degradation_has_db_first_order_signal_and_recent_release_as_false_lead():
    bundle, truth = GENERATORS["database-degradation"](4102)
    db = window_values(bundle, "payments-db", "query_latency_p95")
    app = window_values(bundle, "payment-service", "request_latency_p95")
    assert avg(db["incident"]) > avg(db["baseline"]) * 8
    assert avg(app["incident"]) > avg(app["baseline"]) * 3
    assert bundle.deployments[0].timestamp < bundle.incident.started_at
    assert truth["contradictory_lead"] == "bad_deployment"


def test_external_dependency_has_provider_failure_and_retry_cascade():
    bundle, truth = GENERATORS["external-dependency"](4103)
    provider = window_values(bundle, "payment-provider-api", "latency_p95")
    retries = window_values(bundle, "payment-service", "retry_rate")
    assert avg(provider["incident"]) > avg(provider["baseline"]) * 5
    assert avg(retries["incident"]) > avg(retries["baseline"]) * 10
    assert truth["root_cause_category"] == "external_dependency_failure"


def test_configuration_regression_has_change_at_incident_start_and_retry_cascade():
    bundle, truth = GENERATORS["configuration-regression"](4104)
    change = bundle.configuration_changes[0]
    retries = window_values(bundle, "payment-service", "retry_rate")
    assert change.timestamp >= bundle.incident.started_at
    assert change.new_value == "800"
    assert avg(retries["incident"]) > avg(retries["baseline"]) * 10
    assert truth["root_cause_category"] == "configuration_regression"
