from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone
from hashlib import sha256

from traceiq_data.schemas import (
    ConfigurationChange,
    DependencyEvent,
    DeploymentEvent,
    Incident,
    LogEvent,
    MetricPoint,
    Service,
)

BASE_TIME = datetime(2026, 10, 7, 9, 0, tzinfo=timezone.utc)

SERVICES = [
    Service(id="api-gateway", name="API Gateway", tier="edge", criticality="critical", dependencies=["order-service", "payment-service"]),
    Service(id="order-service", name="Order Service", tier="application", criticality="critical", dependencies=["orders-db", "redis-cache"]),
    Service(id="payment-service", name="Payment Service", tier="application", criticality="critical", dependencies=["payments-db", "payment-provider-api"]),
    Service(id="orders-db", name="Orders PostgreSQL", tier="data", criticality="critical", dependencies=[]),
    Service(id="payments-db", name="Payments PostgreSQL", tier="data", criticality="critical", dependencies=[]),
    Service(id="redis-cache", name="Redis Cache", tier="data", criticality="high", dependencies=[]),
    Service(id="payment-provider-api", name="Payment Provider API", tier="dependency", criticality="critical", dependencies=[]),
]


def stable_id(prefix: str, *parts: object) -> str:
    raw = "|".join(map(str, parts)).encode()
    return f"{prefix}-{sha256(raw).hexdigest()[:12]}"


def ts(offset_minutes: int, second: int = 0) -> datetime:
    return BASE_TIME + timedelta(minutes=offset_minutes, seconds=second)


def normal_noise(rng: random.Random, sigma: float = 1.0) -> float:
    return rng.gauss(0, sigma)


def bounded(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def incident_windows():
    # 120m baseline, 20m degradation/incident, 25m recovery.
    return {"baseline": (0, 120), "incident": (120, 140), "recovery": (140, 165)}


def build_incident(scenario_id: str, title: str, affected: list[str], description: str) -> Incident:
    return Incident(
        id=stable_id("inc", scenario_id),
        scenario_id=scenario_id,
        title=title,
        status="recovered",
        severity="sev2",
        started_at=ts(120),
        detected_at=ts(124),
        recovered_at=ts(165),
        affected_services=affected,
        description=description,
    )


def generate_metric_series(
    rng: random.Random,
    scenario_id: str,
    service: str,
    metric: str,
    unit: str,
    baseline: float,
    sigma: float,
    effect_fn,
    low: float,
    high: float,
) -> list[MetricPoint]:
    points: list[MetricPoint] = []
    for minute in range(166):
        value = baseline + normal_noise(rng, sigma) + effect_fn(minute)
        value = bounded(value, low, high)
        points.append(
            MetricPoint(
                id=stable_id("met", scenario_id, service, metric, minute),
                timestamp=ts(minute),
                service=service,
                metric=metric,
                value=round(value, 3),
                unit=unit,
            )
        )
    return points


def transition_effect(minute: int, peak: float, recovery_ratio: float = 0.25) -> float:
    if minute < 115:
        return 0.0
    if 115 <= minute < 120:
        return peak * ((minute - 115) / 5)
    if 120 <= minute < 140:
        return peak
    if 140 <= minute < 165:
        progress = (minute - 140) / 25
        return peak * max(0.0, 1 - progress) * (1 - recovery_ratio)
    return 0.0


def make_deployment(scenario_id: str, minute: int, service: str, old: str, new: str, status: str = "success") -> DeploymentEvent:
    return DeploymentEvent(
        id=stable_id("dep", scenario_id, service, minute),
        timestamp=ts(minute, 17),
        service=service,
        version_from=old,
        version_to=new,
        environment="production",
        status=status,
        actor="release-bot",
    )


def make_config_change(scenario_id: str, minute: int, service: str, key: str, old: str, new: str, change_type: str) -> ConfigurationChange:
    return ConfigurationChange(
        id=stable_id("cfg", scenario_id, service, key, minute),
        timestamp=ts(minute, 22),
        service=service,
        key=key,
        previous_value=old,
        new_value=new,
        environment="production",
        change_type=change_type,
    )


def make_log(scenario_id: str, minute: int, service: str, level: str, event_type: str, message: str, rng: random.Random, metadata=None) -> LogEvent:
    return LogEvent(
        id=stable_id("log", scenario_id, service, minute, event_type, message),
        timestamp=ts(minute, rng.randint(0, 59)),
        service=service,
        level=level,
        event_type=event_type,
        message=message,
        trace_id=stable_id("trace", scenario_id, minute, service),
        metadata=metadata or {},
    )
