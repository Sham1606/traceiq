"""Custom Evidence Normalizer for Live Incident Lab.

Converts arbitrary user-supplied evidence (metrics, logs, deployments, dependencies,
configurations, and text observations) into a standard, structured EvidenceBundle.
Guarantees NO ground truth is generated or attached.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import uuid

from .models import (
    CorrelationFinding,
    EvidenceBundle,
    LogFinding,
    MetricFinding,
    TimelineFinding,
)


def _ensure_datetime(val: Any) -> datetime:
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00"))
        except Exception:
            pass
    return datetime.now(timezone.utc)


def normalize_custom_evidence(
    incident_id: str,
    scenario_id: str,
    raw_evidence_items: list[Any],
    incident_started_at: Any = None,
    incident_recovered_at: Any = None,
) -> EvidenceBundle:
    """Normalize a list of custom raw evidence items into a validated EvidenceBundle.

    Accepts structured dictionaries or plain text descriptions.
    Never generates or accesses ground truth.
    """
    start_dt = _ensure_datetime(incident_started_at)
    end_dt = _ensure_datetime(incident_recovered_at)

    metric_findings: list[MetricFinding] = []
    timeline_findings: list[TimelineFinding] = []
    log_findings: list[LogFinding] = []
    correlation_findings: list[CorrelationFinding] = []
    evidence_items: list[dict[str, Any]] = []

    item_idx = 1

    for raw in raw_evidence_items:
        # Convert plain string or simple text objects
        if isinstance(raw, str):
            ev_id = f"E-{item_idx:03d}"
            item_idx += 1
            summary = raw.strip()
            # Heuristic category
            cat = "metric" if any(w in summary.lower() for w in ["%", "cpu", "latency", "utilization", "rate", "query"]) else (
                "log" if any(w in summary.lower() for w in ["log", "error", "exception", "warn", "timeout"]) else (
                    "deployment" if any(w in summary.lower() for w in ["deploy", "release", "version", "rollback"]) else (
                        "configuration" if "config" in summary.lower() else "dependency"
                    )
                )
            )
            svc = "system"
            for candidate in ["orders-db", "order-service", "api-gateway", "payment-service", "auth-service", "redis-cache"]:
                if candidate in summary.lower():
                    svc = candidate
                    break

            evidence_items.append({
                "id": ev_id,
                "category": cat,
                "service": svc,
                "strength": "supported",
                "summary": summary,
                "source_ids": [ev_id],
                "contradicts": False,
            })
            continue

        if not isinstance(raw, dict):
            continue

        ev_id = raw.get("id") or f"E-{item_idx:03d}"
        item_idx += 1

        ev_type = str(raw.get("type", raw.get("category", "observation"))).lower()
        service = str(raw.get("service", raw.get("source", "system")))
        timestamp = _ensure_datetime(raw.get("timestamp", start_dt))

        if ev_type in {"metric", "telemetry", "metric_finding"}:
            metric_name = str(raw.get("metric", raw.get("name", "metric_value")))
            baseline = float(raw.get("baseline", raw.get("baseline_mean", 0.0)))
            val = float(raw.get("value", raw.get("incident_mean", raw.get("incident", 1.0))))
            delta = float(raw.get("delta", val - baseline))
            ratio = float(raw.get("delta_ratio", (delta / baseline) if baseline > 0 else 0.0))
            is_anomaly = bool(raw.get("anomaly", abs(delta) > 0 or val > 75.0))
            direction = "up" if delta > 0 else ("down" if delta < 0 else "neutral")
            summary = raw.get("summary") or f"{service} {metric_name} shifted by {delta:.1f} (baseline {baseline:.1f} → incident {val:.1f})"

            metric_findings.append(MetricFinding(
                id=ev_id,
                service=service,
                metric=metric_name,
                baseline_mean=baseline,
                incident_mean=val,
                delta=delta,
                delta_ratio=ratio,
                direction=direction,
                anomaly=is_anomaly,
                source_ids=[ev_id],
                summary=summary,
            ))
            evidence_items.append({
                "id": ev_id,
                "category": "metric",
                "service": service,
                "strength": "strongly_supported" if is_anomaly else "supported",
                "summary": summary,
                "source_ids": [ev_id],
                "contradicts": not is_anomaly,
            })

        elif ev_type in {"log", "log_finding"}:
            event_type = str(raw.get("event_type", raw.get("level", "ERROR")))
            count = int(raw.get("count", 10))
            error_count = int(raw.get("error_or_warn_count", raw.get("error_count", count)))
            summary = raw.get("summary") or raw.get("message") or f"{count} {event_type} logs observed in {service}"

            log_findings.append(LogFinding(
                id=ev_id,
                service=service,
                event_type=event_type,
                count=count,
                error_or_warn_count=error_count,
                source_ids=[ev_id],
                summary=summary,
            ))
            evidence_items.append({
                "id": ev_id,
                "category": "log",
                "service": service,
                "strength": "strongly_supported" if error_count > 0 else "supported",
                "summary": summary,
                "source_ids": [ev_id],
                "contradicts": False,
            })

        elif ev_type in {"deployment", "configuration", "dependency", "timeline", "event"}:
            summary = raw.get("summary") or raw.get("message") or f"{ev_type.capitalize()} event in {service}"
            timeline_findings.append(TimelineFinding(
                id=ev_id,
                event_type=ev_type,
                event_id=str(raw.get("event_id", ev_id)),
                timestamp=timestamp,
                related_event_ids=raw.get("related_event_ids", []),
                ordering="during_incident",
                summary=summary,
            ))
            evidence_items.append({
                "id": ev_id,
                "category": ev_type,
                "service": service,
                "strength": "supported",
                "summary": summary,
                "source_ids": [ev_id],
                "contradicts": bool(raw.get("contradicts", False)),
            })

        else:
            # Generic observation / finding
            summary = raw.get("summary") or raw.get("text") or str(raw)
            evidence_items.append({
                "id": ev_id,
                "category": ev_type,
                "service": service,
                "strength": "supported",
                "summary": summary,
                "source_ids": [ev_id],
                "contradicts": False,
            })

    # If timeline or metrics exist, synthesize at least one correlation finding if not present
    if (metric_findings or timeline_findings) and not correlation_findings:
        impacted_svcs = sorted(list({m.service for m in metric_findings} | {t.event_type for t in timeline_findings} | {l.service for l in log_findings}))
        top_metric = metric_findings[0] if metric_findings else None
        top_timeline = timeline_findings[0] if timeline_findings else None

        summary_text = (
            f"Observed telemetry link: {top_timeline.summary} followed by {top_metric.summary}"
            if top_timeline and top_metric
            else (top_metric.summary if top_metric else "Multi-signal telemetry correlation established across services.")
        )
        corr_id = f"corr-custom-{uuid.uuid4().hex[:6]}"
        correlation_findings.append(CorrelationFinding(
            id=corr_id,
            category=top_timeline.event_type if top_timeline else (top_metric.metric if top_metric else "telemetry"),
            source_ids=[e["id"] for e in evidence_items[:5]],
            services=impacted_svcs[:4] or ["system"],
            summary=summary_text,
            supports=[e["id"] for e in evidence_items if not e.get("contradicts")],
            contradicts=[e["id"] for e in evidence_items if e.get("contradicts")],
        ))

    return EvidenceBundle(
        scenario_id=scenario_id,
        incident_id=incident_id,
        metric_findings=metric_findings,
        timeline_findings=timeline_findings,
        log_findings=log_findings,
        correlation_findings=correlation_findings,
        evidence=evidence_items,
    )
