from __future__ import annotations

from collections import defaultdict

from traceiq_data.schemas import LogEvent
from .models import LogFinding


def analyze_logs(logs: list[LogEvent], incident_start, recovery_start) -> list[LogFinding]:
    grouped = defaultdict(list)
    for log in logs:
        if incident_start <= log.timestamp < recovery_start:
            grouped[(log.service, log.event_type)].append(log)

    findings = []
    for (service, event_type), items in sorted(grouped.items()):
        error_warn = sum(item.level in {"WARN", "ERROR"} for item in items)
        ids = [item.id for item in items]
        findings.append(
            LogFinding(
                id=f"log-{service}-{event_type}".replace("_", "-"),
                service=service,
                event_type=event_type,
                count=len(items),
                error_or_warn_count=error_warn,
                source_ids=ids,
                summary=f"{event_type} occurred {len(items)} times for {service}; {error_warn} were WARN/ERROR.",
            )
        )
    return findings
