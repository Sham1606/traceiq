import React, { useState } from 'react';
import {
  GitFork,
  Server,
  Check,
  X,
  ChevronDown,
  ChevronRight,
  Zap,
  AlertTriangle,
  Activity,
  Link2,
} from 'lucide-react';
import { CorrelationFinding, InvestigationCorrelation } from '../../types/api';

interface CorrelationSectionProps {
  correlations: CorrelationFinding[] | null;
  /** Optional AI correlation findings from evidence.correlations — contains causal_sequence */
  aiCorrelations?: InvestigationCorrelation[] | null;
}

const DOMAIN_COLORS: Record<string, { bg: string; border: string; text: string; icon: string }> = {
  deployment: { bg: 'bg-cyan-950/60', border: 'border-cyan-800/60', text: 'text-cyan-300', icon: '🚀' },
  application: { bg: 'bg-indigo-950/60', border: 'border-indigo-800/60', text: 'text-indigo-300', icon: '⚙️' },
  database: { bg: 'bg-amber-950/60', border: 'border-amber-800/60', text: 'text-amber-300', icon: '🗄️' },
  dependency: { bg: 'bg-rose-950/60', border: 'border-rose-800/60', text: 'text-rose-300', icon: '🔌' },
  metric: { bg: 'bg-purple-950/60', border: 'border-purple-800/60', text: 'text-purple-300', icon: '📊' },
  log: { bg: 'bg-slate-800/80', border: 'border-slate-700', text: 'text-slate-300', icon: '📝' },
  configuration: { bg: 'bg-orange-950/60', border: 'border-orange-800/60', text: 'text-orange-300', icon: '⚙️' },
};

function getDomainStyle(domain: string) {
  const key = domain.toLowerCase();
  return DOMAIN_COLORS[key] || { bg: 'bg-slate-800/60', border: 'border-slate-700', text: 'text-slate-300', icon: '🔍' };
}

function parseCausalLabel(label: string): { domain: string; event: string } {
  // Format: "[DOMAIN] Event description" or "Event description"
  const bracketMatch = label.match(/^\[([A-Z_]+)\]\s*(.+)/);
  if (bracketMatch) {
    return { domain: bracketMatch[1].toLowerCase(), event: bracketMatch[2] };
  }
  return { domain: 'unknown', event: label };
}

interface CausalSequenceProps {
  sequence: string[];
}

function CausalSequenceFlow({ sequence }: CausalSequenceProps) {
  if (!sequence || sequence.length === 0) return null;

  return (
    <div className="space-y-2">
      <div className="text-[10px] uppercase font-bold tracking-wider text-slate-400 flex items-center space-x-1.5">
        <Activity className="w-3 h-3 text-indigo-400" />
        <span>Causal Sequence — {sequence.length} Step{sequence.length !== 1 ? 's' : ''}</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-2">
          {sequence.map((label, idx) => {
            const { domain, event } = parseCausalLabel(label);
            const style = getDomainStyle(domain);

            return (
              <div key={`${idx}-${label}`} className={`min-w-0 rounded border p-3 ${style.bg} ${style.border}`}>
                <div className="flex items-center gap-2 min-w-0">
                  <span className="shrink-0 rounded border border-slate-600/70 bg-slate-950/60 px-1.5 py-1 text-[10px] font-mono font-bold text-slate-200">
                    {String(idx + 1).padStart(2, '0')}
                  </span>
                  <div className="flex items-center gap-1.5 min-w-0">
                    <span aria-hidden="true">{style.icon}</span>
                    <span className={`truncate text-[10px] font-bold uppercase tracking-wider ${style.text}`}>
                      {domain === 'unknown' ? 'Event' : domain}
                    </span>
                  </div>
                </div>
                <p className="mt-2 break-words text-xs leading-relaxed text-slate-200">{event}</p>
              </div>
            );
          })}
      </div>
    </div>
  );
}

