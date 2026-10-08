import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { expect, it, vi } from 'vitest';

import { saveBinaryFile } from '@/lib/downloadBinary';
import { server } from '@/test/server';
import { ReportExports } from './ReportExports';

vi.mock('@/lib/downloadBinary', () => ({ saveBinaryFile: vi.fn() }));

it('supports directional and boundary keyboard navigation without hijacking the marking selector', async () => {
  const user = userEvent.setup();
  render(<ReportExports id="report" version={4} title="Field report" />);
  const trigger = screen.getByRole('button', { name: 'Export' });
  await user.click(trigger);
  const pdf = screen.getByRole('menuitem', { name: 'Download PDF' });
  const docx = screen.getByRole('menuitem', { name: 'Download DOCX' });
  const stix = screen.getByRole('menuitem', { name: 'Download STIX 2.1' });
  expect(pdf).toHaveFocus();
  const marking = screen.getByRole('combobox', { name: 'STIX sharing marking' });
  await user.selectOptions(marking, 'amber');
  fireEvent.keyDown(marking, { key: 'End' });
  expect(marking).toHaveFocus();
  expect(stix).toBeEnabled();
  await user.tab();
  expect(pdf).toHaveFocus();
  await user.keyboard('{ArrowDown}');
  expect(docx).toHaveFocus();
  await user.keyboard('{ArrowUp}');
  expect(pdf).toHaveFocus();
  await user.keyboard('{ArrowUp}');
  expect(stix).toHaveFocus();
  await user.keyboard('{ArrowDown}');
  expect(pdf).toHaveFocus();
  await user.keyboard('{End}');
  expect(stix).toHaveFocus();
  await user.keyboard('{Home}');
  expect(pdf).toHaveFocus();
  await user.keyboard('x');
  expect(pdf).toHaveFocus();
  await user.keyboard('{Escape}');
  expect(screen.queryByRole('menu')).not.toBeInTheDocument();
  expect(trigger).toHaveFocus();
  expect(saveBinaryFile).not.toHaveBeenCalled();
});

it('describes why STIX is disabled until a marking is chosen', async () => {
  const user = userEvent.setup();
  render(<ReportExports id="report" version={4} title="Field report" />);
  await user.click(screen.getByRole('button', { name: 'Export' }));
  const stix = screen.getByRole('menuitem', { name: 'Download STIX 2.1' });
  expect(stix).toBeDisabled();
  expect(stix).toHaveAccessibleDescription('Choose a TLP marking above first.');
  const pdf = screen.getByRole('menuitem', { name: 'Download PDF' });
  expect(pdf).not.toHaveAttribute('aria-describedby');

  await user.selectOptions(screen.getByRole('combobox', { name: 'STIX sharing marking' }), 'green');
  expect(stix).toBeEnabled();
  expect(stix).not.toHaveAttribute('aria-describedby');
  expect(screen.queryByText('Choose a TLP marking above first.')).not.toBeInTheDocument();
});

it('uses the exact version and a safe ZIP fallback when Markdown has no server filename', async () => {
  server.use(
    http.get('/api/reports/:id/markdown', ({ request }) => {
      expect(new URL(request.url).searchParams.get('version')).toBe('4');
      return new HttpResponse('package', { headers: { 'Content-Type': 'application/zip' } });
    }),
  );
  const user = userEvent.setup();
  render(
    <ReportExports
      id="report"
      version={4}
      title="Field / report"
      preferred="md"
      status="needs_review"
    />,
  );
  const trigger = screen.getByRole('button', { name: 'Export' });
  await user.click(trigger);
  expect(
    screen.getByText('Every export repeats the review notice shown on this page.'),
  ).toBeVisible();
  await user.click(screen.getByRole('menuitem', { name: 'Download Markdown' }));
  await waitFor(() =>
    expect(saveBinaryFile).toHaveBeenCalledWith(
      'field-report-v4.zip',
      expect.objectContaining({ type: 'application/zip' }),
    ),
  );
  expect(screen.queryByRole('menu')).not.toBeInTheDocument();
  expect(trigger).toHaveFocus();
});
