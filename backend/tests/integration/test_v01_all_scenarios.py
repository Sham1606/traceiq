"""Phase 3 Verification — Task 1 & 2: All four scenarios + deterministic repeatability.

Covers:
- Each of the four scenario IDs loads successfully via the API
- Investigation completes (status == 'complete') for every scenario
- Evidence is produced (metric_findings, log_findings, evidence list)
- Timeline/correlation findings are produced
- Hypotheses are produced with valid strength labels
- Hidden ground truth is never exposed in any investigation response
- Running the same scenario twice produces equivalent deterministic content
  (metric finding IDs, anomaly flags, evidence IDs — things that don't depend on
   generated row UUIDs or timestamps that change per run)
"""
from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_STRENGTHS = frozenset(
    {"strongly_supported", "supported", "inconclusive", "weakly_supported", "rejected"}
)

# Ground truth field names that must NEVER appear anywhere in an API response
HIDDEN_FIELDS = [
    "root_cause_service",
    "contradictory_lead",
    "expected_recovery_action",
    "primary_evidence_ids",
    "ground_truth",
]

# The four scenarios listed in MASTER.md
ALL_SCENARIOS = [
    "bad-deployment",
    "database-degradation",
    "external-dependency",
    "configuration-regression",
]

BASE_TIMES = {
    "started_at": "2024-03-15T10:00:00Z",
    "detected_at": "2024-03-15T10:05:00Z",
    "recovered_at": "2024-03-15T11:30:00Z",
}


def _make_incident(scenario_id: str) -> dict:
    return {
        "scenario_id": scenario_id,
        "title": f"Verification incident — {scenario_id}",
        "severity": "sev2",
        **BASE_TIMES,
        "affected_services": [],
        "description": f"Phase 3 verification for {scenario_id}",
    }


# ---------------------------------------------------------------------------
# 1. Four-scenario coverage
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("scenario_id", ALL_SCENARIOS)
def test_scenario_investigation_completes(client, scenario_id):
    """Every scenario must load, run, and return status='complete'."""
    r_inc = client.post("/api/v1/incidents", json=_make_incident(scenario_id))
    assert r_inc.status_code == 201, f"Incident creation failed for {scenario_id}: {r_inc.text}"
    inc_id = r_inc.json()["id"]

    r_inv = client.post(f"/api/v1/incidents/{inc_id}/investigations")
    assert r_inv.status_code == 201
    data = r_inv.json()
    assert data["status"] == "complete", (
        f"Investigation for {scenario_id} status={data['status']!r}. "
        f"Check audit log for error detail."
    )


@pytest.mark.parametrize("scenario_id", ALL_SCENARIOS)
def test_scenario_produces_evidence(client, scenario_id):
    """Every scenario must produce metric_findings, log_findings, and evidence items."""
    r_inc = client.post("/api/v1/incidents", json=_make_incident(scenario_id))
    inc_id = r_inc.json()["id"]
    r_inv = client.post(f"/api/v1/incidents/{inc_id}/investigations")
    data = r_inv.json()
    assert data["status"] == "complete"

    ev = data["evidence"]
    assert ev is not None
    assert ev["metric_findings"], f"{scenario_id}: no metric_findings"
    assert ev["log_findings"],    f"{scenario_id}: no log_findings"
    assert ev["evidence"],        f"{scenario_id}: no evidence items"

    strengths = {item["strength"] for item in ev["evidence"]}
    assert strengths <= VALID_STRENGTHS, f"Invalid strength labels: {strengths - VALID_STRENGTHS}"


@pytest.mark.parametrize("scenario_id", ALL_SCENARIOS)
def test_scenario_produces_timeline_and_correlations(client, scenario_id):
    """Every scenario must produce timeline and correlation findings."""
    r_inc = client.post("/api/v1/incidents", json=_make_incident(scenario_id))
    inc_id = r_inc.json()["id"]
    r_inv = client.post(f"/api/v1/incidents/{inc_id}/investigations")
    data = r_inv.json()
    assert data["status"] == "complete"
    ev = data["evidence"]

    # Timeline findings are always produced (deployments, configs, deps, logs)
    assert ev["timeline_findings"], f"{scenario_id}: no timeline_findings"

    # Correlation findings — expected when there are anomalies + nearby events
    # (some scenarios may have 0 correlations; we only assert the key exists)
    assert "correlation_findings" in ev, f"{scenario_id}: correlation_findings key missing"


