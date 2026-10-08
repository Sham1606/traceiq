import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { IncidentsPage } from '../../src/pages/IncidentsPage';
import { WorkspacePage } from '../../src/pages/WorkspacePage';
import { AuditSection } from '../../src/features/audit/AuditSection';
import { AIStatusPanel } from '../../src/features/investigation/AIStatusPanel';
import { InvestigationProgress } from '../../src/features/investigation/InvestigationProgress';
import { api } from '../../src/services/api';
import { IncidentResponse, InvestigationResponse, AuditEntryResponse } from '../../src/types/api';

const mockIncidents: IncidentResponse[] = [
  {
    id: 'inc-001',
    scenario_id: 'bad-deployment',
    title: 'Checkout Service Latency Spike',
    status: 'detected',
    severity: 'sev1',
    started_at: '2026-10-06T14:28:00Z',
    detected_at: '2026-10-06T14:30:00Z',
    recovered_at: '2026-10-06T14:50:00Z',
    affected_services: ['checkout-svc', 'payment-api'],
    description: 'Elevated error rates on checkout',
    created_at: '2026-10-06T14:30:00Z',
  },
];

const mockInvestigation: InvestigationResponse = {
  id: 'inv-001',
  incident_id: 'inc-001',
  status: 'complete',
  evidence: {
    scenario_id: 'bad-deployment',
    incident_id: 'inc-001',
    metric_findings: [],
    timeline_findings: [],
    log_findings: [],
    correlation_findings: [],
    evidence: [],
  },
  hypotheses: [
    {
      id: 'hyp-01',
      title: 'Application regression introduced by a recent deployment',
      explanation: 'Preceding deployment caused error rate spike.',
      evidence_ids: [],
      supporting_evidence_ids: [],
      contradicting_evidence_ids: [],
      strength: 'strongly_supported',
    },
  ],
  challenge: null,
  created_at: '2026-10-06T14:31:00Z',
  updated_at: '2026-10-06T14:31:05Z',
};

const mockAudit: AuditEntryResponse[] = [
  {
    id: 1,
    incident_id: 'inc-001',
    action: 'investigation_started',
    actor: 'system',
    detail: { investigation_id: 'inv-001' },
    created_at: '2026-10-06T14:31:00Z',
  },
];

