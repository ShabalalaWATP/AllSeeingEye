import { render, screen, waitFor, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it } from 'vitest';

import type { SourceReviewRevision } from '@/lib/api/sourceReviews';
import { useAuthStore } from '@/stores/auth';
import { plainUser } from '@/test/fixtures';
import { report } from '@/test/fixtures.reports';
import { apiError } from '@/test/handlers';
import { server } from '@/test/server';

import { EvidenceAnnex } from './EvidenceAnnex';
import type { SourceReviewContext } from './SourceReviewPanel';

const reportId = report.report.id;
const base = `/api/reports/${reportId}/versions/1/source-reviews`;
const managerId = '33333333-3333-4333-8333-333333333333';
const judgements = [
  report.version.body.key_judgements[0]!,
  {
    ...report.version.body.key_judgements[0]!,
    id: 'KJ2',
    statement: 'A pause is unlikely.',
    supporting_evidence: [],
    contradicting_evidence: ['E1'],
  },
];

function context(changes: Partial<SourceReviewContext> = {}): SourceReviewContext {
  return {
    reportId,
    version: 1,
    judgements,
    canWrite: true,
    scopeLabel: 'Personal',
    reviewer: (id) => (id === plainUser.id ? 'You' : id === managerId ? 'Mina Manager' : 'Unknown'),
    ...changes,
  };
}

function revision(number: number, changes: Partial<SourceReviewRevision> = {}) {
  const id = `00000000-0000-4000-8000-${String(number).padStart(12, '0')}`;
  const previous = `00000000-0000-4000-8000-${String(number - 1).padStart(12, '0')}`;
  return {
    scope: { owner_id: plainUser.id, team_id: null },
    target: {
      report_id: reportId,
      report_version_id: '66666666-6666-4666-8666-666666666666',
      source_id: 'bbc_world',
      subject: 'ground-activity',
      capture_id: 'capture-1',
      claim_id: 'claim-1',
    },
    kind: 'reliability',
    number,
    review: {
      id,
      assessor: 'reviewer',
      assessor_id: managerId,
      status: 'applied',
      basis: `Basis ${String(number)}`,
      policy_version: 'ase-source-assessment-v1',
      recorded_at: '2026-09-30T10:00:00Z',
      reviewed_at: '2026-09-30T10:00:00Z',
      supersedes: number === 1 ? null : previous,
      policy_note: null,
    },
    reliability: 'B',
    expertise_basis: null,
    credibility: null,
    authenticity: null,
    ...changes,
  } satisfies SourceReviewRevision;
}

function serve(histories: SourceReviewRevision[][], post?: (body: unknown) => Response) {
  const gets: URLSearchParams[] = [];
  const posts: unknown[] = [];
  server.use(
    http.get(base, ({ request }) => {
      gets.push(new URL(request.url).searchParams);
      return HttpResponse.json(histories[Math.min(gets.length, histories.length) - 1] ?? []);
    }),
    http.post(base, async ({ request }) => {
      const body = await request.json();
      posts.push(body);
      if (post) return post(body);
      return HttpResponse.json(
        revision(1, { review: { ...revision(1).review, assessor_id: plainUser.id } }),
        { status: 201 },
      );
    }),
  );
  return { gets, posts };
}

async function openPanel(review: SourceReviewContext = context(), item = report.version.evidence) {
  render(<EvidenceAnnex evidence={item} findings={[]} status="ready" review={review} />);
  await userEvent.click(screen.getAllByText(item[0]!.title)[0]!);
  return screen.getByRole('region', { name: `Human source reviews for ${item[0]!.label}` });
}

async function loadTarget(panel: HTMLElement, kind = 'Reliability', subject = 'ground-activity') {
  await userEvent.selectOptions(within(panel).getByLabelText('Review kind'), kind);
  const field = within(panel).getByLabelText(/Subject area/);
  await userEvent.clear(field);
  await userEvent.type(field, subject);
  await userEvent.click(within(panel).getByRole('button', { name: 'Load review history' }));
}

