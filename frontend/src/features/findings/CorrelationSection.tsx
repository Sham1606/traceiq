import React from 'react';
import { GitFork, ArrowDown, Server, Check, X, Layers } from 'lucide-react';
import { CorrelationFinding } from '../../types/api';

interface CorrelationSectionProps {
  correlations: CorrelationFinding[] | null;
}

export function CorrelationSection({ correlations }: CorrelationSectionProps) {
  if (!correlations || correlations.length === 0) {
    return (
      <div className="p-8 text-center bg-slate-900/40 rounded-lg border border-slate-800 text-slate-400">
        No correlation chains detected. Run an investigation to synthesize cross-service telemetry links.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <GitFork className="w-4 h-4 text-indigo-400" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-200">
            Telemetry Correlation & Causal Flow ({correlations.length} Chains)
          </h3>
        </div>
        <div className="text-[11px] font-mono text-slate-400">
          Deterministic cross-signal correlation
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {correlations.map((corr) => (
          <div
            key={corr.id}
            className="bg-slate-900/60 rounded-lg border border-slate-800 p-4 space-y-3"
          >
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-2">
              <div className="flex items-center space-x-2">
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider bg-indigo-950 text-indigo-300 border border-indigo-800">
                  {corr.category}
                </span>
                <span className="text-xs font-mono text-slate-400">ID: {corr.id}</span>
              </div>

              <div className="flex items-center space-x-1.5">
                <span className="text-[11px] text-slate-400">Impacted:</span>
                <div className="flex flex-wrap gap-1">
                  {corr.services.map((svc) => (
                    <span
                      key={svc}
                      className="inline-flex items-center px-1.5 py-0.2 rounded text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700"
                    >
                      <Server className="w-2.5 h-2.5 mr-1 text-slate-400" />
                      {svc}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* Summary */}
            <p className="text-xs text-slate-200 font-medium font-sans">
              {corr.summary}
            </p>

            {/* Causal Flow Representation */}
            <div className="bg-slate-950/70 p-3 rounded border border-slate-800/80 space-y-2">
              <div className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider">
                Correlation Flow
              </div>
              <div className="flex flex-col sm:flex-row sm:items-center gap-2 text-xs font-mono">
                <div className="p-2 rounded bg-slate-900 border border-slate-700/80 text-slate-200 text-center flex-1">
                  <div className="text-[10px] text-slate-400 uppercase">Trigger Event</div>
                  <div className="font-semibold text-cyan-300 mt-0.5">
                    {corr.category.toUpperCase()}
                  </div>
                </div>

                <div className="flex justify-center text-indigo-400 shrink-0">
                  <ArrowDown className="w-4 h-4 sm:-rotate-90" />
                </div>

                <div className="p-2 rounded bg-slate-900 border border-slate-700/80 text-slate-200 text-center flex-1">
                  <div className="text-[10px] text-slate-400 uppercase">Component Signals</div>
                  <div className="font-semibold text-amber-300 mt-0.5">
                    {corr.source_ids.length} Sources Linked
                  </div>
                </div>

                <div className="flex justify-center text-indigo-400 shrink-0">
                  <ArrowDown className="w-4 h-4 sm:-rotate-90" />
                </div>

                <div className="p-2 rounded bg-slate-900 border border-slate-700/80 text-slate-200 text-center flex-1">
                  <div className="text-[10px] text-slate-400 uppercase">System Consequence</div>
                  <div className="font-semibold text-rose-300 mt-0.5">
                    Service Degradation
                  </div>
                </div>
              </div>
            </div>

            {/* Hypotheses Supported / Contradicted */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1 text-xs">
              <div className="bg-emerald-950/20 border border-emerald-900/40 p-2.5 rounded">
                <div className="flex items-center space-x-1.5 text-emerald-400 font-semibold text-[11px] mb-1">
                  <Check className="w-3.5 h-3.5" />
                  <span>Supports Hypotheses</span>
                </div>
                {corr.supports && corr.supports.length > 0 ? (
                  <ul className="list-disc list-inside text-slate-300 text-[11px] space-y-0.5">
                    {corr.supports.map((s, idx) => (
                      <li key={idx} className="font-mono text-emerald-300/90">{s}</li>
                    ))}
                  </ul>
                ) : (
                  <span className="text-[11px] text-slate-500 italic">None specifically matched</span>
                )}
              </div>

              <div className="bg-rose-950/20 border border-rose-900/40 p-2.5 rounded">
                <div className="flex items-center space-x-1.5 text-rose-400 font-semibold text-[11px] mb-1">
                  <X className="w-3.5 h-3.5" />
                  <span>Contradicts Hypotheses</span>
                </div>
                {corr.contradicts && corr.contradicts.length > 0 ? (
                  <ul className="list-disc list-inside text-slate-300 text-[11px] space-y-0.5">
                    {corr.contradicts.map((c, idx) => (
                      <li key={idx} className="font-mono text-rose-300/90">{c}</li>
                    ))}
                  </ul>
                ) : (
                  <span className="text-[11px] text-slate-500 italic">No contradictory signals detected</span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
