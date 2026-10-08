import React, { useEffect, useState, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Activity,
  Play,
  RotateCcw,
  Clock,
  Server,
  Layers,
  GitFork,
  ShieldCheck,
  ShieldAlert,
  History,
  ScrollText,
  FileSpreadsheet,
  RefreshCw,
  ArrowLeft,
} from 'lucide-react';
import { api } from '../services/api';
import { IncidentResponse, InvestigationResponse, HypothesisItem } from '../types/api';
import { SeverityBadge, StatusBadge } from '../components/common/Badge';
import { LoadingSpinner, ErrorMessage } from '../components/common/Feedback';

import { InvestigationSummary } from '../features/investigation/InvestigationSummary';
import { AIStatusPanel } from '../features/investigation/AIStatusPanel';
import { InvestigationProgress } from '../features/investigation/InvestigationProgress';
import { EvidenceSection } from '../features/evidence/EvidenceSection';
import { TimelineSection } from '../features/findings/TimelineSection';
import { CorrelationSection } from '../features/findings/CorrelationSection';
import { HypothesesSection } from '../features/rca/HypothesesSection';
import { ChallengeSection } from '../features/rca/ChallengeSection';
import { RecoverySection } from '../features/recovery/RecoverySection';
import { HistoricalMemorySection } from '../features/investigation/HistoricalMemorySection';
import { AuditSection } from '../features/audit/AuditSection';
import { PostmortemSection } from '../features/audit/PostmortemSection';

type WorkspaceTab =
  | 'evidence'
  | 'timeline'
  | 'correlation'
  | 'hypotheses'
  | 'challenge'
  | 'recovery'
  | 'memory'
  | 'audit'
  | 'postmortem';

