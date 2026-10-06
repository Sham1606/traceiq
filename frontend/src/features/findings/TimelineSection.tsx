import React from 'react';
import {
  GitCommit,
  Sliders,
  Share2,
  AlertTriangle,
  Clock,
  Layers,
  FileText,
} from 'lucide-react';
import { TimelineFinding } from '../../types/api';

interface TimelineSectionProps {
  timeline: TimelineFinding[] | null;
}

export function TimelineSection({ timeline }: TimelineSectionProps) {
  if (!timeline || timeline.length === 0) {
    return (
      <div className="p-8 text-center bg-slate-900/40 rounded-lg border border-slate-800 text-slate-400">
        No chronological timeline data available. Run an investigation to correlate time-series events.
      </div>
    );
  }

  // Ensure chronological order
  const sorted = [...timeline].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );

  const getEventBadge = (type: string) => {
    switch (type.toLowerCase()) {
      case 'deployment':
        return {
          icon: GitCommit,
          color: 'text-cyan-400 bg-cyan-950/80 border-cyan-800',
          dot: 'bg-cyan-400',
          label: 'DEPLOYMENT',
        };
      case 'configuration':
        return {
          icon: Sliders,
          color: 'text-purple-400 bg-purple-950/80 border-purple-800',
          dot: 'bg-purple-400',
          label: 'CONFIG CHANGE',
        };
      case 'dependency':
        return {
          icon: Share2,
          color: 'text-amber-400 bg-amber-950/80 border-amber-800',
          dot: 'bg-amber-400',
          label: 'DEPENDENCY EVENT',
        };
      case 'log':
        return {
          icon: FileText,
          color: 'text-rose-400 bg-rose-950/80 border-rose-800',
          dot: 'bg-rose-400',
          label: 'LOG SPIKE',
        };
      default:
        return {
          icon: AlertTriangle,
          color: 'text-indigo-400 bg-indigo-950/80 border-indigo-800',
          dot: 'bg-indigo-400',
          label: type.toUpperCase(),
        };
    }
  };

  const formatTimestamp = (ts: string) => {
    try {
      const d = new Date(ts);
      return d.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      });
    } catch {
      return ts;
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <Clock className="w-4 h-4 text-indigo-400" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-200">
            Chronological Incident Timeline ({sorted.length} Events)
          </h3>
        </div>
        <div className="text-[11px] font-mono text-slate-400">
          Causal sequence ordered by timestamp
        </div>
      </div>

      <div className="relative pl-6 sm:pl-8 space-y-6 before:absolute before:left-2 sm:before:left-3 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-800">
        {sorted.map((item, idx) => {
          const badge = getEventBadge(item.event_type);
          const Icon = badge.icon;

          return (
            <div key={item.id} className="relative group">
              {/* Timeline marker node */}
              <div
                className={`absolute -left-6 sm:-left-8 top-1 w-4 sm:w-5 h-4 sm:h-5 rounded-full border-2 border-slate-950 ${badge.dot} flex items-center justify-center shadow`}
              />

              <div className="bg-slate-900/60 p-3.5 rounded-lg border border-slate-800 hover:border-slate-700 transition">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center space-x-2">
                    <span
                      className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-semibold font-mono border ${badge.color}`}
                    >
                      <Icon className="w-3 h-3" />
                      <span>{badge.label}</span>
                    </span>
                    <span className="text-xs font-mono font-semibold text-slate-200">
                      {formatTimestamp(item.timestamp)}
                    </span>
                    <span className="text-[11px] font-mono text-slate-500">
                      [{item.ordering}]
                    </span>
                  </div>

                  <div className="text-[11px] font-mono text-slate-500">
                    ID: {item.event_id}
                  </div>
                </div>

                <p className="text-xs text-slate-300 mt-2 font-sans font-medium">
                  {item.summary}
                </p>

                {item.related_event_ids && item.related_event_ids.length > 0 && (
                  <div className="mt-2.5 pt-2 border-t border-slate-800/60 flex items-center space-x-2 text-[11px] font-mono">
                    <span className="text-slate-500">Related Events:</span>
                    <div className="flex flex-wrap gap-1">
                      {item.related_event_ids.map((relId) => (
                        <span
                          key={relId}
                          className="px-1.5 py-0.2 rounded bg-slate-800/80 text-slate-400 border border-slate-700/60"
                        >
                          {relId}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
