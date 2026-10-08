import React from 'react';
import { ShieldCheck, AlertCircle, CheckCircle2, XCircle, MinusCircle } from 'lucide-react';
import { ChallengeResult, HypothesisItem } from '../../types/api';

interface ChallengeSectionProps {
  challenge: ChallengeResult | null;
  leadingHypothesis: HypothesisItem | null;
}

export function ChallengeSection({ challenge, leadingHypothesis }: ChallengeSectionProps) {
  const status = challenge?.status || 'not_run';
  const statusLabel = status.replace(/_/g, ' ').toUpperCase();
  const StatusIcon = status === 'supported'
    ? CheckCircle2
    : status === 'rejected'
      ? XCircle
      : challenge
        ? MinusCircle
        : AlertCircle;

  return (
    <div className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <ShieldCheck className="w-4 h-4 text-indigo-400" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-200">
            Adversarial Challenge RCA Protocol
          </h3>
        </div>
        <div className="text-[11px] font-mono text-slate-300 flex items-center space-x-1.5 px-2 py-0.5 rounded bg-slate-900 border border-slate-700">
          <StatusIcon className={`w-3.5 h-3.5 ${status === 'supported' ? 'text-emerald-400' : status === 'rejected' ? 'text-rose-400' : 'text-amber-300'}`} />
          <span>STATUS: {statusLabel}</span>
        </div>
      </div>

      <section className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <h4 className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400">
              Leading hypothesis under challenge
            </h4>
            <p className="mt-1 text-sm font-semibold text-slate-100">
              {leadingHypothesis?.title || 'No leading hypothesis available'}
            </p>
          </div>
          {leadingHypothesis && (
            <span className="text-[10px] font-mono text-slate-400">
              {leadingHypothesis.strength.replace(/_/g, ' ').toUpperCase()}
            </span>
          )}
        </div>
        {challenge ? (
          <>
            <p className="border-t border-slate-800 pt-3 text-xs leading-relaxed text-slate-300">
              {challenge.challenge_rationale}
            </p>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 text-[11px] font-mono">
              <div>
                <span className="text-slate-500">Independent evidence</span>
                <div className="mt-1 flex flex-wrap gap-1.5">
                  {challenge.independent_evidence_ids.length > 0
                    ? challenge.independent_evidence_ids.map((id) => (
                      <span key={id} className="rounded border border-indigo-900/60 bg-slate-950 px-1.5 py-0.5 text-indigo-300">{id}</span>
                    ))
                    : <span className="text-slate-500">None returned</span>}
                </div>
              </div>
              <div>
                <span className="text-slate-500">Contradicting evidence</span>
                <div className="mt-1 flex flex-wrap gap-1.5">
                  {challenge.contradicting_evidence_ids.length > 0
                    ? challenge.contradicting_evidence_ids.map((id) => (
                      <span key={id} className="rounded border border-rose-900/60 bg-slate-950 px-1.5 py-0.5 text-rose-300">{id}</span>
                    ))
                    : <span className="text-slate-500">None returned</span>}
                </div>
              </div>
            </div>
          </>
        ) : (
          <p className="border-t border-slate-800 pt-3 text-xs leading-relaxed text-slate-400">
            No challenge result was returned for this investigation.
          </p>
        )}
      </section>

      <div className="flex items-start gap-2 rounded border border-amber-900/50 bg-amber-950/20 p-3 text-[11px] leading-relaxed text-amber-200/90">
        <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-300" />
        <span>The challenge evaluates a hypothesis; deterministic evidence validation remains separate, and recovery still requires human approval.</span>
      </div>
    </div>
  );
}
