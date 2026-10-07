"""Database Investigator for TRACEIQ.

Analyzes database-related telemetry:
- Query latency and execution time anomalies
- Connection pool utilization and connection exhaustion
- Database locks, deadlocks, and slow query log patterns
- Causal analysis: Is the database the root trigger or an overloaded symptom?
"""
from __future__ import annotations

import uuid
from typing import Any
from ..schemas import EvidenceStrengthLabel, InvestigatorFinding
from .base import BaseInvestigator


class DatabaseInvestigator(BaseInvestigator):
    """Specialized investigator for database telemetry and connection health."""

    investigator_type: str = "database"
    domain: str = "database"

    def filter_evidence(
        self,
        incident: dict[str, Any],
        evidence: dict[str, Any],
    ) -> dict[str, Any]:
        """Filter telemetry strictly to database metrics, logs, and connection signals."""
        metric_findings = evidence.get("metric_findings", [])
        log_findings = evidence.get("log_findings", [])
        ev_items = evidence.get("evidence", [])

        db_metrics = [
            m for m in metric_findings
            if "db" in m.get("service", "").lower()
            or "postgres" in m.get("service", "").lower()
            or "database" in m.get("service", "").lower()
            or any(k in m.get("metric", "").lower() for k in {"query", "connection", "pool", "sql", "lock"})
        ]

        db_logs = [
            l for l in log_findings
            if "db" in l.get("service", "").lower()
            or "postgres" in l.get("service", "").lower()
            or "database" in l.get("service", "").lower()
            or any(k in l.get("summary", "").lower() for k in {"pool", "deadlock", "connection", "transaction"})
        ]

        db_evidence = [
            e for e in ev_items
            if "db" in str(e.get("source_id", "")).lower()
            or "postgres" in str(e.get("source_id", "")).lower()
            or any(k in str(e.get("summary", "")).lower() for k in {"database", "query", "connection", "pool"})
        ]

        return {
            "metrics": db_metrics,
            "logs": db_logs,
            "evidence": db_evidence,
            "incident": incident,
        }

    def build_deterministic_finding(
        self,
        incident: dict[str, Any],
        filtered_evidence: dict[str, Any],
        all_valid_ids: set[str],
    ) -> InvestigatorFinding:
        """Formulate evidence-grounded database finding."""
        metrics = filtered_evidence.get("metrics", [])
        logs = filtered_evidence.get("logs", [])
        ev_items = filtered_evidence.get("evidence", [])

        supporting_ids: list[str] = []
        contradicting_ids: list[str] = []
        anomalies: list[str] = []

        for item in ev_items:
            eid = str(item.get("id"))
            if eid in all_valid_ids:
                if item.get("strength") in {"strongly_supported", "supported"}:
                    supporting_ids.append(eid)
                elif item.get("contradicts"):
                    contradicting_ids.append(eid)

        anomalous_metrics = [m for m in metrics if m.get("anomaly")]
        for m in anomalous_metrics:
            mid = f"ev-{m.get('id')}"
            if mid in all_valid_ids and mid not in supporting_ids:
                supporting_ids.append(mid)
            anomalies.append(f"{m.get('service')}:{m.get('metric')}")

        db_error_logs = [l for l in logs if l.get("error_or_warn_count", 0) > 0]
        for l in db_error_logs:
            lid = f"ev-{l.get('id')}"
            if lid in all_valid_ids and lid not in supporting_ids:
                supporting_ids.append(lid)

        # Check for query latency and connection pool signals
        has_query_latency = any("query" in m.get("metric", "").lower() for m in anomalous_metrics)
        has_pool_exhaustion = any(
            "connection" in m.get("metric", "").lower() or "pool" in m.get("metric", "").lower()
            for m in anomalous_metrics
        )

        if has_query_latency or has_pool_exhaustion:
            strength: EvidenceStrengthLabel = "strongly_supported"
            title = "Database connection pool exhaustion and query latency surge"
            summary = (
                f"Database telemetry shows acute degradation: {len(anomalous_metrics)} metric anomalies detected. "
                f"Connection saturation and p99 query latency elevated during incident window."
            )
            reasoning = (
                "Database query execution latency and connection utilization metrics show significant delta ratio shifts. "
                "Correlating queries and connection pool exhaustion indicates backing store bottleneck."
            )
        elif anomalous_metrics:
            strength = "supported"
            title = "Moderate database performance anomaly"
            summary = f"Detected {len(anomalous_metrics)} database metric anomalies without complete pool saturation."
            reasoning = "Database telemetry exhibits deviation from baseline mean, indicating potential load strain."
        else:
            strength = "inconclusive"
            title = "Database metrics healthy; no storage degradation observed"
            summary = "Database queries and connection pools operate within normal baseline thresholds."
            reasoning = "Database telemetry shows no metric anomalies or error log spikes; database is unlikely incident root cause."

        return InvestigatorFinding(
            finding_id=f"find-db-{uuid.uuid4().hex[:6]}",
            investigator_type="database",
            domain="database",
            title=title,
            summary=summary,
            reasoning=reasoning,
            strength=strength,
            confidence_label=strength,
            evidence_ids=supporting_ids[:10],
            supporting_evidence_ids=supporting_ids[:10],
            contradicting_evidence_ids=contradicting_ids[:5],
            observations=[f"Inspected {len(metrics)} database metrics and {len(logs)} database log groups."],
            uncertainties=["Verify whether connection spike was caused by unindexed queries or upstream request stampede."],
            anomalies_detected=anomalies[:5],
            metadata={"source": "deterministic_database_investigator"},
        )