export function CorrelationSection({ correlations, aiCorrelations }: CorrelationSectionProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const causalSequences = (aiCorrelations || []).filter(
    (correlation) => Array.isArray(correlation.causal_sequence) && correlation.causal_sequence.length > 0
  );

  if ((!correlations || correlations.length === 0) && causalSequences.length === 0) {
    return (
      <div className="p-8 text-center bg-slate-900/40 rounded-lg border border-slate-800 space-y-3">
        <GitFork className="w-8 h-8 text-slate-600 mx-auto" />
        <div className="text-slate-400 text-sm font-medium">No Correlation Chains Detected</div>
        <p className="text-xs text-slate-500 max-w-md mx-auto">
          Run an investigation to synthesize cross-service telemetry links and generate causal sequence chains.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div className="flex items-center space-x-2.5">
          <div className="p-1.5 rounded bg-indigo-950/70 border border-indigo-800/60">
            <GitFork className="w-4 h-4 text-indigo-400" />
          </div>
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
              Cross-Signal Correlation & Causal Flow
            </h3>
            <div className="text-[11px] font-mono text-slate-500 mt-0.5">
              {correlations?.length || 0} correlation chain{correlations?.length === 1 ? '' : 's'} · Deterministic engine
            </div>
          </div>
        </div>
        <div className="flex items-center space-x-2 text-[11px] font-mono text-slate-400">
          <Link2 className="w-3.5 h-3.5 text-emerald-500" />
          <span className="text-emerald-400 font-semibold">Evidence-grounded</span>
        </div>
      </div>

      {causalSequences.length > 0 && (
        <section aria-label="Causal sequences" className="space-y-3">
          {causalSequences.map((correlation, index) => (
            <div key={correlation.correlation_id || index} className="min-w-0 space-y-3 rounded-lg border border-slate-800 bg-slate-900/50 p-4">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0">
                  <h4 className="text-[11px] font-bold uppercase tracking-wider text-slate-200">
                    Causal sequence
                  </h4>
                  {correlation.summary && (
                    <p className="mt-1 break-words text-xs leading-relaxed text-slate-400">{correlation.summary}</p>
                  )}
                </div>
                {correlation.correlation_id && (
                  <span className="shrink-0 text-[10px] font-mono text-slate-500">{correlation.correlation_id}</span>
                )}
              </div>
              <CausalSequenceFlow sequence={correlation.causal_sequence || []} />
              {!!correlation.shared_evidence_ids?.length && (
                <div className="flex flex-wrap items-center gap-1.5 text-[10px] font-mono">
                  <span className="text-slate-500">Evidence:</span>
                  {correlation.shared_evidence_ids.map((id) => (
                    <span key={id} className="rounded border border-indigo-900/60 bg-slate-950 px-1.5 py-0.5 text-indigo-300">{id}</span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </section>
      )}

      {/* Correlation cards */}
      <div className="space-y-4">
        {(correlations || []).map((corr, idx) => {
          const isExpanded = expandedId === corr.id;

          return (
            <div
              key={corr.id}
              className="bg-slate-900/60 rounded-lg border border-slate-800 overflow-hidden"
            >
              {/* Card header — always visible */}
              <button
                onClick={() => setExpandedId(isExpanded ? null : corr.id)}
                className="w-full text-left p-4 flex flex-wrap items-start justify-between gap-3 hover:bg-slate-800/30 transition group"
              >
                <div className="space-y-1.5 flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider bg-indigo-950 text-indigo-300 border border-indigo-800">
                      {corr.category}
                    </span>
                    <span className="text-[11px] font-mono text-slate-500">ID: {corr.id}</span>

                    {/* Service tags */}
                    <div className="flex flex-wrap gap-1">
                      {corr.services.slice(0, 4).map((svc) => (
                        <span
                          key={svc}
                          className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700"
                        >
                          <Server className="w-2.5 h-2.5 mr-1 text-slate-400" />
                          {svc}
                        </span>
                      ))}
                      {corr.services.length > 4 && (
                        <span className="text-[10px] text-slate-500 font-mono">
                          +{corr.services.length - 4} more
                        </span>
                      )}
                    </div>
                  </div>

                  <p className="text-xs text-slate-200 font-medium font-sans leading-relaxed">
                    {corr.summary}
                  </p>

                </div>

                <div className="flex items-center gap-2 shrink-0 self-center">
                  <div className="flex items-center gap-2 text-[11px] font-mono">
                    {corr.supports && corr.supports.length > 0 && (
                      <span className="flex items-center gap-1 text-emerald-400">
                        <Check className="w-3 h-3" />
                        {corr.supports.length} supported
                      </span>
                    )}
                    {corr.contradicts && corr.contradicts.length > 0 && (
                      <span className="flex items-center gap-1 text-rose-400">
                        <X className="w-3 h-3" />
                        {corr.contradicts.length} contradicted
                      </span>
                    )}
                  </div>
                  <div className="text-slate-400 group-hover:text-slate-200 transition">
                    {isExpanded ? (
                      <ChevronDown className="w-4 h-4" />
                    ) : (
                      <ChevronRight className="w-4 h-4" />
                    )}
                  </div>
                </div>
              </button>

              {/* Expanded panel */}
              {isExpanded && (
                <div className="border-t border-slate-800 p-4 space-y-4 bg-slate-950/40">
                  {/* Evidence support / contradiction grid */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                    <div className="bg-emerald-950/20 border border-emerald-900/40 p-3 rounded-lg">
                      <div className="flex items-center space-x-1.5 text-emerald-400 font-semibold text-[11px] mb-2">
                        <Check className="w-3.5 h-3.5" />
                        <span>Supports Hypotheses</span>
                      </div>
                      {corr.supports && corr.supports.length > 0 ? (
                        <ul className="space-y-1">
                          {corr.supports.map((s, i) => (
                            <li
                              key={i}
                              className="flex items-start gap-1.5 text-[11px] font-mono text-emerald-300/90"
                            >
                              <span className="text-emerald-500 mt-0.5 shrink-0">▸</span>
                              <span>{s}</span>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <span className="text-[11px] text-slate-500 italic">
                          No specifically matched hypotheses
                        </span>
                      )}
                    </div>

                    <div className="bg-rose-950/20 border border-rose-900/40 p-3 rounded-lg">
                      <div className="flex items-center space-x-1.5 text-rose-400 font-semibold text-[11px] mb-2">
                        <X className="w-3.5 h-3.5" />
                        <span>Contradicts / False Leads</span>
                      </div>
                      {corr.contradicts && corr.contradicts.length > 0 ? (
                        <ul className="space-y-1">
                          {corr.contradicts.map((c, i) => (
                            <li
                              key={i}
                              className="flex items-start gap-1.5 text-[11px] font-mono text-rose-300/90"
                            >
                              <span className="text-rose-500 mt-0.5 shrink-0">▸</span>
                              <span>{c}</span>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <span className="text-[11px] text-slate-500 italic">
                          No contradictory signals detected
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Source IDs */}
                  {corr.source_ids && corr.source_ids.length > 0 && (
                    <div className="text-[11px] font-mono">
                      <span className="text-slate-400 uppercase text-[10px] font-bold tracking-wider">
                        Correlated Evidence IDs:
                      </span>
                      <div className="flex flex-wrap gap-1.5 mt-1.5">
                        {corr.source_ids.map((sid) => (
                          <span
                            key={sid}
                            className="px-1.5 py-0.5 rounded bg-slate-900 text-indigo-300 border border-indigo-900/60 text-[10px]"
                          >
                            {sid}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
