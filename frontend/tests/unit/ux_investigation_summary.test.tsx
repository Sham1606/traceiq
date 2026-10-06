import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { InvestigationSummary } from '../../src/features/investigation/InvestigationSummary';
import { ChallengeSection } from '../../src/features/rca/ChallengeSection';
import { HistoricalMemorySection } from '../../src/features/investigation/HistoricalMemorySection';
import { RecoverySection } from '../../src/features/recovery/RecoverySection';
import { api } from '../../src/services/api';
import { IncidentResponse, InvestigationResponse } from '../../src/types/api';

const mockIncident: IncidentResponse = {
  id: 'inc-001',
  scenario_id: 'bad-deployment',
  title: 'Payment API regression after deployment',
  status: 'recovered',
  severity: 'sev2',
  started_at: '2026-10-06T14:28:00Z',
  detected_at: '2026-10-06T14:30:00Z',
  recovered_at: '2026-10-06T14:50:00Z',
  affected_services: ['api-gateway', 'payment-service'],
  description: 'Degradation following deployment release',
  created_at: '2026-10-06T14:30:00Z',
};

const mockInvestigation: InvestigationResponse = {
  id: 'inv-001',
  incident_id: 'inc-001',
  status: 'complete',
  evidence: {
    scenario_id: 'bad-deployment',
    incident_id: 'inc-001',
    metric_findings: [
      {
        id: 'mf-1',
        service: 'payment-service',
        metric: 'error_rate',
        baseline_mean: 0.002,
        incident_mean: 0.145,
        delta: 0.143,
        delta_ratio: 71.5,
        direction: 'up',
        anomaly: true,
        source_ids: ['src-1'],
        summary: 'payment-service error_rate elevated by 7150%',
      },
    ],
    timeline_findings: [
      {
        id: 'tl-1',
        event_type: 'deployment',
        event_id: 'dep-v4.2',
        timestamp: '2026-10-06T14:26:00Z',
        related_event_ids: [],
        ordering: 't0 - 4m',
        summary: 'Production deployment release v4.2 applied',
      },
    ],
    log_findings: [
      {
        id: 'log-1',
        service: 'payment-service',
        event_type: 'NullPointerException',
        count: 55,
        error_or_warn_count: 55,
        source_ids: [],
        summary: '55 NullPointerExceptions in PaymentHandler',
      },
    ],
    correlation_findings: [
      {
        id: 'corr-1',
        category: 'deployment',
        source_ids: ['dep-v4.2', 'mf-1'],
        services: ['api-gateway', 'payment-service'],
        summary: 'Deployment directly correlated with error rate increase',
        supports: ['deployment_regression'],
        contradicts: [],
      },
    ],
    evidence: [
      {
        id: 'ev-1',
        incident_id: 'inc-001',
        evidence_type: 'metric',
        source_id: 'mf-1',
        summary: 'Critical error rate jump',
        strength: 'strongly_supported',
        supports: ['deployment_regression'],
        contradicts: [],
      },
    ],
  },
  hypotheses: [
    {
      id: 'hyp-01',
      title: 'Application regression introduced by a recent deployment',
      explanation: 'Recent deployment coincides with error rate spike.',
      evidence_ids: ['ev-1'],
      supporting_evidence_ids: ['ev-1'],
      contradicting_evidence_ids: [],
      strength: 'strongly_supported',
    },
  ],
  challenge: null,
  created_at: '2026-10-06T14:31:00Z',
  updated_at: '2026-10-06T14:31:05Z',
};

describe('Phase 4.5 Investigation UX & Information Hierarchy', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders top-level Investigation Summary with leading hypothesis, stats, and causal flow', () => {
    render(
      <InvestigationSummary
        incident={mockIncident}
        investigation={mockInvestigation}
      />
    );

    // Executive summary title & state
    expect(screen.getByText(/Investigation Executive Summary/i)).toBeInTheDocument();
    expect(screen.getByText(/Deterministic Evidence Synthesis/i)).toBeInTheDocument();
    expect(screen.getByText(/Deterministic Analysis Complete/i)).toBeInTheDocument();

    // Leading hypothesis
    expect(screen.getByText('Application regression introduced by a recent deployment')).toBeInTheDocument();
    expect(screen.getByText('STRONGLY SUPPORTED')).toBeInTheDocument();

    // Causal chain
    expect(screen.getByText(/Correlated Causal Sequence/i)).toBeInTheDocument();
    expect(screen.getByText('DEPLOYMENT')).toBeInTheDocument();

    // What Changed summary
    expect(screen.getByText(/What Changed\? \(Observed Telemetry Shifts\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Production deployment logged in timeline/i)).toBeInTheDocument();
  });

  it('verifies Challenge RCA displays honest pending state without fake AI claims', () => {
    render(
      <ChallengeSection
        challenge={null}
        leadingHypothesis={mockInvestigation.hypotheses![0]}
      />
    );

    expect(screen.getByText(/Adversarial Challenge RCA Protocol/i)).toBeInTheDocument();
    expect(screen.getByText(/STATUS: PENDING — PHASE 5 AI LAYER/i)).toBeInTheDocument();
    expect(screen.getByText(/challenge: null/i)).toBeInTheDocument();
    expect(screen.getByText(/Attempt to disprove the leading hypothesis/i)).toBeInTheDocument();
  });

  it('verifies Historical Memory prominent disclaimer is displayed', async () => {
    vi.spyOn(api, 'searchMemory').mockResolvedValue({
      query_fingerprint: 'test-fp',
      matches: [],
    });

    render(<HistoricalMemorySection initialFingerprint="test-fp" />);

    expect(screen.getByText(/Historical Memory Rule/i)).toBeInTheDocument();
    expect(screen.getByText(/Historical matches are/i)).toBeInTheDocument();
    expect(screen.getByText(/supporting context only/i)).toBeInTheDocument();
    expect(await screen.findByText(/No Matching Historical Incidents/i)).toBeInTheDocument();
  });

  it('verifies Recovery Section enforces mandatory human approval gate', async () => {
    vi.spyOn(api, 'listRecoveryActions').mockResolvedValue([]);

    render(
      <RecoverySection
        investigationId="inv-001"
        leadingHypothesis={mockInvestigation.hypotheses![0]}
      />
    );

    expect(
      screen.getByText(/TRACEIQ never performs autonomous remediation/i)
    ).toBeInTheDocument();
    expect(await screen.findByText(/No Recovery Actions Formulated Yet/i)).toBeInTheDocument();
  });
});
