import { screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import { renderApp } from '@/test/render';
import { readReportJobRequest, reportJob } from '@/test/reportJobFixture';
import { server } from '@/test/server';

it.each([
  ['Basic', 'quick', false],
  ['Deep', 'detailed', true],
  ['Advanced', 'advanced', true],
] as const)(
  'sends the %s report type with the appropriate challenge setting',
  async (label, mode, challenge) => {
    let body: unknown;
    server.use(
      http.post('/api/report-jobs', async ({ request }) => {
        body = await readReportJobRequest(request);
        return HttpResponse.json(reportJob(), { status: 202 });
      }),
    );
    const { user } = renderApp('/research?question=What%20has%20changed%3F', 'user');
    await user.click(await screen.findByRole('radio', { name: new RegExp(`^${label}`) }));
    expect(screen.getByText(/Lengths are indicative/)).toBeVisible();
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Start research' })).toBeEnabled(),
    );
    await user.click(screen.getByRole('button', { name: 'Start research' }));
    await waitFor(() =>
      expect(body).toMatchObject({ research_mode: mode, devils_advocacy: challenge }),
    );
  },
);
