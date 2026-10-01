import { screen, within } from '@testing-library/react';
import { expect, it } from 'vitest';

import { renderApp } from '@/test/render';
import { openAdvancedResearch } from '@/test/researchForm';

it('points the source step at the read-only catalogue an analyst can open', async () => {
  renderApp('/research', 'user');
  await screen.findByRole('form', { name: 'Research a question' });
  await openAdvancedResearch();
  const step = within(screen.getByRole('region', { name: 'What to read' }));
  const link = step.getByRole('link', { name: 'Browse the source catalogue' });
  expect(link).toHaveAttribute('href', '/sources');
});
