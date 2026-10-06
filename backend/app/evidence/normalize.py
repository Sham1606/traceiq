from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from traceiq_data.schemas import ConfigurationChange, DependencyEvent, DeploymentEvent, LogEvent, MetricPoint


@dataclass(frozen=True)
class NormalizedEvidence:
    metrics: tuple[MetricPoint, ...]
    logs: tuple[LogEvent, ...]
    deployments: tuple[DeploymentEvent, ...]
    configurations: tuple[ConfigurationChange, ...]
    dependencies: tuple[DependencyEvent, ...]


def normalize(
    metrics: Iterable[MetricPoint],
    logs: Iterable[LogEvent],
    deployments: Iterable[DeploymentEvent],
    configurations: Iterable[ConfigurationChange],
    dependencies: Iterable[DependencyEvent],
) -> NormalizedEvidence:
    def ordered(items):
        return tuple(sorted(items, key=lambda x: x.timestamp))

    return NormalizedEvidence(
        metrics=ordered(metrics),
        logs=ordered(logs),
        deployments=ordered(deployments),
        configurations=ordered(configurations),
        dependencies=ordered(dependencies),
    )


def in_window(items, start: datetime, end: datetime):
    return [item for item in items if start <= item.timestamp <= end]