describe('source reviews from the evidence panel', () => {
  beforeEach(() => useAuthStore.setState({ user: plainUser, status: 'authenticated' }));

  it('records a first reliability review for the exact target and announces it', async () => {
    const { gets, posts } = serve([[]]);
    const panel = await openPanel();
    expect(within(panel).getByText(/separate from the automatic grade/)).toBeVisible();
    await loadTarget(panel);
    expect(
      await within(panel).findByText('No human reviews recorded for this target.'),
    ).toBeVisible();
    expect(Object.fromEntries(gets[0]!)).toEqual({
      label: 'E1',
      judgement_id: 'KJ1',
      subject: 'ground-activity',
      kind: 'reliability',
    });
    expect(within(panel).getByText(/across this Personal scope/)).toBeVisible();
    await userEvent.selectOptions(within(panel).getByLabelText('Reliability grade'), 'A');
    await userEvent.type(within(panel).getByLabelText(/Basis/), 'Checked the methodology.');
    await userEvent.click(within(panel).getByRole('button', { name: 'Record review' }));
    expect(await within(panel).findByText('Review recorded as revision 1.')).toBeVisible();
    expect(posts).toEqual([
      {
        label: 'E1',
        judgement_id: 'KJ1',
        subject: 'ground-activity',
        kind: 'reliability',
        basis: 'Checked the methodology.',
        previous_id: null,
        reliability: 'A',
      },
    ]);
    expect(within(panel).getByText(/Revision 1 · B: usually reliable · You/)).toBeVisible();
  });

  it('keeps the draft on a stale write and corrects the newer revision after reload', async () => {
    let calls = 0;
    const { posts } = serve([[revision(1)], [revision(1), revision(2)]], () => {
      calls += 1;
      return calls === 1
        ? apiError(409, 'conflict', 'This source assessment has a newer revision.')
        : HttpResponse.json(revision(3), { status: 201 });
    });
    const panel = await openPanel();
    await loadTarget(panel);
    expect(
      await within(panel).findByText(/Revision 1 · B: usually reliable · Mina Manager/),
    ).toBeVisible();
    await userEvent.selectOptions(within(panel).getByLabelText('Reliability grade'), 'C');
    await userEvent.type(within(panel).getByLabelText(/Basis/), 'Later corrections found.');
    await userEvent.click(within(panel).getByRole('button', { name: 'Record correction' }));
    expect(await within(panel).findByRole('alert')).toHaveTextContent(/newer revision/);
    expect(within(panel).getByLabelText(/Basis/)).toHaveValue('Later corrections found.');
    await userEvent.click(within(panel).getByRole('button', { name: 'Reload history' }));
    expect(await within(panel).findByText(/Revision 2 ·/)).toBeVisible();
    expect(within(panel).getByLabelText(/Basis/)).toHaveValue('Later corrections found.');
    await userEvent.click(within(panel).getByRole('button', { name: 'Record correction' }));
    await waitFor(() => expect(posts).toHaveLength(2));
    expect(posts[0]).toMatchObject({ previous_id: revision(1).review.id, reliability: 'C' });
    expect(posts[1]).toMatchObject({ previous_id: revision(2).review.id, reliability: 'C' });
  });

  it('scopes credibility to one judgement and clears history when the target changes', async () => {
    const credibility = revision(1, { kind: 'credibility', reliability: null, credibility: 2 });
    const { gets } = serve([[credibility], []]);
    const panel = await openPanel();
    await loadTarget(panel, 'Credibility');
    expect(await within(panel).findByText(/Credibility of E1 for KJ1 only/)).toBeVisible();
    expect(within(panel).getByText(/Revision 1 · 2: probably true/)).toBeVisible();
    await userEvent.selectOptions(within(panel).getByLabelText('Judgement'), 'KJ2');
    expect(within(panel).queryByText(/Revision 1 · 2: probably true/)).not.toBeInTheDocument();
    expect(within(panel).getByText(/Load the history for this target/)).toBeVisible();
    await userEvent.click(within(panel).getByRole('button', { name: 'Load review history' }));
    await within(panel).findByText('No human reviews recorded for this target.');
    expect(gets[1]!.get('judgement_id')).toBe('KJ2');
    expect(within(panel).getByLabelText('Credibility grade')).toBeVisible();
    await userEvent.selectOptions(within(panel).getByLabelText('Review kind'), 'Authenticity');
    await userEvent.click(within(panel).getByRole('button', { name: 'Load review history' }));
    expect(await within(panel).findByLabelText('Issuer authenticity')).toBeVisible();
  });

  it('shows the revision limit, read-only and access-loss states', async () => {
    const full = Array.from({ length: 100 }, (_, index) => revision(index + 1));
    serve([full]);
    const panel = await openPanel();
    await loadTarget(panel);
    expect(await within(panel).findByText(/reached its 100-revision limit/)).toBeVisible();
    expect(within(panel).queryByRole('button', { name: 'Record correction' })).toBeNull();
    expect(within(panel).getByText(/All 100 retained revisions are shown/)).toBeVisible();

    server.use(
      http.get(base, () => apiError(404, 'not_found', 'The requested item does not exist.')),
    );
    await userEvent.click(within(panel).getByRole('button', { name: 'Load review history' }));
    expect(await within(panel).findByRole('alert')).toHaveTextContent('does not exist');
  });

  it('is read-only without write authority and explains an unavailable target', async () => {
    serve([[revision(1)]]);
    const panel = await openPanel(context({ canWrite: false }));
    await loadTarget(panel);
    await within(panel).findByText(/Revision 1 ·/);
    expect(within(panel).queryByLabelText(/Basis/)).toBeNull();
    expect(within(panel).getByText(/cannot record source reviews/)).toBeVisible();
  });

  it('refuses evidence that no saved judgement cites', async () => {
    const uncited = [{ ...report.version.evidence[1]!, label: 'E7' }];
    const panel = await openPanel(context(), uncited);
    expect(within(panel).getByText(/not cited by a saved key judgement/)).toBeVisible();
    expect(within(panel).queryByRole('button', { name: 'Load review history' })).toBeNull();
  });
});
