import React from 'react';
import {
  CheckCircle2,
  XCircle,
  Layers,
  Sparkles,
  Award,
  HelpCircle,
} from 'lucide-react';
import { HypothesisItem, EvidenceStrength } from '../../types/api';
import { EvidenceStrengthBadge } from '../../components/common/Badge';

interface HypothesesSectionProps {
  hypotheses: HypothesisItem[] | null;
}

export function HypothesesSection({ hypotheses }: HypothesesSectionProps) {
  if (!hypotheses || hypotheses.length === 0) {
    return (
      <div className="p-8 text-center bg-slate-900/40 rounded-lg border border-slate-800 text-slate-400">
        No hypotheses generated yet. Run an investigation to generate and evaluate candidate root-cause explanations.
      </div>
    );
  }

  const leadingHypothesis = hypotheses[0];
  const alternativeHypotheses = hypotheses.slice(1);

  return (
    <div className="space-y-6">
      {/* Informative Header Banner */}
      <div className="bg-slate-900/60 p-4 rounded-lg border border-slate-800 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <div className="flex items-center space-x-2">
            <Layers className="w-4 h-4 text-indigo-400" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-200">
              Competing Hypotheses Evaluation ({hypotheses.length} Considered)
            </h3>
          </div>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl">
            TRACEIQ tests multiple plausible root causes against observed evidence rather than prematurely committing to a single guess.
          </p>
        </div>

        <div className="flex items-center space-x-2 text-[11px] font-mono text-slate-400 bg-slate-950 px-2.5 py-1.5 rounded border border-slate-800 shrink-0">
          <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
          <span>EVALUATION: DETERMINISTIC STUB</span>
        </div>
      </div>

      {/* Prominent Leading Hypothesis Card */}
      {leadingHypothesis && (
        <div className="bg-slate-900/95 rounded-lg border-2 border-indigo-500/80 p-5 shadow-xl shadow-indigo-950/30 space-y-4 relative overflow-hidden">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
            <div className="flex items-center space-x-2.5">
              <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                {leadingHypothesis.id.toUpperCase()}
              </span>
              <span className="px-2.5 py-0.5 rounded text-[11px] font-bold bg-indigo-950 text-indigo-300 border border-indigo-700 uppercase flex items-center space-x-1">
                <Award className="w-3 h-3 text-indigo-400" />
                <span>Leading Candidate</span>
              </span>
            </div>

            <EvidenceStrengthBadge strength={leadingHypothesis.strength as EvidenceStrength} />
          </div>

          <div>
            <h4 className="text-base sm:text-lg font-bold text-slate-100">
              {leadingHypothesis.title}
            </h4>
            <p className="text-xs sm:text-sm text-slate-300 mt-2 leading-relaxed font-sans">
              {leadingHypothesis.explanation}
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-3 border-t border-slate-800/80 font-mono text-xs">
            <div className="bg-emerald-950/20 border border-emerald-900/50 p-3 rounded space-y-1.5">
              <div className="flex items-center space-x-1.5 text-emerald-400 font-semibold text-[11px]">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Supporting Evidence ({leadingHypothesis.supporting_evidence_ids.length})</span>
              </div>
              {leadingHypothesis.supporting_evidence_ids.length > 0 ? (
                <div className="flex flex-wrap gap-1">
                  {leadingHypothesis.supporting_evidence_ids.map((evId) => (
                    <span
                      key={evId}
                      className="px-1.5 py-0.5 rounded text-[10px] bg-emerald-950/60 text-emerald-300 border border-emerald-800/80"
                    >
                      {evId}
                    </span>
                  ))}
                </div>
              ) : (
                <span className="text-[11px] text-slate-500 font-sans italic">
                  No direct supporting evidence
                </span>
              )}
            </div>

            <div className="bg-rose-950/20 border border-rose-900/50 p-3 rounded space-y-1.5">
              <div className="flex items-center space-x-1.5 text-rose-400 font-semibold text-[11px]">
                <XCircle className="w-3.5 h-3.5" />
                <span>Contradicting Evidence ({leadingHypothesis.contradicting_evidence_ids.length})</span>
              </div>
              {leadingHypothesis.contradicting_evidence_ids.length > 0 ? (
                <div className="flex flex-wrap gap-1">
                  {leadingHypothesis.contradicting_evidence_ids.map((evId) => (
                    <span
                      key={evId}
                      className="px-1.5 py-0.5 rounded text-[10px] bg-rose-950/60 text-rose-300 border border-rose-800/80"
                    >
                      {evId}
                    </span>
                  ))}
                </div>
              ) : (
                <span className="text-[11px] text-slate-500 font-sans italic">
                  No contradictory evidence identified
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Alternative Hypotheses Section */}
      {alternativeHypotheses.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-slate-400 px-1">
            <span>Competing Alternative Hypotheses ({alternativeHypotheses.length})</span>
            <span className="font-mono text-slate-500 text-[11px]">Evaluated &amp; Ranked</span>
          </div>

          <div className="grid grid-cols-1 gap-3">
            {alternativeHypotheses.map((h) => (
              <div
                key={h.id}
                className="bg-slate-900/40 hover:bg-slate-900/60 rounded-lg border border-slate-800 hover:border-slate-700 p-4 transition space-y-3"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800/60 pb-2.5">
                  <div className="flex items-center space-x-2.5">
                    <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                      {h.id.toUpperCase()}
                    </span>
                    <h5 className="text-sm font-semibold text-slate-200">
                      {h.title}
                    </h5>
                  </div>
                  <EvidenceStrengthBadge strength={h.strength as EvidenceStrength} />
                </div>

                <p className="text-xs text-slate-300 font-sans leading-relaxed">
                  {h.explanation}
                </p>

                <div className="flex items-center space-x-4 text-xs font-mono text-slate-400 pt-1">
                  <div className="flex items-center space-x-1.5">
                    <span className="text-slate-500">Supporting:</span>
                    <span className="text-emerald-400 font-semibold">{h.supporting_evidence_ids.length}</span>
                  </div>
                  <div className="flex items-center space-x-1.5">
                    <span className="text-slate-500">Contradicting:</span>
                    <span className="text-rose-400 font-semibold">{h.contradicting_evidence_ids.length}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
