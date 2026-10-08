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


DEMO_INCIDENTS = [
    {
        "id": "inc-live-order-latency",
        "scenario_id": "LIVE_CUSTOM",
        "title": "Order Processing Latency & Database Degradation",
        "severity": "sev1",
        "status": "investigating",
        "started_at": "2026-10-08T10:45:00+00:00",
        "detected_at": "2026-10-08T10:48:00+00:00",
        "recovered_at": "2026-10-08T11:30:00+00:00",
        "affected_services": ["order-service", "api-gateway", "orders-db"],
        "description": "Order processing latency spikes 380% following orders-db connection saturation and CPU pressure.",
        "custom_evidence": [
            {
                "id": "E-001",
                "type": "metric",
                "service": "orders-db",
                "metric": "cpu_utilization",
                "baseline": 42.0,
                "incident": 91.0,
                "value": 91.0,
                "delta": 49.0,
                "anomaly": True,
                "summary": "orders-db CPU utilization increased from 42% baseline to 91% incident peak.",
            },
            {
                "id": "E-002",
                "type": "metric",
                "service": "orders-db",
                "metric": "connection_pool_utilization",
                "baseline": 35.0,
                "incident": 97.0,
                "value": 97.0,
                "delta": 62.0,
                "anomaly": True,
                "summary": "orders-db connection pool utilization reached critical 97% capacity.",
            },
            {
                "id": "E-003",
                "type": "metric",
                "service": "order-service",
                "metric": "p99_latency_ms",
                "baseline": 45.0,
                "incident": 216.0,
                "value": 216.0,
                "delta": 171.0,
                "anomaly": True,
                "summary": "order-service p99 latency escalated by 380% due to database connection queuing.",
            },
            {
                "id": "E-004",
                "type": "metric",
                "service": "api-gateway",
                "metric": "http_5xx_rate",
                "baseline": 0.05,
                "incident": 0.17,
                "value": 0.17,
                "delta": 0.12,
                "anomaly": True,
                "summary": "api-gateway error rate increased by 240% during order submission downstream timeouts.",
            },
            {
                "id": "E-005",
                "type": "deployment",
                "service": "order-service",
                "event_id": "dep-none",
                "summary": "No recent deployment detected in 24-hour observation window.",
            },
            {
                "id": "E-006",
                "type": "dependency",
                "service": "payment-gateway",
                "summary": "External payment gateway dependency health remains normal (latency 22ms, error rate 0.0%).",
            },
        ],
    },
    {
        "id": "inc-auth-token-failure",
        "scenario_id": "demo-auth-failure",
        "title": "Authentication Service JWT Verification Storm",
        "severity": "sev1",
        "status": "open",
        "started_at": "2026-10-08T09:15:00+00:00",
        "detected_at": "2026-10-08T09:18:00+00:00",
        "recovered_at": "2026-10-08T10:00:00+00:00",
        "affected_services": ["auth-service", "api-gateway", "redis-cache"],
        "description": "Public key rotation synchronization lag caused widespread 401 verification rejections across ingress.",
        "custom_evidence": [
            {
                "id": "E-010",
                "type": "log",
                "service": "auth-service",
                "event_type": "InvalidSignatureException",
                "count": 4820,
                "error_or_warn_count": 4820,
                "summary": "4,820 JWT signature verification rejections logged within 3 minutes of JWKS rotation.",
            },
            {
                "id": "E-011",
                "type": "metric",
                "service": "api-gateway",
                "metric": "http_401_ratio",
                "baseline": 0.01,
                "incident": 0.44,
                "value": 0.44,
                "delta": 0.43,
                "anomaly": True,
                "summary": "API Gateway 401 Unauthorized responses surged to 44% of total traffic.",
            },
        ],
    },
    {
        "id": "inc-redis-cache-saturation",
        "scenario_id": "demo-redis-saturation",
        "title": "Redis Cluster Memory Eviction Spike",
        "severity": "sev2",
        "status": "resolved",
        "started_at": "2026-10-07T14:30:00+00:00",
        "detected_at": "2026-10-07T14:34:00+00:00",
        "recovered_at": "2026-10-07T15:15:00+00:00",
        "affected_services": ["redis-cache", "product-catalog-service"],
        "description": "Cache memory exceeded maxmemory threshold causing volatile-lru eviction cascades and cache stampede.",
        "custom_evidence": [
            {
                "id": "E-020",
                "type": "metric",
                "service": "redis-cache",
                "metric": "memory_utilization_pct",
                "baseline": 68.0,
                "incident": 99.4,
                "value": 99.4,
                "delta": 31.4,
                "anomaly": True,
                "summary": "Redis cluster memory consumption reached 99.4%, triggering aggressive key eviction.",
            },
        ],
    },
    {
        "id": "inc-notification-backlog",
        "scenario_id": "demo-notification-backlog",
        "title": "Notification Worker Queue Delivery Lag",
        "severity": "sev3",
        "status": "investigating",
        "started_at": "2026-10-08T08:00:00+00:00",
        "detected_at": "2026-10-08T08:15:00+00:00",
        "recovered_at": "2026-10-08T09:00:00+00:00",
        "affected_services": ["notification-service", "worker-pool"],
        "description": "Transactional SMS and email delivery latency degraded due to consumer worker pool starvation.",
        "custom_evidence": [
            {
                "id": "E-030",
                "type": "metric",
                "service": "notification-service",
                "metric": "queue_depth_messages",
                "baseline": 120.0,
                "incident": 48200.0,
                "value": 48200.0,
                "delta": 48080.0,
                "anomaly": True,
                "summary": "Notification queue backlog expanded from 120 to 48,200 pending messages.",
            },
        ],
    },
    {
        "id": "inc-settlement-batch-delay",
        "scenario_id": "demo-batch-delay",
        "title": "Nightly Settlement Batch Processing Delay",
        "severity": "sev3",
        "status": "archived",
        "started_at": "2026-10-06T02:00:00+00:00",
        "detected_at": "2026-10-06T03:30:00+00:00",
        "recovered_at": "2026-10-06T05:45:00+00:00",
        "affected_services": ["settlement-batch-job", "reporting-service", "analytics-db"],
        "description": "Daily reconciliation table lock contention caused 2.5 hour delay in scheduled end-of-day reports.",
        "custom_evidence": [
            {
                "id": "E-040",
                "type": "log",
                "service": "settlement-batch-job",
                "event_type": "LockWaitTimeout",
                "count": 28,
                "error_or_warn_count": 28,
                "summary": "Exclusive lock wait timeout occurred on table 'ledger_transactions_partition_202610'.",
            },
        ],
    },
    {
        "id": "inc-gateway-conn-spike",
        "scenario_id": "demo-gateway-connections",
        "title": "API Gateway Ingress Connection Saturation",
        "severity": "sev2",
        "status": "resolved",
        "started_at": "2026-10-07T18:00:00+00:00",
        "detected_at": "2026-10-07T18:05:00+00:00",
        "recovered_at": "2026-10-07T18:40:00+00:00",
        "affected_services": ["api-gateway", "ingress-controller"],
        "description": "SYN backlog overflow during flash sale traffic burst caused edge connection drops.",
        "custom_evidence": [
            {
                "id": "E-050",
                "type": "metric",
                "service": "api-gateway",
                "metric": "active_connections",
                "baseline": 1500.0,
                "incident": 28400.0,
                "value": 28400.0,
                "delta": 26900.0,
                "anomaly": True,
                "summary": "Edge TCP active connection count jumped 19x beyond provisioned worker pool.",
            },
        ],
    },
    {
        "id": "inc-reporting-analytics-timeout",
        "scenario_id": "demo-reporting-timeout",
        "title": "Reporting Service Analytics Query Timeout",
        "severity": "sev4",
        "status": "archived",
        "started_at": "2026-10-05T11:00:00+00:00",
        "detected_at": "2026-10-05T11:15:00+00:00",
        "recovered_at": "2026-10-05T12:00:00+00:00",
        "affected_services": ["reporting-service", "warehouse-db"],
        "description": "Non-indexed ad-hoc customer cohort analysis query timed out after 300 seconds.",
        "custom_evidence": [
            {
                "id": "E-060",
                "type": "log",
                "service": "reporting-service",
                "event_type": "QueryTimeoutError",
                "count": 5,
                "error_or_warn_count": 5,
                "summary": "Statement timeout exceeded (300000ms) on analytical aggregation query.",
            },
        ],
    },
    {
        "id": "inc-mtls-handshake-failure",
        "scenario_id": "demo-mtls-handshake",
        "title": "Inter-Service mTLS Certificate Handshake Failure",
        "severity": "sev2",
        "status": "resolved",
        "started_at": "2026-10-07T07:00:00+00:00",
        "detected_at": "2026-10-07T07:03:00+00:00",
        "recovered_at": "2026-10-07T07:28:00+00:00",
        "affected_services": ["auth-service", "order-service", "payment-service"],
        "description": "Intermediate CA certificate bundle renewal missing from mesh sidecar proxy Envoy config.",
        "custom_evidence": [
            {
                "id": "E-070",
                "type": "log",
                "service": "order-service",
                "event_type": "SSLHandshakeException",
                "count": 1340,
                "error_or_warn_count": 1340,
                "summary": "PKIX path building failed: unable to find valid certification path to requested target.",
            },
        ],
    },
]


