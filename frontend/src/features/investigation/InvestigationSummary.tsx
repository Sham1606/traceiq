import React from 'react';
import {
  ShieldAlert,
  ArrowRight,
  TrendingUp,
  AlertTriangle,
  GitCommit,
  Layers,
  CheckCircle2,
  Clock,
  Sparkles,
  Server,
  Activity,
  Bot,
  UserCheck,
} from 'lucide-react';
import {
  IncidentResponse,
  InvestigationResponse,
  HypothesisItem,
  EvidenceStrength,
} from '../../types/api';
import { EvidenceStrengthBadge } from '../../components/common/Badge';

interface InvestigationSummaryProps {
  incident: IncidentResponse;
  investigation: InvestigationResponse | null;
  onNavigateTab?: (tab: string) => void;
}

export function InvestigationSummary({
  incident,
  investigation,
  onNavigateTab,
}: InvestigationSummaryProps) {
  if (!investigation || !investigation.evidence) {
    return (
      <div className="bg-slate-900/60 rounded-lg border border-slate-800 p-5 text-center space-y-3">
        <div className="w-10 h-10 rounded-full bg-slate-800 text-slate-400 flex items-center justify-center mx-auto">
          <Activity className="w-5 h-5 text-indigo-400" />
        </div>
        <h3 className="text-sm font-semibold text-slate-200">
          Investigation Not Yet Executed
        </h3>
        <p className="text-xs text-slate-400 max-w-md mx-auto">
          Trigger the deterministic investigation engine to synthesize telemetry, correlate signals, and formulate competing root-cause hypotheses.
        </p>
      </div>
    );
  }

  const { evidence } = investigation;
  const hypotheses = (investigation.hypotheses as unknown as HypothesisItem[]) || [];
  const leadingHypothesis: HypothesisItem | null = hypotheses.length > 0 ? hypotheses[0] : null;

  const metricAnomalies = evidence.metric_findings.filter((m) => m.anomaly);
  const timelineEvents = evidence.timeline_findings;
  const correlationChains = evidence.correlation_findings;

  // Dynamically synthesize "What Changed?" signals from actual evidence
  const changesSummary: string[] = [];

  const deployments = timelineEvents.filter((t) => t.event_type.toLowerCase() === 'deployment');
  if (deployments.length > 0) {
    changesSummary.push(`Production deployment logged in timeline (${deployments[0].summary})`);
  }

  const configs = timelineEvents.filter((t) => t.event_type.toLowerCase() === 'configuration');
  if (configs.length > 0) {
    changesSummary.push(`Configuration update applied (${configs[0].summary})`);
  }

  const dependencies = timelineEvents.filter((t) => t.event_type.toLowerCase() === 'dependency');
  if (dependencies.length > 0) {
    changesSummary.push(`External dependency degradation recorded (${dependencies[0].summary})`);
  }

  metricAnomalies.slice(0, 3).forEach((m) => {
    const deltaStr =
      m.delta_ratio !== null
        ? `${m.delta_ratio > 0 ? '+' : ''}${(m.delta_ratio * 100).toFixed(0)}%`
        : `${m.delta > 0 ? '+' : ''}${m.delta.toFixed(2)}`;
    changesSummary.push(
      `${m.service} ${m.metric} anomaly: shifted from baseline ${m.baseline_mean.toFixed(2)} to ${m.incident_mean.toFixed(2)} (${deltaStr})`
    );
  });

  const highLogs = evidence.log_findings.filter((l) => l.error_or_warn_count > 0);
  if (highLogs.length > 0) {
    changesSummary.push(
      `${highLogs[0].service}: ${highLogs[0].error_or_warn_count} warning/error log events observed (${highLogs[0].event_type})`
    );
  }

  // Dynamically build Causal Chain Nodes from correlation, timeline, or metric findings
  const causalNodes = (() => {
    // 1. Identify Trigger
    let triggerLabel = 'TRIGGER EVENT';
    let triggerDetail = incident.scenario_id.toUpperCase();
    if (deployments.length > 0) {
      triggerLabel = 'DEPLOYMENT';
      triggerDetail = deployments[0].summary;
    } else if (configs.length > 0) {
      triggerLabel = 'CONFIGURATION';
      triggerDetail = configs[0].summary;
    } else if (dependencies.length > 0) {
      triggerLabel = 'DEPENDENCY';
      triggerDetail = dependencies[0].summary;
    } else if (correlationChains.length > 0) {
      triggerLabel = correlationChains[0].category.toUpperCase();
      triggerDetail = correlationChains[0].summary;
    }

    const nodes = [
      {
        stage: '1. TRIGGER EVENT',
        label: triggerLabel,
        detail: triggerDetail,
        color: 'border-cyan-700/70 bg-cyan-950/40 text-cyan-300',
      },
    ];

    // 2. Telemetry Anomaly
    if (metricAnomalies.length > 0) {
      const topMetric = metricAnomalies[0];
      const deltaStr =
        topMetric.delta_ratio !== null
          ? `${topMetric.delta_ratio > 0 ? '+' : ''}${(topMetric.delta_ratio * 100).toFixed(0)}%`
          : `${topMetric.delta > 0 ? '+' : ''}${topMetric.delta.toFixed(2)}`;
      nodes.push({
        stage: '2. TELEMETRY SHIFT',
        label: `${topMetric.service} ${topMetric.metric}`,
        detail: `${deltaStr} (${topMetric.baseline_mean.toFixed(2)} → ${topMetric.incident_mean.toFixed(2)})`,
        color: 'border-amber-700/70 bg-amber-950/40 text-amber-300',
      });
    }

    // 3. Log Pattern / System Conflict (if present)
    if (highLogs.length > 0) {
      nodes.push({
        stage: '3. LOG ANOMALY',
        label: `${highLogs[0].event_type}`,
        detail: `${highLogs[0].error_or_warn_count} errors in ${highLogs[0].service}`,
        color: 'border-purple-700/70 bg-purple-950/40 text-purple-300',
      });
    }

    // 4. Observed System Degradation
    nodes.push({
      stage: `${nodes.length + 1}. OBSERVED SYMPTOM`,
      label: 'Service Degradation',
      detail: incident.affected_services.join(', ') || 'Impacted Service',
      color: 'border-rose-700/70 bg-rose-950/40 text-rose-300',
    });

    return nodes;
  })();

  return (
    <div className="bg-slate-900/90 rounded-lg border border-slate-800 shadow-xl overflow-hidden">
      {/* Top Banner Header */}
      <div className="px-5 py-3.5 bg-gradient-to-r from-slate-900 via-indigo-950/30 to-slate-900 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="flex items-center space-x-2.5">
          <div className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-100 flex items-center space-x-2">
            <span>Investigation Executive Summary</span>
            <span className="text-[10px] font-mono font-medium px-2 py-0.2 rounded bg-indigo-950 text-indigo-300 border border-indigo-800">
              Deterministic Evidence Synthesis
            </span>
          </h2>
        </div>

        <div className="flex items-center space-x-3 text-xs font-mono">
          <span className="text-slate-400">Pipeline State:</span>
          <span className="text-emerald-400 font-semibold flex items-center space-x-1">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Deterministic Analysis Complete</span>
          </span>
        </div>
      </div>

      <div className="p-5 space-y-6">
        {/* Core Top Row: Leading Hypothesis & Stats */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          {/* Leading Hypothesis Card */}
          <div className="lg:col-span-7 bg-slate-950/80 rounded-lg border border-indigo-600/40 p-4 space-y-3 relative overflow-hidden">
            <div className="flex items-start justify-between gap-3">
              <div>
                <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-indigo-400 block">
                  Root Cause Assessment • Leading Candidate
                </span>
                <h3 className="text-base font-bold text-slate-100 mt-1">
                  {leadingHypothesis ? leadingHypothesis.title : 'Root Cause Under Investigation'}
                </h3>
              </div>
              {leadingHypothesis && (
                <div className="shrink-0">
                  <EvidenceStrengthBadge strength={leadingHypothesis.strength as EvidenceStrength} />
                </div>
              )}
            </div>

            <p className="text-xs text-slate-300 leading-relaxed font-sans">
              {leadingHypothesis
                ? leadingHypothesis.explanation
                : 'Deterministic evidence analysis complete. Competing hypotheses formulated.'}
            </p>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-slate-800/80 font-mono text-[11px]">
              <div className="bg-slate-900/60 p-2 rounded border border-slate-800">
                <span className="text-slate-400 text-[10px] uppercase block">Supporting</span>
                <span className="text-emerald-400 font-bold text-sm">
                  {leadingHypothesis?.supporting_evidence_ids.length || 0}
                </span>
                <span className="text-slate-500 text-[10px] block">Items</span>
              </div>
              <div className="bg-slate-900/60 p-2 rounded border border-slate-800">
                <span className="text-slate-400 text-[10px] uppercase block">Contradicting</span>
                <span className="text-rose-400 font-bold text-sm">
                  {leadingHypothesis?.contradicting_evidence_ids.length || 0}
                </span>
                <span className="text-slate-500 text-[10px] block">Items</span>
              </div>
              <div className="bg-slate-900/60 p-2 rounded border border-slate-800">
                <span className="text-slate-400 text-[10px] uppercase block">Correlations</span>
                <span className="text-amber-400 font-bold text-sm">
                  {correlationChains.length}
                </span>
                <span className="text-slate-500 text-[10px] block">Chains</span>
              </div>
              <div className="bg-slate-900/60 p-2 rounded border border-slate-800">
                <span className="text-slate-400 text-[10px] uppercase block">Hypotheses</span>
                <span className="text-indigo-400 font-bold text-sm">
                  {hypotheses.length}
                </span>
                <span className="text-slate-500 text-[10px] block">Evaluated</span>
              </div>
            </div>

            {onNavigateTab && (
              <div className="pt-1 flex items-center justify-end">
                <button
                  onClick={() => onNavigateTab('hypotheses')}
                  className="inline-flex items-center space-x-1 text-[11px] font-mono text-indigo-400 hover:text-indigo-300 transition"
                >
                  <span>Inspect All Competing Hypotheses</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              </div>
            )}
          </div>

          {/* Investigation Governance & Readiness Gate */}
          <div className="lg:col-span-5 bg-slate-950/60 rounded-lg border border-slate-800 p-4 flex flex-col justify-between space-y-3">
            <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400 block">
              Investigation Readiness &amp; Governance
            </span>

            <div className="space-y-2 text-xs font-mono">
              <div className="flex items-center justify-between p-2 rounded bg-slate-900/60 border border-slate-800/80">
                <span className="text-slate-400 flex items-center space-x-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Deterministic Evidence</span>
                </span>
                <span className="text-emerald-400 font-semibold">VERIFIED</span>
              </div>

              <div className="flex items-center justify-between p-2 rounded bg-slate-900/60 border border-slate-800/80">
                <span className="text-slate-400 flex items-center space-x-1.5">
                  <Bot className="w-3.5 h-3.5 text-amber-400" />
                  <span>Adversarial Challenge RCA</span>
                </span>
                <span className="text-amber-400 font-semibold">PENDING (PHASE 5)</span>
              </div>

              <div className="flex items-center justify-between p-2 rounded bg-slate-900/60 border border-slate-800/80">
                <span className="text-slate-400 flex items-center space-x-1.5">
                  <UserCheck className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Recovery Authorization</span>
                </span>
                <span className="text-indigo-300 font-semibold">AWAITING OPERATOR</span>
              </div>
            </div>

            <div className="space-y-2 pt-1">
              <div className="text-[11px] text-slate-500 italic">
                TRACEIQ enforces strict ground-truth isolation and mandatory human authorization.
              </div>
              {onNavigateTab && (
                <div className="flex items-center justify-between pt-1 border-t border-slate-800/60">
                  <button
                    onClick={() => onNavigateTab('challenge')}
                    className="inline-flex items-center space-x-1 text-[11px] font-mono text-amber-400/90 hover:text-amber-300 transition"
                  >
                    <span>Challenge Protocol</span>
                    <ArrowRight className="w-3 h-3" />
                  </button>
                  <button
                    onClick={() => onNavigateTab('recovery')}
                    className="inline-flex items-center space-x-1 text-[11px] font-mono text-indigo-400 hover:text-indigo-300 transition"
                  >
                    <span>Recovery Workflow</span>
                    <ArrowRight className="w-3 h-3" />
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Dynamic Causal Chain Diagram */}
        <div className="bg-slate-950/70 rounded-lg border border-slate-800 p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400 flex items-center space-x-1.5">
              <Layers className="w-3.5 h-3.5 text-indigo-400" />
              <span>Correlated Causal Sequence</span>
            </span>
            <span className="text-[11px] font-mono text-slate-500">
              Deterministic Temporal Flow
            </span>
          </div>

          <div className="flex flex-col md:flex-row items-center justify-between gap-3">
            {causalNodes.map((node, idx) => (
              <React.Fragment key={idx}>
                <div className={`w-full md:flex-1 p-3 rounded-lg border ${node.color} text-center space-y-1`}>
                  <div className="text-[9px] uppercase font-mono font-bold tracking-wider opacity-75">
                    {node.stage}
                  </div>
                  <div className="text-xs font-bold text-slate-100 font-mono">
                    {node.label}
                  </div>
                  <div className="text-[11px] text-slate-400 truncate">
                    {node.detail}
                  </div>
                </div>

                {idx < causalNodes.length - 1 && (
                  <div className="flex items-center space-x-1 text-slate-600 px-1 shrink-0">
                    <span className="text-[10px] font-mono text-slate-500 uppercase hidden sm:inline">
                      correlated
                    </span>
                    <ArrowRight className="w-4 h-4 text-indigo-400 shrink-0" />
                  </div>
                )}
              </React.Fragment>
            ))}
          </div>

          {onNavigateTab && (
            <div className="pt-2 flex items-center justify-between border-t border-slate-800/60 text-[11px] font-mono">
              <span className="text-slate-500">Cross-signal causal propagation synthesized from telemetry</span>
              <button
                onClick={() => onNavigateTab('correlation')}
                className="inline-flex items-center space-x-1 text-indigo-400 hover:text-indigo-300 transition"
              >
                <span>Inspect Correlation Findings ({correlationChains.length})</span>
                <ArrowRight className="w-3 h-3" />
              </button>
            </div>
          )}
        </div>

        {/* "What Changed?" Dynamic Telemetry Summary */}
        <div className="bg-slate-950/70 rounded-lg border border-slate-800 p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400 flex items-center space-x-1.5">
              <Activity className="w-3.5 h-3.5 text-amber-400" />
              <span>What Changed? (Observed Telemetry Shifts)</span>
            </span>
            <span className="text-[11px] font-mono text-slate-500">
              {changesSummary.length} Critical Changes Detected
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
            {changesSummary.map((item, idx) => (
              <div
                key={idx}
                className="flex items-start space-x-2 p-2 rounded bg-slate-900/60 border border-slate-800/80 text-slate-300 font-sans"
              >
                <div className="w-1.5 h-1.5 rounded-full bg-amber-400 shrink-0 mt-1.5" />
                <span className="leading-relaxed">{item}</span>
              </div>
            ))}
          </div>

          {onNavigateTab && (
            <div className="pt-2 flex items-center justify-between border-t border-slate-800/60 text-[11px] font-mono">
              <span className="text-slate-500">Deterministic anomaly detection baseline comparison</span>
              <button
                onClick={() => onNavigateTab('evidence')}
                className="inline-flex items-center space-x-1 text-indigo-400 hover:text-indigo-300 transition"
              >
                <span>View Full Evidence Directory ({evidence.evidence.length})</span>
                <ArrowRight className="w-3 h-3" />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
