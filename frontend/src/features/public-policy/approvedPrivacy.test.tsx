import { screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { renderApp } from '@/test/render';

vi.mock('virtual:policy-approval', () => ({ default: true }));
vi.mock('./privacy.json', async (original) => {
  const { default: notice } = await original<{
    default: {
      operator: Record<string, string | null>;
      purposes: { lawfulBasis: string | null }[];
    };
  }>();
  return {
    default: {
      ...notice,
      version: '2026-10-11-fixture',
      operator: Object.fromEntries(
        Object.keys(notice.operator).map((key) => [key, `Confirmed fixture ${key}`]),
      ),
      purposes: notice.purposes.map((purpose) => ({ ...purpose, lawfulBasis: 'Fixture basis' })),
    },
  };
});

describe('approved privacy notice', () => {
  it('shows reviewed facts without instructions to finish the draft', async () => {
    renderApp('/privacy', 'anonymous');
    await screen.findByRole('heading', { name: 'Privacy and storage' });
    expect(screen.getByText('Confirmed fixture retentionCriteria')).toBeInTheDocument();
    expect(screen.getByText('Confirmed fixture complaintsProcedure')).toBeInTheDocument();
    expect(screen.queryByLabelText('Draft notice')).not.toBeInTheDocument();
    expect(screen.queryByText(/decisions the installation operator must confirm/)).toBeNull();
    expect(screen.queryByText(/not a complete approved retention policy/)).toBeNull();
    expect(screen.queryByText(/operator must confirm the separate/)).toBeNull();
    expect(
      screen.queryByText(/installation-specific retention decision is still required/),
    ).toBeNull();
  });

  it('gives the right to object a separate, findable section', async () => {
    renderApp('/privacy', 'anonymous');
    await screen.findByRole('heading', { name: 'Your right to object' });
    expect(screen.getByRole('link', { name: 'Your right to object' })).toHaveAttribute(
      'href',
      '#object',
    );
    expect(screen.getByRole('region', { name: 'Your right to object' })).toHaveTextContent(
      /legitimate interests or a public task/,
    );
  });

  it('links the approved notice from the request procedure without stale draft wording', async () => {
    renderApp('/privacy/requests', 'anonymous');
    await screen.findByRole('heading', { name: 'Personal-data requests' });
    expect(screen.queryByText(/draft privacy notice/)).toBeNull();
    expect(screen.getByText(/controller and complaints details are in/)).toBeInTheDocument();
    expect(
      screen.getByText(/There is no complete account-wide export or erasure action/),
    ).toBeVisible();
  });
});
