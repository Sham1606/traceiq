import React from 'react';
import { ShieldCheck, AlertCircle, ArrowDown, Bot } from 'lucide-react';
import { HypothesisItem } from '../../types/api';

interface ChallengeSectionProps {
  challenge: Record<string, unknown> | null;
  leadingHypothesis: HypothesisItem | null;
}

export function ChallengeSection({ challenge, leadingHypothesis }: ChallengeSectionProps) {
  return (
    <div className="space-y-6">
      {/* Informative Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <ShieldCheck className="w-4 h-4 text-indigo-400" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-200">
            Adversarial Challenge RCA Protocol
          </h3>
        </div>
        <div className="text-[11px] font-mono text-amber-400 flex items-center space-x-1.5 px-2 py-0.5 rounded bg-amber-950/40 border border-amber-900/60">
          <AlertCircle className="w-3.5 h-3.5" />
          <span>STATUS: PENDING — PHASE 5 AI LAYER</span>
        </div>
      </div>

      {/* Purpose & Honest Limitation Banner */}
      <div className="bg-amber-950/20 border border-amber-900/50 rounded-lg p-5 text-xs text-amber-200/90 space-y-3">
        <div className="flex items-center space-x-2 font-semibold text-amber-300">
          <Bot className="w-4 h-4" />
          <span className="uppercase text-[11px] tracking-wider">Purpose</span>
        </div>
        <p className="leading-relaxed">
          Attempt to disprove the leading hypothesis using contradicting telemetry, alternative causal models, and uncorroborated timing signals.
        </p>
        <div className="pt-2 border-t border-amber-900/40 text-[11px] text-amber-300/80 font-mono">
          [Backend Status]: Endpoint returns <code className="bg-amber-950/80 px-1 py-0.5 rounded text-amber-300">challenge: null</code>. No fake challenge result is displayed. The adversarial challenge engine activates in Phase 5.
        </div>
      </div>

      {/* Visual Workflow Concept */}
      <div className="bg-slate-900/50 rounded-lg border border-slate-800 p-6 space-y-6">
        <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 text-center">
          Adversarial Challenge RCA Workflow
        </div>

        <div className="max-w-xl mx-auto space-y-3">
          {/* Step 1: Leading Hypothesis */}
          <div className="bg-slate-950 border border-indigo-700/60 rounded-lg p-3.5 text-center shadow">
            <span className="text-[10px] uppercase font-mono font-bold text-indigo-400 tracking-wider">
              1. Leading Hypothesis Under Challenge
            </span>
            <div className="text-sm font-semibold text-slate-200 mt-1">
              {leadingHypothesis ? leadingHypothesis.title : 'Leading Candidate Hypothesis'}
            </div>
            {leadingHypothesis && (
              <div className="text-xs font-mono text-slate-400 mt-1">
                Current Strength: {leadingHypothesis.strength.toUpperCase()}
              </div>
            )}
          </div>

          <div className="flex justify-center text-slate-600">
            <ArrowDown className="w-5 h-5 text-indigo-400 animate-pulse" />
          </div>

          {/* Step 2: Challenge Agent */}
          <div className="bg-slate-950 border border-slate-800 rounded-lg p-3.5 text-center opacity-85">
            <span className="text-[10px] uppercase font-mono font-bold text-amber-400 tracking-wider">
              2. Adversarial Challenge Agent
            </span>
            <div className="text-xs text-slate-300 mt-1">
              Stress-tests leading hypothesis against edge-case anomalies, alternative services, and missing evidence
            </div>
          </div>

          <div className="flex justify-center text-slate-600">
            <ArrowDown className="w-5 h-5 text-slate-600" />
          </div>

          {/* Step 3: Contradicting Evidence Search */}
          <div className="bg-slate-950 border border-slate-800 rounded-lg p-3.5 text-center opacity-85">
            <span className="text-[10px] uppercase font-mono font-bold text-slate-400 tracking-wider">
              3. Contradicting Evidence Evaluation
            </span>
            <div className="text-xs text-slate-400 mt-1">
              Identifies conflicting logs or telemetry that invalidate the proposed cause
            </div>
          </div>

          <div className="flex justify-center text-slate-600">
            <ArrowDown className="w-5 h-5 text-slate-600" />
          </div>

          {/* Step 4: Decision Gate */}
          <div className="bg-slate-950 border border-slate-800 rounded-lg p-4 text-center opacity-85 flex flex-col items-center">
            <span className="text-[10px] uppercase font-mono font-bold text-slate-400 tracking-wider">
              4. Final Challenge Decision Gate
            </span>
            <div className="flex items-center space-x-3 mt-2">
              <span className="px-3 py-1 rounded bg-slate-900 text-slate-500 border border-slate-800 text-xs font-bold font-mono">
                [ SUPPORTED ]
              </span>
              <span className="text-slate-600 text-xs">or</span>
              <span className="px-3 py-1 rounded bg-slate-900 text-slate-500 border border-slate-800 text-xs font-bold font-mono">
                [ REJECTED ]
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
