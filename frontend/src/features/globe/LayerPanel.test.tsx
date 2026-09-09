import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { LayerPanel } from './LayerPanel';

it('owns additional topics and the shared time window without repeating category or appearance switches', async () => {
  const toggleCategory = vi.fn();
  const changeWindow = vi.fn();
  const props = {
    counts: { cyber: 7 },
    hidden: [],
    stats: null,
    status: 'live' as const,
    error: null,
    onWindow: changeWindow,
    onToggle: toggleCategory,
  };
  const { rerender } = render(<LayerPanel {...props} windowHours={null} />);
  const user = userEvent.setup();
  expect(screen.getAllByRole('switch')).toHaveLength(5);
  expect(
    screen.queryByRole('switch', { name: /FIRMS|Flights|Boats|GNSS|Day and night|graphics/ }),
  ).not.toBeInTheDocument();
  await user.click(screen.getByRole('switch', { name: 'Cyber 7' }));
  expect(toggleCategory).toHaveBeenCalledExactlyOnceWith('cyber');
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

it('restores only hidden additional topics without changing main layers or time', async () => {
  const toggle = vi.fn();
  const window = vi.fn();
  const user = userEvent.setup();
  render(
    <LayerPanel
      counts={{}}
      hidden={['cyber', 'political', 'aviation']}
      stats={null}
      status="live"
      error={null}
      windowHours={6}
      onWindow={window}
      onToggle={toggle}
    />,
  );
  await user.click(screen.getByRole('button', { name: 'Show all topics' }));
  expect(toggle.mock.calls).toEqual([['cyber'], ['political']]);
  expect(window).not.toHaveBeenCalled();
});