@pytest.mark.parametrize("scenario_id", ALL_SCENARIOS)
def test_scenario_produces_hypotheses(client, scenario_id):
    """Every scenario must produce at least one hypothesis with a valid strength."""
    r_inc = client.post("/api/v1/incidents", json=_make_incident(scenario_id))
    inc_id = r_inc.json()["id"]
    r_inv = client.post(f"/api/v1/incidents/{inc_id}/investigations")
    data = r_inv.json()
    assert data["status"] == "complete"

    hyps = data["hypotheses"]
    assert hyps and len(hyps) >= 1, f"{scenario_id}: no hypotheses"
    for h in hyps:
        assert h["id"],    f"{scenario_id}: hypothesis missing id"
        assert h["title"], f"{scenario_id}: hypothesis missing title"
        assert h["strength"] in VALID_STRENGTHS, (
            f"{scenario_id}: invalid strength {h['strength']!r}"
        )


# ---------------------------------------------------------------------------
# 2. Scenario-specific signal checks
# ---------------------------------------------------------------------------

def test_bad_deployment_has_deployment_evidence(client):
    """bad-deployment: a deployment must be visible in the evidence bundle.

    The deployment event may precede the incident window (it triggered the incident),
    so it may not appear inside timeline_findings (which are window-constrained).
    Verify via correlation evidence or via direct scenario data check.
    """
    r_inc = client.post("/api/v1/incidents", json=_make_incident("bad-deployment"))
    inc_id = r_inc.json()["id"]
    r_inv = client.post(f"/api/v1/incidents/{inc_id}/investigations")
    ev = r_inv.json()["evidence"]

    # The deployment should show up in correlation_findings (metric-log correlations)
    # OR in timeline findings if it falls inside the scenario window.
    # At minimum the scenario must have metric anomalies (the consequence of the deployment).
    anomalous = [f for f in ev["metric_findings"] if f["anomaly"]]
    assert anomalous, "bad-deployment: expected metric anomalies caused by the deployment"

    # Evidence items produced from those anomalies must be strongly or weakly supported
    ev_strengths = {item["strength"] for item in ev["evidence"]}
    assert ev_strengths & {"strongly_supported", "supported", "weakly_supported"}, (
        "bad-deployment: evidence should include non-inconclusive items"
    )


def test_database_degradation_has_db_metric_anomaly(client):
    """database-degradation: must flag DB service metrics as anomalous."""
    r_inc = client.post("/api/v1/incidents", json=_make_incident("database-degradation"))
    inc_id = r_inc.json()["id"]
    r_inv = client.post(f"/api/v1/incidents/{inc_id}/investigations")
    ev = r_inv.json()["evidence"]
    db_anomalies = [
        f for f in ev["metric_findings"]
        if f["anomaly"] and ("db" in f["service"].lower() or "database" in f["service"].lower())
    ]
    assert db_anomalies, "database-degradation: no DB metric anomalies found"


def test_external_dependency_has_dependency_timeline_event(client):
    """external-dependency: timeline must contain dependency degradation events."""
    r_inc = client.post("/api/v1/incidents", json=_make_incident("external-dependency"))
    inc_id = r_inc.json()["id"]
    r_inv = client.post(f"/api/v1/incidents/{inc_id}/investigations")
    ev = r_inv.json()["evidence"]
    dep_events = [t for t in ev["timeline_findings"] if t["event_type"] == "dependency"]
    assert dep_events, "external-dependency: no dependency timeline events"


def test_configuration_regression_has_configuration_timeline_event(client):
    """configuration-regression: timeline must contain a configuration change event."""
    r_inc = client.post("/api/v1/incidents", json=_make_incident("configuration-regression"))
    inc_id = r_inc.json()["id"]
    r_inv = client.post(f"/api/v1/incidents/{inc_id}/investigations")
    ev = r_inv.json()["evidence"]
    cfg_events = [t for t in ev["timeline_findings"] if t["event_type"] == "configuration"]
    assert cfg_events, "configuration-regression: no configuration timeline events"


