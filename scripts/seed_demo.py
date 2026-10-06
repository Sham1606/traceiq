"""Seed script for TRACEIQ demo database.

Populates traceiq.db with the four generated scenarios and historical memories
so the frontend workspace has real data ready for inspection.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.database import SessionLocal, init_db
from app.models.orm import IncidentMemoryRow, IncidentRow

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "generated"

SCENARIOS = [
    "bad-deployment",
    "database-degradation",
    "external-dependency",
    "configuration-regression",
]

MEMORIES = [
    {
        "id": "mem-hist-01",
        "fingerprint": "bad-deployment deployment regression api-gateway payment-service",
        "title": "Historical Release Regression in Payment API",
        "root_cause_category": "deployment",
        "evidence_summary": [
            "NullPointerException in AuthFilter after deployment v4.1",
            "Error rate spiked to 12.5% within 3 minutes of release",
        ],
        "recovery_action": "Rollback to deployment v4.0",
        "recovery_outcome": "Error rate resolved to 0.01% baseline within 2 minutes",
        "scenario_id": "bad-deployment",
        "incident_id": "inc-hist-01",
    },
    {
        "id": "mem-hist-02",
        "fingerprint": "database-degradation connection pool query latency postgresql",
        "title": "PostgreSQL Connection Pool Exhaustion",
        "root_cause_category": "database",
        "evidence_summary": [
            "DB connection pool utilization reached 100%",
            "Payment query latency exceeded 4500ms",
        ],
        "recovery_action": "Increased connection pool limit and killed hanging transaction",
        "recovery_outcome": "Latency restored to 45ms; queue drained",
        "scenario_id": "database-degradation",
        "incident_id": "inc-hist-02",
    },
    {
        "id": "mem-hist-03",
        "fingerprint": "external-dependency third-party gateway timeout payment",
        "title": "Upstream Payment Processor Degradation",
        "root_cause_category": "external_dependency",
        "evidence_summary": [
            "Downstream timeouts observed on external HTTP egress",
            "Retry storm amplified gateway latency",
        ],
        "recovery_action": "Enabled secondary payment provider fallback circuit breaker",
        "recovery_outcome": "Traffic redirected; checkout error rate decreased to 0.1%",
        "scenario_id": "external-dependency",
        "incident_id": "inc-hist-03",
    },
    {
        "id": "mem-hist-04",
        "fingerprint": "configuration-regression configmap environment timeout threadpool",
        "title": "Misconfigured Thread Pool Timeout Regression",
        "root_cause_category": "configuration",
        "evidence_summary": [
            "Worker thread pool timeout reduced from 30s to 500ms in config update",
            "Spike in thread rejection logs",
        ],
        "recovery_action": "Reverted configmap key WORKER_TIMEOUT_MS to 30000",
        "recovery_outcome": "Thread rejection ceased immediately",
        "scenario_id": "configuration-regression",
        "incident_id": "inc-hist-04",
    },
]


def seed():
    init_db()
    db = SessionLocal()
    try:
        # Seed incidents
        for sc_name in SCENARIOS:
            sc_path = DATA_ROOT / sc_name / "scenario.json"
            if not sc_path.exists():
                print(f"Skipping {sc_name}: {sc_path} not found")
                continue

            data = json.loads(sc_path.read_text(encoding="utf-8"))
            inc_id = data["id"]
            existing = db.get(IncidentRow, inc_id)
            if existing:
                print(f"Incident {inc_id} already exists")
                continue

            inc = IncidentRow(
                id=inc_id,
                scenario_id=data["scenario_id"],
                title=data["title"],
                status=data.get("status", "detected"),
                severity=data.get("severity", "sev2"),
                started_at=datetime.fromisoformat(data["started_at"].replace("Z", "+00:00")),
                detected_at=datetime.fromisoformat(data["detected_at"].replace("Z", "+00:00")),
                recovered_at=datetime.fromisoformat(data["recovered_at"].replace("Z", "+00:00")),
                affected_services=data.get("affected_services", []),
                description=data.get("description", ""),
                created_at=datetime.now(timezone.utc),
            )
            db.add(inc)
            print(f"Added incident {inc_id} ({sc_name})")

        # Seed memories
        for mem in MEMORIES:
            existing_mem = db.get(IncidentMemoryRow, mem["id"])
            if existing_mem:
                continue
            row = IncidentMemoryRow(
                id=mem["id"],
                fingerprint=mem["fingerprint"],
                title=mem["title"],
                root_cause_category=mem["root_cause_category"],
                evidence_summary=mem["evidence_summary"],
                recovery_action=mem["recovery_action"],
                recovery_outcome=mem["recovery_outcome"],
                scenario_id=mem["scenario_id"],
                incident_id=mem["incident_id"],
                created_at=datetime.now(timezone.utc),
            )
            db.add(row)
            print(f"Added memory {mem['id']}")

        db.commit()
        print("Seeding complete.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
