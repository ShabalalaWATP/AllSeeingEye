import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { delay, http, HttpResponse } from 'msw';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { apiError } from '@/test/handlers';
import { applySession } from '@/test/render';
import { server } from '@/test/server';

import { ReportExports } from './ReportExports';

let release: () => void = () => undefined;
let fail = true;

beforeEach(() => {
  applySession('user');
  fail = true;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  server.use(
    http.get('/api/reports/:id/export/:format', async () => {
      await gate;
      await delay(10);
      return fail
        ? apiError(503, 'renderer_busy', 'The PDF renderer is busy. Try again shortly.')
        : new HttpResponse('%PDF document', {
            headers: { 'Content-Type': 'application/octet-stream' },
          });
    }),
  );
  Object.assign(URL, { createObjectURL: vi.fn(() => 'blob:test'), revokeObjectURL: vi.fn() });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('report export progress', () => {
  it('shows the format being prepared on the trigger, even after the menu closes', async () => {
    const user = userEvent.setup();
    render(<ReportExports id="report" version={2} title="Ukraine" />);
    const trigger = screen.getByRole('button', { name: 'Export' });
    await user.click(trigger);
    await user.click(screen.getByRole('menuitem', { name: 'Download PDF' }));
    // A click elsewhere mid-request closes the menu but not the progress.
    fireEvent.mouseDown(document.body);
    await waitFor(() => {
      expect(screen.queryByRole('menu')).not.toBeInTheDocument();
    });
    expect(trigger).toHaveAttribute('aria-busy', 'true');
    expect(trigger).toHaveTextContent('Preparing PDF…');
    expect(trigger).toHaveAccessibleName('Export');
    expect(trigger.querySelector('[data-busy-indicator]')).not.toBeNull();
    expect(screen.getByRole('status')).toHaveTextContent('Preparing PDF…');
    // A second activation while preparing does nothing.
    await user.click(trigger);
    expect(screen.queryByRole('menu')).not.toBeInTheDocument();

    release();
    const error = await screen.findByRole('alert');
    expect(error).toHaveTextContent('The PDF renderer is busy.');
    expect(screen.queryByRole('menu')).not.toBeInTheDocument();
    expect(trigger).toHaveAttribute('aria-busy', 'false');
    expect(trigger).toHaveTextContent(/^↓ Export$/);
    const region = screen.getByRole('group', { name: 'Document exports' });
    expect(within(region).getByRole('alert')).toBe(error);
  });

  it('keeps the failure visible until a retry succeeds', async () => {
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(() => undefined);
    const user = userEvent.setup();
    render(<ReportExports id="report" version={2} title="Ukraine" />);
    const trigger = screen.getByRole('button', { name: 'Export' });
    await user.click(trigger);
    await user.click(screen.getByRole('menuitem', { name: 'Download DOCX' }));
    expect(trigger).toHaveTextContent('Preparing DOCX…');
    release();
    expect(await screen.findByRole('alert')).toHaveTextContent('The PDF renderer is busy.');
    await user.click(trigger);
    // The menu opening does not hide the earlier failure.
    expect(screen.getByRole('alert')).toBeInTheDocument();
    fail = false;
    await user.click(screen.getByRole('menuitem', { name: 'Download DOCX' }));
    await waitFor(() => {
      expect(click).toHaveBeenCalledTimes(1);
    });
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(trigger).toHaveAttribute('aria-busy', 'false');
  });
});
