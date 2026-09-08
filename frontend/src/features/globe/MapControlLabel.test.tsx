import { fireEvent, render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { expect, it } from 'vitest';
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
