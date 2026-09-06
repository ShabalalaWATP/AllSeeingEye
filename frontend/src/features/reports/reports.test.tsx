import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { report, reportSummary } from '@/test/fixtures';
import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

describe('ReportsPage', () => {
  it('lists reports and links to the reader', async () => {
    const { user } = renderApp('/reports', 'user');
    const table = await screen.findByRole('table', { name: 'Reports' });
    const link = within(table).getByRole('link', { name: 'Intelligence summary: Ukraine' });
    expect(within(table).getByText('Ready')).toBeInTheDocument();
    await user.click(link);
    expect(
      await screen.findByRole('heading', { name: 'Intelligence summary: Ukraine' }),
    ).toBeInTheDocument();
  });

  it('generates a report and opens it, showing the model error when refused', async () => {
    let body: Record<string, unknown> | null = null;
    const asked = {
      ...report,
      report: {
        ...reportSummary,
        id: '99999999-9999-4999-8999-999999999999',
        title: 'Ask the Eye: What next?',
      },
    };
    server.use(
      http.post('/api/reports', async ({ request }) => {
        body = (await request.json()) as Record<string, unknown>;
        if (body.template === 'intsum') {
          return apiError(409, 'no_model', 'No enabled model profile can play this role.');
        }
        return HttpResponse.json(asked, { status: 201 });
      }),
      http.get('/api/reports/99999999-9999-4999-8999-999999999999', () => HttpResponse.json(asked)),
    );
    const { user } = renderApp('/reports', 'user');
    const form = await screen.findByRole('form', { name: 'Generate a report' });
    await user.click(within(form).getByRole('button', { name: 'Generate' }));
    expect(
      await within(form).findByText('No enabled model profile can play this role.'),
    ).toBeInTheDocument();

    await user.selectOptions(within(form).getByLabelText('Product'), 'ask');
    await user.type(within(form).getByLabelText('Question'), 'What next?');
    await user.selectOptions(within(form).getByLabelText('Nation'), 'UA');
    await user.type(within(form).getByLabelText('Window (hours)'), '24');
    await user.click(within(form).getByRole('button', { name: 'Generate' }));
    expect(
      await screen.findByRole('heading', { name: 'Ask the Eye: What next?' }),
    ).toBeInTheDocument();
    expect(body).toEqual({
      template: 'ask',
      research_focus: 'general',
      devils_advocacy: false,
      country: 'UA',
      question: 'What next?',
      window_hours: 24,
    });
  });
});

describe('ReportPage', () => {
  it.each(['user', 'admin'] as const)('limits shared report actions for a %s', async (role) => {
    server.use(
      http.get('/api/reports/:id', () =>
        HttpResponse.json({
          ...report,
          report: { ...reportSummary, created_by: '77777777-7777-4777-8777-777777777777' },
        }),
      ),
    );
    renderApp(`/reports/${reportSummary.id}`, role);
    await screen.findByRole('heading', { name: 'Intelligence summary: Ukraine' });
    expect(screen.getByRole('button', { name: 'Download Markdown' })).toBeInTheDocument();
    for (const name of ['Regenerate', 'Delete']) {
      if (role === 'admin') expect(screen.getByRole('button', { name })).toBeInTheDocument();
      else expect(screen.queryByRole('button', { name })).not.toBeInTheDocument();
    }
  });

  it('renders every section, the annex with safe links only, and deletes', async () => {
    const { user } = renderApp(`/reports/${reportSummary.id}`, 'user');
    expect(
      await screen.findByRole('heading', { name: 'Intelligence summary: Ukraine' }),
    ).toBeInTheDocument();
    const judgements = screen.getByRole('region', { name: 'Key judgements' });
    expect(within(judgements).getByText(/highly likely that fighting/)).toBeInTheDocument();
    expect(within(judgements).getByText('highly likely')).toBeInTheDocument();
    expect(within(judgements).getByText('moderate confidence')).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Reporting' })).toHaveTextContent(
      'Shelling was reported overnight.',
    );
    expect(screen.getByRole('region', { name: 'Assumptions' })).toHaveTextContent('(lynchpin)');
    expect(screen.getByRole('region', { name: 'Indicators and warning' })).toHaveTextContent(
      'elevated',
    );
    expect(screen.getByRole('region', { name: 'Gaps and collection' })).toHaveTextContent('EEI-1');
    const annex = screen.getByRole('region', { name: 'Evidence annex' });
    await user.click(within(annex).getByText('Shelling in Kharkiv'));
    expect(within(annex).getByRole('link', { name: 'Open source' })).toHaveAttribute(
      'href',
      'https://example.org/e1',
    );
    expect(
      within(annex).queryByRole('link', { name: 'Ministry statement' }),
    ).not.toBeInTheDocument();
    await user.click(within(annex).getByText('Ministry statement'));
    expect(within(annex).getByText('Source flags: state controlled')).toBeVisible();
    expect(screen.getByText('1 validator note(s)')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Copy Markdown' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Delete' }));
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Reports' })).toBeInTheDocument();
    });
  });

  it('shows findings prominently when the report needs review, and errors when missing', async () => {
    server.use(
      http.get('/api/reports/:id', () =>
        HttpResponse.json({
          ...report,
          version: {
            ...report.version,
            status: 'needs_review',
            findings: [
              { rule: 'yardstick', severity: 'error', location: 'KJ1', message: 'Two terms' },
            ],
          },
        }),
      ),
    );
    renderApp(`/reports/${reportSummary.id}`, 'user');
    expect(await screen.findByText('Validator findings')).toBeInTheDocument();
    expect(screen.getByText(/Two terms/)).toBeInTheDocument();
    expect(screen.getByText('Needs review')).toBeInTheDocument();
    server.use(http.get('/api/reports/:id', () => apiError(404, 'not_found', 'Report not found.')));
    renderApp('/reports/missing', 'user');
    expect(await screen.findByText('Report not found.')).toBeInTheDocument();
  });
});
