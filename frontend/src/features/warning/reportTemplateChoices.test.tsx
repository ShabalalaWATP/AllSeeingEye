import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import { aoi, indicator, plan } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

import { chooseCountry } from './ruleTestSteps';

const templates = [
  ['intsum', {}],
  ['country_brief', { needs_country: true }],
  ['ask', { needs_question: true }],
  ['disaster_sitrep', { needs_hazard: true }],
  ['conflict_assessment', { needs_conflict: true }],
] as const;

function serveTemplates() {
  server.use(
    http.get('/api/reports/templates', () =>
      HttpResponse.json({
        items: templates.map(([id, requirements]) => ({
          id,
          title: id,
          purpose: '',
          window_hours: 24,
          needs_country: false,
          needs_question: false,
          needs_conflict: false,
          needs_hazard: false,
          ...requirements,
        })),
      }),
    ),
  );
}

it('offers only templates supported by the current saved rule inputs', async () => {
  serveTemplates();
  const { user } = renderApp('/warning', 'user');
  const form = within(await screen.findByRole('form', { name: 'New alert rule' }));
  const select = form.getByRole('combobox', { name: 'Report when it fires' });
  await waitFor(() => expect(within(select).getByRole('option', { name: 'intsum' })).toBeVisible());
  for (const name of ['ask', 'disaster_sitrep', 'conflict_assessment', 'country_brief']) {
    expect(within(select).queryByRole('option', { name })).not.toBeInTheDocument();
  }
  await chooseCountry(user, form, 'Ukraine');
  expect(within(select).getByRole('option', { name: 'country_brief' })).toBeVisible();
  await user.selectOptions(form.getByRole('combobox', { name: /Collection plan/ }), 'Kharkiv axis');
  expect(within(select).getByRole('option', { name: 'ask' })).toBeVisible();
  await user.selectOptions(form.getByRole('combobox', { name: /Collection plan/ }), '');
  expect(within(select).queryByRole('option', { name: 'ask' })).not.toBeInTheDocument();
});

it('retains an incompatible saved choice and lets the operator remove it', async () => {
  serveTemplates();
  const saved = { ...indicator, report_template: 'ask', plan_id: null };
  let submitted: Record<string, unknown> | null = null;
  server.use(
    http.get('/api/warning/indicators', () => HttpResponse.json({ items: [saved] })),
    http.put('/api/warning/indicators/:id', async ({ request }) => {
      submitted = (await request.json()) as Record<string, unknown>;
      return HttpResponse.json({ ...saved, ...submitted });
    }),
  );
  const { user } = renderApp('/warning', 'user');
  await user.click(await screen.findByRole('button', { name: `Edit ${saved.name}` }));
  const form = within(screen.getByRole('form', { name: `Edit alert rule ${saved.name}` }));
  const select = form.getByRole('combobox', { name: 'Report when it fires' });
  expect(select).toHaveValue('ask');
  expect(form.getByText(/Link a collection plan with a question/)).toBeVisible();
  await user.click(form.getByRole('button', { name: 'Save changes' }));
  expect(submitted).toBeNull();
  await user.selectOptions(select, '');
  await user.click(form.getByRole('button', { name: 'Save changes' }));
  await waitFor(() => expect(submitted).not.toBeNull());
  expect(submitted).toMatchObject({ report_template: null });
});

it.each(['polygon', 'unavailable', 'wrong_scope'])(
  'offers No report for a plan whose area is %s',
  async (areaState) => {
    serveTemplates();
    server.use(
      http.get('/api/direction/aois', () =>
        HttpResponse.json({
          items:
            areaState === 'unavailable'
              ? []
              : [
                  {
                    ...aoi,
                    ...(areaState === 'polygon'
                      ? {
                          research_area: {
                            geometry: {
                              type: 'Polygon',
                              coordinates: [
                                [
                                  [0, 0],
                                  [1, 0],
                                  [1, 1],
                                  [0, 0],
                                ],
                              ],
                            },
                            sha256: 'a'.repeat(64),
                          },
                        }
                      : { created_by: '33333333-3333-4333-8333-333333333333' }),
                  },
                ],
        }),
      ),
    );
    const { user } = renderApp('/warning', 'user');
    const form = within(await screen.findByRole('form', { name: 'New alert rule' }));
    await form.findByRole('option', { name: plan.name });
    await user.selectOptions(form.getByRole('combobox', { name: /Collection plan/ }), plan.id);
    const select = form.getByRole('combobox', { name: 'Report when it fires' });
    await waitFor(() => expect(within(select).getAllByRole('option')).toHaveLength(1));
    expect(within(select).getByRole('option', { name: 'No report' })).toBeVisible();
    expect(form.getByText(/The linked plan cannot produce an automatic report/)).toBeVisible();
  },
);
