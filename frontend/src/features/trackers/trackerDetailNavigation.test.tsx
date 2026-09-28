import { act, screen, waitFor } from '@testing-library/react';
import { http } from 'msw';
import { describe, expect, it } from 'vitest';

import { apiError } from '@/test/handlers';
import { conflictDetail, hazardCard } from '@/test/fixtures.trackers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

function conflictNamed(name: string) {
  const { card } = conflictDetail;
  return Response.json({
    ...conflictDetail,
    card: { ...card, conflict: { ...card.conflict, name } },
  });
}

/** Holds each conflict response until the test releases it, so arrivals can be reordered. */
function holdConflicts() {
  const held = new Map<string, (response: Response) => void>();
  server.use(
    http.get(
      '/api/trackers/conflicts/:id',
      ({ params }) => new Promise<Response>((resolve) => held.set(String(params.id), resolve)),
    ),
  );
  return async (id: string, response: Response) => {
    await waitFor(() => expect(held.has(id)).toBe(true));
    held.get(id)?.(response);
  };
}

const heading = (name: string) => screen.queryByRole('heading', { name, level: 1 });

describe('tracker detail navigation', () => {
  it('keeps each conflict with its own route, whatever order responses arrive in', async () => {
    const release = holdConflicts();
    const { router } = renderApp('/trackers/conflicts/alpha', 'user');
    await waitFor(() => expect(screen.getByText('Loading conflict')).toBeVisible());
    await act(() => router.navigate('/trackers/conflicts/bravo'));
    await release('bravo', conflictNamed('Bravo conflict'));
    expect(await screen.findByRole('heading', { name: 'Bravo conflict' })).toBeVisible();

    // The superseded request settles late and must not replace the current record.
    await release('alpha', conflictNamed('Alpha conflict'));
    await expect(
      screen.findByRole('heading', { name: 'Alpha conflict' }, { timeout: 300 }),
    ).rejects.toThrow();
    expect(heading('Bravo conflict')).toBeVisible();

    // A new route hides the old record at once, then shows its own failure.
    await act(() => router.navigate('/trackers/conflicts/charlie'));
    expect(heading('Bravo conflict')).not.toBeInTheDocument();
    expect(screen.getByText('Loading conflict')).toBeVisible();
    await release('charlie', apiError(503, 'unavailable', 'Conflict tracker unavailable'));
    expect(await screen.findByRole('alert')).toHaveTextContent('Conflict tracker unavailable');
    expect(heading('Bravo conflict')).not.toBeInTheDocument();
  });

  it('shows the current hazard error instead of the previous hazard', async () => {
    const { router } = renderApp('/trackers/disasters/earthquake', 'user');
    expect(await screen.findByRole('heading', { name: hazardCard.title })).toBeVisible();
    await act(() => router.navigate('/trackers/disasters/flood'));
    expect(await screen.findByRole('alert')).toHaveTextContent('Unknown hazard');
    expect(heading(hazardCard.title)).not.toBeInTheDocument();
  });
});
