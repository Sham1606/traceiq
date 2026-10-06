from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from traceiq_data.generators import GENERATORS
from traceiq_data.validation import assert_valid

DEFAULT_SEEDS = {
    "bad-deployment": 4101,
    "database-degradation": 4102,
    "external-dependency": 4103,
    "configuration-regression": 4104,
}


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def generate(selected: list[str], output_root: Path) -> None:
    ground_truth_root = output_root / ".test_ground_truth"
    for scenario_id in selected:
        bundle, truth = GENERATORS[scenario_id](DEFAULT_SEEDS[scenario_id])
        assert_valid(bundle)
        scenario_root = output_root / scenario_id
        scenario_root.mkdir(parents=True, exist_ok=True)

        write_json(scenario_root / "scenario.json", bundle.incident.model_dump(mode="json"))
        write_json(scenario_root / "services.json", [x.model_dump(mode="json") for x in bundle.services])
        write_json(scenario_root / "metrics.json", [x.model_dump(mode="json") for x in bundle.metrics])
        write_json(scenario_root / "logs.json", [x.model_dump(mode="json") for x in bundle.logs])
        write_json(scenario_root / "deployments.json", [x.model_dump(mode="json") for x in bundle.deployments])
        write_json(scenario_root / "configuration_changes.json", [x.model_dump(mode="json") for x in bundle.configuration_changes])
        write_json(scenario_root / "dependencies.json", [x.model_dump(mode="json") for x in bundle.dependencies])
        write_json(ground_truth_root / f"{scenario_id}.json", truth)

        print(f"generated {scenario_id}: {len(bundle.metrics)} metrics, {len(bundle.logs)} logs, {len(bundle.dependencies)} dependency events")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate deterministic TRACEIQ synthetic incident data")
    parser.add_argument("--scenario", action="append", choices=sorted(GENERATORS), help="scenario to generate; repeat for multiple")
    parser.add_argument("--output", default=str(ROOT / "generated"), help="output directory")
    args = parser.parse_args()
    selected = args.scenario or sorted(GENERATORS)
    generate(selected, Path(args.output))
