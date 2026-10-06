from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from traceiq_data.schemas import (
    ConfigurationChange,
    DependencyEvent,
    DeploymentEvent,
    Incident,
    LogEvent,
    MetricPoint,
    Service,
)


class ScenarioData:
    def __init__(self, root: Path, scenario_id: str) -> None:
        self.root = root
        self.scenario_id = scenario_id
        self.incident = Incident.model_validate(self._read("scenario.json"))
        self.services = self._load("services.json", Service)
        self.metrics = self._load("metrics.json", MetricPoint)
        self.logs = self._load("logs.json", LogEvent)
        self.deployments = self._load("deployments.json", DeploymentEvent)
        self.configuration_changes = self._load("configuration_changes.json", ConfigurationChange)
        self.dependencies = self._load("dependencies.json", DependencyEvent)

    def _read(self, name: str) -> Any:
        path = self.root / self.scenario_id / name
        return json.loads(path.read_text(encoding="utf-8"))

    def _load(self, name: str, model):
        return [model.model_validate(item) for item in self._read(name)]


def load_scenario(data_root: Path, scenario_id: str) -> ScenarioData:
    return ScenarioData(data_root, scenario_id)
