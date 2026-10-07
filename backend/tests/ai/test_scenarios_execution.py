"""Cross-scenario pipeline integration tests across all four synthetic scenarios."""
from __future__ import annotations

from pathlib import Path
import pytest
from app.ai.graph import run_investigation_graph
from app.ai.ground_truth import assert_no_ground_truth
from app.ai.providers import MockAIProvider
from app.ai.state import create_initial_state
from app.ai.validation import extract_valid_evidence_ids
from app.core.config import settings
from app.evidence.engine import EvidenceEngine
from app.evidence.loader import load_scenario


SCENARIO_IDS = [
    "bad-deployment",
    "database-degradation",
    "external-dependency",
    "configuration-regression",
]


@pytest.mark.parametrize("scenario_id", SCENARIO_IDS)
def test_pipeline_executes_successfully_for_scenario(scenario_id: str):
    engine = EvidenceEngine(settings.data_root)
    bundle = engine.investigate(scenario_id)

    scenario_data = load_scenario(Path(settings.data_root), scenario_id)
    incident = scenario_data.incident

    initial_state = create_initial_state(
        incident=incident,
        evidence_bundle=bundle,
        provider="mock",
        model="mock-reasoner",
    )

    # Assert no ground truth in initial state
    assert_no_ground_truth(initial_state)

    provider = MockAIProvider()
    final_state = run_investigation_graph(initial_state, provider=provider)

    # 1. State must contain completed plan
    assert final_state.get("plan") is not None
    assert final_state["plan"]["status"] == "planned"
    assert len(final_state["plan"]["steps"]) >= 2

    # 2. Findings must be present
    findings = final_state.get("findings", [])
    assert len(findings) >= 1

    # 3. All findings must have real evidence IDs
    valid_ids = extract_valid_evidence_ids(bundle.model_dump(mode="json"))
    for f in findings:
        for eid in f.get("supporting_evidence_ids", []):
            assert eid in valid_ids

    # 4. Final state must be completely free of hidden ground truth
    assert_no_ground_truth(final_state)

    # 5. Phase 5.3: correlation node must have executed
    nodes = final_state["metadata"]["nodes_executed"]
    assert "correlation" in nodes, "Phase 5.3 correlation node not executed"
    assert "challenge" in nodes, "Phase 5.3 challenge node not executed"

    # 6. Phase 5.3: correlations must be present
    assert len(final_state.get("correlations", [])) >= 1, "No correlations produced"

    # 7. Phase 5.3: challenge result must be present and valid
    challenge = final_state.get("challenge")
    assert challenge is not None, "No challenge result produced"
    assert challenge["status"] in ("supported", "rejected", "inconclusive")
