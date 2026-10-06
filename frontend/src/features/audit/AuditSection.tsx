import React, { useEffect, useState } from 'react';
import { ScrollText, Clock, User, CheckCircle2, ChevronRight, RefreshCw } from 'lucide-react';
import { api } from '../../services/api';
import { AuditEntryResponse } from '../../types/api';
import { LoadingSpinner, ErrorMessage } from '../../components/common/Feedback';

interface AuditSectionProps {
  incidentId: string;
}

export function AuditSection({ incidentId }: AuditSectionProps) {
  const [entries, setEntries] = useState<AuditEntryResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const fetchAudit = async () => {
    if (!incidentId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.getAuditLog(incidentId);
      setEntries(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch audit log');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAudit();
  }, [incidentId]);

  const formatTimestamp = (ts: string) => {
    try {
      return new Date(ts).toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      });
    } catch {
      return ts;
    }
  };

  const getActionBadge = (action: string) => {
    if (action.startsWith('investigation')) {
      return {
        label: 'INVESTIGATION',
        color: 'bg-cyan-950 text-cyan-300 border-cyan-800',
      };
    }
    if (action.startsWith('recovery')) {
      return {
        label: 'RECOVERY',
        color: 'bg-indigo-950 text-indigo-300 border-indigo-800',
      };
    }
    return {
      label: 'SYSTEM',
      color: 'bg-slate-800 text-slate-300 border-slate-700',
    };
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <ScrollText className="w-4 h-4 text-indigo-400" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-200">
            Immutable Investigation Audit Trail ({entries.length} Events)
          </h3>
        </div>
        <button
          onClick={fetchAudit}
          disabled={loading}
          className="inline-flex items-center space-x-1 px-2.5 py-1 rounded text-[11px] font-medium bg-slate-900 border border-slate-700 hover:bg-slate-800 text-slate-300 transition"
        >
          <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {loading && entries.length === 0 ? (
        <LoadingSpinner message="Retrieving audit records..." />
      ) : error ? (
        <ErrorMessage message={error} onRetry={fetchAudit} />
      ) : entries.length === 0 ? (
        <div className="p-8 text-center bg-slate-900/40 rounded-lg border border-slate-800 text-slate-400">
          No audit entries recorded for this incident yet.
        </div>
      ) : (
        <div className="border border-slate-800 rounded-lg overflow-hidden bg-slate-900/50">
          <div className="divide-y divide-slate-800/80">
            {entries.map((entry) => {
              const isExpanded = expandedId === entry.id;
              const badge = getActionBadge(entry.action);

              return (
                <div key={entry.id} className="p-3.5 hover:bg-slate-850/40 transition">
                  <div
                    onClick={() => setExpandedId(isExpanded ? null : entry.id)}
                    className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 cursor-pointer"
                  >
                    <div className="flex items-center space-x-2.5">
                      <ChevronRight
                        className={`w-3.5 h-3.5 text-slate-500 transition-transform ${
                          isExpanded ? 'rotate-90 text-indigo-400' : ''
                        }`}
                      />
                      <span
                        className={`text-[10px] font-mono px-1.5 py-0.2 rounded border font-semibold ${badge.color}`}
                      >
                        {badge.label}
                      </span>
                      <span className="font-mono text-xs font-semibold text-slate-200">
                        {entry.action}
                      </span>
                    </div>

                    <div className="flex items-center space-x-3 text-xs font-mono text-slate-400">
                      <div className="flex items-center space-x-1">
                        <User className="w-3 h-3 text-slate-500" />
                        <span className="text-slate-300">{entry.actor}</span>
                      </div>
                      <span className="text-slate-600">•</span>
                      <div className="flex items-center space-x-1">
                        <Clock className="w-3 h-3 text-slate-500" />
                        <span>{formatTimestamp(entry.created_at)}</span>
                      </div>
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="mt-3 pl-6">
                      <pre className="bg-slate-950 p-3 rounded text-[11px] font-mono text-slate-300 overflow-x-auto border border-slate-800">
                        {JSON.stringify(entry.detail, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
