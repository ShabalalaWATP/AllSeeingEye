import { act, fireEvent, render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { MapControlLabel, TOOLTIP_CLOSE_DELAY_MS } from './MapControlLabel';

/** Real timers: Testing Library's async wrapper stalls under Vitest fake timers. */
const wait = (ms: number) => act(() => new Promise<void>((done) => setTimeout(done, ms)));

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
  await wait(TOOLTIP_CLOSE_DELAY_MS + 50);
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

describe('hoverable label (WCAG 1.4.13)', () => {
  function setup() {
    const user = userEvent.setup();
    render(
      <>
        <MapControlLabel label="Flights: shown">
          <button>Plane</button>
        </MapControlLabel>
        <button>Elsewhere</button>
      </>,
    );
    return { user, button: screen.getByRole('button', { name: 'Plane' }) };
  }

  it('stays open while the pointer moves from the rail button onto its label', async () => {
    const { user, button } = setup();
    await user.hover(button);
    await user.unhover(button);
    await user.hover(screen.getByRole('tooltip'));
    await wait(TOOLTIP_CLOSE_DELAY_MS * 2);
    expect(screen.getByRole('tooltip')).toHaveTextContent('Flights: shown');
    expect(screen.getByRole('tooltip')).not.toHaveStyle({ pointerEvents: 'none' });
  });

  it('closes after a short delay once the pointer has left both the button and the label', async () => {
    const { user, button } = setup();
    await user.hover(button);
    await user.unhover(button);
    await user.hover(screen.getByRole('tooltip'));
    await user.unhover(screen.getByRole('tooltip'));
    expect(screen.getByRole('tooltip')).toBeInTheDocument();
    await wait(TOOLTIP_CLOSE_DELAY_MS + 50);
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  });

  it('closes on Escape while the label itself is hovered', async () => {
    const { user, button } = setup();
    await user.hover(button);
    await user.unhover(button);
    await user.hover(screen.getByRole('tooltip'));
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
    await wait(TOOLTIP_CLOSE_DELAY_MS * 2);
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  });

  it('closes when focus moves away, even while the label is hovered', async () => {
    const { user } = setup();
    await user.tab();
    await user.hover(screen.getByRole('tooltip'));
    await user.tab();
    expect(screen.getByRole('button', { name: 'Elsewhere' })).toHaveFocus();
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  });
});
