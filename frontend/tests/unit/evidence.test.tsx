import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { EvidenceSection } from '../../src/features/evidence/EvidenceSection';
import { EvidenceBundle } from '../../src/types/api';

const mockEvidenceBundle: EvidenceBundle = {
  scenario_id: 'bad-deployment',
  incident_id: 'inc-001',
  metric_findings: [
    {
      id: 'metric-01',
      service: 'web-api',
      metric: 'error_rate',
      baseline_mean: 0.005,
      incident_mean: 0.125,
      delta: 0.12,
      delta_ratio: 24.0,
      direction: 'up',
      anomaly: true,
      source_ids: ['src-1'],
      summary: 'Elevated HTTP 500 error rate in web-api',
    },
  ],
  timeline_findings: [],
  log_findings: [
    {
      id: 'log-01',
      service: 'web-api',
      event_type: 'NullPointerException',
      count: 42,
      error_or_warn_count: 42,
      source_ids: ['log-src-1'],
      summary: 'Recurring NullPointerException in AuthFilter',
    },
  ],
  correlation_findings: [],
  evidence: [
    {
      id: 'ev-metric-01',
      incident_id: 'inc-001',
      evidence_type: 'metric',
      source_id: 'metric-01',
      summary: 'Elevated HTTP 500 error rate in web-api',
      strength: 'strongly_supported',
      supports: ['error_rate'],
      contradicts: [],
    },
  ],
};

describe('EvidenceSection', () => {
  it('renders metric anomalies, log findings, and evidence items', () => {
    render(<EvidenceSection evidence={mockEvidenceBundle} />);

    expect(screen.getByText('web-api')).toBeInTheDocument();
    expect(screen.getByText('error_rate')).toBeInTheDocument();
    expect(screen.getByText('ANOMALY')).toBeInTheDocument();
    expect(screen.getByText('STRONGLY SUPPORTED')).toBeInTheDocument();
    expect(screen.getAllByText('Elevated HTTP 500 error rate in web-api').length).toBeGreaterThanOrEqual(1);
  });

  it('renders empty message when no evidence bundle is provided', () => {
    render(<EvidenceSection evidence={null} />);
    expect(
      screen.getByText(/No evidence bundle available/i)
    ).toBeInTheDocument();
  });
});
