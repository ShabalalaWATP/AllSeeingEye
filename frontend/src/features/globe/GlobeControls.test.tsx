import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { ControlPanel, GlobeControls } from './GlobeControls';

function Fixture({ action = () => undefined }: { action?: () => void }) {
  return (
    <GlobeControls layers={<button>Flight layer</button>}>
      <ControlPanel label="Map style" icon="layers">
        <button onClick={action}>Choose layer</button>
      </ControlPanel>
      <ControlPanel label="Measure" icon="measure">
        <button>Pick points</button>
      </ControlPanel>
    </GlobeControls>
  );
}
it('starts closed at every viewport and leaves only compact controls', () => {
  render(<Fixture />);
  expect(screen.getByRole('button', { name: 'Flight layer' })).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Choose layer' })).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Map style' })).toHaveAttribute(
    'aria-expanded',
    'false',
  );
});
it('opens one tool at a time, supports interaction and restores focus on Escape', async () => {
  const user = userEvent.setup();
  const action = vi.fn();
  render(<Fixture action={action} />);
  await user.click(screen.getByRole('button', { name: 'Map style' }));
  expect(screen.getByRole('button', { name: 'Close tool' })).toHaveFocus();
  await user.click(screen.getByRole('button', { name: 'Choose layer' }));
  expect(action).toHaveBeenCalledOnce();
  await user.click(screen.getByRole('button', { name: 'Measure' }));
  expect(screen.queryByRole('button', { name: 'Choose layer' })).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Pick points' })).toBeInTheDocument();
  await user.keyboard('{Escape}');
  expect(screen.queryByRole('button', { name: 'Pick points' })).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Measure' })).toHaveFocus();
});
it('closes through the explicit control or the same rail button', async () => {
  const user = userEvent.setup();
  render(<Fixture />);
  await user.click(screen.getByRole('button', { name: 'Map style' }));
  await user.click(screen.getByRole('button', { name: 'Close tool' }));
  expect(screen.getByRole('button', { name: 'Map style' })).toHaveFocus();
  await user.click(screen.getByRole('button', { name: 'Map style' }));
  await user.click(screen.getByRole('button', { name: 'Map style' }));
  expect(screen.queryByRole('button', { name: 'Choose layer' })).not.toBeInTheDocument();
});
