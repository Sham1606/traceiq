from __future__ import annotations

from collections import Counter
from datetime import datetime

from traceiq_data.schemas import ScenarioBundle


class ValidationError(Exception):
    pass


def validate_bundle(bundle: ScenarioBundle) -> list[str]:
    errors: list[str] = []
    all_ids = []
    all_timestamps = []

    for collection_name in ("metrics", "logs", "deployments", "configuration_changes", "dependencies"):
        collection = getattr(bundle, collection_name)
        all_ids.extend(item.id for item in collection)
        all_timestamps.extend(item.timestamp for item in collection)

    duplicates = [item_id for item_id, count in Counter(all_ids).items() if count > 1]
    if duplicates:
        errors.append(f"duplicate telemetry ids: {duplicates[:5]}")

    if any(ts.tzinfo is None for ts in all_timestamps):
        errors.append("all telemetry timestamps must be timezone-aware")

    start = bundle.incident.started_at
    detected = bundle.incident.detected_at
    recovered = bundle.incident.recovered_at
    if not start < detected < recovered:
        errors.append("incident timestamps must satisfy started_at < detected_at < recovered_at")

    if bundle.incident.affected_services and "payment-service" not in bundle.incident.affected_services:
        errors.append("payment-service must be affected in the payment incident scenarios")

    metric_ranges = {
        "ratio": (0, 1),
        "ms": (0, 60_000),
        "count": (0, 10_000_000),
    }
    for point in bundle.metrics:
        if point.unit in metric_ranges:
            low, high = metric_ranges[point.unit]
            if not low <= point.value <= high:
                errors.append(f"metric {point.id} outside plausible range: {point.value} {point.unit}")

    for dep in bundle.dependencies:
        if dep.latency_ms < 0:
            errors.append(f"negative dependency latency: {dep.id}")

    metric_services = {m.service for m in bundle.metrics}
    required = {"api-gateway", "payment-service"}
    if bundle.scenario_id == "database-degradation":
        required.add("payments-db")
    missing = required - metric_services
    if missing:
        errors.append(f"missing required metric services: {sorted(missing)}")

    # Ensure incident telemetry exists around the incident window.
    incident_points = [m for m in bundle.metrics if 0 <= (m.timestamp - start).total_seconds() / 60 <= 40]
    if len(incident_points) < 10:
        errors.append("insufficient telemetry during incident window")

    return errors


def assert_valid(bundle: ScenarioBundle) -> None:
    errors = validate_bundle(bundle)
    if errors:
        raise ValidationError("; ".join(errors))
