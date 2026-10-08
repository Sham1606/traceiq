import React from 'react';
import { Severity, EvidenceStrength, ApprovalStatus, SimulatedResult } from '../../types/api';

export function SeverityBadge({ severity }: { severity: Severity | string }) {
  const styles: Record<string, string> = {
    sev1: 'bg-red-950/80 text-red-300 border-red-800',
    sev2: 'bg-amber-950/80 text-amber-300 border-amber-800',
    sev3: 'bg-yellow-950/80 text-yellow-300 border-yellow-800',
    sev4: 'bg-blue-950/80 text-blue-300 border-blue-800',
  };

  const style = styles[severity.toLowerCase()] || 'bg-slate-800 text-slate-300 border-slate-700';

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold uppercase tracking-wider border ${style}`}>
      {severity}
    </span>
  );
}

export function EvidenceStrengthBadge({ strength }: { strength: EvidenceStrength | string }) {
  const styles: Record<string, { bg: string; text: string; label: string }> = {
    strongly_supported: {
      bg: 'bg-emerald-950/90 text-emerald-300 border-emerald-700',
      text: 'Strongly Supported',
      label: 'STRONGLY SUPPORTED',
    },
    supported: {
      bg: 'bg-blue-950/90 text-blue-300 border-blue-700',
      text: 'Supported',
      label: 'SUPPORTED',
    },
    weakly_supported: {
      bg: 'bg-slate-900 text-slate-300 border-slate-700',
      text: 'Weakly Supported',
      label: 'WEAKLY SUPPORTED',
    },
    inconclusive: {
      bg: 'bg-amber-950/80 text-amber-300 border-amber-700',
      text: 'Inconclusive',
      label: 'INCONCLUSIVE',
    },
    rejected: {
      bg: 'bg-rose-950/90 text-rose-300 border-rose-800',
      text: 'Rejected',
      label: 'REJECTED',
    },
  };

  const item = styles[strength.toLowerCase()] || {
    bg: 'bg-slate-800 text-slate-300 border-slate-700',
    label: strength.toUpperCase(),
  };

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${item.bg}`}>
      {item.label}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  let style = 'bg-slate-800 text-slate-300 border-slate-700';
  if (status === 'complete' || status === 'resolved' || status === 'recovered' || status === 'mitigated') {
    style = 'bg-emerald-950/80 text-emerald-300 border-emerald-800';
  } else if (status === 'running' || status === 'investigating') {
    style = 'bg-indigo-950/80 text-indigo-300 border-indigo-800 animate-pulse';
  } else if (status === 'failed' || status === 'detected') {
    style = 'bg-red-950/80 text-red-300 border-red-800';
  }

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium capitalize border ${style}`}>
      {status}
    </span>
  );
}

export function ApprovalBadge({ status }: { status: ApprovalStatus }) {
  const styles: Record<string, string> = {
    pending: 'bg-amber-950/80 text-amber-300 border-amber-700',
    approved: 'bg-emerald-950/80 text-emerald-300 border-emerald-700',
    rejected: 'bg-rose-950/80 text-rose-300 border-rose-700',
  };
  const style = styles[status] || 'bg-slate-800 text-slate-300 border-slate-700';

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium uppercase border ${style}`}>
      {status}
    </span>
  );
}

export function SimulationBadge({ result }: { result: SimulatedResult }) {
  const styles: Record<string, string> = {
    safe: 'bg-emerald-950/80 text-emerald-300 border-emerald-700',
    unsafe: 'bg-rose-950/80 text-rose-300 border-rose-700',
    partial: 'bg-amber-950/80 text-amber-300 border-amber-700',
    not_run: 'bg-slate-900 text-slate-400 border-slate-800',
  };
  const style = styles[result] || 'bg-slate-800 text-slate-300 border-slate-700';

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium uppercase border ${style}`}>
      Simulation: {result}
    </span>
  );
}
