"""B003: Investigation service tests — success, failure, hypothesis generation."""
from __future__ import annotations

import json
import pytest

BASE_INCIDENT = {
    "scenario_id": "bad-deployment",
    "title": "Error rate spike",
    "severity": "sev2",
    "started_at": "2024-03-15T10:00:00Z",
    "detected_at": "2024-03-15T10:05:00Z",
    "recovered_at": "2024-03-15T11:30:00Z",
    "affected_services": ["api-gateway"],
    "description": "Test incident for investigation.",
}


@pytest.fixture()
def incident_id(client):
    r = client.post("/api/v1/incidents", json=BASE_INCIDENT)
    assert r.status_code == 201
    return r.json()["id"]


def test_start_investigation_returns_201(client, incident_id):
    r = client.post(f"/api/v1/incidents/{incident_id}/investigations")
    assert r.status_code == 201
    data = r.json()
    assert data["incident_id"] == incident_id
    assert data["id"]
    assert data["status"] in {"complete", "failed"}


def test_start_investigation_complete_has_evidence(client, incident_id):
    r = client.post(f"/api/v1/incidents/{incident_id}/investigations")
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "complete", f"Investigation failed: {data}"
    assert data["evidence"] is not None
    assert "metric_findings" in data["evidence"]
    assert data["evidence"]["metric_findings"]


def test_start_investigation_complete_has_hypotheses(client, incident_id):
    r = client.post(f"/api/v1/incidents/{incident_id}/investigations")
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "complete"
    assert data["hypotheses"] is not None
    assert len(data["hypotheses"]) >= 1
    h = data["hypotheses"][0]
    assert "id" in h
    assert "title" in h
    assert "strength" in h
    assert h["strength"] in {
        "strongly_supported", "supported", "inconclusive", "weakly_supported", "rejected"
    }


def test_investigation_does_not_expose_ground_truth(client, incident_id):
    r = client.post(f"/api/v1/incidents/{incident_id}/investigations")
    assert r.status_code == 201
    text = r.text.lower()
    # Ground truth fields must never appear in investigation responses
    assert "root_cause_service" not in text
    assert "contradictory_lead" not in text
    assert "expected_recovery_action" not in text
    assert "primary_evidence_ids" not in text


def test_start_investigation_nonexistent_incident_returns_404(client):
    r = client.post("/api/v1/incidents/does-not-exist/investigations")
    assert r.status_code == 404


def test_get_investigation(client, incident_id):
    r1 = client.post(f"/api/v1/incidents/{incident_id}/investigations")
    inv_id = r1.json()["id"]
    r2 = client.get(f"/api/v1/investigations/{inv_id}")
    assert r2.status_code == 200
    assert r2.json()["id"] == inv_id


def test_list_investigations_for_incident(client, incident_id):
    client.post(f"/api/v1/incidents/{incident_id}/investigations")
    client.post(f"/api/v1/incidents/{incident_id}/investigations")
    r = client.get(f"/api/v1/incidents/{incident_id}/investigations")
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 2


def test_investigation_with_bad_scenario_records_failure(client):
    """When scenario data is missing, investigation status must be 'failed', not a 500."""
    bad_incident = {
        **BASE_INCIDENT,
        "scenario_id": "nonexistent-scenario",
        "title": "Bad scenario",
    }
    r = client.post("/api/v1/incidents", json=bad_incident)
    incident_id = r.json()["id"]

    r2 = client.post(f"/api/v1/incidents/{incident_id}/investigations")
    assert r2.status_code == 201
    assert r2.json()["status"] == "failed"


def test_investigation_for_database_degradation_scenario(client):
    """Database degradation scenario should find DB metric anomalies."""
    payload = {
        **BASE_INCIDENT,
        "scenario_id": "database-degradation",
        "title": "DB degradation test",
    }
    r = client.post("/api/v1/incidents", json=payload)
    inc_id = r.json()["id"]

    r2 = client.post(f"/api/v1/incidents/{inc_id}/investigations")
    assert r2.status_code == 201
    data = r2.json()
    assert data["status"] == "complete"
    # At least one hypothesis should mention database
    hyps = data["hypotheses"]
    titles = [h["title"].lower() for h in hyps]
    assert any("database" in t or "db" in t for t in titles)


