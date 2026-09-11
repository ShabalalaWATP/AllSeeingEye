import { reportJob, readReportJobRequest } from '@/test/reportJobFixture';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { expect, it, vi } from 'vitest';
import { server } from '@/test/server';
import { applySession, renderApp } from '@/test/render';
import { secPage, secChoice, secReceipt } from '@/test/fixtures.secFilings';
import type { SecFilingsSearch } from '@/lib/api/secFilings';
import type { ReportRequest } from '@/lib/api/reports';
import { DocumentResearchInput } from './DocumentResearchInput';
async function open() {
  await userEvent.click(await screen.findByRole('button', { name: 'Find an SEC filing' }));
  fireEvent.change(screen.getByLabelText('SEC company identifier (CIK)'), {
    target: { value: '320193' },
  });
}
function handlers() {
  server.use(
    http.post('/api/research/sec/filings', () => HttpResponse.json(secPage())),
    http.post('/api/research/sec/filings/:id/import', () =>
      HttpResponse.json(secReceipt(), { status: 201 }),
    ),
  );
}
it('uses the imported document ID for actual research and cannot start from metadata alone', async () => {
  handlers();
  const requests: ReportRequest[] = [];
  server.use(
    http.post('/api/report-jobs', async ({ request }) => {
      requests.push(await readReportJobRequest(request));
      return HttpResponse.json(reportJob(), { status: 202 });
    }),
  );
  renderApp('/research?question=Analyse%20this%20filing', 'user');
  await screen.findByLabelText('Research focus');
  await userEvent.click(screen.getByText('Scope and sources'));
  await userEvent.selectOptions(screen.getByLabelText('Research focus'), 'document');
  await open();
  await userEvent.click(screen.getByRole('button', { name: 'Discover SEC filings' }));
  await screen.findByText('Filing metadata, documents not imported yet');
  await userEvent.click(screen.getByRole('button', { name: 'Start research' }));
  expect(requests).toHaveLength(0);
  await userEvent.click(
    screen.getByRole('button', { name: `Import document ${secChoice().accession}` }),
  );
  await screen.findByRole('heading', { name: 'Attached filing document: filing.htm' });
  await userEvent.click(screen.getByRole('button', { name: 'Start research' }));
  await waitFor(() => expect(requests).toHaveLength(1));
  expect(requests[0]).toMatchObject({
    research_focus: 'document',
    research_input_id: secReceipt().id,
  });
});
it('sends only bounded CIK/date/paging inputs and clears stale results when the query changes', async () => {
  applySession('user');
  const bodies: SecFilingsSearch[] = [];
  server.use(
    http.post('/api/research/sec/filings', async ({ request }) => {
      const body = (await request.json()) as SecFilingsSearch;
      bodies.push(body);
      return HttpResponse.json(
        secPage({
          archive_page: body.archive_page,
          offset: body.offset,
          next_offset: body.offset === 0 ? 20 : null,
        }),
      );
    }),
  );
  render(<DocumentResearchInput onChange={vi.fn()} />);
  await open();
  await userEvent.click(screen.getByRole('button', { name: 'Discover SEC filings' }));
  await screen.findByText('Filing metadata, documents not imported yet');
  await userEvent.click(screen.getByRole('button', { name: 'Next filing results' }));
  await waitFor(() => expect(bodies).toHaveLength(2));
  await screen.findByText('Filing metadata, documents not imported yet');
  await userEvent.click(screen.getByRole('button', { name: 'Previous filing results' }));
  await waitFor(() => expect(bodies).toHaveLength(3));
  await screen.findByText('Filing metadata, documents not imported yet');
  await userEvent.click(screen.getByRole('button', { name: 'Older submissions file' }));
  await screen.findByText(/Older submissions file 1 of 1/);
  expect(bodies[1]).toMatchObject({ cik: '320193', archive_page: 0, offset: 20 });
  expect(bodies[3]).toMatchObject({ archive_page: 1, offset: 0 });
  await userEvent.click(screen.getByRole('button', { name: 'Newer submissions file' }));
  await screen.findByText('Filing metadata, documents not imported yet');
  fireEvent.change(screen.getByLabelText('SEC company identifier (CIK)'), {
    target: { value: '123' },
  });
  expect(screen.queryByText('Filing metadata, documents not imported yet')).not.toBeInTheDocument();
  expect(bodies.every((body) => !('url' in body))).toBe(true);
});
it('shows no-results coverage and fixed contact configuration guidance without requesting an API key', async () => {
  applySession('admin');
  let fail = true;
  server.use(
    http.post('/api/research/sec/filings', () =>
      fail
        ? HttpResponse.json(
            { error: { code: 'unavailable', message: 'SEC contact is not configured.' } },
            { status: 503 },
          )
        : HttpResponse.json(secPage({ items: [], archive_pages: 0 })),
    ),
  );
  render(<DocumentResearchInput onChange={vi.fn()} />);
  await open();
  await userEvent.click(screen.getByRole('button', { name: 'Discover SEC filings' }));
  await screen.findByText('SEC contact is not configured.');
  expect(screen.getByText(/ASE_FEEDS_CONTACT/)).toBeInTheDocument();
  expect(screen.queryByLabelText(/API key/i)).not.toBeInTheDocument();
  fail = false;
  await userEvent.click(screen.getByRole('button', { name: 'Discover SEC filings' }));
  await screen.findByText(/No selectable filings on this page/);
  expect(screen.getByRole('button', { name: 'Older submissions file' })).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Next filing results' })).toBeDisabled();
});
it('rejects malformed CIKs and dates locally before making a discovery request', async () => {
  applySession('user');
  const calls = vi.fn();
  server.use(
    http.post('/api/research/sec/filings', () => {
      calls();
      return HttpResponse.json(secPage());
    }),
  );
  render(<DocumentResearchInput onChange={vi.fn()} />);
  await open();
  fireEvent.change(screen.getByLabelText('SEC company identifier (CIK)'), {
    target: { value: 'https://example.com' },
  });
  await userEvent.click(screen.getByRole('button', { name: 'Discover SEC filings' }));
  await screen.findByText(/Enter a CIK with 1 to 10 digits/);
  expect(calls).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText('SEC company identifier (CIK)'), {
    target: { value: '320193' },
  });
  fireEvent.change(screen.getByLabelText('Filed from'), { target: { value: '1980-01-01' } });
  await userEvent.click(screen.getByRole('button', { name: 'Discover SEC filings' }));
  expect(calls).not.toHaveBeenCalled();
});
