import React, { useState, useEffect } from 'react';
import {
  FileSpreadsheet,
  CheckCircle,
  Clock,
  ShieldCheck,
  AlertCircle,
  FileText,
  RotateCcw,
  Archive,
  ArrowRight,
  ListChecks,
} from 'lucide-react';
import { api } from '../../services/api';
import { PostmortemDraft } from '../../types/api';
import { LoadingSpinner, ErrorMessage } from '../../components/common/Feedback';

interface PostmortemSectionProps {
  investigationId?: string | null;
}

export function PostmortemSection({ investigationId }: PostmortemSectionProps) {
  const [postmortem, setPostmortem] = useState<PostmortemDraft | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [archiving, setArchiving] = useState(false);
  const [archived, setArchived] = useState(false);
  const [customNotes, setCustomNotes] = useState('');

  const fetchPostmortem = async () => {
    if (!investigationId) return;
    setLoading(true);
    setError(null);
    try {
      const pm = await api.getPostmortem(investigationId);
      setPostmortem(pm);
    } catch {
      // 404 means not yet generated
      setPostmortem(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPostmortem();
  }, [investigationId]);

  const handleGenerate = async () => {
    if (!investigationId) return;
    setLoading(true);
    setError(null);
    try {
      const pm = await api.createPostmortem(investigationId, customNotes.trim() || undefined);
      setPostmortem(pm);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate postmortem');
    } finally {
      setLoading(false);
    }
  };

  const handleArchive = async () => {
    if (!investigationId) return;
    setArchiving(true);
    setError(null);
    try {
      await api.archiveMemory(investigationId);
      setArchived(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to archive incident to memory');
    } finally {
      setArchiving(false);
    }
  };

  if (!investigationId) {
    return (
      <div className="p-8 text-center bg-slate-900/40 rounded-lg border border-slate-800 text-slate-400">
        Initiate and complete an investigation to synthesize an automated postmortem.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-slate-800">
        <div>
          <div className="flex items-center space-x-2">
            <FileSpreadsheet className="w-4 h-4 text-indigo-400" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-200">
              Automated Postmortem Generation &amp; Memory Archival
            </h3>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Synthesized strictly from visible facts, timeline findings, validated RCA, and executed recovery simulations. Zero hidden ground truth.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {!postmortem && (
            <button
              onClick={handleGenerate}
              disabled={loading}
              className="px-3.5 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition shrink-0 shadow-sm"
            >
              Generate Postmortem
            </button>
          )}

          {postmortem && (
            <button
              onClick={handleArchive}
              disabled={archiving || archived}
              className={`px-3.5 py-1.5 rounded text-xs font-semibold transition shrink-0 flex items-center gap-1.5 ${
                archived
                  ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                  : 'bg-indigo-600 hover:bg-indigo-500 text-white'
              }`}
            >
              <Archive className="w-3.5 h-3.5" />
              <span>{archived ? 'Archived to Memory' : 'Archive to Historical Memory'}</span>
            </button>
          )}
        </div>
      </div>

      {error && <ErrorMessage message={error} />}

      {loading ? (
        <LoadingSpinner message="Synthesizing grounded postmortem document..." />
      ) : !postmortem ? (
        <div className="bg-slate-900/50 rounded-lg border border-slate-800 p-8 text-center space-y-4">
          <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center text-slate-400 mx-auto">
            <FileText className="w-6 h-6" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-slate-200">
              Postmortem Document Ready for Synthesis
            </h4>
            <p className="text-xs text-slate-400 max-w-lg mx-auto mt-1 leading-relaxed">
              Generate an automated postmortem based on the validated hypothesis, supporting evidence, and recovery execution simulation.
            </p>
          </div>

          <div className="max-w-md mx-auto pt-2 space-y-2">
            <input
              type="text"
              placeholder="Optional operator notes or follow-up observations..."
              value={customNotes}
              onChange={(e) => setCustomNotes(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            />
            <button
              onClick={handleGenerate}
              className="w-full px-4 py-2 rounded bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition shadow-sm"
            >
              Synthesize Postmortem
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Postmortem Card Header */}
          <div className="bg-slate-900/70 rounded-lg border border-slate-800 p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800/80 pb-3">
              <div>
                <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-indigo-400">
                  AUTOMATED POSTMORTEM DRAFT
                </span>
                <h3 className="text-lg font-bold text-slate-100 mt-0.5">{postmortem.title}</h3>
                <div className="flex items-center gap-3 text-xs text-slate-400 mt-1 font-mono">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5 text-slate-500" />
                    Impact Duration: <strong className="text-slate-200">{postmortem.impact_duration_minutes ?? 30} mins</strong>
                  </span>
                  <span>•</span>
                  <span>
                    Severity: <strong className="text-slate-200 uppercase">{postmortem.severity || 'SEV2'}</strong>
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <span className="px-2.5 py-1 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-800 text-[11px] font-mono font-semibold flex items-center gap-1">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  EVIDENCE GROUNDED
                </span>
              </div>
            </div>

            {/* Executive Summary */}
            <div className="bg-slate-950/70 p-4 rounded border border-slate-800/70 space-y-1.5 text-xs">
              <span className="font-semibold text-slate-400 uppercase text-[10px] tracking-wider block">
                Executive Incident Summary:
              </span>
              <p className="text-slate-200 leading-relaxed">{postmortem.summary}</p>
            </div>

            {/* Verified RCA */}
            <div className="bg-slate-950/70 p-4 rounded border border-indigo-900/40 space-y-2 text-xs">
              <span className="font-semibold text-indigo-300 uppercase text-[10px] tracking-wider block">
                Verified Root Cause Analysis:
              </span>
              <p className="text-slate-200 leading-relaxed font-mono">{postmortem.root_cause_analysis}</p>

              {postmortem.evidence_references && postmortem.evidence_references.length > 0 && (
                <div className="flex flex-wrap items-center gap-1.5 pt-1">
                  <span className="text-[10px] text-slate-500 font-mono">Primary Evidence IDs:</span>
                  {postmortem.evidence_references.map((eid) => (
                    <span
                      key={eid}
                      className="px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-[10px] font-mono text-cyan-300"
                    >
                      {eid}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Timeline */}
            {postmortem.timeline && postmortem.timeline.length > 0 && (
              <div className="space-y-2">
                <span className="font-semibold text-slate-400 uppercase text-[10px] tracking-wider block">
                  Incident Timeline (Observable Facts):
                </span>
                <div className="bg-slate-950/80 rounded border border-slate-800 divide-y divide-slate-850">
                  {postmortem.timeline.map((item, idx) => (
                    <div key={idx} className="p-2.5 text-xs flex items-start gap-3">
                      <span className="font-mono text-[11px] text-slate-500 shrink-0">
                        {item.timestamp ? new Date(item.timestamp).toLocaleTimeString() : '00:00:00'}
                      </span>
                      <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-800 text-slate-300 shrink-0">
                        {item.type}
                      </span>
                      <span className="text-slate-300">{item.event}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Remediation & Outcome */}
            <div className="bg-slate-950/70 p-4 rounded border border-slate-800/70 space-y-2 text-xs">
              <span className="font-semibold text-slate-400 uppercase text-[10px] tracking-wider block">
                Remediation &amp; Simulated Outcome:
              </span>
              <p className="text-slate-200">{postmortem.remediation_summary}</p>
            </div>

            {/* Action Items */}
            {postmortem.action_items && postmortem.action_items.length > 0 && (
              <div className="space-y-2">
                <span className="font-semibold text-slate-400 uppercase text-[10px] tracking-wider block flex items-center gap-1.5">
                  <ListChecks className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Action Items &amp; Architectural Prevention:</span>
                </span>
                <ul className="space-y-1.5 text-xs text-slate-300 bg-slate-950/80 p-3.5 rounded border border-slate-800">
                  {postmortem.action_items.map((item, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="text-indigo-400 font-bold">•</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
