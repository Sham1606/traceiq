import React, { useState, useEffect } from 'react';
import { History, Search, AlertTriangle, ArrowRight, ShieldAlert, Sparkles, BookOpen } from 'lucide-react';
import { api } from '../../services/api';
import { MemoryMatch } from '../../types/api';
import { LoadingSpinner, ErrorMessage } from '../../components/common/Feedback';

interface HistoricalMemorySectionProps {
  initialFingerprint?: string;
}

export function HistoricalMemorySection({ initialFingerprint = '' }: HistoricalMemorySectionProps) {
  const [fingerprint, setFingerprint] = useState(initialFingerprint || 'bad-deployment');
  const [matches, setMatches] = useState<MemoryMatch[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (query: string) => {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.searchMemory(query.trim(), 5);
      setMatches(res.matches);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to search memory index');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (initialFingerprint) {
      setFingerprint(initialFingerprint);
      handleSearch(initialFingerprint);
    } else {
      handleSearch('deployment');
    }
  }, [initialFingerprint]);

  return (
    <div className="space-y-6">
      {/* Warning / Policy Banner */}
      <div className="bg-amber-950/30 border border-amber-900/60 rounded-lg p-4 space-y-2 text-xs">
        <div className="flex items-center space-x-2 text-amber-300 font-semibold uppercase tracking-wider text-[11px]">
          <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
          <span>Historical Memory Rule</span>
        </div>
        <p className="text-amber-200/90 leading-relaxed font-sans">
          Historical matches are <strong className="text-amber-100">supporting context only</strong>.
          Always validate against current incident evidence. Never assume: <em>&ldquo;Historical match = Current root cause&rdquo;</em>.
        </p>
      </div>

      {/* Search Input Bar */}
      <div className="flex flex-col sm:flex-row items-center gap-3 bg-slate-900/60 p-3 rounded-lg border border-slate-800">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
          <input
            type="text"
            value={fingerprint}
            onChange={(e) => setFingerprint(e.target.value)}
            placeholder="Search organizational incident memory by fingerprint or keyword..."
            className="w-full bg-slate-950 border border-slate-800 rounded pl-9 pr-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
          />
        </div>
        <button
          onClick={() => handleSearch(fingerprint)}
          disabled={loading || !fingerprint.trim()}
          className="w-full sm:w-auto px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded text-xs font-medium transition"
        >
          {loading ? 'Searching...' : 'Search Memory'}
        </button>
      </div>

      {/* Content */}
      {loading ? (
        <LoadingSpinner message="Searching organizational incident memory..." />
      ) : error ? (
        <ErrorMessage message={error} onRetry={() => handleSearch(fingerprint)} />
      ) : matches.length === 0 ? (
        <div className="bg-slate-900/40 border border-dashed border-slate-800 rounded-lg p-8 text-center text-slate-400">
          <BookOpen className="w-8 h-8 text-slate-600 mx-auto mb-2" />
          <p className="text-sm font-medium text-slate-300">No Matching Historical Incidents</p>
          <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
            No past incidents shared fingerprint tokens with &quot;{fingerprint}&quot;.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {matches.map((item, idx) => {
            const mem = item.memory;
            return (
              <div
                key={mem.id || idx}
                className="bg-slate-900/60 rounded-lg border border-slate-800 p-4 space-y-3"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800/80 pb-2.5">
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                        {mem.root_cause_category.toUpperCase()}
                      </span>
                      <h4 className="text-sm font-semibold text-slate-100">{mem.title}</h4>
                    </div>
                    <div className="text-[11px] font-mono text-slate-400 mt-0.5">
                      Memory ID: {mem.id} • Historical Incident: {mem.incident_id}
                    </div>
                  </div>

                  <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800 shrink-0">
                    {item.match_note}
                  </span>
                </div>

                {/* Shared Fingerprint Tokens */}
                <div className="flex items-center space-x-2 text-xs font-mono">
                  <span className="text-slate-400 text-[11px]">Shared Tokens:</span>
                  <div className="flex flex-wrap gap-1">
                    {item.shared_fingerprint_tokens.map((token) => (
                      <span
                        key={token}
                        className="px-1.5 py-0.2 rounded bg-slate-800 text-slate-300 border border-slate-700 text-[10px]"
                      >
                        {token}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Evidence Summary & Past Resolution */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs pt-1">
                  <div className="bg-slate-950/80 p-3 rounded border border-slate-800 space-y-1">
                    <span className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider">
                      Historical Evidence Summary
                    </span>
                    <ul className="list-disc list-inside text-slate-300 text-[11px] space-y-0.5 font-mono">
                      {mem.evidence_summary && mem.evidence_summary.length > 0 ? (
                        mem.evidence_summary.map((ev, i) => <li key={i}>{ev}</li>)
                      ) : (
                        <li className="italic text-slate-500">No summarized items stored</li>
                      )}
                    </ul>
                  </div>

                  <div className="bg-slate-950/80 p-3 rounded border border-slate-800 space-y-1">
                    <span className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider">
                      Historical Resolution
                    </span>
                    <div className="text-slate-200">
                      <strong className="text-slate-400 text-[11px]">Action:</strong> {mem.recovery_action}
                    </div>
                    <div className="text-slate-200">
                      <strong className="text-slate-400 text-[11px]">Outcome:</strong> {mem.recovery_outcome}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
