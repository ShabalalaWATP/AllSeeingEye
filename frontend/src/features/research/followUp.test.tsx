import { reportJob, readReportJobRequest } from '@/test/reportJobFixture';
import { act, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { report } from '@/test/fixtures';
import { roster, team } from '@/test/fixtures.teams';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
import { followUpRequest } from '@/lib/followUpScope';

const privateScope = {
  report_language: 'es',
  report_style: 'briefing',
  research_mode: 'detailed',
  research_focus: 'document',
  research_languages: ['fr'],
  window_hours: 168,
  devils_advocacy: true,
  research_input: { filename: 'notes.txt' },
};

describe('private and follow-up research', () => {
  it('hides the old parent while a different follow-up scope is loading', async () => {
    const nextId = '77777777-7777-4777-8777-777777777777';
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    server.use(
      http.get(`/api/reports/${report.report.id}`, () =>
        HttpResponse.json({ ...report, report: { ...report.report, scope: privateScope } }),
      ),
      http.get(`/api/reports/${nextId}`, async () => {
        await gate;
        return HttpResponse.json({
          ...report,
          report: {
            ...report.report,
            id: nextId,
            title: 'Different company scope',
            scope: {
              research_mode: 'quick',
              research_focus: 'company',
              research_subject: 'Different Company Ltd',
            },
          },
        });
      }),
    );
    const { router } = renderApp(`/research?parent=${report.report.id}`, 'user');
    await screen.findByLabelText('Your question');
    await act(async () => {
      await router.navigate(`/research?parent=${nextId}`);
    });
    expect(screen.queryByLabelText('Your question')).not.toBeInTheDocument();
    release();
    await screen.findByLabelText('Your question');
    expect(screen.getByText(/Different Company Ltd/)).toBeVisible();
    expect(screen.queryByText(/No public search is started/)).not.toBeInTheDocument();
  });

  it('waits for extraction, submits only the private input id and blocks a removed attachment', async () => {
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    let body: unknown;
    server.use(
      http.post('/api/research/inputs', async () => {
        await gate;
        return HttpResponse.json({
          id: '10000000-0000-4000-8000-000000000001',
          filename: 'notes.txt',
          media_type: 'text/plain',
          sha256: 'a'.repeat(64),
          imported_at: new Date().toISOString(),
          expires_at: new Date(Date.now() + 900_000).toISOString(),
          event_count: 1,
          extracted_characters: 4,
          preview: 'Text',
          limitations: [],
          previews: [],
        });
      }),
      http.post('/api/report-jobs', async ({ request }) => {
        body = await readReportJobRequest(request);
        return HttpResponse.json(
          { error: { code: 'unavailable', message: 'Drafting unavailable.' } },
          { status: 503 },
        );
      }),
    );
    const { user } = renderApp('/research?country=UA', 'user');
    await user.type(await screen.findByLabelText('Your question'), 'Summarise the attachment.');
    await user.click(screen.getByText('Scope and sources'));
    await user.selectOptions(screen.getByLabelText('Research focus'), 'document');
    await user.upload(
      screen.getByLabelText('Document or media'),
      new File(['Text'], 'notes.txt', { type: 'text/plain' }),
    );
    await screen.findByText(/Uploading and extracting/);
    expect(screen.getByRole('button', { name: 'Start research' })).toBeDisabled();
    release();
    await screen.findByText('Attached: notes.txt');
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Start research' })).toBeEnabled(),
    );
    await user.click(screen.getByRole('button', { name: 'Start research' }));
    await screen.findByText('Drafting unavailable.');
    expect(body).toMatchObject({
      research_focus: 'document',
      research_input_id: '10000000-0000-4000-8000-000000000001',
    });
    expect(body).not.toHaveProperty('country');
    expect(body).not.toHaveProperty('preview');
    await user.click(screen.getByRole('button', { name: 'Remove attachment' }));
    await user.click(screen.getByRole('button', { name: 'Start research' }));
    expect(
      screen.getByText('Attach a document or media file before starting this research.'),
    ).toBeVisible();
    expect(screen.getByLabelText('Research focus')).toHaveValue('document');
  });

  it('locks the parent team and private scope while creating a separate report from saved evidence', async () => {
    let requestBody: unknown;
    server.use(
      http.get('/api/teams', () => HttpResponse.json({ items: [team] })),
      http.get('/api/teams/:id', () => HttpResponse.json(roster)),
    );
    const nextId = '99999999-9999-4999-8999-999999999999';
    server.use(
      http.get(`/api/reports/${report.report.id}`, () =>
        HttpResponse.json({
          ...report,
          report: { ...report.report, team_id: team.id, scope: privateScope },
        }),
      ),
      http.post('/api/report-jobs', async ({ request }) => {
        requestBody = await readReportJobRequest(request);
        return HttpResponse.json(reportJob({ id: nextId, team_id: team.id }), { status: 202 });
      }),
    );
    const { user, router } = renderApp(`/research?parent=${report.report.id}&country=UA`, 'user');
    await user.type(
      await screen.findByLabelText('Your question'),
      'What would change this assessment?',
    );
    expect(screen.getByRole('radio', { name: /Deep/ })).toBeChecked();
    expect(screen.getByRole('radio', { name: /Basic/ })).toBeDisabled();
    expect(screen.queryByLabelText('Workspace')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Research focus')).not.toBeInTheDocument();
    expect(screen.getByText(/No public search is started/)).toBeVisible();
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Start research' })).toBeEnabled(),
    );
    await user.click(screen.getByRole('button', { name: 'Start research' }));
    await waitFor(() => expect(router.state.location.pathname).toBe(`/research/jobs/${nextId}`));
    expect(requestBody).toMatchObject({
      parent_report_id: report.report.id,
      parent_version: 1,
      team_id: team.id,
      research_focus: 'document',
      report_language: 'es',
      report_style: 'briefing',
      research_mode: 'detailed',
      research_languages: ['fr'],
      window_hours: 168,
      country: null,
      question: 'What would change this assessment?',
    });
    expect(requestBody).not.toHaveProperty('research_input_id');
  });

  it('never falls back to a public form when a parent is missing or inaccessible', async () => {
    server.use(
      http.get(`/api/reports/${report.report.id}`, () =>
        HttpResponse.json(
          { error: { code: 'not_found', message: 'Parent unavailable.' } },
          { status: 404 },
        ),
      ),
    );
    renderApp(`/research?parent=${report.report.id}`, 'user');
    expect(await screen.findByRole('alert')).toHaveTextContent('Parent unavailable.');
    expect(screen.queryByRole('button', { name: 'Start research' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Retry parent report' })).toBeVisible();
  });

  it('requires an attachment for a new private run and preserves private focus after rejection', async () => {
    let posts = 0;
    server.use(
      http.post('/api/report-jobs', () => {
        posts++;
        return HttpResponse.json(reportJob(), { status: 202 });
      }),
    );
    const { user } = renderApp('/research', 'user');
    await user.type(await screen.findByLabelText('Your question'), 'Summarise this source.');
    await user.click(screen.getByText('Scope and sources'));
    await user.selectOptions(screen.getByLabelText('Research focus'), 'media');
    expect(screen.getByLabelText('Document or media')).toBeVisible();
    expect(screen.queryByLabelText('Domain name')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Start research' }));
    expect(screen.getByRole('alert')).toHaveTextContent('Attach a document or media file');
    expect(screen.getByLabelText('Research focus')).toHaveValue('media');
    expect(posts).toBe(0);
  });

  it('preserves all declared public scope fields and blocks incomplete private scope', () => {
    const request = followUpRequest({
      ...report,
      report: {
        ...report.report,
        scope: {
          research_mode: 'quick',
          research_focus: 'company',
          research_subject: 'Example Ltd',
          research_languages: ['en', 'fr'],
          categories: ['economic'],
          window_hours: 24,
          plan: 'plan-id',
          hazard: null,
          conflict: null,
          country: null,
        },
      },
    });
    expect(request).toMatchObject({
      research_focus: 'company',
      research_subject: 'Example Ltd',
      categories: ['economic'],
      plan: 'plan-id',
      window_hours: 24,
    });
    expect(() =>
      followUpRequest({
        ...report,
        report: { ...report.report, scope: { research_input: { filename: 'private.txt' } } },
      }),
    ).toThrow(/private research scope is incomplete/);
  });
});
