import { screen } from '@testing-library/react';
import { expect, it } from 'vitest';

import { reportSummary } from '@/test/fixtures';
import { renderApp } from '@/test/render';

it('keeps focused and cited supporting content clear of the sticky view bar', async () => {
  const { user } = renderApp(`/reports/${reportSummary.id}`, 'user');
  await screen.findByRole('heading', { name: 'Intelligence summary: Ukraine' });
  await user.click(screen.getByRole('button', { name: 'Sources & methods' }));
  const views = await screen.findByRole('navigation', { name: 'Supporting report views' });
  expect(views).toHaveClass('sticky', 'top-0');
  // The drawer owns the scroll container, so the margin sits on the content itself: focus
  // scrolling and the cited-evidence scrollIntoView stop below the bar, not under it.
  const content = views.nextElementSibling;
  expect(content).toHaveClass('[&_*]:scroll-mt-16');
});
