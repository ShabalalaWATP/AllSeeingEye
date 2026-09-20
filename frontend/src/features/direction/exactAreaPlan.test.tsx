import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import { aoi, plan, planEvidence } from '@/test/fixtures.direction';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
import { researchAreaGeometry } from '@/lib/map/researchAreaGeometry';

const exactArea = {
  ...aoi,
  kind: 'geometry',
  bbox: null,
  research_area: {
    geometry: researchAreaGeometry('polygon', [
      [0, 0],
      [2, 0],
      [0, 2],
    ]),
    sha256: 'a'.repeat(64),
  },
};

it('offers supported standalone area research instead of a lossy plan assessment', async () => {
  server.use(
    http.get('/api/direction/plans/:id', () =>
      HttpResponse.json({ ...planEvidence, aoi: exactArea }),
    ),
  );
  renderApp(`/direction/plans/${plan.id}`, 'user');
  await screen.findByRole('heading', { name: 'Kharkiv axis' });
  expect(screen.queryByRole('link', { name: 'Generate assessment' })).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Research area' })).toBeInTheDocument();
  expect(screen.getByText(/plan requirements are not transferred/i)).toBeInTheDocument();
});

it('explains the report boundary before saving a polygon collection plan', async () => {
  server.use(http.get('/api/direction/aois', () => HttpResponse.json({ items: [exactArea] })));
  const { user } = renderApp('/direction', 'user');
  const form = await screen.findByRole('form', { name: 'New collection plan' });
  await within(form).findByRole('option', { name: aoi.name });
  await user.selectOptions(within(form).getByLabelText('Area'), aoi.id);
  expect(
    within(form).getByText(/exact-shape plans support evidence matching/i),
  ).toBeInTheDocument();
});
