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

  approveRecoveryAction: (actionId: string, payload: ApprovalRequest): Promise<RecoveryActionResponse> =>
    request<RecoveryActionResponse>(`/api/v1/recovery-actions/${encodeURIComponent(actionId)}/approve`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  simulateRecoveryAction: (actionId: string): Promise<RecoveryActionResponse> =>
    request<RecoveryActionResponse>(`/api/v1/recovery-actions/${encodeURIComponent(actionId)}/simulate`, {
      method: 'POST',
    }),

  recordRecoveryOutcome: (actionId: string, outcome: string): Promise<RecoveryActionResponse> =>
    request<RecoveryActionResponse>(
      `/api/v1/recovery-actions/${encodeURIComponent(actionId)}/outcome?outcome=${encodeURIComponent(outcome)}`,
      {
        method: 'POST',
      }
    ),

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
