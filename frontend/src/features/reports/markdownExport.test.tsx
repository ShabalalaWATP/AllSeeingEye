import { render, screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { saveTextFile } from '@/lib/download';
import { saveBinaryFile } from '@/lib/downloadBinary';
import { server } from '@/test/server';

import { ReportExports } from './ReportExports';

vi.mock('@/lib/download', async (original) => ({
  ...(await original<typeof import('@/lib/download')>()),
  saveTextFile: vi.fn(),
}));
vi.mock('@/lib/downloadBinary', () => ({ saveBinaryFile: vi.fn() }));

describe('portable Markdown export', () => {
  beforeEach(() => vi.clearAllMocks());

  it('uses the server ZIP filename when figures are included', async () => {
    server.use(
      http.get('/api/reports/:id/markdown', ({ request }) => {
        expect(request.headers.get('Accept')).toBe('application/zip, text/markdown;q=0.9');
        return new HttpResponse('package', {
          headers: {
            'Content-Type': 'application/zip',
            'Content-Disposition': 'attachment; filename="report-safe-v2-markdown.zip"',
          },
        });
      }),
    );
    render(<ReportExports id="safe" version={2} title="Ignored title" preferred="md" />);

    await userEvent.setup().click(screen.getByRole('button', { name: 'Export' }));
    expect(
      screen.getByText('Portable report; figures include local images in a ZIP'),
    ).toBeVisible();
    await userEvent.setup().click(screen.getByRole('menuitem', { name: 'Download Markdown' }));

    await waitFor(() => {
      expect(saveBinaryFile).toHaveBeenCalledWith(
        'report-safe-v2-markdown.zip',
        expect.objectContaining({ type: 'application/zip' }),
      );
    });
    expect(saveTextFile).not.toHaveBeenCalled();
  });

  it('uses the server Markdown filename when there are no figures', async () => {
    server.use(
      http.get(
        '/api/reports/:id/markdown',
        () =>
          new HttpResponse('report text', {
            headers: {
              'Content-Type': 'text/markdown; charset=utf-8',
              'Content-Disposition': 'attachment; filename="report-safe-v3.md"',
            },
          }),
      ),
    );
    render(<ReportExports id="safe" version={3} title="Ignored title" preferred="md" />);

    await userEvent.setup().click(screen.getByRole('button', { name: 'Export' }));
    await userEvent.setup().click(screen.getByRole('menuitem', { name: 'Download Markdown' }));

    await waitFor(() => {
      expect(saveTextFile).toHaveBeenCalledWith('report-safe-v3.md', 'report text');
    });
    expect(saveBinaryFile).not.toHaveBeenCalled();
  });
});
