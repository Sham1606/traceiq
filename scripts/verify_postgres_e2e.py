"""End-to-end verification script for PostgreSQL persistence and full workflow.
Tests all 16 verification steps across all 4 scenarios.
"""
from __future__ import annotations

import json
import httpx

BASE_URL = "http://127.0.0.1:8000"
HIDDEN_GROUND_TRUTH = [
    "root_cause_service",
    "contradictory_lead",
    "expected_recovery_action",
    "primary_evidence_ids",
    "ground_truth",
]


def check_no_ground_truth(data: dict | list | str, label: str):
    dumped = json.dumps(data).lower() if not isinstance(data, str) else data.lower()
    for field in HIDDEN_GROUND_TRUTH:
        assert field not in dumped, f"LEAK DETECTED in {label}: {field} found!"


def test_scenario_workflow(client: httpx.Client, inc_id: str, scenario_id: str):
    print(f"\n--- Testing Scenario: {scenario_id} ({inc_id}) ---")

    # 1 & 2: Incident Directory & Incident Detail
    r = client.get(f"/api/v1/incidents/{inc_id}")
    assert r.status_code == 200, f"Failed getting incident: {r.text}"
    inc = r.json()
    assert inc["scenario_id"] == scenario_id
    check_no_ground_truth(inc, f"incident {inc_id}")
    print(f"  [PASS] Incident loaded: {inc['title']}")

    # 3, 4, 5, 6, 7, 8: Start Investigation (Evidence, Findings, Correlation, Hypotheses, Challenge)
    r = client.post(f"/api/v1/incidents/{inc_id}/investigations")
    assert r.status_code == 201, f"Failed starting investigation: {r.text}"
    inv = r.json()
    inv_id = inv["id"]
    assert inv["status"] == "complete", f"Investigation status was {inv['status']}"
    assert inv.get("evidence"), "Evidence missing in investigation"
    assert inv.get("hypotheses"), "Hypotheses missing in investigation"
    assert inv.get("challenge"), "Challenge missing in investigation"
    check_no_ground_truth(inv, f"investigation {inv_id}")
    print(f"  [PASS] Investigation completed: {inv_id}")
    print(f"         Hypotheses count: {len(inv['hypotheses'])}")
    print(f"         Challenge status: {inv['challenge'].get('status')}")

    # 9: Recommend Recovery Actions
    r = client.post(f"/api/v1/investigations/{inv_id}/recommend-recovery")
    assert r.status_code == 201, f"Failed recommending recovery: {r.text}"
    actions = r.json()
    assert len(actions) > 0, "No recovery actions recommended"
    action = actions[0]
    action_id = action["id"]
    check_no_ground_truth(actions, f"recovery actions {inv_id}")
    print(f"  [PASS] Recovery recommended: {action['action']} (action_id: {action_id})")

    # 10: Blast Radius Evaluation
    r = client.post(f"/api/v1/recovery-actions/{action_id}/blast-radius")
    assert r.status_code == 200, f"Failed blast radius: {r.text}"
    blast = r.json()
    assert "risk_level" in blast or "estimated_recovery_time_seconds" in blast
    print(f"  [PASS] Blast radius evaluated: risk_level={blast.get('risk_level')}")

    # 11: Human Approval Gate
    r = client.post(
        f"/api/v1/recovery-actions/{action_id}/approve",
        json={"approved_by": "lead-sre@company.internal", "approved": True},
    )
    assert r.status_code == 200, f"Failed approval: {r.text}"
    approved = r.json()
    assert approved["approval_status"] == "approved"
    print(f"  [PASS] Human approval granted by {approved['approved_by']}")

    # 12: Duplicate Approval Rejected
    r_dup = client.post(
        f"/api/v1/recovery-actions/{action_id}/approve",
        json={"approved_by": "attacker@fake.internal", "approved": True},
    )
    assert r_dup.status_code == 409, f"Duplicate approval not rejected! Status: {r_dup.status_code}"
    print(f"  [PASS] Duplicate approval correctly rejected with 409 Conflict")

    # 13: Simulation Execution
    r = client.post(f"/api/v1/recovery-actions/{action_id}/execute")
    assert r.status_code == 200, f"Failed simulation execution: {r.text}"
    exec_res = r.json()
    assert exec_res["outcome"] == "SUCCESS" or exec_res["simulated_result"] in ("safe", "partial", "unsafe")
    print(f"  [PASS] Simulation executed: simulated_result={exec_res['simulated_result']}, outcome={exec_res['outcome']}")

    # 14: Postmortem Generation
    r = client.post(
        f"/api/v1/investigations/{inv_id}/postmortem",
        json={"custom_notes": "Postmortem generated during PostgreSQL E2E verification."},
    )
    assert r.status_code == 201, f"Failed postmortem generation: {r.text}"
    postmortem = r.json()
    assert postmortem.get("title")
    check_no_ground_truth(postmortem, f"postmortem {inv_id}")
    print(f"  [PASS] Postmortem generated: {postmortem['title']}")

    # 15: Historical Memory Archival & Retrieval
    r = client.post(f"/api/v1/investigations/{inv_id}/archive-memory")
    assert r.status_code == 201, f"Failed archiving memory: {r.text}"
    mem = r.json()
    mem_fp = mem["fingerprint"]
    print(f"  [PASS] Incident archived to memory: fingerprint='{mem_fp}'")

    # Search memory
    r_search = client.get(f"/api/v1/memory/search?fingerprint={mem_fp[:10]}")
    assert r_search.status_code == 200, f"Failed searching memory: {r_search.text}"
    search_data = r_search.json()
    assert search_data.get("matches") is not None
    print(f"  [PASS] Memory search retrieved matches successfully")

    # 16: Audit Trail
    r = client.get(f"/api/v1/incidents/{inc_id}/audit")
    assert r.status_code == 200, f"Failed retrieving audit trail: {r.text}"
    audit_entries = r.json()
    assert len(audit_entries) >= 3, f"Expected >= 3 audit entries, got {len(audit_entries)}"
    print(f"  [PASS] Audit trail verified: {len(audit_entries)} entries logged")


def main():
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        # Check overall health
        r_health = client.get("/health")
        assert r_health.status_code == 200 and r_health.json()["db"] == "ok"
        print("Backend is HEALTHY and connected to PostgreSQL.")

        # List incidents
        r_list = client.get("/api/v1/incidents")
        assert r_list.status_code == 200
        items = r_list.json()["items"]
        print(f"Found {len(items)} incidents in directory.")

        scenarios_seen = set()
        for item in items:
            test_scenario_workflow(client, item["id"], item["scenario_id"])
            scenarios_seen.add(item["scenario_id"])

        print(f"\nALL {len(scenarios_seen)} SCENARIOS FULLY VERIFIED ON POSTGRESQL!")


if __name__ == "__main__":
    main()