@pytest.mark.parametrize(
    ("successful_calls", "expected_mode"),
    [(0, "fallback"), (1, "live")],
)
def test_gemini_telemetry_requires_successful_provider_response(
    client, incident_id, monkeypatch, successful_calls, expected_mode
):
    import app.ai.config as ai_config
    import app.ai.graph as ai_graph
    import app.ai.providers as ai_providers

    class ProviderStub:
        provider_name = "gemini"
        model_name = "gemini-test-model"

        def __init__(self, call_count):
            self.successful_calls = call_count
            self.runtime_metadata = {
                "request_started_at": "2026-10-09T12:00:00+00:00",
                "request_completed_at": "2026-10-09T12:00:01.840000+00:00",
                "latency_ms": 1840,
                "last_request_latency_ms": 1840,
                "status": "success" if call_count else "unavailable",
                "structured_output_valid": bool(call_count),
                "evidence_ids_referenced": 1,
            }

    monkeypatch.setattr(ai_config.ai_settings, "enabled", True)
    monkeypatch.setattr(ai_providers, "get_ai_provider", lambda _settings: ProviderStub(successful_calls))
    monkeypatch.setattr(
        ai_graph,
        "run_investigation_graph",
        lambda state, provider: {
            **state,
            "metadata": {"deterministic_fallback": False},
            "hypotheses": [],
            "findings": [{"evidence_ids": [state["evidence"]["evidence"][0]["id"]]}],
            "correlations": [],
            "challenge": None,
        },
    )

    response = client.post(f"/api/v1/incidents/{incident_id}/investigations")

    assert response.status_code == 201
    telemetry = response.json()["evidence"]["ai_telemetry"]
    assert telemetry["mode"] == expected_mode
    assert telemetry["provider"] == "gemini"
    assert telemetry["model"] == "gemini-test-model"
    assert telemetry["status"] == ("success" if expected_mode == "live" else "fallback")
    assert telemetry["structured_output_valid"] is (expected_mode == "live")
    assert telemetry["evidence_ids_referenced"] == 1
    assert telemetry["fallback_used"] is (expected_mode == "fallback")
    assert telemetry["latency_ms"] == 1840


def test_mock_investigation_telemetry_never_reports_live(client, incident_id, monkeypatch):
    import app.ai.config as ai_config
    import app.ai.graph as ai_graph
    import app.ai.providers as ai_providers
    from app.ai.providers import MockAIProvider

    monkeypatch.setattr(ai_config.ai_settings, "enabled", True)
    monkeypatch.setattr(ai_providers, "get_ai_provider", lambda _settings: MockAIProvider())
    monkeypatch.setattr(
        ai_graph,
        "run_investigation_graph",
        lambda state, provider: {
            **state,
            "metadata": {"deterministic_fallback": False},
            "hypotheses": [],
            "findings": [],
            "correlations": [],
            "challenge": None,
            "errors": [{"node_name": "investigator", "recovered": True}],
        },
    )

    response = client.post(f"/api/v1/incidents/{incident_id}/investigations")

    assert response.status_code == 201
    telemetry = response.json()["evidence"]["ai_telemetry"]
    assert telemetry["mode"] == "mock"
    assert telemetry["provider"] == "mock"
    assert telemetry["fallback_used"] is True


def test_partial_gemini_graph_failure_is_reported_as_fallback(client, incident_id, monkeypatch):
    import app.ai.config as ai_config
    import app.ai.graph as ai_graph
    import app.ai.providers as ai_providers

    class ProviderStub:
        provider_name = "gemini"
        model_name = "gemini-test-model"
        successful_calls = 2
        runtime_metadata = {
            "request_count": 3,
            "attempt_count": 1,
            "latency_ms": 1200,
            "structured_output_valid": True,
            "evidence_ids_referenced": 1,
        }

    def graph_with_one_failed_stage(state, provider):
        evidence_id = state["evidence"]["evidence"][0]["id"]
        return {
            **state,
            "metadata": {"deterministic_fallback": False},
            "findings": [{"evidence_ids": [evidence_id]}],
            "correlations": [],
            "hypotheses": [{
                "id": "hyp-gemini-01",
                "title": "Evidence-supported candidate",
                "explanation": "A test-only grounded summary.",
                "evidence_ids": [evidence_id],
                "supporting_evidence_ids": [evidence_id],
                "contradicting_evidence_ids": [],
                "strength": "supported",
            }],
            "challenge": None,
            "errors": [{
                "node_name": "investigate_database",
                "exception_class": "AIProviderError",
                "failure_category": "rate_limit",
                "explanation": "Provider rate limit was reached.",
                "retryable": True,
                "attempt_count": 2,
                "recovered": True,
            }],
        }

    monkeypatch.setattr(ai_config.ai_settings, "enabled", True)
    monkeypatch.setattr(ai_providers, "get_ai_provider", lambda _settings: ProviderStub())
    monkeypatch.setattr(ai_graph, "run_investigation_graph", graph_with_one_failed_stage)

    response = client.post(f"/api/v1/incidents/{incident_id}/investigations")

    assert response.status_code == 201
    body = response.json()
    telemetry = body["evidence"]["ai_telemetry"]
    assert body["status"] == "complete"
    assert body["hypotheses"][0]["supporting_evidence_ids"]
    assert telemetry["mode"] == "fallback"
    assert telemetry["fallback_used"] is True
    assert telemetry["structured_output_valid"] is False
    assert telemetry["failure_details"][0]["node_name"] == "investigate_database"
    assert telemetry["failure_details"][0]["attempt_count"] == 2
    assert "message" not in telemetry["failure_details"][0]


