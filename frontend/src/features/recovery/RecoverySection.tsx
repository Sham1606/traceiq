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
  Activity,
  Layers,
  ArrowRight,
  Info,
} from 'lucide-react';
import { api } from '../../services/api';
import {
  RecoveryActionResponse,
  ApprovalStatus,
  SimulatedResult,
  HypothesisItem,
  BlastRadiusSimulation,
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

  const handleProposeAdvisorAction = async () => {
    if (!investigationId) return;
    setLoading(true);
    setError(null);
    try {
      // First attempt backend Recovery Advisor
      try {
        const advised = await api.recommendRecoveryActions(investigationId);
        if (advised && advised.length > 0) {
          await fetchActions();
          onActionUpdated?.();
          return;
        }
      } catch {
        // Fallback to client-side derivation if advisor endpoint fails
      }

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

  const handleSimulateAndExecute = async (actionId: string) => {
    setProcessingId(actionId);
    setError(null);
    try {
      // 1. Run pre-execution safety simulation
      await api.simulateRecoveryAction(actionId);
      // 2. Execute deterministic execution simulation
      try {
        await api.executeRecoverySimulation(actionId);
      } catch {
        // Ignored if already simulated or backend uses legacy endpoint
      }
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
      {/* Informative Header with Core Safety Principle */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-slate-800">
        <div>
          <div className="flex items-center space-x-2">
            <ShieldAlert className="w-4 h-4 text-indigo-400" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-200">
              Recovery Advisor & Human Approval Gate
            </h3>
          </div>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl leading-relaxed">
            TRACEIQ never performs autonomous remediation. All mitigating actions require explicit human operator authorization.
          </p>
        </div>

        {actions.length === 0 && (
          <button
            onClick={handleProposeAdvisorAction}
            disabled={loading}
            className="px-3.5 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition shrink-0 shadow-sm"
          >
            Propose Recommended Action
          </button>
        )}
      </div>

      {/* Safety Discipline Badges */}
      <div className="flex flex-wrap gap-2 text-[10px] font-mono">
        <span className="px-2.5 py-1 rounded bg-indigo-950/80 text-indigo-300 border border-indigo-800/60 flex items-center gap-1.5">
          <Activity className="w-3 h-3 text-indigo-400" />
          DETERMINISTIC: PROPOSES RECOVERY
        </span>
        <span className="px-2.5 py-1 rounded bg-cyan-950/80 text-cyan-300 border border-cyan-800/60 flex items-center gap-1.5">
          <Layers className="w-3 h-3 text-cyan-400" />
          DETERMINISTIC: BLAST RADIUS &amp; SIMULATION
        </span>
        <span className="px-2.5 py-1 rounded bg-amber-950/80 text-amber-300 border border-amber-800/60 flex items-center gap-1.5">
          <UserCheck className="w-3 h-3 text-amber-400" />
          HUMAN: MANDATORY APPROVAL
        </span>
      </div>

      {error && <ErrorMessage message={error} />}

      {loading && actions.length === 0 ? (
        <LoadingSpinner message="Evaluating validated RCA and calculating blast radius..." />
      ) : actions.length === 0 ? (
        <div className="bg-slate-900/40 border border-dashed border-slate-800 rounded-lg p-8 text-center space-y-3">
          <FileCheck className="w-10 h-10 text-slate-600 mx-auto" />
          <h4 className="text-sm font-semibold text-slate-300">
            No Recovery Actions Formulated Yet
          </h4>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            Propose a recommended recovery action aligned with the validated hypothesis to run blast-radius analysis and begin operator approval.
          </p>
          <button
            onClick={handleProposeAdvisorAction}
            className="px-4 py-2 rounded bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition"
          >
            Formulate Action from Leading Hypothesis
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          {actions.map((act) => {
            const isPending = act.approval_status === 'pending';
            const isApproved = act.approval_status === 'approved';
            const isRejected = act.approval_status === 'rejected';
            const isProcessing = processingId === act.id;
            const blast = act.blast_radius || (act.detail?.blast_radius as BlastRadiusSimulation | undefined);
            const execSim = act.execution_simulation;
            const risk = act.risk_level || (blast?.risk_level) || 'medium';
            const isHighRisk = risk === 'high';
            const isBlocked = blast?.status === 'BLOCKED';

            return (
              <div
                key={act.id}
                className="bg-slate-900/70 rounded-lg border border-slate-800 p-5 space-y-5 shadow-sm"
              >
                {/* Top Status & Target */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800/80 pb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400">
                        ACTION ID: {act.id.slice(0, 8)}
                      </span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                        DETERMINISTIC RECOMMENDATION
                      </span>
                      {isHighRisk && (
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800 flex items-center gap-1 font-semibold">
                          <AlertTriangle className="w-3 h-3 text-rose-400" />
                          HIGH RISK
                        </span>
                      )}
                      {isBlocked && (
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-red-950 text-red-300 border border-red-800 font-semibold">
                          BLOCKED
                        </span>
                      )}
                    </div>
                    <h4 className="text-base font-bold text-slate-100 mt-1">
                      {act.action}
                    </h4>
                    <div className="text-xs text-slate-400 font-mono mt-0.5">
                      Target Service: <span className="text-slate-200 font-semibold">{act.target}</span>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <ApprovalBadge status={act.approval_status} />
                    <SimulationBadge result={act.simulated_result} />
                  </div>
                </div>

                {/* Rationale and Expected Impact */}
                <div className="bg-slate-950/70 p-3.5 rounded border border-slate-800/70 text-xs space-y-2.5">
                  <div>
                    <span className="font-semibold text-slate-400 uppercase text-[10px] tracking-wider block">
                      Operational Rationale (Evidence Grounded):
                    </span>
                    <p className="text-slate-300 mt-0.5 leading-relaxed">{act.rationale}</p>
                  </div>

                  {act.supporting_evidence_ids && act.supporting_evidence_ids.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1.5 pt-1">
                      <span className="text-[10px] text-slate-400 font-mono">Grounded In Evidence:</span>
                      {act.supporting_evidence_ids.map((eid) => (
                        <span
                          key={eid}
                          className="px-1.5 py-0.5 rounded bg-slate-900 border border-slate-700 text-[10px] font-mono text-cyan-300"
                        >
                          {eid}
                        </span>
                      ))}
                    </div>
                  )}

                  <div>
                    <span className="font-semibold text-slate-400 uppercase text-[10px] tracking-wider block">
                      Expected Effect:
                    </span>
                    <div className="text-slate-300 mt-0.5 font-mono text-[11px]">
                      Error rate ↓ • Latency baseline restored • Service health verified
                    </div>
                  </div>
                </div>

                {/* Deterministic Blast-Radius Simulation Preview */}
                {blast && (
                  <div className="bg-slate-950/50 p-3.5 rounded border border-cyan-900/40 text-xs space-y-2.5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5 text-cyan-300 font-semibold text-[11px] uppercase tracking-wider">
                        <Layers className="w-3.5 h-3.5" />
                        <span>Deterministic Blast-Radius Simulation</span>
                      </div>
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold border ${
                        blast.status === 'SAFE'
                          ? 'bg-emerald-950/80 text-emerald-300 border-emerald-800'
                          : blast.status === 'SAFE_WITH_WARNINGS'
                          ? 'bg-amber-950/80 text-amber-300 border-amber-800'
                          : 'bg-rose-950/80 text-rose-300 border-rose-800'
                      }`}>
                        STATUS: {blast.status}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-[11px] font-mono">
                      <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
                        <span className="text-[10px] text-slate-500 uppercase block">Directly Affected:</span>
                        <span className="text-sky-300 font-semibold">{blast.directly_affected.join(', ') || act.target}</span>
                      </div>
                      <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
                        <span className="text-[10px] text-slate-500 uppercase block">Indirectly Affected (Callers/Deps):</span>
                        <span className="text-amber-300">{blast.indirectly_affected.join(', ') || 'None'}</span>
                      </div>
                      <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
                        <span className="text-[10px] text-slate-500 uppercase block">Unaffected Components:</span>
                        <span className="text-emerald-300">{blast.unaffected_components.length} services</span>
                      </div>
                    </div>

                    {blast.warnings && blast.warnings.length > 0 && (
                      <div className="text-[11px] text-amber-300/90 flex items-start gap-1.5 bg-amber-950/30 p-2 rounded border border-amber-900/40">
                        <Info className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                        <span>{blast.warnings.join(' • ')}</span>
                      </div>
                    )}
                  </div>
                )}

                {/* Step 1: Human Approval Gate */}
                <div className="border border-slate-800 rounded p-4 bg-slate-950/40 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2 text-xs font-semibold uppercase tracking-wider text-slate-300">
                      <UserCheck className="w-4 h-4 text-indigo-400" />
                      <span>Step 1: Human Operator Authorization</span>
                    </div>
                    {act.requires_human_approval && (
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-950/80 text-amber-300 border border-amber-800 font-bold">
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
                        Status:{' '}
                        <span className={`font-semibold capitalize ${isApproved ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {act.approval_status}
                        </span>{' '}
                        by <span className="font-mono text-slate-200">{act.approved_by || 'Operator'}</span>
                      </div>
                      {act.approved_at && (
                        <div className="text-[11px] font-mono text-slate-500">
                          {new Date(act.approved_at).toLocaleString()}
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Step 2: Recovery Execution Simulation */}
                <div className="border border-slate-800 rounded p-4 bg-slate-950/40 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2 text-xs font-semibold uppercase tracking-wider text-slate-300">
                      <Play className="w-4 h-4 text-cyan-400" />
                      <span>Step 2: Pre-Execution Simulation</span>
                    </div>
                    <span className="text-[11px] font-mono text-slate-400">
                      Deterministic Environment Simulation
                    </span>
                  </div>

                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1">
                    <p className="text-xs text-slate-400 max-w-md">
                      Simulate the recovery effect on state machines and dependent systems before actual deployment.
                    </p>

                    <button
                      onClick={() => handleSimulateAndExecute(act.id)}
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

                  {/* Telemetry shift details if available */}
                  {execSim && execSim.telemetry_changes && Object.keys(execSim.telemetry_changes).length > 0 && (
                    <div className="bg-slate-950/80 p-3 rounded border border-emerald-900/40 text-[11px] font-mono space-y-1">
                      <div className="text-emerald-400 font-semibold flex items-center gap-1 mb-1">
                        <CheckCircle className="w-3.5 h-3.5" />
                        <span>Simulated Telemetry Shifts (Outcome: {execSim.status}):</span>
                      </div>
                      {Object.entries(execSim.telemetry_changes).map(([k, v]) => (
                        <div key={k} className="text-slate-300">
                          <span className="text-slate-500">{k}:</span> {String(v)}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Step 3: Record Actual Recovery Outcome */}
                <div className="border border-slate-800 rounded p-4 bg-slate-950/40 space-y-3">
                  <div className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                    Step 3: Actual Outcome Verification
                  </div>

                  {act.outcome ? (
                    <div className="bg-slate-900/80 p-2.5 rounded text-xs flex items-center justify-between">
                      <div>
                        <span className="text-[10px] text-slate-500 uppercase block">Recorded Outcome:</span>
                        <span className="text-emerald-300 font-mono mt-0.5 font-semibold">{act.outcome}</span>
                      </div>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800">
                        VERIFIED OUTCOME
                      </span>
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
