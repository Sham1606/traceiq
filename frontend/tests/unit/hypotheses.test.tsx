import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { HypothesesSection } from '../../src/features/rca/HypothesesSection';
import { HypothesisItem } from '../../src/types/api';

const mockHypotheses: HypothesisItem[] = [
  {
    id: 'hyp-01',
    title: 'Application regression introduced by a recent deployment',
    explanation: 'A deployment event precedes the incident window. 4 anomalies observed.',
    evidence_ids: ['ev-01', 'ev-02'],
    supporting_evidence_ids: ['ev-01'],
    contradicting_evidence_ids: [],
    strength: 'strongly_supported',
  },
  {
    id: 'hyp-02',
    title: 'Database connection pool exhaustion',
    explanation: 'Database metrics show elevated wait events.',
    evidence_ids: ['ev-03'],
    supporting_evidence_ids: ['ev-03'],
    contradicting_evidence_ids: ['ev-04'],
    strength: 'weakly_supported',
  },
];

describe('HypothesesSection', () => {
  it('renders competing hypotheses with evidence linkages', () => {
    render(<HypothesesSection hypotheses={mockHypotheses} />);

    expect(screen.getByText('Application regression introduced by a recent deployment')).toBeInTheDocument();
    expect(screen.getByText('Database connection pool exhaustion')).toBeInTheDocument();
    expect(screen.getByText('STRONGLY SUPPORTED')).toBeInTheDocument();
    expect(screen.getByText('WEAKLY SUPPORTED')).toBeInTheDocument();
    expect(screen.getByText('Leading Candidate')).toBeInTheDocument();
    expect(screen.getByText('ev-01')).toBeInTheDocument();
  });

  it('renders placeholder when hypotheses list is empty', () => {
    render(<HypothesesSection hypotheses={[]} />);
    expect(screen.getByText(/No hypotheses generated yet/i)).toBeInTheDocument();
  });
});
