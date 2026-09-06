import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { fileNameFor } from '@/lib/download';
import { report, reportSummary } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

describe('report versions', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('regenerates into a new version and lists every version', async () => {
    let posted = 0;
    let served = 0;
    server.use(
      http.post('/api/reports/:id/versions', () => {
        posted += 1;
        return HttpResponse.json(
          {
            report: { ...reportSummary, latest_version: 2 },
            version: { ...report.version, number: 2 },
          },
          { status: 201 },
        );
      }),
      http.get('/api/reports/:id', ({ request }) => {
        served += 1;
        const version = new URL(request.url).searchParams.get('version');
        const latest = posted > 0 ? 2 : 1;
        const number = version === null ? latest : Number(version);
        return HttpResponse.json({
          report: { ...reportSummary, latest_version: latest },
          version: { ...report.version, number },
        });
      }),
    );
    const { user } = renderApp(`/reports/${reportSummary.id}`, 'user');
    await screen.findByRole('heading', { name: 'Intelligence summary: Ukraine' });
    const versions = screen.getByRole('navigation', { name: 'Versions' });
    expect(within(versions).getAllByRole('link')).toHaveLength(1);
    await user.click(screen.getByRole('button', { name: 'Regenerate' }));
    await waitFor(() => {
      expect(within(versions).getAllByRole('link')).toHaveLength(2);
    });
    expect(posted).toBe(1);
    expect(served).toBeGreaterThanOrEqual(2);
    expect(within(versions).getByRole('link', { name: '2' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    await user.click(within(versions).getByRole('link', { name: '1' }));
    await waitFor(() => {
      expect(
        within(screen.getByRole('navigation', { name: 'Versions' })).getByRole('link', {
          name: '1',
        }),
      ).toHaveAttribute('aria-current', 'page');
    });
  });

  it('downloads the Markdown through the API as a saved file', async () => {
    const createObjectURL = vi.fn(() => 'blob:report');
    const revokeObjectURL = vi.fn();
    Object.assign(URL, { createObjectURL, revokeObjectURL });
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(() => undefined);
    const { user } = renderApp(`/reports/${reportSummary.id}`, 'user');
    await screen.findByRole('heading', { name: 'Intelligence summary: Ukraine' });
    await user.click(screen.getByRole('button', { name: 'Download Markdown' }));
    await waitFor(() => {
      expect(click).toHaveBeenCalledTimes(1);
    });
    expect(createObjectURL).toHaveBeenCalledTimes(1);
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:report');
  });

  it('builds safe file names', () => {
    expect(fileNameFor('Intelligence summary: Ukraine-v1', 'md')).toBe(
      'intelligence-summary-ukraine-v1.md',
    );
    expect(fileNameFor('   ', 'md')).toBe('report.md');
  });
});
