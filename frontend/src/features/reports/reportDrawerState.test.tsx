import { screen, within } from '@testing-library/react';
import { expect, it } from 'vitest';

import { report } from '@/test/fixtures';
import { renderApp } from '@/test/render';

it('keeps in-progress review work through view switches, Escape and the backdrop', async () => {
  const { user } = renderApp(`/reports/${report.report.id}`, 'user');
  const opener = await screen.findByRole('button', { name: 'Sources & methods' });
  await user.click(opener);
  let dialog = await screen.findByRole('dialog', { name: 'Sources and methods' });
  await user.click(await within(dialog).findByRole('button', { name: 'Review' }));
  const monitors = await within(dialog).findByRole('button', { name: 'Monitor annotations' });
  await user.click(monitors);
  expect(monitors).toHaveAttribute('aria-expanded', 'true');

  await user.click(within(dialog).getByRole('button', { name: 'Collection' }));
  expect(monitors).not.toBeVisible();
  await user.click(within(dialog).getByRole('button', { name: 'Review' }));
  expect(monitors).toBeVisible();
  expect(monitors).toHaveAttribute('aria-expanded', 'true');

  await user.keyboard('{Escape}');
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  expect(opener).toHaveFocus();
  await user.click(opener);
  dialog = await screen.findByRole('dialog', { name: 'Sources and methods' });
  expect(within(dialog).getByRole('button', { name: 'Monitor annotations' })).toBe(monitors);
  expect(monitors).toHaveAttribute('aria-expanded', 'true');

  await user.click(screen.getByRole('button', { name: 'Close sources and methods' }));
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  await user.click(opener);
  expect(monitors).toHaveAttribute('aria-expanded', 'true');
  expect(monitors).toBeVisible();
});
