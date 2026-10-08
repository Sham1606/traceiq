import React from 'react';
import {
  ShieldAlert,
  ArrowRight,
  ArrowDown,
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
  const formatMetric = (value: number) => new Intl.NumberFormat('en-US', {
    maximumSignificantDigits: 4,
  }).format(value);

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
      `${m.service} ${m.metric} anomaly: shifted from baseline ${formatMetric(m.baseline_mean)} to ${formatMetric(m.incident_mean)} (${deltaStr})`
    );
  });

  const highLogs = evidence.log_findings.filter((l) => l.error_or_warn_count > 0);
  if (highLogs.length > 0) {
    changesSummary.push(
      `${highLogs[0].service}: ${highLogs[0].error_or_warn_count} warning/error log events observed (${highLogs[0].event_type})`
    );
  }

  const causalSequences = (evidence.correlations || []).filter(
    (correlation) => (correlation.causal_sequence?.length || 0) > 0
  );
  const causalStepCount = causalSequences.reduce(
    (count, correlation) => count + (correlation.causal_sequence?.length || 0),
    0
  );
  const challengeStatus = typeof investigation.challenge?.status === 'string'
    ? investigation.challenge.status.toUpperCase()
    : investigation.challenge
      ? 'COMPLETED'
      : 'NOT RUN';

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
                <span className={`font-semibold ${investigation.challenge ? 'text-emerald-400' : 'text-slate-400'}`}>
                  {challengeStatus}
                </span>
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

        <section aria-label="Summary causal sequences" className="space-y-4 rounded-lg border border-slate-800 bg-slate-950/80 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-2">
            <span className="flex items-center gap-1.5 text-[10px] font-mono font-bold uppercase tracking-wider text-slate-300">
              <Layers className="h-3.5 w-3.5 text-indigo-400" />
              Correlated causal sequences ({causalStepCount} returned steps)
            </span>
            <span className="text-[11px] font-mono text-slate-400">Backend correlation results</span>
          </div>

          {causalSequences.length === 0 ? (
            <p className="text-xs text-slate-500">No causal sequence was returned; no steps are inferred.</p>
          ) : (
            causalSequences.map((correlation) => (
              <div key={correlation.correlation_id} className="min-w-0 space-y-3">
                <p className="break-words text-xs leading-relaxed text-slate-400">{correlation.summary}</p>
                <ol className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-3">
                  {(correlation.causal_sequence || []).map((step, index) => (
                    <li key={`${index}-${step}`} className="min-w-0 rounded border border-slate-800 bg-slate-900/70 p-3">
                      <span className="text-[10px] font-mono font-bold text-indigo-300">
                        STEP {String(index + 1).padStart(2, '0')}
                      </span>
                      <p className="mt-1 break-words text-xs leading-relaxed text-slate-200">{step}</p>
                    </li>
                  ))}
                </ol>
                {!!correlation.shared_evidence_ids?.length && (
                  <div className="flex flex-wrap items-center gap-1.5 text-[10px] font-mono">
                    <span className="text-slate-500">Evidence:</span>
                    {(correlation.shared_evidence_ids || []).map((id) => (
                      <span key={id} className="rounded border border-indigo-900/60 bg-slate-900 px-1.5 py-0.5 text-indigo-300">{id}</span>
                    ))}
                  </div>
                )}
              </div>
            ))
          )}

          {onNavigateTab && (
            <div className="flex items-center justify-between border-t border-slate-800/60 pt-2 text-[11px] font-mono">
              <span className="text-slate-500">Sequence steps are shown as returned by the backend.</span>
              <button
                onClick={() => onNavigateTab('correlation')}
                className="inline-flex items-center space-x-1 text-indigo-400 hover:text-indigo-300 transition"
              >
                <span>Inspect Correlation Findings ({correlationChains.length})</span>
                <ArrowRight className="w-3 h-3" />
              </button>
            </div>
          )}
        </section>

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
