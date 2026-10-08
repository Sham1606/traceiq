import React from 'react';
import {
  Cpu,
  CheckCircle2,
  Sparkles,
  UserCheck,
} from 'lucide-react';
import { InvestigationResponse, HypothesisItem } from '../../types/api';

interface AIStatusPanelProps {
  investigation: InvestigationResponse | null;
  leadingHypothesis: HypothesisItem | null;
}

export function AIStatusPanel({ investigation, leadingHypothesis }: AIStatusPanelProps) {
  if (!investigation) return null;

  const evidence = investigation.evidence;
  const telemetry = evidence?.ai_telemetry || {};
  const providerName: string = telemetry.provider || 'not configured';
  const mode: string = telemetry.mode || (
    providerName === 'mock'
      ? 'mock'
      : providerName === 'deterministic-engine'
        ? 'deterministic'
        : 'not-configured'
  );
  const modelName: string | null = telemetry.model || null;

  const evidenceCount: number =
    telemetry.evidence_analyzed ??
    (evidence?.evidence ? evidence.evidence.length : 0);
  const domainsCount: number =
    telemetry.domains_analyzed ??
    (evidence?.investigator_findings ? evidence.investigator_findings.length : 0);
  const hypothesesCount: number =
    telemetry.hypotheses_count ??
    (investigation.hypotheses ? investigation.hypotheses.length : 0);
  const challengeStatus: string =
    telemetry.challenge_status ??
    (investigation.challenge ? 'Completed' : 'Not run');

  // Mode badge styling
  const isLive = mode === 'live';
  const isFallback = mode === 'fallback' || Boolean(telemetry.fallback_reason);
  const isMock = mode === 'mock';
  const isDeterministic = mode === 'deterministic';
  const isUnconfigured = mode === 'not-configured';
  const isUnverified = isUnconfigured && providerName !== 'not configured';
  const modeLabel = isLive
    ? 'AI MODE LIVE'
    : isFallback
      ? 'AI MODE FALLBACK'
      : isMock
        ? 'AI MODE DETERMINISTIC / MOCK'
        : isDeterministic
          ? 'DETERMINISTIC ANALYSIS'
          : isUnverified
            ? 'PROVIDER INVOCATION UNVERIFIED'
            : 'LIVE PROVIDER NOT CONFIGURED';

  return (
    <div className="bg-slate-900/95 rounded-lg border border-slate-800 p-5 space-y-4 shadow-xl">
      {/* Top Header: AI Engine Status */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-800/80">
        <div className="flex items-center space-x-2.5">
          <div className="p-1.5 rounded bg-indigo-950/70 border border-indigo-800/60 text-indigo-400">
            <Cpu className="w-4 h-4" />
          </div>
          <div>
            <div className="text-[11px] font-mono uppercase font-bold tracking-wider text-slate-300 flex flex-wrap items-center gap-2">
              <span>INVESTIGATION ENGINE STATUS</span>
              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wider border ${
                isLive ? 'bg-emerald-950 text-emerald-300 border-emerald-700/80'
                  : isFallback ? 'bg-amber-950 text-amber-300 border-amber-700/80'
                  : isMock ? 'bg-sky-950 text-sky-300 border-sky-700/80'
                  : 'bg-slate-900 text-slate-300 border-slate-700'
              }`}>
                {modeLabel}
              </span>
            </div>
            <div className="text-[11px] text-slate-400 font-mono mt-0.5">
              Provider: <span className="text-slate-200 font-semibold">{providerName.toUpperCase()}</span>
              {modelName && <> · Model: <span className="text-slate-200">{modelName}</span></>}
            </div>
          </div>
        </div>

        {/* Responsibility Tagging */}
        <div className="flex flex-wrap gap-1.5 text-[10px] font-mono">
          {(isLive || isMock) && (
            <span className="px-2 py-0.5 rounded bg-indigo-950/80 text-indigo-300 border border-indigo-800/60">
              {isLive ? 'AI PROPOSAL' : 'MOCK PROVIDER OUTPUT'}
            </span>
          )}
          {(isDeterministic || isFallback || isUnconfigured && !isUnverified) && (
            <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
              DETERMINISTIC ANALYSIS
            </span>
          )}
          {isUnverified && (
            <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
              ANALYSIS MODE UNVERIFIED
            </span>
          )}
          <span className="px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-800/60">
            DETERMINISTIC VALIDATION
          </span>
          <span className="px-2 py-0.5 rounded bg-purple-950/80 text-purple-300 border border-purple-800/60">
            HUMAN APPROVAL
          </span>
        </div>
      </div>

      {/* Metric Breakdown Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
        <div className="p-2.5 rounded bg-slate-950/70 border border-slate-800/80 space-y-1">
          <div className="text-[10px] text-slate-500 uppercase tracking-wider">Evidence Analyzed</div>
          <div className="text-base font-bold text-slate-100">{evidenceCount}</div>
          <div className="text-[10px] text-slate-400 truncate">Normalized Signals</div>
        </div>

        <div className="p-2.5 rounded bg-slate-950/70 border border-slate-800/80 space-y-1">
          <div className="text-[10px] text-slate-500 uppercase tracking-wider">Investigation Domains</div>
          <div className="text-base font-bold text-indigo-300">{domainsCount}</div>
          <div className="text-[10px] text-slate-400 truncate">Deploy / DB / Dep / App</div>
        </div>

        <div className="p-2.5 rounded bg-slate-950/70 border border-slate-800/80 space-y-1">
          <div className="text-[10px] text-slate-500 uppercase tracking-wider">Hypotheses</div>
          <div className="text-base font-bold text-amber-300">{hypothesesCount}</div>
          <div className="text-[10px] text-slate-400 truncate">Competing Models</div>
        </div>

        <div className="p-2.5 rounded bg-slate-950/70 border border-slate-800/80 space-y-1">
          <div className="text-[10px] text-slate-500 uppercase tracking-wider">Adversarial Challenge</div>
          <div className="text-base font-bold text-emerald-300">{challengeStatus}</div>
          <div className="text-[10px] text-slate-400 truncate">Falsification Check</div>
        </div>
      </div>

      {/* Leading AI Finding & Grounding Card */}
      {leadingHypothesis && (
        <div className="bg-slate-950/80 rounded border border-indigo-900/40 p-3.5 space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono uppercase font-bold tracking-wider text-indigo-400 flex items-center space-x-1.5">
              <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
              <span>LEADING HYPOTHESIS</span>
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 text-slate-300 border border-slate-800">
              Rank #1 ({leadingHypothesis.strength.toUpperCase()})
            </span>
          </div>

          <div className="text-xs font-semibold text-slate-100 font-sans">
            {leadingHypothesis.title}
          </div>

          {/* Evidence Grounding IDs */}
          <div className="flex flex-wrap items-center gap-1.5 text-xs font-mono pt-1">
            <span className="text-[10px] text-slate-400 uppercase font-semibold">Grounded Evidence:</span>
            {leadingHypothesis.evidence_ids && leadingHypothesis.evidence_ids.length > 0 ? (
              leadingHypothesis.evidence_ids.slice(0, 6).map((eid) => (
                <span
                  key={eid}
                  className="px-1.5 py-0.5 rounded text-[10px] bg-slate-900 text-indigo-300 border border-indigo-800/60 font-semibold"
                >
                  {eid}
                </span>
              ))
            ) : (
              <span className="text-[11px] text-slate-500">Telemetry cross-referenced</span>
            )}
          </div>

          {/* High-level finding summary */}
          <p className="text-xs text-slate-300 leading-relaxed font-sans bg-slate-900/60 p-2.5 rounded border border-slate-800/80">
            {leadingHypothesis.explanation}
          </p>
        </div>
      )}

      {/* Deterministic Validation & Human Safety Assurance Footer */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pt-2 border-t border-slate-800/60 text-[11px] font-mono text-slate-400">
        <div className={`flex items-center space-x-1.5 ${telemetry.deterministic_validation === 'PASS' ? 'text-emerald-400' : 'text-slate-400'}`}>
          <CheckCircle2 className="w-3.5 h-3.5" />
          <span className="font-semibold">DETERMINISTIC VALIDATION: {telemetry.deterministic_validation || 'NOT REPORTED'}</span>
          {telemetry.deterministic_validation === 'PASS' && (
            <span className="text-slate-500">Evidence references validated</span>
          )}
        </div>
        <div className="flex items-center space-x-1.5 text-slate-400">
          <UserCheck className="w-3.5 h-3.5 text-purple-400" />
          <span>HUMAN APPROVAL REQUIRED FOR RECOVERY</span>
        </div>
      </div>
    </div>
  );
}
