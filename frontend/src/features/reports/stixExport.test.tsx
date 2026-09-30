import { render, screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { expect, it, vi } from 'vitest';
import { saveBinaryFile } from '@/lib/downloadBinary';
import { server } from '@/test/server';
import { ReportExports } from './ReportExports';

vi.mock('@/lib/downloadBinary', () => ({ saveBinaryFile: vi.fn() }));

it('requires a selected TLP and requests the displayed exact version', async () => {
  let calls = 0;
  server.use(
    http.get('/api/reports/:id/stix', ({ request }) => {
      calls += 1;
      const query = new URL(request.url).searchParams;
      expect(query.get('version')).toBe('2');
      expect(query.get('tlp')).toBe('red');
      return new HttpResponse('{}', { headers: { 'Content-Type': 'application/stix+json' } });
    }),
  );
  const user = userEvent.setup();
  render(<ReportExports id="fixture" version={2} title="Cyber report" />);
  await user.click(screen.getByRole('button', { name: 'Export' }));
  expect(screen.getByRole('menuitem', { name: 'Download STIX 2.1' })).toBeDisabled();
  expect(calls).toBe(0);
  await user.selectOptions(screen.getByRole('combobox', { name: 'STIX sharing marking' }), 'red');
  await user.click(screen.getByRole('menuitem', { name: 'Download STIX 2.1' }));
  await waitFor(() => expect(saveBinaryFile).toHaveBeenCalled());
  expect(calls).toBe(1);
});
