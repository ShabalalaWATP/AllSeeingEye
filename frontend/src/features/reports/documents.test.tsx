import { render, screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { delay, http, HttpResponse } from 'msw';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { saveBinaryFile } from '@/lib/downloadBinary';
import { applySession } from '@/test/render';
import { server } from '@/test/server';

import { ReportDiff } from './ReportDiff';
import { ReportExports } from './ReportExports';

const changes = [
  {
    section: 'Content',
    path: 'sourcing_statement',
    kind: 'changed',
    before: 'Original',
    after: '<script>literal</script>',
  },
  { section: 'Evidence', path: 'E1.grade', kind: 'added', before: null, after: 'A1' },
  {
    section: 'Content',
    path: 'assumptions[1]',
    kind: 'removed',
    before: 'Unconfirmed assumption',
    after: null,
  },
];

describe('report documents', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('downloads both binary formats for the selected frozen version', async () => {
    applySession('user');
    const requests: string[] = [];
    server.use(
      http.get('/api/reports/:id/export/:format', ({ request, params }) => {
        requests.push(request.url);
        expect(request.headers.get('Authorization')).toMatch(/^Bearer /);
        return new HttpResponse(params.format === 'pdf' ? '%PDF document' : 'PK document', {
          headers: { 'Content-Type': 'application/octet-stream' },
        });
      }),
    );
    const create = vi.fn(() => 'blob:test');
    const revoke = vi.fn();
    Object.assign(URL, { createObjectURL: create, revokeObjectURL: revoke });
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(() => undefined);
    render(<ReportExports id="report" version={2} title="Ukraine" />);
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'Download PDF' }));
    await waitFor(() => {
      expect(click).toHaveBeenCalledTimes(1);
    });
    await user.click(screen.getByRole('button', { name: 'Download DOCX' }));
    await waitFor(() => {
      expect(click).toHaveBeenCalledTimes(2);
    });
    expect(requests[0]).toContain('/export/pdf?version=2');
    expect(requests[1]).toContain('/export/docx?version=2');
    expect(revoke).toHaveBeenCalledTimes(2);
  });

  it('reports download errors and releases URLs after browser download failures', async () => {
    server.use(
      http.get('/api/reports/:id/export/:format', () => new HttpResponse(null, { status: 503 })),
    );
    render(<ReportExports id="report" version={1} title="Title" />);
    await userEvent.setup().click(screen.getByRole('button', { name: 'Download PDF' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('503');
    const revoke = vi.fn();
    Object.assign(URL, { createObjectURL: vi.fn(() => 'blob:failure'), revokeObjectURL: revoke });
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {
      throw new Error('Save failed');
    });
    expect(() => saveBinaryFile('report.pdf', new Blob(['test']))).toThrow('Save failed');
    expect(revoke).toHaveBeenCalledWith('blob:failure');
    expect(document.querySelector('a[download]')).toBeNull();
  });

  it('explains why comparison needs another version', async () => {
    render(<ReportDiff id="report" current={1} latest={1} />);
    await userEvent.setup().click(screen.getByText('Compare versions'));
    expect(screen.getByText(/Regenerate this report to create a second version/)).toBeVisible();
    expect(screen.queryByRole('button', { name: 'Compare selected versions' })).toBeNull();
  });

  it('shows accessible before and after fields, literal markup and loading state', async () => {
    server.use(
      http.get('/api/reports/:id/diff', async () => {
        await delay(80);
        return HttpResponse.json({ from_version: 1, to_version: 2, changes });
      }),
    );
    render(<ReportDiff id="report" current={2} latest={2} />);
    const user = userEvent.setup();
    await user.click(screen.getByText('Compare versions'));
    await user.click(screen.getByRole('button', { name: 'Compare selected versions' }));
    expect(await screen.findByText('Comparing report versions')).toBeVisible();
    expect(await screen.findByText('<script>literal</script>')).toBeVisible();
    expect(screen.getByText('Original')).toBeVisible();
    expect(screen.getByText('Unconfirmed assumption')).toBeVisible();
    expect(screen.getByText('A1')).toBeVisible();
    expect(screen.getAllByText('Before')).toHaveLength(2);
    expect(screen.getAllByText('After')).toHaveLength(2);
    expect(screen.getByRole('status')).toHaveTextContent('3 changed fields');
    expect(document.querySelector('script')).toBeNull();
  });

  it('allows either version order, clears old results and handles no differences', async () => {
    const queries: string[] = [];
    server.use(
      http.get('/api/reports/:id/diff', ({ request }) => {
        queries.push(new URL(request.url).search);
        return HttpResponse.json({ from_version: 2, to_version: 1, changes: [] });
      }),
    );
    render(<ReportDiff id="report" current={2} latest={2} />);
    const user = userEvent.setup();
    await user.click(screen.getByText('Compare versions'));
    await user.selectOptions(screen.getByLabelText('From version'), '2');
    await user.selectOptions(screen.getByLabelText('To version'), '1');
    await user.click(screen.getByRole('button', { name: 'Compare selected versions' }));
    expect(await screen.findByText(/No changes to content/)).toBeVisible();
    expect(queries).toEqual(['?from_version=2&to_version=1']);
    await user.selectOptions(screen.getByLabelText('To version'), '2');
    expect(screen.queryByText(/No changes to content/)).toBeNull();
  });

  it('shows comparison failures and retries through the same authenticated API', async () => {
    let calls = 0;
    server.use(
      http.get('/api/reports/:id/diff', () => {
        calls += 1;
        return calls === 1
          ? new HttpResponse(null, { status: 404 })
          : HttpResponse.json({ from_version: 1, to_version: 2, changes: [] });
      }),
    );
    render(<ReportDiff id="report" current={2} latest={2} />);
    const user = userEvent.setup();
    await user.click(screen.getByText('Compare versions'));
    await user.click(screen.getByRole('button', { name: 'Compare selected versions' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('404');
    await user.click(screen.getByRole('button', { name: 'Retry comparison' }));
    expect(await screen.findByText(/No changes to content/)).toBeVisible();
  });
});
