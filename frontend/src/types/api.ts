/**
 * TypeScript types strictly mirroring FastAPI schemas in app.schemas.api
 */

export type Severity = 'sev1' | 'sev2' | 'sev3' | 'sev4';
export type IncidentStatus = 'detected' | 'investigating' | 'mitigated' | 'resolved' | string;

export interface IncidentResponse {
  id: string;
  scenario_id: string;
  title: string;
  status: IncidentStatus;
  severity: Severity;
  started_at: string;
  detected_at: string;
  recovered_at: string;
  affected_services: string[];
  description: string;
  created_at: string;
}

export interface IncidentList {
  total: number;
  items: IncidentResponse[];
}

export type EvidenceStrength =
  | 'strongly_supported'
  | 'supported'
  | 'inconclusive'
  | 'weakly_supported'
  | 'rejected';

export interface MetricFinding {
  id: string;
  service: string;
  metric: string;
  baseline_mean: number;
  incident_mean: number;
  delta: number;
  delta_ratio: number | null;
  direction: string;
  anomaly: boolean;
  source_ids: string[];
  summary: string;
}

export interface TimelineFinding {
  id: string;
  event_type: string;
  event_id: string;
  timestamp: string;
  related_event_ids: string[];
  ordering: string;
  summary: string;
}

export interface LogFinding {
  id: string;
  service: string;
  event_type: string;
  count: number;
  error_or_warn_count: number;
  source_ids: string[];
  summary: string;
}

export interface CorrelationFinding {
  id: string;
  category: string;
  source_ids: string[];
  services: string[];
  summary: string;
  supports: string[];
  contradicts: string[];
}

export interface EvidenceItem {
  id: string;
  incident_id: string;
  evidence_type: 'metric' | 'log' | 'timeline' | string;
  source_id: string;
  summary: string;
  strength: EvidenceStrength;
  supports: string[];
  contradicts: string[];
}

export interface EvidenceBundle {
  scenario_id: string;
  incident_id: string;
  metric_findings: MetricFinding[];
  timeline_findings: TimelineFinding[];
  log_findings: LogFinding[];
  correlation_findings: CorrelationFinding[];
  evidence: EvidenceItem[];
}

export interface HypothesisItem {
  id: string;
  title: string;
  explanation: string;
  evidence_ids: string[];
  supporting_evidence_ids: string[];
  contradicting_evidence_ids: string[];
  strength: EvidenceStrength;
}

export interface InvestigationResponse {
  id: string;
  incident_id: string;
  status: 'running' | 'complete' | 'failed' | string;
  evidence: EvidenceBundle | null;
  hypotheses: HypothesisItem[] | null;
  challenge: Record<string, unknown> | null;
  postmortem?: PostmortemDraft | null;
  created_at: string;
  updated_at: string;
}

export type ApprovalStatus = 'pending' | 'approved' | 'rejected' | string;
export type SimulatedResult = 'not_run' | 'safe' | 'unsafe' | 'partial' | string;

export interface BlastRadiusSimulation {
  simulation_id: string;
  recommendation_id: string;
  status: 'SAFE' | 'SAFE_WITH_WARNINGS' | 'HIGH_RISK' | 'BLOCKED' | 'INCONCLUSIVE' | string;
  target_service: string;
  directly_affected: string[];
  indirectly_affected: string[];
  unaffected_components: string[];
  dependency_impacts: string[];
  risk_level: 'low' | 'medium' | 'high' | string;
  predicted_outcome: string;
  rollback_possible: boolean;
  warnings: string[];
  validation_errors: string[];
}

export interface RecoveryExecutionSimulation {
  execution_id: string;
  recommendation_id: string;
  status: 'SUCCESS' | 'PARTIAL_SUCCESS' | 'FAILED' | 'BLOCKED' | string;
  simulated_action: string;
  telemetry_changes: Record<string, unknown>;
  remaining_symptoms: string[];
  notes: string;
  timestamp: string;
}

export interface PostmortemDraft {
  title: string;
  summary: string;
  impact_duration_minutes?: number | null;
  root_cause_analysis: string;
  causal_sequence: string[];
  remediation_summary: string;
  action_items: string[];
  evidence_references: string[];
  incident_id?: string | null;
  severity?: string | null;
  timeline?: Array<{ timestamp: string; type: string; event: string }>;
  detected_symptoms?: string[];
  investigation_summary?: string | null;
  root_cause_hypothesis_id?: string | null;
  contributing_factors?: string[];
  rejected_hypotheses?: string[];
  recovery_action_taken?: string | null;
  recovery_outcome?: string | null;
  remaining_risks?: string[];
  lessons_learned?: string[];
  prevention_recommendations?: string[];
}

export interface RecoveryActionResponse {
  id: string;
  investigation_id: string;
  action: string;
  target: string;
  rationale: string;
  requires_human_approval: boolean;
  approval_status: ApprovalStatus;
  approved_by: string | null;
  approved_at: string | null;
  simulated_result: SimulatedResult;
  outcome: string | null;
  created_at: string;
  risk_level?: 'low' | 'medium' | 'high' | string;
  action_type?: string;
  supporting_evidence_ids?: string[];
  blast_radius?: BlastRadiusSimulation | null;
  execution_simulation?: RecoveryExecutionSimulation | null;
  detail?: Record<string, unknown> | null;
}

export interface RecoveryActionCreate {
  action: string;
  target: string;
  rationale: string;
}

export interface ApprovalRequest {
  approved_by: string;
  approved: boolean;
}

export interface IncidentMemoryResponse {
  id: string;
  fingerprint: string;
  title: string;
  root_cause_category: string;
  evidence_summary: string[];
  recovery_action: string;
  recovery_outcome: string;
  scenario_id: string;
  incident_id: string;
  created_at: string;
}

export interface MemoryMatch {
  memory: IncidentMemoryResponse;
  shared_fingerprint_tokens: string[];
  match_note: string;
}

export interface MemorySearchResponse {
  query_fingerprint: string;
  matches: MemoryMatch[];
}

export interface AuditEntryResponse {
  id: number;
  incident_id: string;
  action: string;
  actor: string;
  detail: Record<string, unknown>;
  created_at: string;
}

export interface HealthResponse {
  status: 'ok' | 'degraded';
  version: string;
  db: 'ok' | 'error';
}
