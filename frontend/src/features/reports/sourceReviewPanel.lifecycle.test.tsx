import { act, render, screen, waitFor, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it } from 'vitest';

import type { SourceReviewInput, SourceReviewRevision } from '@/lib/api/sourceReviews';
import { useAuthStore } from '@/stores/auth';
import { plainUser } from '@/test/fixtures';
import { report } from '@/test/fixtures.reports';
import { server } from '@/test/server';

import { SourceReviewPanel } from './SourceReviewPanel';

const base = `/api/reports/${report.report.id}/versions/1/source-reviews`;
const reviewId = '00000000-0000-4000-8000-000000000001';

function revision(changes: Partial<SourceReviewRevision> = {}): SourceReviewRevision {
  return {
    scope: { owner_id: plainUser.id, team_id: null },
    target: {
      report_id: report.report.id,
      report_version_id: '66666666-6666-4666-8666-666666666666',
      source_id: 'bbc_world',
      subject: 'ground-activity',
      capture_id: 'capture-1',
      claim_id: 'claim-1',
    },
    kind: 'reliability',
    number: 1,
    review: {
      id: reviewId,
      assessor: 'reviewer',
      assessor_id: plainUser.id,
      status: 'applied',
      basis: 'Checked the original record.',
      policy_version: 'ase-source-assessment-v1',
      recorded_at: '2026-09-30T10:00:00Z',
      reviewed_at: '2026-09-30T10:00:00Z',
      supersedes: null,
      policy_note: null,
    },
    reliability: 'B',
    expertise_basis: null,
    credibility: null,
    authenticity: null,
    ...changes,
  };
}

function renderPanel() {
  render(
    <SourceReviewPanel
      item={report.version.evidence[0]!}
      context={{
        reportId: report.report.id,
        version: 1,
        judgements: report.version.body.key_judgements,
        canWrite: true,
        scopeLabel: 'Personal',
        reviewer: () => 'You',
      }}
    />,
  );
  return userEvent.setup();
}

async function load(kind: string) {
  await userEvent.selectOptions(screen.getByLabelText('Review kind'), kind);
  await userEvent.type(screen.getByLabelText(/Subject area/), '  ground-activity  ');
  await userEvent.click(screen.getByRole('button', { name: 'Load review history' }));
  await screen.findByText('No human reviews recorded for this target.');
}

