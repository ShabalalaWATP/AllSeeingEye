import { render, screen, waitFor, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { CitationVerdict, CitationVerdictList } from '@/lib/api/citationVerdicts';
import type { ReportVersion } from '@/lib/api/reports';
import { saveBinaryFile } from '@/lib/downloadBinary';
import { useAuthStore } from '@/stores/auth';
import { plainUser } from '@/test/fixtures';
import { report } from '@/test/fixtures.reports';
import { citationChecks } from '@/test/fixtures.researchMetadata';
import { manager, roster } from '@/test/fixtures.teams';
import { apiError } from '@/test/handlers';
import { server } from '@/test/server';

import { AssessmentReview } from './AssessmentReview';

vi.mock('@/lib/downloadBinary', () => ({ saveBinaryFile: vi.fn() }));

const reportId = report.report.id;
const version = { ...report.version, citation_checks: citationChecks } as ReportVersion;
const path = `/api/reports/${reportId}/versions/${String(version.number)}/citation-verdicts`;
const notice =
  'Citation verdicts are human opinions recorded by reviewers. They are not ground truth.';

function verdict(changes: Partial<CitationVerdict>): CitationVerdict {
  return {
    id: '55555555-5555-4555-8555-555555555555',
    report_id: reportId,
    report_version_id: '66666666-6666-4666-8666-666666666666',
    version_number: version.number,
    judgement_id: 'KJ1',
    label: 'E1',
    relation: 'supporting',
    verdict: 'cannot_tell',
    note: 'Snippet too short to judge.',
    reviewer_id: manager.id,
    team_id: null,
    recorded_at: '2026-09-30T10:00:00Z',
    ...changes,
  };
}

function serve(list: Partial<CitationVerdictList> = {}) {
  const posts: unknown[] = [];
  let current: CitationVerdictList = {
    verdicts: [],
    can_record: true,
    limit: 500,
    note_limit: 300,
    notice,
    ...list,
  };
  server.use(
    http.get(path, () => HttpResponse.json(current)),
    http.post(path, async ({ request }) => {
      const body = (await request.json()) as Partial<CitationVerdict>;
      posts.push(body);
      if (body.note === 'conflict') return apiError(422, 'invalid_request', 'Limit reached.');
      const created = verdict({
        ...body,
        id: '77777777-7777-4777-8777-777777777777',
        reviewer_id: plainUser.id,
        recorded_at: '2026-09-30T11:00:00Z',
      });
      current = { ...current, verdicts: [...current.verdicts, created] };
      return HttpResponse.json(created, { status: 201 });
    }),
    http.get(`${path}/export`, () =>
      HttpResponse.text('{"record":"header"}\n', {
        headers: {
          'Content-Type': 'application/x-ndjson',
          'Content-Disposition': 'attachment; filename="citation-verdicts-x-v1.jsonl"',
        },
      }),
    ),
  );
  return posts;
}

async function openCitation() {
  await userEvent.click(await screen.findByText(/Citation excerpts/));
  return screen.getByRole('region', { name: 'E1 supporting citation check' });
}

describe('citation verdicts in the report reader', () => {
  beforeEach(() => {
    useAuthStore.setState({ user: plainUser, status: 'authenticated' });
    vi.mocked(saveBinaryFile).mockClear();
  });

  it('records a verdict for the exact citation and announces it', async () => {
    const posts = serve({ verdicts: [verdict({})] });
    render(<AssessmentReview reportId={reportId} version={version} teams={[roster]} />);
    const region = await openCitation();
    expect(await within(region).findByText(/Mina Manager/)).toBeVisible();
    expect(within(region).getByText('Snippet too short to judge.')).toBeVisible();
    expect(screen.getAllByText(/human opinions/).length).toBeGreaterThan(0);
    const group = within(region).getByRole('radiogroup', { name: /Your verdict on E1/ });
    await userEvent.click(within(group).getByRole('radio', { name: 'Partly supports' }));
    await userEvent.type(
      within(region).getByLabelText(/Note \(optional/),
      'Only the date matches.',
    );
    await userEvent.click(within(region).getByRole('button', { name: 'Record verdict' }));
    expect(await within(region).findByText('Verdict recorded: Partly supports.')).toBeVisible();
    expect(posts).toEqual([
      {
        judgement_id: 'KJ1',
        label: 'E1',
        relation: 'supporting',
        verdict: 'partly_supports',
        note: 'Only the date matches.',
      },
    ]);
    expect(await within(region).findByText(/^You/)).toBeVisible();
    expect(within(region).getByLabelText(/Note \(optional/)).toHaveValue('');
  });

  it('requires a choice and keeps the draft when recording fails', async () => {
    serve();
    render(<AssessmentReview reportId={reportId} version={version} teams={[]} />);
    const region = await openCitation();
    await within(region).findByText('No verdicts recorded for this citation.');
    const record = within(region).getByRole('button', { name: 'Record verdict' });
    expect(record).toBeDisabled();
    await userEvent.click(within(region).getByRole('radio', { name: 'Does not support' }));
    await userEvent.type(within(region).getByLabelText(/Note \(optional/), 'conflict');
    await userEvent.click(record);
    expect(await within(region).findByRole('alert')).toHaveTextContent('Limit reached.');
    expect(within(region).getByLabelText(/Note \(optional/)).toHaveValue('conflict');
    expect(within(region).getByRole('radio', { name: 'Does not support' })).toBeChecked();
  });

  it('is read-only without recording authority and names unknown reviewers honestly', async () => {
    serve({
      can_record: false,
      verdicts: [verdict({ reviewer_id: '99999999-9999-4999-8999-999999999999' })],
    });
    render(<AssessmentReview reportId={reportId} version={version} teams={[]} />);
    const region = await openCitation();
    expect(await within(region).findByText(/not in your current team rosters/)).toBeVisible();
    expect(within(region).queryByRole('radiogroup')).not.toBeInTheDocument();
    expect(within(region).getByText(/cannot record verdicts/)).toBeVisible();
  });

  it('shows an unavailable state and exports the labelled set', async () => {
    serve();
    render(<AssessmentReview reportId={reportId} version={version} teams={[]} />);
    await userEvent.click(
      await screen.findByRole('button', { name: 'Download citation verdicts (JSONL)' }),
    );
    await waitFor(() => expect(saveBinaryFile).toHaveBeenCalled());
    expect(vi.mocked(saveBinaryFile).mock.calls[0]?.[0]).toBe('citation-verdicts-x-v1.jsonl');
    server.use(http.get(path, () => apiError(404, 'not_found', 'Not found.')));
    render(<AssessmentReview reportId={reportId} version={version} teams={[]} />);
    expect(await screen.findByText(/Citation verdicts are unavailable/)).toBeVisible();
  });
});
