import React, { useState } from 'react';
import {
  Activity,
  FileText,
  TrendingUp,
  TrendingDown,
  AlertOctagon,
  Search,
  Filter,
  CheckCircle,
  XCircle,
} from 'lucide-react';
import { EvidenceBundle, EvidenceStrength } from '../../types/api';
import { EvidenceStrengthBadge } from '../../components/common/Badge';

interface EvidenceSectionProps {
  evidence: EvidenceBundle | null;
}

export function EvidenceSection({ evidence }: EvidenceSectionProps) {
  const [filterType, setFilterType] = useState<string>('all');
  const [filterStrength, setFilterStrength] = useState<string>('all');
  const [search, setSearch] = useState('');

  if (!evidence) {
    return (
      <div className="p-8 text-center bg-slate-900/40 rounded-lg border border-slate-800 text-slate-400">
        No evidence bundle available. Trigger an investigation to collect and correlate telemetry.
      </div>
    );
  }

  const { metric_findings, log_findings, evidence: evidenceItems } = evidence;

  const filteredEvidence = (evidenceItems || []).filter((item) => {
    const matchesSearch =
      item.summary.toLowerCase().includes(search.toLowerCase()) ||
      item.id.toLowerCase().includes(search.toLowerCase()) ||
      item.source_id.toLowerCase().includes(search.toLowerCase());

    const matchesType = filterType === 'all' || item.evidence_type === filterType;
    const matchesStrength = filterStrength === 'all' || item.strength === filterStrength;

    return matchesSearch && matchesType && matchesStrength;
  });

  return (
    <div className="space-y-6">
      {/* Overview Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-slate-900/60 p-4 rounded-lg border border-slate-800">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
              Metric Findings
            </span>
            <Activity className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-2xl font-bold font-mono text-slate-100">
              {metric_findings.length}
            </span>
            <span className="text-xs text-amber-400 font-mono">
              ({metric_findings.filter((m) => m.anomaly).length} Anomalous)
            </span>
          </div>
          <p className="text-[11px] text-slate-500 mt-1">
            Normalized telemetry deltas from baseline
          </p>
        </div>

        <div className="bg-slate-900/60 p-4 rounded-lg border border-slate-800">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
              Log Patterns
            </span>
            <FileText className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-2xl font-bold font-mono text-slate-100">
              {log_findings.length}
            </span>
            <span className="text-xs text-rose-400 font-mono">
              (
              {log_findings.reduce((acc, curr) => acc + curr.error_or_warn_count, 0)} Warnings/Errors)
            </span>
          </div>
          <p className="text-[11px] text-slate-500 mt-1">
            Categorized log event distributions
          </p>
        </div>

        <div className="bg-slate-900/60 p-4 rounded-lg border border-slate-800">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
              Strong Evidence
            </span>
            <CheckCircle className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-2xl font-bold font-mono text-emerald-400">
              {evidenceItems.filter((e) => e.strength === 'strongly_supported').length}
            </span>
            <span className="text-xs text-slate-400 font-mono">
              / {evidenceItems.length} items
            </span>
          </div>
          <p className="text-[11px] text-slate-500 mt-1">
            Exceeds high anomaly threshold (&gt;100% or error spike)
          </p>
        </div>

        <div className="bg-slate-900/60 p-4 rounded-lg border border-slate-800">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
              Correlation Chains
            </span>
            <AlertOctagon className="w-4 h-4 text-amber-400" />
          </div>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-2xl font-bold font-mono text-slate-100">
              {evidence.correlation_findings.length}
            </span>
            <span className="text-xs text-slate-400 font-mono">Findings</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-1">
            Deterministic causal correlation links
          </p>
        </div>
      </div>

      {/* Metric Anomalies Deep Dive */}
      <div className="bg-slate-900/50 rounded-lg border border-slate-800 overflow-hidden">
        <div className="px-4 py-3 bg-slate-900/80 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Activity className="w-4 h-4 text-indigo-400" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-200">
              Metric Telemetry Findings
            </h3>
          </div>
          <span className="text-[11px] font-mono text-slate-400">
            Baseline vs. Incident Window
          </span>
        </div>

        <div className="p-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {metric_findings.map((finding) => (
            <div
              key={finding.id}
              className={`p-3 rounded border transition ${
                finding.anomaly
                  ? 'bg-slate-950 border-amber-800/60 hover:border-amber-700'
                  : 'bg-slate-950/60 border-slate-800/80'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                    {finding.service}
                  </span>
                  <div className="text-xs font-bold text-slate-200 mt-1 font-mono">
                    {finding.metric}
                  </div>
                </div>
                {finding.anomaly ? (
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-amber-950/80 text-amber-300 border border-amber-800">
                    ANOMALY
                  </span>
                ) : (
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-800 text-slate-400">
                    NORMAL
                  </span>
                )}
              </div>

              <div className="grid grid-cols-3 gap-2 mt-3 pt-2 border-t border-slate-800/60 font-mono text-[11px]">
                <div>
                  <div className="text-[10px] text-slate-500 uppercase">Baseline</div>
                  <div className="text-slate-300">{finding.baseline_mean.toFixed(2)}</div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-500 uppercase">Incident</div>
                  <div className="text-slate-200 font-semibold">{finding.incident_mean.toFixed(2)}</div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-500 uppercase">Delta</div>
                  <div
                    className={`flex items-center space-x-0.5 font-bold ${
                      finding.delta > 0 ? 'text-amber-400' : 'text-slate-400'
                    }`}
                  >
                    {finding.delta > 0 ? (
                      <TrendingUp className="w-3 h-3 shrink-0" />
                    ) : (
                      <TrendingDown className="w-3 h-3 shrink-0" />
                    )}
                    <span>
                      {finding.delta_ratio !== null
                        ? `${(finding.delta_ratio * 100).toFixed(0)}%`
                        : `${finding.delta.toFixed(2)}`}
                    </span>
                  </div>
                </div>
              </div>

              <p className="text-[11px] text-slate-400 mt-2 line-clamp-2">
                {finding.summary}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Master Evidence Table */}
      <div className="bg-slate-900/50 rounded-lg border border-slate-800 overflow-hidden">
        <div className="p-3 bg-slate-900/80 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center space-x-2">
            <FileText className="w-4 h-4 text-indigo-400" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-200">
              Evaluated Evidence Directory ({evidenceItems.length})
            </h3>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2" />
              <input
                type="text"
                placeholder="Search evidence..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="bg-slate-950 border border-slate-800 rounded pl-7 pr-2.5 py-1 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 w-36 sm:w-44"
              />
            </div>

            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
            >
              <option value="all">All Types</option>
              <option value="metric">Metric</option>
              <option value="log">Log</option>
              <option value="timeline">Timeline</option>
            </select>

            <select
              value={filterStrength}
              onChange={(e) => setFilterStrength(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
            >
              <option value="all">All Strengths</option>
              <option value="strongly_supported">Strongly Supported</option>
              <option value="supported">Supported</option>
              <option value="inconclusive">Inconclusive</option>
              <option value="weakly_supported">Weakly Supported</option>
              <option value="rejected">Rejected</option>
            </select>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/70 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-2.5 px-3">Evidence ID</th>
                <th className="py-2.5 px-3">Type</th>
                <th className="py-2.5 px-3">Strength Label</th>
                <th className="py-2.5 px-3">Summary / Finding</th>
                <th className="py-2.5 px-3">Supports</th>
                <th className="py-2.5 px-3">Contradicts</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {filteredEvidence.map((item) => (
                <tr key={item.id} className="hover:bg-slate-850/50 transition">
                  <td className="py-2.5 px-3 font-semibold text-slate-300 whitespace-nowrap">
                    {item.id}
                  </td>
                  <td className="py-2.5 px-3 whitespace-nowrap">
                    <span className="uppercase text-[10px] font-medium px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                      {item.evidence_type}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 whitespace-nowrap">
                    <EvidenceStrengthBadge strength={item.strength as EvidenceStrength} />
                  </td>
                  <td className="py-2.5 px-3 font-sans text-slate-300 max-w-md">
                    {item.summary}
                  </td>
                  <td className="py-2.5 px-3 font-sans">
                    {item.supports && item.supports.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {item.supports.map((s, idx) => (
                          <span
                            key={idx}
                            className="inline-flex items-center px-1.5 py-0.2 rounded text-[10px] font-mono bg-emerald-950/60 text-emerald-300 border border-emerald-800/60"
                          >
                            +{s}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-slate-600 font-mono text-[11px]">—</span>
                    )}
                  </td>
                  <td className="py-2.5 px-3 font-sans">
                    {item.contradicts && item.contradicts.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {item.contradicts.map((c, idx) => (
                          <span
                            key={idx}
                            className="inline-flex items-center px-1.5 py-0.2 rounded text-[10px] font-mono bg-rose-950/60 text-rose-300 border border-rose-800/60"
                          >
                            -{c}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-slate-600 font-mono text-[11px]">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