export function WorkspacePage() {
  const { incidentId } = useParams<{ incidentId: string }>();

  const [incident, setIncident] = useState<IncidentResponse | null>(null);
  const [investigation, setInvestigation] = useState<InvestigationResponse | null>(null);
  const [, setInvestigationsList] = useState<InvestigationResponse[]>([]);
  const [activeTab, setActiveTab] = useState<WorkspaceTab>('evidence');

  const [loadingIncident, setLoadingIncident] = useState(true);
  const [runningInvestigation, setRunningInvestigation] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [investigationStartedAt, setInvestigationStartedAt] = useState<number | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState<number | null>(null);

  useEffect(() => {
    if (!runningInvestigation || investigationStartedAt === null) return;
    const timer = window.setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - investigationStartedAt) / 1000));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [runningInvestigation, investigationStartedAt]);

  // Load Incident details
  const fetchIncident = useCallback(async () => {
    if (!incidentId) return;
    setLoadingIncident(true);
    setError(null);
    try {
      const data = await api.getIncident(incidentId);
      setIncident(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to retrieve incident');
    } finally {
      setLoadingIncident(false);
    }
  }, [incidentId]);

  // Load investigations for incident
  const fetchInvestigations = useCallback(async () => {
    if (!incidentId) return;
    try {
      const list = await api.listInvestigations(incidentId);
      setInvestigationsList(list);
      if (list.length > 0) {
        setInvestigation(list[0]);
      } else {
        setInvestigation(null);
      }
    } catch (err) {
      console.error('Failed to retrieve investigations', err);
    }
  }, [incidentId]);

  useEffect(() => {
    fetchIncident();
    fetchInvestigations();
  }, [fetchIncident, fetchInvestigations]);

  // Backend stages are not streamed; track only the actual request duration.
  const handleStartInvestigation = async () => {
    if (!incidentId) return;
    const startedAt = Date.now();
    setRunningInvestigation(true);
    setInvestigationStartedAt(startedAt);
    setElapsedSeconds(0);
    setError(null);

    try {
      const newInv = await api.startInvestigation(incidentId);
      setInvestigation(newInv);
      await fetchInvestigations();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Investigation failed to execute');
    } finally {
      setElapsedSeconds(Math.floor((Date.now() - startedAt) / 1000));
      setInvestigationStartedAt(null);
      setRunningInvestigation(false);
    }
  };

  const leadingHypothesis: HypothesisItem | null =
    investigation?.hypotheses && investigation.hypotheses.length > 0
      ? (investigation.hypotheses[0] as unknown as HypothesisItem)
      : null;

  const formatDate = (isoString?: string) => {
    if (!isoString) return '—';
    try {
      return new Date(isoString).toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      });
    } catch {
      return isoString;
    }
  };

  if (loadingIncident) {
    return <LoadingSpinner message="Loading incident workspace..." />;
  }

  if (error && !incident) {
    return <ErrorMessage message={error} onRetry={fetchIncident} />;
  }

  if (!incident) {
    return (
      <div className="p-8 text-center text-slate-400">
        Incident not found. <Link to="/incidents" className="text-indigo-400 underline">Return to Directory</Link>
      </div>
    );
  }

  // Precise status label disambiguating deterministic completion from future AI stages
  const getPipelineStatusLabel = () => {
    if (runningInvestigation) return 'INVESTIGATION IN PROGRESS';
    if (!investigation) return 'INVESTIGATION NOT STARTED';
    if (investigation.status === 'complete') return 'DETERMINISTIC ANALYSIS COMPLETE';
    if (investigation.status === 'failed') return 'INVESTIGATION FAILED';
    return investigation.status.toUpperCase();
  };

  return (
    <div className="space-y-6">
      {/* Back button and breadcrumb */}
      <div className="flex items-center space-x-2 text-xs text-slate-400">
        <Link to="/incidents" className="flex items-center space-x-1 hover:text-slate-200 transition">
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Incident Directory</span>
        </Link>
        <span>/</span>
        <span className="text-slate-200 font-mono">{incident.id}</span>
      </div>

      {/* Top Workspace Header */}
      <div className="bg-slate-900/90 rounded-lg border border-slate-800 p-5 shadow-lg space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <SeverityBadge severity={incident.severity} />
              <StatusBadge status={incident.status} />
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                SCENARIO: {incident.scenario_id}
              </span>
            </div>

            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-100">
              {incident.title}
            </h1>

            <div className="flex flex-wrap items-center gap-y-1 gap-x-4 text-xs font-mono text-slate-400">
              <div className="flex items-center space-x-1">
                <Clock className="w-3.5 h-3.5 text-slate-500" />
                <span>Detected: {formatDate(incident.detected_at)}</span>
              </div>
              <div className="flex items-center space-x-1">
                <span className="text-slate-600">•</span>
                <span>Window: {formatDate(incident.started_at)} → {formatDate(incident.recovered_at)}</span>
              </div>
            </div>
          </div>

          {/* Primary Actions */}
          <div className="flex items-center space-x-3 shrink-0">
            <button
              onClick={handleStartInvestigation}
              disabled={runningInvestigation}
              className={`inline-flex items-center space-x-2 px-4 py-2 rounded text-xs font-semibold shadow transition ${
                runningInvestigation
                  ? 'bg-indigo-900 text-indigo-300 cursor-wait'
                  : 'bg-indigo-600 hover:bg-indigo-500 text-white'
              }`}
            >
              {investigation ? (
                <>
                  <RotateCcw className={`w-3.5 h-3.5 ${runningInvestigation ? 'animate-spin' : ''}`} />
                  <span>{runningInvestigation ? 'Analyzing Telemetry...' : 'Re-run Investigation'}</span>
                </>
              ) : (
                <>
                  <Play className={`w-3.5 h-3.5 ${runningInvestigation ? 'animate-spin' : ''}`} />
                  <span>{runningInvestigation ? 'Investigating...' : 'Start Investigation'}</span>
                </>
              )}
            </button>

            <button
              onClick={() => {
                fetchIncident();
                fetchInvestigations();
              }}
              className="p-2 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
              title="Refresh workspace state"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Impacted Services */}
        <div className="flex items-center space-x-2 pt-2 border-t border-slate-800/80 text-xs">
          <span className="text-slate-400 flex items-center space-x-1">
            <Server className="w-3.5 h-3.5 text-slate-500" />
            <span>Impacted Services:</span>
          </span>
          <div className="flex flex-wrap gap-1.5">
            {incident.affected_services.map((svc) => (
              <span
                key={svc}
                className="px-2 py-0.5 rounded text-[11px] font-mono bg-slate-950 text-slate-300 border border-slate-800"
              >
                {svc}
              </span>
            ))}
          </div>
        </div>

        {/* Upgraded Investigation Pipeline Stepper */}
        <div className="pt-3 border-t border-slate-800/80 space-y-2">
          <div className="flex items-center justify-between text-[11px] uppercase tracking-wider text-slate-400 font-semibold">
            <span>Investigation Pipeline &amp; Progression</span>
            <span className="font-mono text-emerald-400 font-bold bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800/60">
              {getPipelineStatusLabel()}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-5 gap-2 text-xs font-mono">
            {[
              {
                label: 'Evidence Collection',
                done: !!investigation?.evidence,
                detail: 'Metrics & Logs Normalized',
              },
              {
                label: 'Evidence Correlation',
                done: !!investigation?.evidence?.correlation_findings.length,
                detail: 'Causal Ordering Verified',
              },
              {
                label: 'Hypothesis Generation',
                done: !!investigation?.hypotheses?.length,
                detail: 'Deterministic Ranking',
              },
              {
                label: 'Challenge RCA',
                done: !!investigation?.challenge,
                pending: !investigation?.challenge,
                detail: investigation?.challenge ? 'Falsification Verified' : 'Adversarial Evaluation',
              },
              {
                label: 'Recovery Decision',
                done: false,
                step: true,
                detail: 'Awaiting Human Operator',
              },
            ].map((step, idx) => (
              <div
                key={idx}
                className={`p-2.5 rounded border text-left flex flex-col justify-between ${
                  step.done
                    ? 'bg-emerald-950/40 border-emerald-800/70 text-emerald-300'
                    : step.pending
                    ? 'bg-amber-950/30 border-amber-800/60 text-amber-300'
                    : 'bg-slate-950/60 border-slate-800 text-slate-400'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase tracking-wider">
                    {step.label}
                  </span>
                  <span className="text-xs font-bold">
                    {step.done ? '✓' : step.pending ? '○' : '○'}
                  </span>
                </div>
                <span className="text-[10px] opacity-80 mt-1 truncate">
                  {step.detail}
                </span>
              </div>
            ))}
          </div>

        </div>
      </div>

      {error && <ErrorMessage message={error} />}

      {(runningInvestigation || investigation) && (
        <InvestigationProgress
          investigation={runningInvestigation ? null : investigation}
          running={runningInvestigation}
          elapsedSeconds={elapsedSeconds}
        />
      )}

      {/* AI Investigation Engine Status & Transparency Panel */}
      {investigation && (
        <AIStatusPanel
          investigation={investigation}
          leadingHypothesis={leadingHypothesis}
        />
      )}

      {/* Top-Level Investigation Summary (Executive View) */}
      <InvestigationSummary
        incident={incident}
        investigation={investigation}
        onNavigateTab={(t) => setActiveTab(t as WorkspaceTab)}
      />

      {/* Logical Section Category Headers and Navigation Tabs */}
      <div className="space-y-2 pt-2">
        <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-slate-400 px-1">
          <span>Investigation Details &amp; Operational Modules</span>
          <span className="text-[11px] font-mono text-slate-500">
            Select module to inspect evidence
          </span>
        </div>

        <div className="border-b border-slate-800 flex items-center space-x-2 overflow-x-auto pb-px">
          {[
            {
              group: 'EVIDENCE',
              items: [
                { id: 'evidence', label: 'Evidence Directory', icon: Layers },
                { id: 'timeline', label: 'Timeline', icon: Clock },
                { id: 'correlation', label: 'Correlation Flow', icon: GitFork },
              ],
            },
            {
              group: 'REASONING',
              items: [
                { id: 'hypotheses', label: 'Competing Hypotheses', icon: Activity },
                { id: 'challenge', label: 'Challenge RCA', icon: ShieldCheck },
              ],
            },
            {
              group: 'RECOVERY',
              items: [
                { id: 'recovery', label: 'Recovery Workflow', icon: ShieldAlert },
              ],
            },
            {
              group: 'MEMORY',
              items: [
                { id: 'memory', label: 'Historical Memory', icon: History },
              ],
            },
            {
              group: 'GOVERNANCE',
              items: [
                { id: 'audit', label: 'Audit Trail', icon: ScrollText },
                { id: 'postmortem', label: 'Postmortem', icon: FileSpreadsheet },
              ],
            },
          ].map((cluster, cIdx) => (
            <div key={cluster.group} className="flex items-center space-x-1 shrink-0">
              {cIdx > 0 && <div className="h-4 w-px bg-slate-800 mx-1" />}
              {cluster.items.map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;

                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as WorkspaceTab)}
                    className={`flex items-center space-x-2 px-3 py-2 text-xs font-semibold whitespace-nowrap border-b-2 transition ${
                      isActive
                        ? 'border-indigo-500 text-indigo-300 bg-slate-900/60'
                        : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
                    }`}
                  >
                    <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-indigo-400' : 'text-slate-500'}`} />
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      </div>

      {/* Detailed Investigation Tab Content */}
      <div className="pt-1">
        {activeTab === 'evidence' && (
          <EvidenceSection evidence={investigation?.evidence || null} />
        )}

        {activeTab === 'timeline' && (
          <TimelineSection timeline={investigation?.evidence?.timeline_findings || null} />
        )}

        {activeTab === 'correlation' && (
          <CorrelationSection
            correlations={investigation?.evidence?.correlation_findings || null}
            aiCorrelations={investigation?.evidence?.correlations || null}
          />
        )}

        {activeTab === 'hypotheses' && (
          <HypothesesSection
            hypotheses={(investigation?.hypotheses as unknown as HypothesisItem[]) || null}
          />
        )}

        {activeTab === 'challenge' && (
          <ChallengeSection
            challenge={investigation?.challenge || null}
            leadingHypothesis={leadingHypothesis}
          />
        )}

        {activeTab === 'recovery' && (
          <RecoverySection
            investigationId={investigation?.id || null}
            leadingHypothesis={leadingHypothesis}
            onActionUpdated={fetchInvestigations}
          />
        )}

        {activeTab === 'memory' && (
          <HistoricalMemorySection initialFingerprint={incident.scenario_id} />
        )}

        {activeTab === 'audit' && <AuditSection incidentId={incident.id} />}

        {activeTab === 'postmortem' && (
          <PostmortemSection investigationId={investigation?.id || null} />
        )}
      </div>
    </div>
  );
}
