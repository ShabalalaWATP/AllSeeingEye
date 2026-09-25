import { fireEvent, screen } from '@testing-library/react';

/** Reveal every research step; the form opens in quick mode with only question and scope. */
export async function openAdvancedResearch(): Promise<void> {
  const toggle = await screen.findByRole('button', { name: 'Advanced options' });
  if (toggle.getAttribute('aria-expanded') !== 'true') fireEvent.click(toggle);
}
