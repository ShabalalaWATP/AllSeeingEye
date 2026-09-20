import { screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import { report } from '@/test/fixtures';
import { readReportJobRequest } from '@/test/reportJobFixture';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

it.each([{ countries: [] }, { countries: ['US'] }])(
  'shows and submits retained regions with countries $countries',
  async ({ countries }) => {
    let submitted: unknown;
    server.use(
      http.get(`/api/reports/${report.report.id}`, () =>
        HttpResponse.json({
          ...report,
          report: {
            ...report.report,
            scope: {
              research_mode: 'quick',
              research_focus: 'general',
              regions: ['europe', 'middle_east'],
              countries,
            },
          },
        }),
      ),
      http.post('/api/report-jobs', async ({ request }) => {
        submitted = await readReportJobRequest(request);
        return HttpResponse.json(
          { error: { code: 'unavailable', message: 'Controlled collection unavailable.' } },
          { status: 503 },
        );
      }),
    );
    const { user } = renderApp(`/research?parent=${report.report.id}`, 'user');
    await user.type(await screen.findByLabelText('Your question'), 'What changed in this region?');
    expect(screen.getByLabelText('Follow-up scope')).toHaveTextContent('Europe, Middle East');
    expect(screen.getByLabelText('Follow-up scope')).not.toHaveTextContent('Worldwide');
    await user.click(screen.getByRole('button', { name: 'Start research' }));
    await screen.findByText('Controlled collection unavailable.');
    expect(submitted).toMatchObject({
      regions: ['europe', 'middle_east'],
      countries,
      parent_report_id: report.report.id,
      parent_version: report.version.number,
    });
  },
);
