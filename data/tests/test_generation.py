import json
import sys
from pathlib import Path

DATA_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(DATA_SRC))

from traceiq_data.generators import GENERATORS
from traceiq_data.validation import validate_bundle


SCENARIOS = sorted(GENERATORS)


def test_all_scenarios_generate_valid_bundles():
    for index, scenario_id in enumerate(SCENARIOS, start=1):
        bundle, truth = GENERATORS[scenario_id](4100 + index)
        assert validate_bundle(bundle) == []
        assert truth["scenario_id"] == scenario_id
        assert truth["root_cause_category"]
        assert truth["primary_evidence_ids"]


def test_generation_is_deterministic():
    for scenario_id in SCENARIOS:
        first, first_truth = GENERATORS[scenario_id](12345)
        second, second_truth = GENERATORS[scenario_id](12345)
        assert first.model_dump(mode="json") == second.model_dump(mode="json")
        assert first_truth == second_truth


def test_different_seed_changes_telemetry():
    for scenario_id in SCENARIOS:
        first, _ = GENERATORS[scenario_id](1)
        second, _ = GENERATORS[scenario_id](2)
        assert first.metrics[0].value != second.metrics[0].value


def test_ground_truth_is_not_part_of_visible_bundle():
    for scenario_id in SCENARIOS:
        bundle, _ = GENERATORS[scenario_id](99)
        payload = bundle.model_dump(mode="json")
        assert "ground_truth" not in payload
        assert "root_cause_category" not in payload
