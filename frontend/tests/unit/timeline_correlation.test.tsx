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
});
