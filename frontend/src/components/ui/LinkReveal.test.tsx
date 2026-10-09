import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';

import { LinkReveal } from './LinkReveal';

const LINK = 'https://example.test/activate#token';

it('selects the link on focus and offers no dismiss control by default', async () => {
  render(<LinkReveal title="Reset link" link={LINK} expiresAt="2026-09-04T10:30:00Z" />);
  const input = screen.getByLabelText('Reset link');
  await userEvent.setup().click(input);
  expect(input).toHaveFocus();
  expect((input as HTMLInputElement).selectionEnd).toBe(LINK.length);
  expect(screen.queryByRole('button', { name: /Dismiss/ })).not.toBeInTheDocument();
});

it('dismisses through a control named after the link', async () => {
  const onDismiss = vi.fn();
  render(
    <LinkReveal
      title="Reset link"
      link={LINK}
      expiresAt="2026-09-04T10:30:00Z"
      onDismiss={onDismiss}
    />,
  );
  await userEvent.setup().click(screen.getByRole('button', { name: 'Dismiss Reset link' }));
  expect(onDismiss).toHaveBeenCalledTimes(1);
});
