import { fireEvent, screen, within } from '@testing-library/react';
import { expect, it } from 'vitest';

import { report } from '@/test/fixtures';
import { renderApp } from '@/test/render';

it('keeps the keyboard loop on reachable summaries and returns focus on Escape', async () => {
  const { user } = renderApp(`/reports/${report.report.id}`, 'user');
  const opener = await screen.findByRole('button', { name: 'Sources & methods' });
  await user.click(opener);
  const dialog = await screen.findByRole('dialog', { name: 'Sources and methods' });
  const close = within(dialog).getByRole('button', { name: 'Close' });
  expect(close).toHaveFocus();

  const hidden = document.createElement('div');
  hidden.hidden = true;
  hidden.innerHTML = '<button type="button">Hidden action</button>';
  dialog.append(hidden);
  const styledHidden = document.createElement('div');
  styledHidden.style.display = 'none';
  styledHidden.innerHTML = '<button type="button">Styled hidden action</button>';
  dialog.append(styledHidden);
  const details = document.createElement('details');
  details.innerHTML =
    '<summary>Last reachable summary</summary><button type="button">Closed action</button>';
  dialog.append(details);
  const summary = within(dialog).getByText('Last reachable summary');
  summary.focus();
  fireEvent.keyDown(document, { key: 'Tab' });
  expect(close).toHaveFocus();
  fireEvent.keyDown(document, { key: 'Tab', shiftKey: true });
  expect(summary).toHaveFocus();

  fireEvent.keyDown(document, { key: 'Escape' });
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  expect(opener).toHaveFocus();
});
