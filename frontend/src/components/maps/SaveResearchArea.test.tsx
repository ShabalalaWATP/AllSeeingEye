import { render, screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import { server } from '@/test/server';
import { aoi } from '@/test/fixtures.direction';
import { applySession } from '@/test/render';
import { rectangleArea } from '@/lib/map/areaGeometry';
import { SaveResearchArea } from './SaveResearchArea';

it('saves a personal reusable dateline area with explicit enclosing-box semantics', async () => {
  applySession('user');
  let saved: unknown;
  server.use(
    http.post('/api/direction/aois', async ({ request }) => {
      saved = await request.json();
      return HttpResponse.json(aoi, { status: 201 });
    }),
  );
  render(
    <MemoryRouter>
      <SaveResearchArea area={rectangleArea({ west: 170, east: -170, south: -10, north: 10 })} />
    </MemoryRouter>,
  );
  const user = userEvent.setup();
  await user.click(screen.getByText('Save as a reusable area'));
  expect(screen.getByText(/includes any space outside your drawn shape/)).toBeInTheDocument();
  await user.type(screen.getByLabelText('Reusable area name'), 'Pacific watch');
  await user.click(screen.getByRole('button', { name: 'Save reusable area' }));
  await waitFor(() =>
    expect(saved).toMatchObject({
      name: 'Pacific watch',
      team_id: null,
      bbox: [170, -10, -170, 10],
    }),
  );
  expect(await screen.findByRole('status')).toHaveTextContent('Area saved');
});
