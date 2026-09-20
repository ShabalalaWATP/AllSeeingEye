import { fireEvent, render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { MapControlLabel } from './MapControlLabel';
it('shows a visible label outside the clipping rail on hover and removes it on leave', async () => {
  const user = userEvent.setup();
  render(
    <div data-testid="rail" style={{ overflow: 'hidden' }}>
      <MapControlLabel label="Flights: shown">
        <button>Plane</button>
      </MapControlLabel>
    </div>,
  );
  await user.hover(screen.getByRole('button'));
  const tooltip = screen.getByRole('tooltip');
  expect(tooltip).toHaveTextContent('Flights: shown');
  expect(screen.getByTestId('rail')).not.toContainElement(tooltip);
  expect(tooltip.parentElement).toBe(document.body);
  await user.unhover(screen.getByRole('button'));
  expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
});
it('supports keyboard focus, Escape and viewport scrolling', async () => {
  const user = userEvent.setup();
  render(
    <MapControlLabel label="Map style">
      <button>Style</button>
    </MapControlLabel>,
  );
  await user.tab();
  expect(screen.getByRole('tooltip')).toHaveTextContent('Map style');
  await user.keyboard('{Escape}');
  expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  await user.hover(screen.getByRole('button'));
  fireEvent.scroll(window);
  expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  await user.unhover(screen.getByRole('button'));
  await user.hover(screen.getByRole('button'));
  fireEvent.resize(window);
  expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
});

it('places labels left of the right rail, clamps to the viewport and keeps them for unrelated keys', () => {
  render(
    <MapControlLabel label="Radio planning">
      <button>Radio</button>
    </MapControlLabel>,
  );
  const button = screen.getByRole('button', { name: 'Radio' });
  const wrapper = button.parentElement!;
  vi.spyOn(wrapper, 'getBoundingClientRect').mockReturnValue(
    new DOMRect(window.innerWidth - 50, window.innerHeight + 50, 40, 40),
  );
  fireEvent.mouseEnter(wrapper);
  expect(screen.getByRole('tooltip')).toHaveStyle({
    left: `${window.innerWidth - 58}px`,
    top: `${window.innerHeight - 20}px`,
    transform: 'translate(-100%, -50%)',
  });
  fireEvent.keyDown(window, { key: 'ArrowRight' });
  expect(screen.getByRole('tooltip')).toBeVisible();
  fireEvent.blur(button);
  expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
});
