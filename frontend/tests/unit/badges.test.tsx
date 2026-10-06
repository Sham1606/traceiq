import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import {
  SeverityBadge,
  EvidenceStrengthBadge,
  StatusBadge,
  ApprovalBadge,
  SimulationBadge,
} from '../../src/components/common/Badge';

describe('Common Badges', () => {
  it('renders severity badges with proper styles', () => {
    const { rerender } = render(<SeverityBadge severity="sev1" />);
    expect(screen.getByText('sev1')).toBeInTheDocument();

    rerender(<SeverityBadge severity="sev2" />);
    expect(screen.getByText('sev2')).toBeInTheDocument();
  });

  it('renders all evidence strength labels correctly without percentages', () => {
    const strengths = [
      'strongly_supported',
      'supported',
      'inconclusive',
      'weakly_supported',
      'rejected',
    ] as const;

    for (const strength of strengths) {
      const { unmount } = render(<EvidenceStrengthBadge strength={strength} />);
      const expectedText = strength.replace('_', ' ').toUpperCase();
      expect(screen.getByText(expectedText)).toBeInTheDocument();
      unmount();
    }
  });

  it('renders approval status badges', () => {
    const { rerender } = render(<ApprovalBadge status="pending" />);
    expect(screen.getByText(/pending/i)).toBeInTheDocument();

    rerender(<ApprovalBadge status="approved" />);
    expect(screen.getByText(/approved/i)).toBeInTheDocument();
  });

  it('renders simulation badges', () => {
    render(<SimulationBadge result="safe" />);
    expect(screen.getByText('Simulation: safe')).toBeInTheDocument();
  });
});
