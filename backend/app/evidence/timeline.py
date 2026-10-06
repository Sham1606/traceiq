from __future__ import annotations

from traceiq_data.schemas import ConfigurationChange, DeploymentEvent, DependencyEvent, LogEvent
from .models import TimelineFinding


def correlate_timeline(incident_start, incident_end, deployments, configurations, dependencies, logs) -> list[TimelineFinding]:
    events = []
    for item in deployments:
        events.append((item.timestamp, "deployment", item.id))
    for item in configurations:
        events.append((item.timestamp, "configuration", item.id))
    for item in dependencies:
        if item.status in {"degraded", "failed"}:
            events.append((item.timestamp, "dependency", item.id))
    for item in logs:
        if item.level in {"WARN", "ERROR"}:
            events.append((item.timestamp, "log", item.id))
    events.sort()

    findings = []
    for timestamp, event_type, event_id in events:
        if timestamp > incident_end or timestamp < incident_start:
            continue
        related = [eid for ts, typ, eid in events if eid != event_id and abs((ts - timestamp).total_seconds()) <= 300]
        prior = [typ for ts, typ, _ in events if ts <= timestamp and ts >= incident_start]
        ordering = "preceded_by=" + (prior[-2] if len(prior) >= 2 else "incident_start")
        findings.append(
            TimelineFinding(
                id=f"timeline-{event_id}",
                event_type=event_type,
                event_id=event_id,
                timestamp=timestamp,
                related_event_ids=related[:10],
                ordering=ordering,
                summary=f"{event_type} event {event_id} occurred at {timestamp.isoformat()} with {len(related)} nearby events.",
            )
        )
    return findings