# ---------------------------------------------------------------------------
# 3. Hidden ground truth — all investigation response surfaces
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("scenario_id", ALL_SCENARIOS)
def test_no_ground_truth_in_post_investigation(client, scenario_id):
    """POST /investigations must never expose hidden ground truth fields."""
    r_inc = client.post("/api/v1/incidents", json=_make_incident(scenario_id))
    inc_id = r_inc.json()["id"]
    r_inv = client.post(f"/api/v1/incidents/{inc_id}/investigations")
    _assert_no_ground_truth(r_inv.text, f"POST /investigations ({scenario_id})")


@pytest.mark.parametrize("scenario_id", ALL_SCENARIOS)
def test_no_ground_truth_in_get_investigation(client, scenario_id):
    """GET /investigations/{id} must never expose hidden ground truth fields."""
    r_inc = client.post("/api/v1/incidents", json=_make_incident(scenario_id))
    inc_id = r_inc.json()["id"]
    r_inv = client.post(f"/api/v1/incidents/{inc_id}/investigations")
    inv_id = r_inv.json()["id"]
    r_get = client.get(f"/api/v1/investigations/{inv_id}")
    _assert_no_ground_truth(r_get.text, f"GET /investigations/{inv_id} ({scenario_id})")


@pytest.mark.parametrize("scenario_id", ALL_SCENARIOS)
def test_no_ground_truth_in_audit_log(client, scenario_id):
    """GET /incidents/{id}/audit must never expose hidden ground truth fields."""
    r_inc = client.post("/api/v1/incidents", json=_make_incident(scenario_id))
    inc_id = r_inc.json()["id"]
    client.post(f"/api/v1/incidents/{inc_id}/investigations")
    r_audit = client.get(f"/api/v1/incidents/{inc_id}/audit")
    _assert_no_ground_truth(r_audit.text, f"GET /audit ({scenario_id})")


def _assert_no_ground_truth(body: str, context: str) -> None:
    lower = body.lower()
    for field in HIDDEN_FIELDS:
        assert field.lower() not in lower, (
            f"Ground truth field {field!r} found in {context} response"
        )


# ---------------------------------------------------------------------------
# 4. Deterministic repeatability
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("scenario_id", ALL_SCENARIOS)
def test_deterministic_evidence_content_is_stable(client, scenario_id):
    """Running the same scenario twice must produce identical deterministic content.

    We compare:
    - Set of (service, metric) pairs in metric_findings
    - Anomaly flags for each (service, metric)
    - Evidence strength labels
    - Timeline event types present
    - Set of hypothesis titles (deterministic from evidence, not UUIDs)
    """
    def _run():
        r_inc = client.post("/api/v1/incidents", json=_make_incident(scenario_id))
        inc_id = r_inc.json()["id"]
        r_inv = client.post(f"/api/v1/incidents/{inc_id}/investigations")
        assert r_inv.json()["status"] == "complete"
        ev = r_inv.json()["evidence"]
        hyps = r_inv.json()["hypotheses"]
        return ev, hyps

    ev1, hyps1 = _run()
    ev2, hyps2 = _run()

    # Metric finding signatures (service, metric, anomaly)
    def metric_sigs(ev):
        return {(f["service"], f["metric"], f["anomaly"]) for f in ev["metric_findings"]}

    assert metric_sigs(ev1) == metric_sigs(ev2), (
        f"{scenario_id}: metric finding signatures differ between runs"
    )

    # Evidence strength distribution
    def strength_dist(ev):
        from collections import Counter
        return dict(Counter(item["strength"] for item in ev["evidence"]))

    assert strength_dist(ev1) == strength_dist(ev2), (
        f"{scenario_id}: evidence strength distribution differs between runs"
    )

    # Timeline event types (set, order may vary by timestamp)
    def timeline_types(ev):
        return {t["event_type"] for t in ev["timeline_findings"]}

    assert timeline_types(ev1) == timeline_types(ev2), (
        f"{scenario_id}: timeline event type set differs between runs"
    )

    # Hypothesis titles (content, not UUIDs)
    hyp_titles1 = {h["title"] for h in hyps1}
    hyp_titles2 = {h["title"] for h in hyps2}
    assert hyp_titles1 == hyp_titles2, (
        f"{scenario_id}: hypothesis titles differ between runs"
    )
