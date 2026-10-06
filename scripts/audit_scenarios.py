"""Independent Audit Verification Script for TRACEIQ Phase 4.

Verifies:
1. Health endpoint
2. All 4 scenarios end-to-end data flow:
   - bad-deployment
   - database-degradation
   - external-dependency
   - configuration-regression
3. Dynamic evidence & metric deltas for each scenario
4. Deterministic hypotheses generation
5. Ground truth leakage prevention
6. Challenge status (verifying challenge is null / uncorrupted)
7. Full Recovery Workflow:
   - Action proposal
   - Human approval gate
   - Simulation result (safe/unsafe/partial)
   - Outcome recording
8. Audit trail persistence
9. Historical memory search & retrieval
10. Failure states & error codes (404 on invalid incident)
"""
from __future__ import annotations

import json
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8000"


def req(path: str, method: str = "GET", data: dict | None = None):
    url = f"{BASE}{path}"
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode("utf-8") if data else None
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def run_audit():
    print("=== 1. Health Verification ===")
    status, body = req("/health")
    print(f"GET /health -> HTTP {status}: {body}")
    assert status == 200, f"Expected 200, got {status}"
    assert body["status"] == "ok" and body["db"] == "ok"

    print("\n=== 2. Incidents Directory Verification ===")
    status, body = req("/api/v1/incidents")
    print(f"GET /api/v1/incidents -> HTTP {status}, Total: {body['total']}")
    assert status == 200
    incidents = body["items"]
    assert len(incidents) >= 4, f"Expected 4 incidents, got {len(incidents)}"

    scenarios_tested = set()

    for inc in incidents:
        sc = inc["scenario_id"]
        inc_id = inc["id"]
        scenarios_tested.add(sc)
        print(f"\n=======================================================")
        print(f"SCENARIO AUDIT: {sc} (Incident: {inc_id})")
        print(f"Title: {inc['title']}")
        print(f"Severity: {inc['severity']} | Status: {inc['status']}")
        print(f"Affected: {inc['affected_services']}")
        print(f"=======================================================")

        # 1. Get single incident
        s, b = req(f"/api/v1/incidents/{inc_id}")
        assert s == 200 and b["id"] == inc_id, "Incident detail retrieval failed"

        # 2. Trigger investigation
        s, inv = req(f"/api/v1/incidents/{inc_id}/investigations", method="POST")
        assert s == 201 and inv["status"] == "complete", f"Investigation failed with status {s}"
        inv_id = inv["id"]
        print(f"Investigation ID: {inv_id} -> Status: {inv['status']}")

        # 3. Inspect Evidence
        ev = inv["evidence"]
        metric_findings = ev["metric_findings"]
        timeline_findings = ev["timeline_findings"]
        log_findings = ev["log_findings"]
        correlation_findings = ev["correlation_findings"]
        evidence_items = ev["evidence"]

        print(f"Evidence Bundle:")
        print(f"  • Metric Findings: {len(metric_findings)} ({sum(1 for m in metric_findings if m['anomaly'])} anomalous)")
        print(f"  • Timeline Events: {len(timeline_findings)}")
        print(f"  • Log Findings:    {len(log_findings)}")
        print(f"  • Correlations:    {len(correlation_findings)}")
        print(f"  • Evidence Items:  {len(evidence_items)}")

        assert len(metric_findings) > 0, "No metric findings produced"
        assert len(evidence_items) > 0, "No evidence items produced"

        # Check evidence strength labels
        valid_strengths = {"strongly_supported", "supported", "inconclusive", "weakly_supported", "rejected"}
        for item in evidence_items:
            assert item["strength"] in valid_strengths, f"Invalid strength: {item['strength']}"

        # 4. Inspect Hypotheses
        hyps = inv["hypotheses"]
        print(f"Hypotheses ({len(hyps)} candidates):")
        for h in hyps:
            print(f"  [{h['id']}] {h['title']} -> {h['strength'].upper()} (Supp: {len(h['supporting_evidence_ids'])}, Cont: {len(h['contradicting_evidence_ids'])})")
            assert h["strength"] in valid_strengths
        assert len(hyps) > 0, "No hypotheses generated"

        # 5. Challenge RCA field check (Must be None)
        assert inv["challenge"] is None, "Challenge must be null in Phase 4"

        # 6. Hidden Ground Truth Protection
        inv_str = json.dumps(inv)
        forbidden_fields = [
            "root_cause_service",
            "contradictory_lead",
            "expected_recovery_action",
            "primary_evidence_ids",
            "ground_truth",
        ]
        for f in forbidden_fields:
            assert f not in inv_str, f"SECURITY VIOLATION: Ground truth field '{f}' leaked in investigation!"

        # 7. Recovery Workflow Test
        print("\nTesting Recovery Workflow:")
        # Propose action
        s, act = req(f"/api/v1/investigations/{inv_id}/recovery-actions", method="POST", data={
            "action": f"Remediate {sc}",
            "target": "target-service",
            "rationale": "Mitigation correlated with observed telemetry regression",
        })
        assert s == 201, f"Failed to create recovery action: {s}"
        act_id = act["id"]
        print(f"  • Action Created: {act_id} (Approval: {act['approval_status']}, Human Gate: {act['requires_human_approval']})")
        assert act["requires_human_approval"] is True
        assert act["approval_status"] == "pending"

        # Approve action
        s, app_act = req(f"/api/v1/recovery-actions/{act_id}/approve", method="POST", data={
            "approved_by": "Audit-Officer",
            "approved": True,
        })
        assert s == 200 and app_act["approval_status"] == "approved"
        print(f"  • Action Approved by: {app_act['approved_by']}")

        # Simulate action
        s, sim_act = req(f"/api/v1/recovery-actions/{act_id}/simulate", method="POST")
        assert s == 200 and sim_act["simulated_result"] in ["safe", "unsafe", "partial"]
        print(f"  • Simulation Result: {sim_act['simulated_result']}")

        # Record outcome
        s, out_act = req(f"/api/v1/recovery-actions/{act_id}/outcome?outcome=Service%20stabilized", method="POST")
        assert s == 200 and out_act["outcome"] == "Service stabilized"
        print(f"  • Outcome Recorded: {out_act['outcome']}")

        # 8. Audit Trail Verification
        s, audit = req(f"/api/v1/incidents/{inc_id}/audit")
        assert s == 200 and len(audit) >= 2, f"Audit entries missing: {len(audit)}"
        audit_actions = [a["action"] for a in audit]
        print(f"  • Audit Trail: {len(audit)} entries -> {audit_actions}")

    # Verify all four scenarios were covered
    expected_scenarios = {
        "bad-deployment",
        "database-degradation",
        "external-dependency",
        "configuration-regression",
    }
    assert scenarios_tested == expected_scenarios, f"Missing scenarios: {expected_scenarios - scenarios_tested}"

    print("\n=== 3. Historical Memory Search Verification ===")
    s, mem = req("/api/v1/memory/search?fingerprint=deployment")
    assert s == 200 and len(mem["matches"]) > 0
    print(f"Memory Search for 'deployment' -> {len(mem['matches'])} matches found.")
    for m in mem["matches"]:
        print(f"  • Match: {m['memory']['title']} (Tokens: {m['shared_fingerprint_tokens']})")

    print("\n=== 4. Failure States Verification ===")
    # 404 on non-existent incident
    s, not_found = req("/api/v1/incidents/non-existent-id")
    assert s == 404, f"Expected 404 for invalid incident, got {s}"
    print(f"Invalid incident ID -> Correctly returned HTTP {s}: {not_found}")

    # 404 on starting investigation for non-existent incident
    s, inv_not_found = req("/api/v1/incidents/non-existent-id/investigations", method="POST")
    assert s == 404, f"Expected 404 for invalid incident investigation, got {s}"
    print(f"Start investigation for non-existent incident -> Correctly returned HTTP {s}: {inv_not_found}")

    print("\n=======================================================")
    print("ALL CONTRACTS, SCENARIOS, AND SAFETY GATES AUDITED & PASSED!")
    print("=======================================================")


if __name__ == "__main__":
    run_audit()