def seed():
    init_db()
    db = SessionLocal()
    try:
        # Seed canonical scenarios
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
                status=data.get("status", "open"),
                severity=data.get("severity", "sev2"),
                started_at=datetime.fromisoformat(data["started_at"].replace("Z", "+00:00")),
                detected_at=datetime.fromisoformat(data["detected_at"].replace("Z", "+00:00")),
                recovered_at=datetime.fromisoformat(data["recovered_at"].replace("Z", "+00:00")),
                affected_services=data.get("affected_services", []),
                description=data.get("description", ""),
                created_at=datetime.now(timezone.utc),
            )
            db.add(inc)
            print(f"Added canonical incident {inc_id} ({sc_name})")

        # Seed demonstration & variety incidents
        for demo in DEMO_INCIDENTS:
            existing_demo = db.get(IncidentRow, demo["id"])
            if existing_demo:
                print(f"Demo incident {demo['id']} already exists")
                continue

            inc = IncidentRow(
                id=demo["id"],
                scenario_id=demo["scenario_id"],
                title=demo["title"],
                status=demo["status"],
                severity=demo["severity"],
                started_at=datetime.fromisoformat(demo["started_at"]),
                detected_at=datetime.fromisoformat(demo["detected_at"]),
                recovered_at=datetime.fromisoformat(demo["recovered_at"]),
                affected_services=demo["affected_services"],
                description=demo["description"],
                created_at=datetime.now(timezone.utc),
            )
            if demo.get("custom_evidence"):
                inc.custom_evidence = demo["custom_evidence"]
            db.add(inc)
            print(f"Added demo incident {demo['id']} ({demo['title']} [{demo['severity']} - {demo['status']}])")

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