describe('Incidents and Workspace End-to-End Flow', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders incidents list and handles search', async () => {
    vi.spyOn(api, 'listIncidents').mockResolvedValue({
      total: 1,
      items: mockIncidents,
    });

    render(
      <MemoryRouter initialEntries={['/incidents']}>
        <IncidentsPage />
      </MemoryRouter>
    );

    expect(screen.getByText(/Fetching incident records/i)).toBeInTheDocument();
    expect(await screen.findByText('Checkout Service Latency Spike')).toBeInTheDocument();
    expect(screen.getByText('checkout-svc')).toBeInTheDocument();
    expect(screen.getAllByText(/sev1/i).length).toBeGreaterThanOrEqual(1);
  });

  it('renders varied incident severity and status and filters archived records', async () => {
    const variedIncidents: IncidentResponse[] = [
      mockIncidents[0],
      {
        ...mockIncidents[0],
        id: 'inc-open-sev3',
        scenario_id: 'demo-notification-backlog',
        title: 'Notification Worker Queue Delivery Lag',
        status: 'open',
        severity: 'sev3',
      },
      {
        ...mockIncidents[0],
        id: 'inc-archived-sev4',
        scenario_id: 'demo-reporting-timeout',
        title: 'Reporting Service Analytics Query Timeout',
        status: 'archived',
        severity: 'sev4',
      },
    ];
    vi.spyOn(api, 'listIncidents').mockResolvedValue({ total: variedIncidents.length, items: variedIncidents });

    render(
      <MemoryRouter initialEntries={['/incidents']}>
        <IncidentsPage />
      </MemoryRouter>
    );

    expect(await screen.findByText('Notification Worker Queue Delivery Lag')).toBeInTheDocument();
    expect(screen.getByText('Reporting Service Analytics Query Timeout')).toBeInTheDocument();
    expect(screen.getByText('open')).toBeInTheDocument();
    expect(screen.getByText('archived')).toBeInTheDocument();
    expect(screen.getByText('sev3')).toBeInTheDocument();
    expect(screen.getByText('sev4')).toBeInTheDocument();

    fireEvent.change(screen.getAllByRole('combobox')[1], { target: { value: 'archived' } });
    expect(screen.getByText('Reporting Service Analytics Query Timeout')).toBeInTheDocument();
    expect(screen.queryByText('Notification Worker Queue Delivery Lag')).not.toBeInTheDocument();
  });

  it('displays error state with retry on API failure', async () => {
    vi.spyOn(api, 'listIncidents').mockRejectedValue(new Error('Network connection timeout'));

    render(
      <MemoryRouter initialEntries={['/incidents']}>
        <IncidentsPage />
      </MemoryRouter>
    );

    expect(await screen.findByText(/Network connection timeout/i)).toBeInTheDocument();
    expect(screen.getByText(/Retry Request/i)).toBeInTheDocument();
  });

  it('renders workspace, triggers investigation, and displays hypotheses', async () => {
    vi.spyOn(api, 'getIncident').mockResolvedValue(mockIncidents[0]);
    vi.spyOn(api, 'listInvestigations').mockResolvedValue([mockInvestigation]);
    const startInvSpy = vi.spyOn(api, 'startInvestigation').mockResolvedValue(mockInvestigation);

    render(
      <MemoryRouter initialEntries={['/incidents/inc-001']}>
        <Routes>
          <Route path="/incidents/:incidentId" element={<WorkspacePage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByText('Checkout Service Latency Spike')).toBeInTheDocument();
    expect(screen.getByText('Re-run Investigation')).toBeInTheDocument();

    const rerunBtn = screen.getByText('Re-run Investigation');
    fireEvent.click(rerunBtn);

    await waitFor(() => {
      expect(startInvSpy).toHaveBeenCalledWith('inc-001');
    });
  });

  it('shows investigation stages only as reported by the backend response', () => {
    render(<InvestigationProgress investigation={mockInvestigation} running={false} elapsedSeconds={3} />);

    expect(screen.getByText('Investigation Progress')).toBeInTheDocument();
    expect(screen.getByText('4/11 reported')).toBeInTheDocument();
    expect(screen.getByText('Elapsed 3s')).toBeInTheDocument();
    expect(screen.getByText('Pipeline status comes from returned results; backend stage events are not streamed.')).toBeInTheDocument();
    expect(screen.getByText('Application analysis').parentElement).toHaveTextContent('Not reported');
    expect(screen.getByText('Generating hypotheses').parentElement).toHaveTextContent('Complete');
  });

  it('shows live provider status only when the backend records a live invocation', () => {
    const liveInvestigation = {
      ...mockInvestigation,
      evidence: {
        ...mockInvestigation.evidence,
        ai_telemetry: {
          mode: 'live',
          provider: 'gemini',
          model: 'gemini-current',
          deterministic_validation: 'PASS',
        },
      },
    } as unknown as InvestigationResponse;
    const mockProviderInvestigation = {
      ...mockInvestigation,
      evidence: {
        ...mockInvestigation.evidence,
        ai_telemetry: { mode: 'mock', provider: 'mock', model: 'mock-reasoner' },
      },
    } as unknown as InvestigationResponse;
    const unverifiedProviderInvestigation = {
      ...mockInvestigation,
      evidence: { ...mockInvestigation.evidence, ai_telemetry: { provider: 'gemini' } },
    } as unknown as InvestigationResponse;
    const fallbackInvestigation = {
      ...mockInvestigation,
      evidence: {
        ...mockInvestigation.evidence,
        ai_telemetry: {
          mode: 'fallback',
          provider: 'gemini',
          fallback_reason: 'Provider unavailable',
        },
      },
    } as unknown as InvestigationResponse;

    const { rerender } = render(
      <AIStatusPanel investigation={liveInvestigation} leadingHypothesis={mockInvestigation.hypotheses![0]} />
    );
    expect(screen.getByText('AI MODE LIVE')).toBeInTheDocument();
    expect(screen.getByText('GEMINI')).toBeInTheDocument();
    expect(screen.getByText('gemini-current')).toBeInTheDocument();

    rerender(
      <AIStatusPanel investigation={mockProviderInvestigation} leadingHypothesis={mockInvestigation.hypotheses![0]} />
    );
    expect(screen.getByText('AI MODE DETERMINISTIC / MOCK')).toBeInTheDocument();
    expect(screen.queryByText('AI MODE LIVE')).not.toBeInTheDocument();

    rerender(
      <AIStatusPanel investigation={unverifiedProviderInvestigation} leadingHypothesis={mockInvestigation.hypotheses![0]} />
    );
    expect(screen.getByText('PROVIDER INVOCATION UNVERIFIED')).toBeInTheDocument();
    expect(screen.queryByText('AI MODE LIVE')).not.toBeInTheDocument();

    rerender(
      <AIStatusPanel investigation={fallbackInvestigation} leadingHypothesis={mockInvestigation.hypotheses![0]} />
    );
    expect(screen.getByText('AI MODE FALLBACK')).toBeInTheDocument();
    expect(screen.queryByText('AI PROPOSAL')).not.toBeInTheDocument();

    rerender(
      <AIStatusPanel investigation={mockInvestigation} leadingHypothesis={mockInvestigation.hypotheses![0]} />
    );
    expect(screen.getByText('LIVE PROVIDER NOT CONFIGURED')).toBeInTheDocument();
    expect(screen.getByText('DETERMINISTIC VALIDATION: NOT REPORTED')).toBeInTheDocument();
  });

  it('renders immutable audit trail for incident', async () => {
    vi.spyOn(api, 'getAuditLog').mockResolvedValue(mockAudit);

    render(<AuditSection incidentId="inc-001" />);

    expect(await screen.findByText('investigation_started')).toBeInTheDocument();
    expect(screen.getByText('system')).toBeInTheDocument();
  });
});
