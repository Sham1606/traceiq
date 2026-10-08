import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TimelineSection } from '../../src/features/findings/TimelineSection';
import { CorrelationSection } from '../../src/features/findings/CorrelationSection';
import { TimelineFinding, CorrelationFinding } from '../../src/types/api';

const mockTimeline: TimelineFinding[] = [
  {
    id: 'tl-1',
    event_type: 'deployment',
    event_id: 'dep-v4.2',
    timestamp: '2026-10-06T14:28:00Z',
    related_event_ids: [],
    ordering: 't0 - 5m',
    summary: 'Production deployment service-v4.2 completed',
  },
  {
    id: 'tl-2',
    event_type: 'log',
    event_id: 'err-500',
    timestamp: '2026-10-06T14:32:00Z',
    related_event_ids: ['tl-1'],
    ordering: 't0 - 1m',
    summary: 'Error rate elevated above threshold',
  },
];

const mockCorrelations: CorrelationFinding[] = [
  {
    id: 'corr-1',
    category: 'deployment',
    source_ids: ['dep-v4.2', 'err-500'],
    services: ['web-api', 'payment-svc'],
    summary: 'Deployment v4.2 directly precedes error spike across web-api',
    supports: ['deployment_regression'],
    contradicts: [],
  },
];

describe('Timeline and Correlation Sections', () => {
  it('renders chronological timeline events', () => {
    render(<TimelineSection timeline={mockTimeline} />);
    expect(screen.getByText('DEPLOYMENT')).toBeInTheDocument();
    expect(screen.getByText('Production deployment service-v4.2 completed')).toBeInTheDocument();
    expect(screen.getByText('LOG SPIKE')).toBeInTheDocument();
  });

  it('renders causal correlation chains', () => {
    render(<CorrelationSection correlations={mockCorrelations} />);
    expect(screen.getByText(/Deployment v4.2 directly precedes error spike/i)).toBeInTheDocument();
    expect(screen.getByText('web-api')).toBeInTheDocument();
    expect(screen.getByText('payment-svc')).toBeInTheDocument();
  });

  it('renders every backend-provided causal step and evidence reference', () => {
    render(
      <CorrelationSection
        correlations={mockCorrelations}
        aiCorrelations={[
          {
            correlation_id: 'ai-corr-1',
            correlated_domains: ['application'],
            false_lead_domains: [],
            contradicting_evidence_ids: [],
            causal_sequence: [
              '[DEPLOYMENT] Deployment v4.2 released',
              '[METRIC] Error rate increased',
              '[LOG] Upstream timeout observed',
              '[APPLICATION] Payment service degraded',
              '[APPLICATION] Checkout requests failed',
            ],
            shared_evidence_ids: ['E-101', 'E-204'],
            summary: 'Backend correlation summary',
            strength: 'supported',
          },
        ]}
      />
    );

    const sequenceRegion = screen.getByLabelText('Causal sequences');
    const sequenceGrid = sequenceRegion.querySelector('.grid');
    expect(sequenceGrid).toHaveClass('grid-cols-1', 'sm:grid-cols-2', 'xl:grid-cols-3');
    expect(sequenceGrid).not.toHaveClass('overflow-hidden', 'overflow-x-auto');
    expect(screen.getByText('05')).toBeInTheDocument();
    expect(screen.getByText('Checkout requests failed')).toBeInTheDocument();
    expect(screen.getByText('Upstream timeout observed')).toBeInTheDocument();
    expect(screen.getByText('E-101')).toBeInTheDocument();
    expect(screen.getByText('E-204')).toBeInTheDocument();
  });

  it('does not invent causal steps when the backend provides no sequence', () => {
    render(<CorrelationSection correlations={mockCorrelations} aiCorrelations={[]} />);

    expect(screen.queryByText('Causal sequence')).not.toBeInTheDocument();
    expect(screen.queryByText(/downstream degradation signal/i)).not.toBeInTheDocument();
    expect(screen.getByText(/Deployment v4.2 directly precedes error spike/i)).toBeInTheDocument();
  });

  it('renders a returned causal sequence when deterministic correlation findings are empty', () => {
    render(
      <CorrelationSection
        correlations={null}
        aiCorrelations={[
          {
            summary: 'Correlation timeline sequence',
            causal_sequence: ['[LOG] Timeout occurred at 14:32Z'],
          },
        ]}
      />
    );

    expect(screen.getByText('log')).toBeInTheDocument();
    expect(screen.getByText('Timeout occurred at 14:32Z')).toBeInTheDocument();
    expect(screen.getByText(/Deterministic engine/)).toBeInTheDocument();
  });
});
