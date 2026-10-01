import { render, screen, waitFor, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { expect, it, vi } from 'vitest';

import { saveBinaryFile } from '@/lib/downloadBinary';
import { apiError } from '@/test/handlers';
import { applySession } from '@/test/render';
import { server } from '@/test/server';
import { ReportExports } from './ReportExports';

vi.mock('@/lib/downloadBinary', () => ({ saveBinaryFile: vi.fn() }));

function pendingResponse() {
  let release: (response: Response) => void = () => undefined;
  const pending = new Promise<Response>((resolve) => {
    release = (response) => resolve(response);
  });
  return { pending, release };
}

it('keeps STIX progress visible after dismissal without stealing focus on completion', async () => {
  applySession('user');
  const gate = pendingResponse();
  const queries: string[] = [];
  server.use(
    http.get('/api/reports/:id/stix', ({ request }) => {
      queries.push(new URL(request.url).search);
      return gate.pending;
    }),
  );
  const user = userEvent.setup();
  render(
    <>
      <ReportExports id="report" version={3} title="Cyber briefing" />
      <button type="button">Read another report</button>
    </>,
  );
  const trigger = screen.getByRole('button', { name: 'Export' });
  await user.click(trigger);
  expect(screen.getByRole('menuitem', { name: 'Download STIX 2.1' })).toBeDisabled();
  await user.selectOptions(screen.getByRole('combobox', { name: 'STIX sharing marking' }), 'green');
  await user.click(screen.getByRole('menuitem', { name: 'Download STIX 2.1' }));
  await waitFor(() => expect(queries).toEqual(['?version=3&tlp=green']));
  expect(trigger).toHaveAttribute('aria-disabled', 'true');
  await user.click(trigger);
  expect(screen.getByRole('menu')).toBeVisible();
  expect(queries).toHaveLength(1);
  expect(trigger).toHaveTextContent('Preparing STIX 2.1…');
  expect(screen.getByRole('status')).toHaveTextContent('Preparing STIX 2.1…');
  const elsewhere = screen.getByRole('button', { name: 'Read another report' });
  await user.click(elsewhere);
  expect(screen.queryByRole('menu')).not.toBeInTheDocument();
  expect(trigger).toHaveAttribute('aria-busy', 'true');

  gate.release(new HttpResponse('{}', { headers: { 'Content-Type': 'application/stix+json' } }));
  await waitFor(() => expect(trigger).toHaveAttribute('aria-busy', 'false'));
  expect(elsewhere).toHaveFocus();
  expect(saveBinaryFile).toHaveBeenCalledWith(
    'cyber-briefing-v3.stix.json',
    expect.objectContaining({ type: 'application/stix+json' }),
  );
});

it('retains a STIX failure beside the closed menu and retries with the selected marking', async () => {
  applySession('user');
  const gate = pendingResponse();
  const queries: string[] = [];
  server.use(
    http.get('/api/reports/:id/stix', ({ request }) => {
      queries.push(new URL(request.url).search);
      return queries.length === 1
        ? gate.pending
        : new HttpResponse('{}', { headers: { 'Content-Type': 'application/stix+json' } });
    }),
  );
  const user = userEvent.setup();
  render(<ReportExports id="report" version={4} title="Cyber briefing" />);
  const trigger = screen.getByRole('button', { name: 'Export' });
  await user.click(trigger);
  await user.selectOptions(screen.getByRole('combobox', { name: 'STIX sharing marking' }), 'amber');
  await user.click(screen.getByRole('menuitem', { name: 'Download STIX 2.1' }));
  await waitFor(() => expect(queries).toHaveLength(1));
  gate.release(apiError(409, 'conflict', 'This report version changed. Select it again.'));
  const error = await screen.findByRole('alert');
  expect(error).toHaveTextContent('This report version changed.');
  expect(screen.queryByRole('menu')).not.toBeInTheDocument();
  expect(trigger).toHaveFocus();
  expect(within(screen.getByRole('group', { name: 'Document exports' })).getByRole('alert')).toBe(
    error,
  );
  expect(saveBinaryFile).not.toHaveBeenCalled();

  await user.click(trigger);
  expect(screen.getByRole('alert')).toBeVisible();
  expect(screen.getByRole('combobox', { name: 'STIX sharing marking' })).toHaveValue('amber');
  await user.selectOptions(screen.getByRole('combobox', { name: 'STIX sharing marking' }), 'red');
  await user.click(screen.getByRole('menuitem', { name: 'Download STIX 2.1' }));
  await waitFor(() => expect(saveBinaryFile).toHaveBeenCalledTimes(1));
  expect(queries).toEqual(['?version=4&tlp=amber', '?version=4&tlp=red']);
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  expect(trigger).toHaveFocus();
});
