from __future__ import annotations

from .models import CorrelationFinding, LogFinding, MetricFinding, TimelineFinding


def correlate(metric_findings: list[MetricFinding], log_findings: list[LogFinding], timeline_findings: list[TimelineFinding]) -> list[CorrelationFinding]:
    findings = []

    for metric in metric_findings:
        if not metric.anomaly:
            continue
        related_logs = [x for x in log_findings if x.service == metric.service and x.count > 0]
        if not related_logs:
            continue
        source_ids = metric.source_ids[:5] + [x.id for x in related_logs]
        findings.append(
            CorrelationFinding(
                id=f"corr-{metric.id}",
                category="metric-log",
                source_ids=source_ids,
                services=[metric.service],
                summary=f"{metric.metric} anomaly on {metric.service} coincides with {sum(x.count for x in related_logs)} related log events.",
                supports=[metric.metric],
            )
        )

    for timeline in timeline_findings:
        if timeline.event_type not in {"deployment", "configuration", "dependency"}:
            continue
        nearby = [x for x in timeline_findings if x.event_id != timeline.event_id and x.event_type == "log" and x.event_id in timeline.related_event_ids]
        if nearby:
            findings.append(
                CorrelationFinding(
                    id=f"corr-timeline-{timeline.event_id}",
                    category=f"{timeline.event_type}-log",
                    source_ids=[timeline.event_id] + [x.event_id for x in nearby],
                    services=[],
                    summary=f"{timeline.event_type.capitalize()} event {timeline.event_id} is temporally close to warning/error logs.",
                )
            )
    return findings
