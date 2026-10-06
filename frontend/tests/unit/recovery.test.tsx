import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { RecoverySection } from '../../src/features/recovery/RecoverySection';
import { api } from '../../src/services/api';
import { RecoveryActionResponse } from '../../src/types/api';

const mockActions: RecoveryActionResponse[] = [
  {
    id: 'rec-01',
    investigation_id: 'inv-101',
    action: 'Rollback recent release',
    target: 'Deployment v4.2',
    rationale: 'Deployment is temporally correlated with the observed regression.',
    requires_human_approval: true,
    approval_status: 'pending',
    approved_by: null,
    approved_at: null,
    simulated_result: 'not_run',
    outcome: null,
    created_at: '2026-10-06T14:35:00Z',
  },
];

describe('RecoverySection', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders recovery action with human approval requirement', async () => {
    vi.spyOn(api, 'listRecoveryActions').mockResolvedValue(mockActions);

    render(
      <RecoverySection
        investigationId="inv-101"
        leadingHypothesis={null}
      />
    );

    expect(await screen.findByText('Rollback recent release')).toBeInTheDocument();
    expect(screen.getByText('MANDATORY HUMAN GATE')).toBeInTheDocument();
    expect(screen.getByText('Approve Action')).toBeInTheDocument();
    expect(screen.getByText('Reject')).toBeInTheDocument();
  });

  it('handles human approval execution', async () => {
    vi.spyOn(api, 'listRecoveryActions').mockResolvedValue(mockActions);
    const approveSpy = vi.spyOn(api, 'approveRecoveryAction').mockResolvedValue({
      ...mockActions[0],
      approval_status: 'approved',
      approved_by: 'Incident Commander',
      approved_at: '2026-10-06T14:36:00Z',
    });

    render(
      <RecoverySection
        investigationId="inv-101"
        leadingHypothesis={null}
      />
    );

    const approveButton = await screen.findByText('Approve Action');
    fireEvent.click(approveButton);

    await waitFor(() => {
      expect(approveSpy).toHaveBeenCalledWith('rec-01', {
        approved_by: 'Incident Commander',
        approved: true,
      });
    });
  });
});
