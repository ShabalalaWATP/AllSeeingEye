import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { LayerPanel } from './LayerPanel';

it('owns the shared time window without repeating layer or appearance controls', async () => {
  const changeWindow = vi.fn();
  const props = {
    counts: { social: 7 },
    stats: null,
    status: 'live' as const,
    error: null,
    onWindow: changeWindow,
  };
  const { rerender } = render(<LayerPanel {...props} windowHours={null} />);
  const user = userEvent.setup();
  expect(screen.getByRole('region', { name: 'Event time controls' })).toBeInTheDocument();
  expect(screen.getByRole('heading', { name: 'Event time' })).toBeVisible();
  expect(screen.queryByRole('switch')).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Show all topics' })).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Clear time filter' })).toBeDisabled();
  await user.click(screen.getByRole('radio', { name: '6 h' }));
  expect(changeWindow).toHaveBeenCalledExactlyOnceWith(6);
  rerender(<LayerPanel {...props} windowHours={6} />);
  await user.click(screen.getByRole('button', { name: 'Clear time filter' }));
  expect(changeWindow).toHaveBeenLastCalledWith(null);
  expect(screen.getByRole('button', { name: 'Reload live events' })).not.toBeVisible();
  await user.click(screen.getByText('Connection and coverage'));
  expect(screen.getByRole('button', { name: 'Reload live events' })).toBeVisible();
});

it('opens connection coverage without changing the selected time window', async () => {
  const changeWindow = vi.fn();
  const user = userEvent.setup();
  render(
    <LayerPanel
      counts={{}}
      stats={null}
      status="live"
      error={null}
      windowHours={6}
      onWindow={changeWindow}
    />,
  );
  expect(screen.getByRole('radio', { name: '6 h' })).toBeChecked();
  await user.click(screen.getByText('Connection and coverage'));
  expect(screen.getByRole('button', { name: 'Reload live events' })).toBeVisible();
  await user.click(screen.getByText('Connection and coverage'));
  expect(screen.getByRole('button', { name: 'Reload live events' })).not.toBeVisible();
  expect(screen.getByRole('radio', { name: '6 h' })).toBeChecked();
  expect(changeWindow).not.toHaveBeenCalled();
});
