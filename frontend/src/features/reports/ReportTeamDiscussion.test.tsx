import { render, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';

import { followUpAvailability } from '@/lib/followUpScope';
import type { ReportDiscussion } from '@/lib/api/teamBoard';
import { report } from '@/test/fixtures.reports';
import { apiError } from '@/test/handlers';
import { server } from '@/test/server';

import { ReportPageFooter } from './ReportPageFooter';
import { ReportTeamDiscussion } from './ReportTeamDiscussion';

const reportId = report.report.id;
const teamId = '11111111-1111-4111-8111-111111111111';
const postId = '33333333-3333-4333-8333-333333333333';

function serve(discussion: ReportDiscussion | 404) {
  const requests: string[] = [];
  server.use(
    http.get('/api/reports/:id/team-discussion', ({ params }) => {
      requests.push(String(params.id));
      if (discussion === 404) return apiError(404, 'not_found', 'Not found.');
      return HttpResponse.json(discussion);
    }),
  );
  return requests;
}

function renderDiscussion(version = 2) {
  return render(
    <MemoryRouter>
      <ReportTeamDiscussion reportId={reportId} version={version} />
    </MemoryRouter>,
  );
}

describe('ReportTeamDiscussion', () => {
  it('links to the latest team thread and starts a thread for this exact version', async () => {
    const requests = serve({ team_id: teamId, count: 2, latest_post_id: postId, can_post: true });
    renderDiscussion(2);
    const thread = await screen.findByRole('link', { name: 'Team discussion (2)' });
    expect(thread).toHaveAttribute('href', `/teams?team=${teamId}&board=thread&post=${postId}`);
    const start = screen.getByRole('link', { name: 'Discuss this version' });
    expect(start).toHaveAttribute(
      'href',
      `/teams?team=${teamId}&board=thread&subject=report_version&subject_id=${reportId}&version=2`,
    );
    expect(requests).toEqual([reportId]);
  });

  it('shows an empty count without a thread link, and no start link when read-only', async () => {
    serve({ team_id: teamId, count: 0, latest_post_id: null, can_post: false });
    renderDiscussion();
    expect(await screen.findByText('Team discussion (0)')).toBeInTheDocument();
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
  });

  it('renders nothing for personal reports or when the board cannot be read', async () => {
    const personal = serve({ team_id: null, count: 0, latest_post_id: null, can_post: false });
    const { container, unmount } = renderDiscussion();
    await waitFor(() => expect(personal).toHaveLength(1));
    expect(container).toBeEmptyDOMElement();
    unmount();
    const refused = serve(404);
    const second = renderDiscussion();
    await waitFor(() => expect(refused).toHaveLength(1));
    expect(second.container).toBeEmptyDOMElement();
  });

  it('is mounted in the report page footer for the version being read', async () => {
    serve({ team_id: teamId, count: 1, latest_post_id: postId, can_post: true });
    render(
      <MemoryRouter>
        <ReportPageFooter
          reportId={reportId}
          version={report.version}
          followUp={followUpAvailability({ report: report.report, version: report.version })}
        />
      </MemoryRouter>,
    );
    expect(await screen.findByRole('link', { name: 'Team discussion (1)' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Discuss this version' })).toHaveAttribute(
      'href',
      expect.stringContaining(`&version=${String(report.version.number)}`),
    );
  });
});