describe('source review lifecycle and validation', () => {
  beforeEach(() => {
    useAuthStore.setState({ user: plainUser, status: 'authenticated' });
    server.use(http.get(base, () => HttpResponse.json([])));
  });

  it('keeps an authenticity draft after a failed save and records only its capture-specific fields on retry', async () => {
    const posts: SourceReviewInput[] = [];
    server.use(
      http.post(base, async ({ request }) => {
        const body = (await request.json()) as SourceReviewInput;
        posts.push(body);
        if (posts.length === 1)
          return HttpResponse.json(
            { error: { code: 'unavailable', message: 'Review service unavailable.' } },
            { status: 503 },
          );
        return HttpResponse.json(
          revision({
            kind: 'authenticity',
            reliability: null,
            review: {
              ...revision().review,
              basis: body.basis,
              policy_note: body.policy_note ?? null,
            },
            authenticity: {
              evidence_id: 'capture-1',
              issuer_id: 'bbc_world',
              status: 'disputed',
              basis: body.basis,
              observed_reference: null,
            },
          }),
          { status: 201 },
        );
      }),
    );
    const user = renderPanel();
    await load('Authenticity');
    expect(screen.getByText(/Authenticity of capture E1 and its issuer/)).toBeVisible();
    await user.selectOptions(screen.getByLabelText('Issuer authenticity'), 'disputed');
    await user.type(
      screen.getByLabelText(/^Basis/),
      '  Issuer identity differs from the original.  ',
    );
    await user.type(
      screen.getByLabelText(/^Policy note/),
      '  Reviewed under the current policy.  ',
    );
    await user.click(screen.getByRole('button', { name: 'Record review' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Review service unavailable.');
    expect(screen.queryByRole('button', { name: 'Reload history' })).not.toBeInTheDocument();
    expect(screen.getByLabelText('Issuer authenticity')).toHaveValue('disputed');
    expect(screen.getByLabelText(/^Basis/)).toHaveValue(
      '  Issuer identity differs from the original.  ',
    );
    await user.click(screen.getByRole('button', { name: 'Record review' }));
    expect(await screen.findByText('Review recorded as revision 1.')).toBeVisible();
    const expected = {
      label: 'E1',
      judgement_id: 'KJ1',
      subject: 'ground-activity',
      kind: 'authenticity',
      basis: 'Issuer identity differs from the original.',
      previous_id: null,
      authenticity: 'disputed',
      policy_note: 'Reviewed under the current policy.',
    };
    expect(posts).toEqual([expected, expected]);
    expect(screen.getByRole('list', { name: 'Review history' })).toHaveTextContent(
      'Authenticity Disputed',
    );
    expect(screen.getByLabelText(/^Basis/)).toHaveValue('');
    expect(screen.getByLabelText('Issuer authenticity')).toHaveValue('');
    expect(screen.getByRole('button', { name: 'Record correction' })).toBeDisabled();
  });

  it('includes trimmed expertise and policy notes in a reliability review and displays their provenance', async () => {
    const posts: SourceReviewInput[] = [];
    server.use(
      http.post(base, async ({ request }) => {
        const body = (await request.json()) as SourceReviewInput;
        posts.push(body);
        return HttpResponse.json(
          revision({
            reliability: 'C',
            expertise_basis: body.expertise_basis ?? null,
            review: {
              ...revision().review,
              basis: body.basis,
              policy_note: body.policy_note ?? null,
            },
          }),
          { status: 201 },
        );
      }),
    );
    const user = renderPanel();
    await load('Reliability');
    await user.selectOptions(screen.getByLabelText('Reliability grade'), 'C');
    await user.type(screen.getByLabelText(/^Basis/), '  Compared the methodology.  ');
    await user.type(
      screen.getByLabelText(/^Expertise basis/),
      '  Regional reporting experience.  ',
    );
    await user.type(screen.getByLabelText(/^Policy note/), '  Updated assessment policy.  ');
    await user.click(screen.getByRole('button', { name: 'Record review' }));
    const history = await screen.findByRole('list', { name: 'Review history' });
    expect(history).toHaveTextContent('C: fairly reliable');
    expect(
      within(history).getByText('Expertise basis: Regional reporting experience.'),
    ).toBeVisible();
    expect(within(history).getByText('Policy note: Updated assessment policy.')).toBeVisible();
    expect(posts).toEqual([
      {
        label: 'E1',
        judgement_id: 'KJ1',
        subject: 'ground-activity',
        kind: 'reliability',
        basis: 'Compared the methodology.',
        previous_id: null,
        reliability: 'C',
        expertise_basis: 'Regional reporting experience.',
        policy_note: 'Updated assessment policy.',
      },
    ]);
  });

  it('requires a selected credibility and nonblank basis, and records no source-wide grade', async () => {
    const posts: SourceReviewInput[] = [];
    server.use(
      http.post(base, async ({ request }) => {
        posts.push((await request.json()) as SourceReviewInput);
        return HttpResponse.json(
          revision({ kind: 'credibility', reliability: null, credibility: 4 }),
          { status: 201 },
        );
      }),
    );
    const user = renderPanel();
    await load('Credibility');
    const grade = screen.getByLabelText('Credibility grade');
    const record = screen.getByRole('button', { name: 'Record review' });
    await user.type(screen.getByLabelText(/^Basis/), '  ');
    await user.selectOptions(grade, '4');
    expect(record).toBeDisabled();
    await user.type(screen.getByLabelText(/^Basis/), 'The claim conflicts with the capture.');
    await user.selectOptions(grade, '');
    expect(record).toBeDisabled();
    await user.selectOptions(grade, '4');
    await user.click(record);
    expect(await screen.findByRole('list', { name: 'Review history' })).toHaveTextContent(
      '4: doubtful',
    );
    expect(posts).toEqual([
      {
        label: 'E1',
        judgement_id: 'KJ1',
        subject: 'ground-activity',
        kind: 'credibility',
        basis: 'The claim conflicts with the capture.',
        previous_id: null,
        credibility: 4,
      },
    ]);
  });

  it('never applies a late history to the subject selected while that request was pending', async () => {
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    const requested: string[] = [];
    server.use(
      http.get(base, async ({ request }) => {
        const subject = new URL(request.url).searchParams.get('subject')!;
        requested.push(subject);
        if (subject === 'ground-activity') {
          await gate;
          return HttpResponse.json([revision()]);
        }
        return HttpResponse.json([]);
      }),
    );
    const user = renderPanel();
    const subject = screen.getByLabelText(/Subject area/);
    await user.type(subject, 'ground-activity');
    await user.click(screen.getByRole('button', { name: 'Load review history' }));
    await waitFor(() => expect(requested).toEqual(['ground-activity']));
    await user.clear(subject);
    await user.type(subject, 'maritime-activity');
    await act(async () => {
      release();
      await gate;
    });
    expect(
      await screen.findByText('Load the history for this target before recording.'),
    ).toBeVisible();
    expect(screen.queryByRole('list', { name: 'Review history' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Record correction' })).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Load review history' }));
    expect(await screen.findByText('No human reviews recorded for this target.')).toBeVisible();
    expect(requested).toEqual(['ground-activity', 'maritime-activity']);
    expect(screen.getByRole('button', { name: 'Record review' })).toBeDisabled();
  });
});
