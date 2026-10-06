from __future__ import annotations

from collections import defaultdict
from statistics import mean

from traceiq_data.schemas import MetricPoint
from .models import MetricFinding


ANOMALY_RATIO = 0.35
ANOMALY_ABS_THRESHOLDS = {
    "error_rate": 0.02,
    "cpu_utilization": 12.0,
    "request_latency_p95": 80.0,
    "query_latency_p95": 100.0,
    "connection_utilization": 12.0,
    "retry_rate": 0.04,
    "queue_depth": 20.0,
    "latency_p95": 100.0,
}


def analyze_metrics(points: list[MetricPoint], incident_start, recovery_start) -> list[MetricFinding]:
    grouped: dict[tuple[str, str], list[MetricPoint]] = defaultdict(list)
    for point in points:
        grouped[(point.service, point.metric)].append(point)

    findings: list[MetricFinding] = []
    for (service, metric), values in sorted(grouped.items()):
        baseline = [x for x in values if x.timestamp < incident_start]
        incident = [x for x in values if incident_start <= x.timestamp < recovery_start]
        if not baseline or not incident:
            continue

        baseline_mean = mean(x.value for x in baseline)
        incident_mean = mean(x.value for x in incident)
        delta = incident_mean - baseline_mean
        ratio = delta / baseline_mean if baseline_mean else None
        abs_threshold = ANOMALY_ABS_THRESHOLDS.get(metric, 0.0)
        anomaly = abs(delta) >= abs_threshold or (ratio is not None and abs(ratio) >= ANOMALY_RATIO)
        direction = "increased" if delta > 0 else "decreased" if delta < 0 else "stable"
        source_ids = [x.id for x in incident]
        finding_id = f"metric-{service}-{metric}".replace("_", "-")
        findings.append(
            MetricFinding(
                id=finding_id,
                service=service,
                metric=metric,
                baseline_mean=round(baseline_mean, 4),
                incident_mean=round(incident_mean, 4),
                delta=round(delta, 4),
                delta_ratio=round(ratio, 4) if ratio is not None else None,
                direction=direction,
                anomaly=anomaly,
                source_ids=source_ids,
                summary=(
                    f"{service} {metric} {direction} from {baseline_mean:.2f} to "
                    f"{incident_mean:.2f} during the incident window."
                ),
            )
        )
    return findings
