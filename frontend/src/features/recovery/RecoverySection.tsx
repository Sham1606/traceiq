import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  CheckCircle,
  XCircle,
  Play,
  RotateCcw,
  Check,
  X,
  FileCheck,
  AlertTriangle,
  UserCheck,
} from 'lucide-react';
import { api } from '../../services/api';
import {
  RecoveryActionResponse,
  ApprovalStatus,
  SimulatedResult,
  HypothesisItem,
} from '../../types/api';
import { ApprovalBadge, SimulationBadge } from '../../components/common/Badge';
import { LoadingSpinner, ErrorMessage } from '../../components/common/Feedback';

interface RecoverySectionProps {
  investigationId: string | null;
  leadingHypothesis: HypothesisItem | null;
  onActionUpdated?: () => void;
}

export function RecoverySection({
  investigationId,
  leadingHypothesis,
  onActionUpdated,
}: RecoverySectionProps) {
  const [actions, setActions] = useState<RecoveryActionResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [approverName, setApproverName] = useState('Incident Commander');
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [outcomeInput, setOutcomeInput] = useState('');

  const fetchActions = async () => {
    if (!investigationId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.listRecoveryActions(investigationId);
      setActions(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load recovery actions');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchActions();
  }, [investigationId]);

  const handleProposeDefaultAction = async () => {
    if (!investigationId) return;
    setLoading(true);
    setError(null);
    try {
      let actionTitle = 'Rollback recent release';
      let target = 'Deployment v4.2';
      let rationale = 'Deployment is temporally correlated with the observed regression.';

      if (leadingHypothesis?.title.toLowerCase().includes('database')) {
        actionTitle = 'Scale connection pool & optimize slow queries';
        target = 'PostgreSQL Cluster';
        rationale = 'Database metrics show connection pool exhaustion and query latency degradation.';
      } else if (leadingHypothesis?.title.toLowerCase().includes('dependency')) {
        actionTitle = 'Enable fallback circuit breaker & retry backoff';
        target = 'External Payment Gateway';
        rationale = 'External dependency latency is causing cascade timeouts.';
      } else if (leadingHypothesis?.title.toLowerCase().includes('configuration')) {
        actionTitle = 'Revert recent config change';
        target = 'ConfigMap / Environment variables';
        rationale = 'Configuration regression correlated with error rate jump.';
      }

      await api.createRecoveryAction(investigationId, {
        action: actionTitle,
        target,
        rationale,
      });
      await fetchActions();
      onActionUpdated?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to propose recovery action');
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (actionId: string, approved: boolean) => {
    setProcessingId(actionId);
    setError(null);
    try {
      await api.approveRecoveryAction(actionId, {
        approved_by: approverName.trim() || 'Incident Commander',
        approved,
      });
      await fetchActions();
      onActionUpdated?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Approval operation failed');
    } finally {
      setProcessingId(null);
    }
  };

  const handleSimulate = async (actionId: string) => {
    setProcessingId(actionId);
    setError(null);
    try {
      await api.simulateRecoveryAction(actionId);
      await fetchActions();
      onActionUpdated?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Simulation failed');
    } finally {
      setProcessingId(null);
    }
  };

  const handleRecordOutcome = async (actionId: string) => {
    if (!outcomeInput.trim()) return;
    setProcessingId(actionId);
    setError(null);
    try {
      await api.recordRecoveryOutcome(actionId, outcomeInput.trim());
      setOutcomeInput('');
      await fetchActions();
      onActionUpdated?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to record outcome');
    } finally {
      setProcessingId(null);
    }
  };

  if (!investigationId) {
    return (
      <div className="p-8 text-center bg-slate-900/40 rounded-lg border border-slate-800 text-slate-400">
        Investigation must be initiated before recovery workflows can be generated.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Informative Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-2 border-b border-slate-800">
        <div>
          <div className="flex items-center space-x-2">
            <ShieldAlert className="w-4 h-4 text-indigo-400" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-200">
              Recovery Action & Human Approval Gate
            </h3>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            TRACEIQ never performs autonomous remediation. All mitigating actions require explicit human operator authorization.
          </p>
        </div>

        {actions.length === 0 && (
          <button
            onClick={handleProposeDefaultAction}
            disabled={loading}
            className="px-3 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition shrink-0"
          >
            Propose Recommended Action
          </button>
        )}
      </div>

      {error && <ErrorMessage message={error} />}

      {loading && actions.length === 0 ? (
        <LoadingSpinner message="Checking recovery plan..." />
      ) : actions.length === 0 ? (
        <div className="bg-slate-900/40 border border-dashed border-slate-800 rounded-lg p-8 text-center space-y-3">
          <FileCheck className="w-10 h-10 text-slate-600 mx-auto" />
          <h4 className="text-sm font-semibold text-slate-300">
            No Recovery Actions Formulated Yet
          </h4>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            Propose a recommended recovery action aligned with the leading hypothesis to begin the human approval gate.
          </p>
          <button
            onClick={handleProposeDefaultAction}
            className="px-4 py-2 rounded bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition"
          >
            Formulate Action from Leading Hypothesis
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {actions.map((act) => {
            const isPending = act.approval_status === 'pending';
            const isApproved = act.approval_status === 'approved';
            const isProcessing = processingId === act.id;

            return (
              <div
                key={act.id}
                className="bg-slate-900/60 rounded-lg border border-slate-800 p-5 space-y-4"
              >
                {/* Top Status & Target */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
                  <div>
                    <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400">
                      ACTION ID: {act.id}
                    </span>
                    <h4 className="text-base font-bold text-slate-100 mt-0.5">
                      {act.action}
                    </h4>
                    <div className="text-xs text-slate-400 font-mono mt-0.5">
                      Target: <span className="text-slate-200">{act.target}</span>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <ApprovalBadge status={act.approval_status} />
                    <SimulationBadge result={act.simulated_result} />
                  </div>
                </div>

                {/* Rationale and Expected Impact */}
                <div className="bg-slate-950/70 p-3.5 rounded border border-slate-800/70 text-xs space-y-2">
                  <div>
                    <span className="font-semibold text-slate-400 uppercase text-[10px]">
                      Operational Rationale:
                    </span>
                    <p className="text-slate-300 mt-0.5">{act.rationale}</p>
                  </div>
                  <div>
                    <span className="font-semibold text-slate-400 uppercase text-[10px]">
                      Expected Impact:
                    </span>
                    <div className="text-slate-300 mt-0.5 font-mono text-[11px]">
                      Error rate ↓ • Latency baseline restored • Service health verified
                    </div>
                  </div>
                </div>

                {/* Step 1: Human Approval Gate */}
                <div className="border border-slate-800 rounded p-4 bg-slate-950/40 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2 text-xs font-semibold uppercase tracking-wider text-slate-300">
                      <UserCheck className="w-4 h-4 text-indigo-400" />
                      <span>Step 1: Human Operator Authorization</span>
                    </div>
                    {act.requires_human_approval && (
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-950/80 text-amber-300 border border-amber-800">
                        MANDATORY HUMAN GATE
                      </span>
                    )}
                  </div>

                  {isPending ? (
                    <div className="flex flex-col sm:flex-row sm:items-center gap-3 pt-1">
                      <div className="flex-1">
                        <label className="text-[11px] text-slate-400 block mb-1">
                          Approver Identifier
                        </label>
                        <input
                          type="text"
                          value={approverName}
                          onChange={(e) => setApproverName(e.target.value)}
                          placeholder="e.g. SRE-Lead-01"
                          className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                        />
                      </div>

                      <div className="flex items-center space-x-2 sm:self-end">
                        <button
                          onClick={() => handleApprove(act.id, true)}
                          disabled={isProcessing}
                          className="inline-flex items-center space-x-1 px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition"
                        >
                          <Check className="w-3.5 h-3.5" />
                          <span>Approve Action</span>
                        </button>
                        <button
                          onClick={() => handleApprove(act.id, false)}
                          disabled={isProcessing}
                          className="inline-flex items-center space-x-1 px-3 py-1.5 rounded bg-rose-900 hover:bg-rose-800 text-white text-xs font-semibold transition"
                        >
                          <X className="w-3.5 h-3.5" />
                          <span>Reject</span>
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="text-xs text-slate-300 flex items-center justify-between bg-slate-900/80 px-3 py-2 rounded">
                      <div>
                        Status: <span className="font-semibold capitalize text-emerald-400">{act.approval_status}</span> by{' '}
                        <span className="font-mono text-slate-200">{act.approved_by || 'Operator'}</span>
                      </div>
                      {act.approved_at && (
                        <div className="text-[11px] font-mono text-slate-500">
                          {new Date(act.approved_at).toLocaleString()}
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Step 2: Recovery Simulation */}
                <div className="border border-slate-800 rounded p-4 bg-slate-950/40 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2 text-xs font-semibold uppercase tracking-wider text-slate-300">
                      <Play className="w-4 h-4 text-indigo-400" />
                      <span>Step 2: Pre-Execution Simulation</span>
                    </div>
                    <span className="text-[11px] font-mono text-slate-400">
                      Simulated Environment Validation
                    </span>
                  </div>

                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1">
                    <p className="text-xs text-slate-400 max-w-md">
                      Simulate the recovery effect on state machines and dependent systems before actual deployment.
                    </p>

                    <button
                      onClick={() => handleSimulate(act.id)}
                      disabled={!isApproved || isProcessing || act.simulated_result !== 'not_run'}
                      className={`inline-flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-semibold transition ${
                        isApproved && act.simulated_result === 'not_run'
                          ? 'bg-indigo-600 hover:bg-indigo-500 text-white'
                          : 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700/60'
                      }`}
                    >
                      <RotateCcw className={`w-3.5 h-3.5 ${isProcessing ? 'animate-spin' : ''}`} />
                      <span>
                        {act.simulated_result !== 'not_run'
                          ? `Simulated (${act.simulated_result.toUpperCase()})`
                          : 'Execute Simulation'}
                      </span>
                    </button>
                  </div>
                </div>

                {/* Step 3: Record Actual Recovery Outcome */}
                <div className="border border-slate-800 rounded p-4 bg-slate-950/40 space-y-3">
                  <div className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                    Step 3: Actual Outcome Verification
                  </div>

                  {act.outcome ? (
                    <div className="bg-slate-900/80 p-2.5 rounded text-xs">
                      <span className="text-[10px] text-slate-500 uppercase block">Recorded Outcome:</span>
                      <span className="text-slate-200 font-mono mt-0.5">{act.outcome}</span>
                    </div>
                  ) : (
                    <div className="flex flex-col sm:flex-row items-center gap-2">
                      <input
                        type="text"
                        placeholder="e.g. Rolled back to v4.1; error rate dropped to 0.01% within 2m"
                        value={outcomeInput}
                        onChange={(e) => setOutcomeInput(e.target.value)}
                        className="flex-1 bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                      />
                      <button
                        onClick={() => handleRecordOutcome(act.id)}
                        disabled={!outcomeInput.trim() || isProcessing}
                        className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 text-xs font-medium rounded border border-slate-700 transition shrink-0"
                      >
                        Record Outcome
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
