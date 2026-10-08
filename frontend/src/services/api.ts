import {
  IncidentList,
  IncidentResponse,
  InvestigationResponse,
  RecoveryActionResponse,
  RecoveryActionCreate,
  ApprovalRequest,
  AuditEntryResponse,
  MemorySearchResponse,
  IncidentMemoryResponse,
  HealthResponse,
  BlastRadiusSimulation,
  PostmortemDraft,
} from '../types/api';

const API_BASE = import.meta.env.VITE_API_URL || '';

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${path}`;
  const headers = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
    ...options.headers,
  };

  let res: Response;
  try {
    res = await fetch(url, { ...options, headers });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Network failure';
    throw new ApiError(`Unable to connect to TRACEIQ backend: ${msg}`, 0);
  }

  if (!res.ok) {
    let errorDetail = res.statusText;
    let data: unknown = null;
    try {
      data = await res.json();
      if (typeof data === 'object' && data !== null && 'detail' in data) {
        errorDetail = (data as { detail: string }).detail;
      }
    } catch {
      // response wasn't JSON
    }
    throw new ApiError(errorDetail || `Request failed with status ${res.status}`, res.status, data);
  }

  try {
    return (await res.json()) as T;
  } catch (err) {
    throw new ApiError('Malformed JSON received from backend', res.status, err);
  }
}

export const api = {
  // Health
  getHealth: (): Promise<HealthResponse> => request<HealthResponse>('/health'),

  // Incidents
  listIncidents: (skip = 0, limit = 50): Promise<IncidentList> =>
    request<IncidentList>(`/api/v1/incidents?skip=${skip}&limit=${limit}`),

  getIncident: (incidentId: string): Promise<IncidentResponse> =>
    request<IncidentResponse>(`/api/v1/incidents/${encodeURIComponent(incidentId)}`),

  createLiveIncident: (payload: {
    title: string;
    severity: string;
    affected_services: string[];
    description: string;
    detected_at?: string;
    started_at?: string;
    recovered_at?: string;
    evidence_items: any[];
  }): Promise<IncidentResponse> =>
    request<IncidentResponse>('/api/v1/incidents/live', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // Investigations
  startInvestigation: (incidentId: string): Promise<InvestigationResponse> =>
    request<InvestigationResponse>(`/api/v1/incidents/${encodeURIComponent(incidentId)}/investigations`, {
      method: 'POST',
    }),

  listInvestigations: (incidentId: string): Promise<InvestigationResponse[]> =>
    request<InvestigationResponse[]>(`/api/v1/incidents/${encodeURIComponent(incidentId)}/investigations`),

  getInvestigation: (investigationId: string): Promise<InvestigationResponse> =>
    request<InvestigationResponse>(`/api/v1/investigations/${encodeURIComponent(investigationId)}`),

  // Recovery Actions
  listRecoveryActions: (investigationId: string): Promise<RecoveryActionResponse[]> =>
    request<RecoveryActionResponse[]>(`/api/v1/investigations/${encodeURIComponent(investigationId)}/recovery-actions`),

  createRecoveryAction: (investigationId: string, payload: RecoveryActionCreate): Promise<RecoveryActionResponse> =>
    request<RecoveryActionResponse>(`/api/v1/investigations/${encodeURIComponent(investigationId)}/recovery-actions`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  recommendRecoveryActions: (investigationId: string): Promise<RecoveryActionResponse[]> =>
    request<RecoveryActionResponse[]>(`/api/v1/investigations/${encodeURIComponent(investigationId)}/recommend-recovery`, {
      method: 'POST',
    }),

  approveRecoveryAction: (actionId: string, payload: ApprovalRequest): Promise<RecoveryActionResponse> =>
    request<RecoveryActionResponse>(`/api/v1/recovery-actions/${encodeURIComponent(actionId)}/approve`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  simulateRecoveryAction: (actionId: string): Promise<RecoveryActionResponse> =>
    request<RecoveryActionResponse>(`/api/v1/recovery-actions/${encodeURIComponent(actionId)}/simulate`, {
      method: 'POST',
    }),

  simulateBlastRadius: (actionId: string): Promise<BlastRadiusSimulation> =>
    request<BlastRadiusSimulation>(`/api/v1/recovery-actions/${encodeURIComponent(actionId)}/blast-radius`, {
      method: 'POST',
    }),

  executeRecoverySimulation: (actionId: string): Promise<RecoveryActionResponse> =>
    request<RecoveryActionResponse>(`/api/v1/recovery-actions/${encodeURIComponent(actionId)}/execute`, {
      method: 'POST',
    }),

  recordRecoveryOutcome: (actionId: string, outcome: string): Promise<RecoveryActionResponse> =>
    request<RecoveryActionResponse>(
      `/api/v1/recovery-actions/${encodeURIComponent(actionId)}/outcome?outcome=${encodeURIComponent(outcome)}`,
      {
        method: 'POST',
      }
    ),

  // Postmortem
  createPostmortem: (investigationId: string, customNotes?: string): Promise<PostmortemDraft> =>
    request<PostmortemDraft>(`/api/v1/investigations/${encodeURIComponent(investigationId)}/postmortem`, {
      method: 'POST',
      body: JSON.stringify({ custom_notes: customNotes }),
    }),

  getPostmortem: (investigationId: string): Promise<PostmortemDraft> =>
    request<PostmortemDraft>(`/api/v1/investigations/${encodeURIComponent(investigationId)}/postmortem`),

  // Incident Memory Archival
  archiveMemory: (investigationId: string): Promise<IncidentMemoryResponse> =>
    request<IncidentMemoryResponse>(`/api/v1/investigations/${encodeURIComponent(investigationId)}/archive-memory`, {
      method: 'POST',
    }),

  // Audit
  getAuditLog: (incidentId: string): Promise<AuditEntryResponse[]> =>
    request<AuditEntryResponse[]>(`/api/v1/incidents/${encodeURIComponent(incidentId)}/audit`),

  // Memory
  searchMemory: (fingerprint: string, limit = 5): Promise<MemorySearchResponse> =>
    request<MemorySearchResponse>(
      `/api/v1/memory/search?fingerprint=${encodeURIComponent(fingerprint)}&limit=${limit}`
    ),

  getMemory: (memoryId: string): Promise<IncidentMemoryResponse> =>
    request<IncidentMemoryResponse>(`/api/v1/memory/${encodeURIComponent(memoryId)}`),
};