def test_swallowed_gemini_stage_failure_cannot_report_live(client, incident_id, monkeypatch):
    import app.ai.config as ai_config
    import app.ai.graph as ai_graph
    import app.ai.providers as ai_providers

    class ProviderStub:
        provider_name = "gemini"
        model_name = "gemini-test-model"
        successful_calls = 1
        failed_calls = 1
        runtime_metadata = {
            "request_count": 2,
            "successful_calls": 1,
            "failed_calls": 1,
            "retry_count": 0,
        }

    def graph_with_locally_recovered_challenge_failure(state, provider):
        evidence_id = state["evidence"]["evidence"][0]["id"]
        return {
            **state,
            "metadata": {"deterministic_fallback": False},
            "findings": [],
            "correlations": [],
            "hypotheses": [{
                "id": "hyp-gemini-01",
                "title": "Evidence-supported candidate",
                "explanation": "A test-only grounded summary.",
                "evidence_ids": [evidence_id],
                "supporting_evidence_ids": [evidence_id],
                "contradicting_evidence_ids": [],
                "strength": "supported",
            }],
            "challenge": {
                "hypothesis_id": "hyp-gemini-01",
                "status": "supported",
                "challenge_rationale": "Deterministic challenge fallback used.",
                "contradicting_evidence_ids": [],
                "independent_evidence_ids": [evidence_id],
                "challenger_agent": "ChallengeAgent",
            },
            "errors": [],
        }

    monkeypatch.setattr(ai_config.ai_settings, "enabled", True)
    monkeypatch.setattr(ai_providers, "get_ai_provider", lambda _settings: ProviderStub())
    monkeypatch.setattr(ai_graph, "run_investigation_graph", graph_with_locally_recovered_challenge_failure)

    response = client.post(f"/api/v1/incidents/{incident_id}/investigations")

    assert response.status_code == 201
    telemetry = response.json()["evidence"]["ai_telemetry"]
    assert telemetry["mode"] == "fallback"
    assert telemetry["provider"] == "gemini"
    assert telemetry["fallback_used"] is True


def test_gemini_credential_echo_is_not_exposed_or_persisted(client, incident_id, db, monkeypatch):
    import app.ai.config as ai_config
    import app.ai.providers.gemini as gemini_module
    from app.models.orm import AuditEntryRow, InvestigationRow

    api_key = "test-only-gemini-key-not-a-credential"

    class StubResponse:
        status_code = 500
        text = f"upstream diagnostic echoed {api_key}"

    class StubClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, *, json, headers):
            assert "?" not in url
            assert api_key not in url
            assert headers["x-goog-api-key"] == api_key
            return StubResponse()

    monkeypatch.setattr(ai_config.ai_settings, "enabled", True)
    monkeypatch.setattr(ai_config.ai_settings, "provider", "gemini")
    monkeypatch.setattr(ai_config.ai_settings, "gemini_api_key", api_key)
    monkeypatch.setattr(ai_config.ai_settings, "model", "test-gemini-model")
    monkeypatch.setattr(gemini_module.httpx, "Client", StubClient)

    response = client.post(f"/api/v1/incidents/{incident_id}/investigations")

    assert response.status_code == 201
    assert response.json()["status"] == "complete"
    assert response.json()["evidence"]["ai_telemetry"]["mode"] == "fallback"
    assert api_key not in response.text

    audit_response = client.get(f"/api/v1/incidents/{incident_id}/audit")
    assert audit_response.status_code == 200
    assert api_key not in audit_response.text

    investigation = db.query(InvestigationRow).filter_by(incident_id=incident_id).one()
    audit_entries = db.query(AuditEntryRow).filter_by(incident_id=incident_id).all()
    persisted = {
        "evidence": investigation.evidence,
        "hypotheses": investigation.hypotheses,
        "challenge": investigation.challenge,
        "audit": [entry.detail for entry in audit_entries],
    }
    assert api_key not in json.dumps(persisted)
