import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import { aoi, schedule } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

async function openAreaForm() {
  const { user } = renderApp('/subscriptions', 'user');
  const form = within(await screen.findByRole('form', { name: 'New subscription' }));
  await user.type(form.getByLabelText('Subscription name'), 'Pacific update');
  await user.type(form.getByLabelText('Question'), 'What changed in this area?');
  await user.click(form.getByRole('button', { name: 'Choose a conflict, disaster or saved area' }));
  await form.findByLabelText('Saved area');
  return { user, form };
}

it('retains an antimeridian area as short polygons instead of crossing Greenwich', async () => {
  let captured: unknown;
  server.use(
    http.get('/api/direction/aois', () =>
      HttpResponse.json({ items: [{ ...aoi, bbox: [170, -10, -170, 10] }] }),
    ),
    http.post('/api/schedules', async ({ request }) => {
      captured = await request.json();
      return HttpResponse.json(schedule, { status: 201 });
    }),
  );
  const { user, form } = await openAreaForm();
  await user.selectOptions(form.getByLabelText('Saved area'), aoi.id);
  await user.click(form.getByRole('checkbox', { name: /^Allow source providers/ }));
  await user.click(form.getByRole('button', { name: 'Create subscription' }));
  await waitFor(() =>
    expect(captured).toMatchObject({
      research_area: {
        geometry: {
          type: 'FeatureCollection',
          features: [
            {
              geometry: {
                type: 'MultiPolygon',
                coordinates: [
                  [
                    [
                      [170, -10],
                      [180, -10],
                      [180, 10],
                      [170, 10],
                      [170, -10],
                    ],
                  ],
                  [
                    [
                      [-180, -10],
                      [-170, -10],
                      [-170, 10],
                      [-180, 10],
                      [-180, -10],
                    ],
                  ],
                ],
              },
            },
          ],
        },
      },
    }),
  );
});

it('requires explicit boundary removal before switching to existing live evidence', async () => {
  const { user, form } = await openAreaForm();
  await user.selectOptions(form.getByLabelText('Saved area'), aoi.id);
  const live = form.getByRole('checkbox', { name: /^Use existing live evidence only/ });
  expect(live).toBeDisabled();
  expect(form.getByText('Clear the fixed boundary first to change collection mode.')).toBeVisible();
  await user.click(form.getByRole('button', { name: 'Clear boundary' }));
  expect(live).toBeEnabled();
  await user.click(live);
  expect(live).toBeChecked();
});

it('does not offer saved country areas exceeding the subscription country limit', async () => {
  server.use(
    http.get('/api/direction/aois', () =>
      HttpResponse.json({
        items: [
          {
            ...aoi,
            name: 'Large region',
            kind: 'countries',
            bbox: null,
            countries: ['GB', 'UA', 'US', 'FR', 'DE', 'PL', 'IT', 'ES', 'NO'],
          },
          aoi,
        ],
      }),
    ),
  );
  const { form } = await openAreaForm();
  expect(
    within(form.getByLabelText('Saved area')).queryByRole('option', { name: 'Large region' }),
  ).not.toBeInTheDocument();
  expect(form.getByText(/Subscriptions support up to eight countries/)).toHaveTextContent(
    'Large region',
  );
  expect(
    within(form.getByLabelText('Saved area')).getByRole('option', { name: aoi.name }),
  ).toBeInTheDocument();
});
